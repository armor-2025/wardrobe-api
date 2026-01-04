"""
Universal Wishlist - Tiered Product Extraction with SAM3 Segmentation
1. Schema.org JSON-LD (best)
2. Open Graph meta tags (fallback)
3. Manual upload/edit (last resort)

Images are cached to Firebase (no hotlinking)
- image_original_url: Full retailer image with model (for VTO)
- image_url: SAM3 segmented garment only (for canvas)

Prices stored as snapshots with timestamp
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
import json
import re
import base64
import os
from rembg import remove
from PIL import Image
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, storage
import uuid
from urllib.parse import urlparse
from datetime import datetime
import numpy as np
import cv2
import httpx

# Initialize Firebase if not already done
def init_firebase():
    """Initialize Firebase if not already done - uses FIREBASE_CREDENTIALS_JSON"""
    if not firebase_admin._apps:
        firebase_creds = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if firebase_creds:
            import json
            creds_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(creds_dict)
        else:
            cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'your-online-wardrobe-jm85cl.firebasestorage.app')
        })

init_firebase()

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# SAM3 API config
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY')
SAM3_API_URL = "https://serverless.roboflow.com/sam3/concept_segment"


class WishlistAddRequest(BaseModel):
    url: Optional[str] = None
    image_url: Optional[str] = None  # Direct image URL (for manual upload flow)
    image_base64: Optional[str] = None  # Manual image upload
    title: Optional[str] = None  # Manual override
    price: Optional[str] = None  # Manual override
    currency: Optional[str] = None
    category: Optional[str] = None
    user_id: str
    notes: Optional[str] = None
    remove_bg: bool = True  # Toggle background removal (now uses SAM3)


class WishlistAddResponse(BaseModel):
    success: bool
    image_url: Optional[str] = None  # Segmented cutout (for canvas)
    image_original_url: Optional[str] = None  # Original with model (for VTO)
    title: Optional[str] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    source_url: Optional[str] = None
    price_snapshot_date: Optional[str] = None
    extraction_method: Optional[str] = None  # schema_org, open_graph, heuristic, manual
    capture_method: Optional[str] = None  # url_scrape, manual_upload
    segmentation_method: Optional[str] = None  # sam3, rembg, none
    error: Optional[str] = None
    needs_user_input: bool = False


# ============== URL KEYWORD EXTRACTION ==============

def extract_keywords_from_url(url: str) -> Optional[str]:
    """Extract clothing keywords from URL path - most reliable source"""
    if not url:
        return None
        
    path = urlparse(url).path.lower()
    
    # Split path into segments and also check hyphenated words
    segments = []
    for segment in path.split('/'):
        segments.append(segment)
        # Also split by hyphens for URLs like /short-sleeved-maxi-dress-black/
        segments.extend(segment.split('-'))
    
    # Priority order matters - check more specific terms first
    keywords_map = [
        # Dresses & full-body (check first - "dress" could be in path with other words)
        (['dress', 'dresses', 'gown', 'maxi', 'midi'], 'dress'),
        (['jumpsuit', 'jumpsuits', 'romper', 'playsuit'], 'dress'),
        
        # Outerwear
        (['jacket', 'jackets', 'blazer', 'blazers'], 'jacket'),
        (['coat', 'coats', 'overcoat', 'trench'], 'jacket'),
        (['cardigan', 'cardigans', 'gilet'], 'jacket'),
        
        # Bottoms
        (['jean', 'jeans', 'denim'], 'bottoms'),
        (['trouser', 'trousers', 'pant', 'pants', 'chino', 'chinos'], 'bottoms'),
        (['short', 'shorts'], 'bottoms'),
        (['skirt', 'skirts'], 'bottoms'),
        (['legging', 'leggings'], 'bottoms'),
        
        # Tops
        (['shirt', 'shirts', 'blouse', 'blouses'], 'top'),
        (['top', 'tops', 'tee', 'tshirt', 't-shirt'], 'top'),
        (['sweater', 'sweaters', 'jumper', 'jumpers', 'knit', 'knitwear'], 'top'),
        (['hoodie', 'hoodies', 'sweatshirt', 'sweatshirts'], 'top'),
        (['polo', 'polos', 'vest', 'vests', 'tank'], 'top'),
        
        # Footwear
        (['shoe', 'shoes', 'footwear'], 'shoes'),
        (['sneaker', 'sneakers', 'trainer', 'trainers'], 'shoes'),
        (['boot', 'boots', 'bootie', 'booties'], 'shoes'),
        (['heel', 'heels', 'pump', 'pumps', 'sandal', 'sandals'], 'shoes'),
        (['loafer', 'loafers', 'moccasin', 'flat', 'flats'], 'shoes'),
        
        # Accessories
        (['bag', 'bags', 'handbag', 'purse', 'tote', 'clutch'], 'bag'),
        (['hat', 'hats', 'cap', 'caps', 'beanie', 'beret'], 'hat'),
    ]
    
    for keywords, sam_prompt in keywords_map:
        for keyword in keywords:
            for segment in segments:
                if keyword in segment:
                    print(f"🔍 URL keyword match: '{keyword}' → SAM prompt: '{sam_prompt}'")
                    return sam_prompt
    
    return None


def map_to_sam_prompt(product_title: str = None, category: str = None, source_url: str = None) -> str:
    """Map product info to SAM text prompt - checks URL first, then title/category"""
    
    # Try URL first (most reliable - structured data)
    if source_url:
        url_keyword = extract_keywords_from_url(source_url)
        if url_keyword:
            return url_keyword
    
    # Fall back to title/category text matching
    text = (product_title or category or "").lower()
    
    if any(word in text for word in ['dress', 'gown', 'maxi', 'midi', 'jumpsuit', 'romper', 'playsuit']):
        return 'dress'
    elif any(word in text for word in ['jacket', 'coat', 'blazer', 'cardigan', 'gilet', 'parka', 'puffer']):
        return 'jacket'
    elif any(word in text for word in ['jean', 'trouser', 'pant', 'short', 'skirt', 'chino', 'legging']):
        return 'bottoms'
    elif any(word in text for word in ['shirt', 'top', 'blouse', 'sweater', 'hoodie', 't-shirt', 'jumper', 'knit', 'polo', 'vest', 'sweatshirt']):
        return 'top'
    elif any(word in text for word in ['shoe', 'sneaker', 'boot', 'heel', 'loafer', 'trainer', 'sandal', 'pump', 'flat']):
        return 'shoes'
    elif any(word in text for word in ['hat', 'cap', 'beanie', 'beret']):
        return 'hat'
    elif any(word in text for word in ['bag', 'purse', 'handbag', 'tote', 'clutch']):
        return 'bag'
    else:
        return 'garment'


# ============== SAM3 SEGMENTATION ==============

async def segment_with_sam3(image_bytes: bytes, text_prompt: str) -> Optional[bytes]:
    """Use SAM3 API to segment garment from image using text prompt"""
    if not ROBOFLOW_API_KEY:
        print("⚠️ ROBOFLOW_API_KEY not set, skipping SAM3")
        return None
    
    try:
        print(f"🎯 SAM3 segmenting with prompt: '{text_prompt}'")
        
        # Convert to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SAM3_API_URL,
                params={"api_key": ROBOFLOW_API_KEY},
                json={
                    "image": {"type": "base64", "value": image_b64},
                    "prompts": [text_prompt]
                }
            )
        
        if response.status_code != 200:
            print(f"❌ SAM3 API error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        
        # Get mask from response
        if not result.get('outputs') or not result['outputs']:
            print("❌ SAM3 returned no outputs")
            return None
        
        mask_data = result['outputs'][0].get('mask')
        if not mask_data:
            print("❌ SAM3 returned no mask")
            return None
        
        # Decode mask
        mask_bytes = base64.b64decode(mask_data)
        mask_img = Image.open(BytesIO(mask_bytes)).convert('L')
        
        # Load original image
        original_img = Image.open(BytesIO(image_bytes)).convert('RGBA')
        
        # Resize mask to match original if needed
        if mask_img.size != original_img.size:
            mask_img = mask_img.resize(original_img.size, Image.LANCZOS)
        
        # Apply mask as alpha channel
        mask_array = np.array(mask_img)
        original_array = np.array(original_img)
        original_array[:, :, 3] = mask_array
        
        # Find bounding box and crop
        coords = np.argwhere(mask_array > 128)
        if len(coords) == 0:
            print("❌ SAM3 mask is empty")
            return None
        
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0)
        
        # Add small padding
        padding = 10
        y0 = max(0, y0 - padding)
        x0 = max(0, x0 - padding)
        y1 = min(original_array.shape[0], y1 + padding)
        x1 = min(original_array.shape[1], x1 + padding)
        
        cropped = original_array[y0:y1, x0:x1]
        result_img = Image.fromarray(cropped)
        
        # Save to bytes
        output = BytesIO()
        result_img.save(output, format='PNG')
        output.seek(0)
        
        print(f"✅ SAM3 segmentation successful: {result_img.size}")
        return output.getvalue()
        
    except Exception as e:
        print(f"❌ SAM3 error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============== FIREBASE UPLOAD ==============

def upload_to_firebase(image_bytes: bytes, folder: str = "wishlist") -> str:
    """Upload image bytes to Firebase Storage and return public URL"""
    bucket = storage.bucket()
    filename = f"{folder}/{uuid.uuid4()}.png"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type='image/png')
    blob.make_public()
    return blob.public_url


def download_image(url: str) -> Optional[bytes]:
    """Download image from URL, return bytes"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.content
        print(f"❌ Failed to download image: {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Image download error: {e}")
        return None


# ============== EXTRACTION METHODS ==============

def extract_from_schema_org(soup: BeautifulSoup) -> dict:
    """Extract product data from Schema.org JSON-LD"""
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
            # Handle @graph arrays
            if isinstance(data, dict) and '@graph' in data:
                data = data['@graph']
            
            # Find Product schema
            products = []
            if isinstance(data, list):
                products = [item for item in data if item.get('@type') == 'Product']
            elif isinstance(data, dict) and data.get('@type') == 'Product':
                products = [data]
            
            for product in products:
                result = {}
                result['title'] = product.get('name')
                result['brand'] = product.get('brand', {}).get('name') if isinstance(product.get('brand'), dict) else product.get('brand')
                result['category'] = product.get('category')
                
                # Get image
                image = product.get('image')
                if isinstance(image, list):
                    result['image'] = image[0] if image else None
                elif isinstance(image, dict):
                    result['image'] = image.get('url')
                else:
                    result['image'] = image
                
                # Get price from offers
                offers = product.get('offers')
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if isinstance(offers, dict):
                    result['price'] = offers.get('price')
                    result['currency'] = offers.get('priceCurrency')
                
                if result.get('title') or result.get('image'):
                    return result
                    
        except (json.JSONDecodeError, AttributeError):
            continue
    
    return {}


def extract_from_open_graph(soup: BeautifulSoup) -> dict:
    """Extract product data from Open Graph meta tags"""
    result = {}
    
    og_title = soup.find('meta', property='og:title')
    if og_title:
        result['title'] = og_title.get('content')
    
    og_image = soup.find('meta', property='og:image')
    if og_image:
        result['image'] = og_image.get('content')
    
    # Try product-specific OG tags
    og_price = soup.find('meta', property='product:price:amount') or soup.find('meta', property='og:price:amount')
    if og_price:
        result['price'] = og_price.get('content')
    
    og_currency = soup.find('meta', property='product:price:currency') or soup.find('meta', property='og:price:currency')
    if og_currency:
        result['currency'] = og_currency.get('content')
    
    og_brand = soup.find('meta', property='product:brand') or soup.find('meta', property='og:brand')
    if og_brand:
        result['brand'] = og_brand.get('content')
    
    return result


def extract_from_heuristics(soup: BeautifulSoup, url: str) -> dict:
    """Fallback heuristic extraction"""
    result = {}
    
    # Try common price patterns
    price_patterns = [
        r'[\$£€]\s*[\d,]+\.?\d*',
        r'[\d,]+\.?\d*\s*(?:USD|EUR|GBP|SEK|NOK|DKK)',
    ]
    
    page_text = soup.get_text()
    for pattern in price_patterns:
        match = re.search(pattern, page_text)
        if match:
            result['price'] = match.group().strip()
            break
    
    # Try to get title from h1
    h1 = soup.find('h1')
    if h1:
        result['title'] = h1.get_text().strip()
    
    # Try to find main product image
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and any(keyword in src.lower() for keyword in ['product', 'main', 'hero', 'large']):
            result['image'] = src
            break
    
    return result


def get_retailer_from_url(url: str) -> str:
    """Extract retailer name from URL"""
    domain = urlparse(url).netloc.lower()
    domain = domain.replace('www.', '')
    
    # Map common domains to brand names
    retailer_map = {
        'asos.com': 'ASOS',
        'zara.com': 'Zara',
        'hm.com': 'H&M',
        'uniqlo.com': 'UNIQLO',
        'cos.com': 'COS',
        'arket.com': 'ARKET',
        'weekday.com': 'Weekday',
        'ronningstore.com': 'RonningStore',
        'net-a-porter.com': 'Net-A-Porter',
        'mrporter.com': 'Mr Porter',
        'ssense.com': 'SSENSE',
        'farfetch.com': 'Farfetch',
        'nordstrom.com': 'Nordstrom',
        'mytheresa.com': 'Mytheresa',
        'matchesfashion.com': 'Matches',
        'endclothing.com': 'END.',
    }
    
    for key, value in retailer_map.items():
        if key in domain:
            return value
    
    # Default: capitalize domain name
    return domain.split('.')[0].capitalize()


# ============== MAIN ENDPOINT ==============

@router.post("/add", response_model=WishlistAddResponse)
async def add_wishlist_item(request: WishlistAddRequest):
    """
    Add item to wishlist with tiered extraction:
    1. Schema.org JSON-LD (best)
    2. Open Graph meta tags
    3. Heuristic extraction
    4. Manual upload fallback
    
    Supports:
    - URL only: auto-extract image/title/price
    - Direct image URL: process existing Firebase image
    - Image base64: manual upload
    """
    try:
        title = request.title
        price = request.price
        currency = request.currency
        category = request.category
        brand = None
        retailer = None
        source_url = request.url
        image_url = None
        image_bytes = None
        extraction_method = "manual"
        capture_method = "manual_upload"
        segmentation_method = "none"
        
        # ===== PATH 1: Direct image URL (from Upload Screenshot) =====
        if request.image_url:
            print(f"📸 Processing direct image URL: {request.image_url[:50]}...")
            capture_method = "direct_image"
            
            # Download image from Firebase URL
            image_bytes = download_image(request.image_url)
            
            if image_bytes and request.remove_bg:
                # Get SAM prompt from URL or use generic
                sam_prompt = map_to_sam_prompt(
                    product_title=title,
                    category=category,
                    source_url=source_url
                )
                
                # Try SAM3 segmentation
                segmented = await segment_with_sam3(image_bytes, sam_prompt)
                if segmented:
                    cutout_url = upload_to_firebase(segmented, "wishlist_cutouts")
                    segmentation_method = "sam3"
                else:
                    # Fallback to rembg
                    try:
                        pil_img = Image.open(BytesIO(image_bytes))
                        removed = remove(pil_img)
                        output = BytesIO()
                        removed.save(output, format='PNG')
                        cutout_url = upload_to_firebase(output.getvalue(), "wishlist_cutouts")
                        segmentation_method = "rembg"
                    except:
                        cutout_url = request.image_url
                        segmentation_method = "none"
            else:
                cutout_url = request.image_url
            
            return WishlistAddResponse(
                success=True,
                image_url=cutout_url,
                image_original_url=request.image_url,
                title=title,
                price=price,
                currency=currency,
                category=category,
                brand=brand,
                retailer=retailer or "Manual Upload",
                source_url=source_url,
                price_snapshot_date=datetime.utcnow().isoformat(),
                extraction_method=extraction_method,
                capture_method=capture_method,
                segmentation_method=segmentation_method
            )
        
        # ===== PATH 2: URL scraping =====
        if request.url:
            print(f"🔍 Scraping URL: {request.url}")
            capture_method = "url_scrape"
            source_url = request.url
            retailer = get_retailer_from_url(request.url)
            
            # Fetch page
            response = requests.get(request.url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try extraction methods in order
            schema_data = extract_from_schema_org(soup)
            if schema_data.get('title') or schema_data.get('image'):
                extraction_method = "schema_org"
                title = title or schema_data.get('title')
                price = price or schema_data.get('price')
                currency = currency or schema_data.get('currency')
                brand = schema_data.get('brand')
                category = category or schema_data.get('category')
                image_url = schema_data.get('image')
                print(f"✅ Schema.org extraction: {title}")
            
            if not (title and image_url):
                og_data = extract_from_open_graph(soup)
                if og_data.get('title') or og_data.get('image'):
                    extraction_method = extraction_method if extraction_method != "manual" else "open_graph"
                    title = title or og_data.get('title')
                    price = price or og_data.get('price')
                    currency = currency or og_data.get('currency')
                    brand = brand or og_data.get('brand')
                    image_url = image_url or og_data.get('image')
                    print(f"✅ Open Graph extraction: {title}")
            
            if not (title and image_url):
                heuristic_data = extract_from_heuristics(soup, request.url)
                if heuristic_data:
                    extraction_method = extraction_method if extraction_method != "manual" else "heuristic"
                    title = title or heuristic_data.get('title')
                    price = price or heuristic_data.get('price')
                    image_url = image_url or heuristic_data.get('image')
                    print(f"✅ Heuristic extraction: {title}")
            
            # Download and process image
            if image_url:
                # Make URL absolute if needed
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    parsed = urlparse(request.url)
                    image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
                
                print(f"📥 Downloading image: {image_url[:80]}...")
                image_bytes = download_image(image_url)
        
        # ===== PATH 3: Base64 image upload =====
        elif request.image_base64:
            print("📸 Processing base64 image upload")
            capture_method = "manual_upload"
            image_bytes = base64.b64decode(request.image_base64)
        
        # ===== Process image =====
        if image_bytes:
            # Upload original to Firebase first
            original_url = upload_to_firebase(image_bytes, "wishlist_originals")
            print(f"✅ Original uploaded: {original_url[:50]}...")
            
            if request.remove_bg:
                # Get SAM prompt from URL keywords, title, or category
                sam_prompt = map_to_sam_prompt(
                    product_title=title,
                    category=category,
                    source_url=source_url
                )
                print(f"🎯 SAM prompt: '{sam_prompt}' (from URL/title analysis)")
                
                # Try SAM3 first
                segmented = await segment_with_sam3(image_bytes, sam_prompt)
                
                if segmented:
                    cutout_url = upload_to_firebase(segmented, "wishlist_cutouts")
                    segmentation_method = "sam3"
                    print(f"✅ SAM3 cutout: {cutout_url[:50]}...")
                else:
                    # Fallback to rembg
                    print("⚠️ SAM3 failed, trying rembg...")
                    try:
                        pil_img = Image.open(BytesIO(image_bytes))
                        removed = remove(pil_img)
                        output = BytesIO()
                        removed.save(output, format='PNG')
                        cutout_url = upload_to_firebase(output.getvalue(), "wishlist_cutouts")
                        segmentation_method = "rembg"
                        print(f"✅ Rembg cutout: {cutout_url[:50]}...")
                    except Exception as e:
                        print(f"❌ Rembg also failed: {e}")
                        cutout_url = original_url
                        segmentation_method = "none"
            else:
                cutout_url = original_url
                segmentation_method = "none"
        else:
            # No image available
            original_url = None
            cutout_url = None
        
        # Build response
        return WishlistAddResponse(
            success=True,
            image_url=cutout_url,
            image_original_url=original_url,
            title=title,
            price=str(price) if price else None,
            currency=currency,
            category=category,
            brand=brand,
            retailer=retailer,
            source_url=source_url,
            price_snapshot_date=datetime.utcnow().isoformat(),
            extraction_method=extraction_method,
            capture_method=capture_method,
            segmentation_method=segmentation_method,
            needs_user_input=not (title and cutout_url)
        )
        
    except Exception as e:
        print(f"❌ Wishlist error: {e}")
        import traceback
        traceback.print_exc()
        return WishlistAddResponse(
            success=False,
            error=str(e),
            needs_user_input=True
        )


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "extraction_tiers": ["schema_org", "open_graph", "heuristic", "manual"],
        "segmentation": ["sam3", "rembg_fallback"],
        "features": [
            "url_keyword_extraction",
            "image_caching",
            "sam3_garment_segmentation",
            "dual_image_storage",
            "price_snapshot",
            "direct_image_processing",
            "partial_data_on_failure"
        ]
    }
