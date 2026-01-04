"""
Universal Wishlist - Tiered Product Extraction with SAM3 Segmentation
1. Schema.org JSON-LD (best)
2. Open Graph meta tags (fallback)
3. Manual upload/edit (last resort)

Images are cached to Firebase (no hotlinking)
- image_original_url: Full retailer image with model (for VTO)
- image_url: SAM3 segmented garment only (for canvas)

Prices stored as snapshots with timestamp

NOW SAVES TO POSTGRESQL (favorites table) instead of returning data for Firestore
"""

from fastapi import APIRouter, HTTPException, Header, Depends
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
from sqlalchemy.orm import Session

# Database imports
from database import get_db, Favorite

# Auth - use existing auth service
from auth_service import get_current_user

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

# Note: SAM3 segmentation uses sam3_service.py (same as ItemSorter)


class WishlistAddRequest(BaseModel):
    """Request to save item to wishlist (after scraping or from product card)"""
    # Product info - from scrape response or product card
    title: Optional[str] = None
    price: Optional[str] = None  # String to handle currency symbols
    brand: Optional[str] = None
    retailer: Optional[str] = None
    
    # Images - from scrape response or product card
    image_url: Optional[str] = None  # Cutout/canvas image
    image_original_url: Optional[str] = None  # Original image (for VTO)
    
    # Source
    source_url: Optional[str] = None  # Product URL
    product_id: Optional[str] = None  # External product ID (for API products)


class WishlistAddResponse(BaseModel):
    success: bool
    id: Optional[int] = None  # Database ID
    image_url: Optional[str] = None  # Segmented cutout (for canvas)
    image_original_url: Optional[str] = None  # Original with model (for VTO)
    title: Optional[str] = None
    price: Optional[float] = None  # Changed to float
    currency: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    source_url: Optional[str] = None
    price_snapshot_date: Optional[str] = None
    extraction_method: Optional[str] = None  # schema_org, open_graph, heuristic, manual, api_product
    capture_method: Optional[str] = None  # url_scrape, manual_upload, product_card
    segmentation_method: Optional[str] = None  # sam3, rembg, none
    error: Optional[str] = None
    needs_user_input: bool = False


class WishlistItemResponse(BaseModel):
    """Response model for wishlist items"""
    id: int
    title: Optional[str]
    price: Optional[float]
    brand: Optional[str]
    retailer: Optional[str]
    image_url: Optional[str]  # Original image
    canvas_image_url: Optional[str]  # Segmented cutout
    product_url: Optional[str]
    created_at: str


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
# Import the working SAM3 service used by ItemSorter
from sam3_service import get_sam3_service

async def segment_with_sam3(image_bytes: bytes, text_prompt: str) -> Optional[bytes]:
    """Use SAM3 to segment garment from image using text prompt - uses same service as ItemSorter"""
    try:
        print(f"🎯 SAM3 segmenting with prompt: '{text_prompt}'")
        
        # Preprocess image - ensure RGB JPEG format for best SAM compatibility
        original_img = None
        try:
            img = Image.open(BytesIO(image_bytes))
            original_size = img.size
            print(f"📐 Image size: {original_size}, mode: {img.mode}")
            
            # Keep original for later use
            original_img = img.copy()
            
            # Convert to RGB (SAM struggles with RGBA, P, L modes)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                print(f"🔄 Converted to RGB")
            
            # Re-encode as JPEG for consistency
            output = BytesIO()
            img.save(output, format='JPEG', quality=95)
            image_bytes = output.getvalue()
            print(f"📦 Preprocessed image: {len(image_bytes)} bytes")
        except Exception as preprocess_error:
            print(f"⚠️ Preprocessing failed, using original: {preprocess_error}")
        
        # Use the same SAM3 service that works for ItemSorter
        sam3 = get_sam3_service()
        seg_result = await sam3.segment_item(image_bytes, text_prompt)
        
        if not seg_result.get("success"):
            print(f"❌ SAM3 failed: {seg_result.get('error', 'unknown error')}")
            return None
        
        result = seg_result.get("result", {})
        
        # Handle NEW response format (prompt_results with polygons)
        polygon = None
        if "prompt_results" in result:
            prompt_results = result.get("prompt_results", [])
            if prompt_results and len(prompt_results) > 0:
                predictions = prompt_results[0].get("predictions", [])
                if predictions and len(predictions) > 0:
                    masks = predictions[0].get("masks", [])
                    if masks and len(masks) > 0:
                        polygon = masks[0]  # Array of [x, y] points
                        print(f"✅ SAM3 found polygon with {len(polygon)} points")
        
        # Handle OLD response format (outputs with base64 mask) as fallback
        if polygon is None and "outputs" in result:
            outputs = result.get("outputs", [])
            if outputs and len(outputs) > 0:
                mask_data = outputs[0].get("mask")
                if mask_data:
                    print(f"📦 SAM3 using legacy mask format")
                    # Decode mask
                    mask_bytes = base64.b64decode(mask_data)
                    mask_img = Image.open(BytesIO(mask_bytes)).convert('L')
                    
                    # Load original image
                    if original_img is None:
                        original_img = Image.open(BytesIO(image_bytes))
                    original_rgba = original_img.convert('RGBA')
                    
                    # Resize mask to match original if needed
                    if mask_img.size != original_rgba.size:
                        mask_img = mask_img.resize(original_rgba.size, Image.LANCZOS)
                    
                    # Apply mask as alpha channel
                    mask_array = np.array(mask_img)
                    original_array = np.array(original_rgba)
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
                    
                    print(f"✅ SAM3 segmentation successful (legacy): {result_img.size}")
                    return output.getvalue()
        
        if polygon is None:
            print("❌ SAM3 returned no usable mask data")
            print(f"   Response keys: {list(result.keys())}")
            return None
        
        # Process polygon format - convert to mask and apply
        if original_img is None:
            original_img = Image.open(BytesIO(image_bytes))
        
        width, height = original_img.size
        original_rgba = original_img.convert('RGBA')
        
        # Create mask from polygon
        mask_img = Image.new('L', (width, height), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask_img)
        
        # Convert polygon points to tuples
        poly_points = [(int(p[0]), int(p[1])) for p in polygon]
        draw.polygon(poly_points, fill=255)
        
        # Apply mask as alpha channel
        mask_array = np.array(mask_img)
        original_array = np.array(original_rgba)
        original_array[:, :, 3] = mask_array
        
        # Find bounding box and crop
        coords = np.argwhere(mask_array > 128)
        if len(coords) == 0:
            print("❌ SAM3 polygon mask is empty")
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


# ============== SCRAPE ENDPOINT (preview only, no save) ==============

class ScrapeResponse(BaseModel):
    """Response from scraping - for preview before saving"""
    success: bool
    image_url: Optional[str] = None  # Segmented cutout
    image_original_url: Optional[str] = None  # Original image
    title: Optional[str] = None
    price: Optional[str] = None  # Keep as string for display
    currency: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    source_url: Optional[str] = None
    extraction_method: Optional[str] = None
    segmentation_method: Optional[str] = None
    error: Optional[str] = None


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_product_url(
    url: str,
    remove_bg: bool = True
):
    """
    Scrape product URL and return data for preview.
    Does NOT save to database - user can edit before saving.
    """
    try:
        print(f"🔍 Scraping URL: {url}")
        
        title = None
        price = None
        currency = None
        category = None
        brand = None
        retailer = get_retailer_from_url(url)
        image_url = None
        original_url = None
        cutout_url = None
        extraction_method = "manual"
        segmentation_method = "none"
        
        # Fetch page
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try extraction methods in order
        schema_data = extract_from_schema_org(soup)
        if schema_data.get('title') or schema_data.get('image'):
            extraction_method = "schema_org"
            title = schema_data.get('title')
            price = schema_data.get('price')
            currency = schema_data.get('currency')
            brand = schema_data.get('brand')
            category = schema_data.get('category')
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
            heuristic_data = extract_from_heuristics(soup, url)
            if heuristic_data:
                extraction_method = extraction_method if extraction_method != "manual" else "heuristic"
                title = title or heuristic_data.get('title')
                price = price or heuristic_data.get('price')
                image_url = image_url or heuristic_data.get('image')
                print(f"✅ Heuristic extraction: {title}")
        
        # Download and process image
        if image_url:
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                parsed = urlparse(url)
                image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
            
            print(f"📥 Downloading image: {image_url[:80]}...")
            image_bytes = download_image(image_url)
            
            if image_bytes:
                original_url = upload_to_firebase(image_bytes, "wishlist_originals")
                print(f"✅ Original uploaded: {original_url[:50]}...")
                
                if remove_bg:
                    sam_prompt = map_to_sam_prompt(
                        product_title=title,
                        category=category,
                        source_url=url
                    )
                    print(f"🎯 SAM prompt: '{sam_prompt}'")
                    
                    segmented = await segment_with_sam3(image_bytes, sam_prompt)
                    if segmented:
                        cutout_url = upload_to_firebase(segmented, "wishlist_cutouts")
                        segmentation_method = "sam3"
                        print(f"✅ SAM3 cutout: {cutout_url[:50]}...")
                    else:
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
        
        return ScrapeResponse(
            success=True,
            image_url=cutout_url,
            image_original_url=original_url,
            title=title,
            price=str(price) if price else None,
            currency=currency,
            category=category,
            brand=brand,
            retailer=retailer,
            source_url=url,
            extraction_method=extraction_method,
            segmentation_method=segmentation_method
        )
        
    except Exception as e:
        print(f"❌ Scrape error: {e}")
        import traceback
        traceback.print_exc()
        return ScrapeResponse(
            success=False,
            error=str(e)
        )


# ============== MAIN ENDPOINT ==============

@router.post("/add", response_model=WishlistAddResponse)
async def add_wishlist_item(
    request: WishlistAddRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Save item to wishlist. Two use cases:
    
    1. After scraping: Pass data from /scrape response (images already processed)
    2. Product card (heart icon): Pass product data, we'll process image for canvas
    
    All items saved to PostgreSQL favorites table.
    """
    # Auth check
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        print(f"💾 Saving wishlist item: {request.title}")
        
        # Use provided images directly (from /scrape or product card)
        original_url = request.image_original_url or request.image_url
        cutout_url = request.image_url
        
        # If we only have original image (product card), process for canvas
        if original_url and not request.image_url:
            print(f"🖼️ Processing image for canvas...")
            image_bytes = download_image(original_url)
            if image_bytes:
                sam_prompt = map_to_sam_prompt(
                    product_title=request.title,
                    category=None,
                    source_url=request.source_url
                )
                
                segmented = await segment_with_sam3(image_bytes, sam_prompt)
                if segmented:
                    cutout_url = upload_to_firebase(segmented, "wishlist_cutouts")
                    print(f"✅ SAM3 cutout created")
                else:
                    try:
                        pil_img = Image.open(BytesIO(image_bytes))
                        removed = remove(pil_img)
                        output = BytesIO()
                        removed.save(output, format='PNG')
                        cutout_url = upload_to_firebase(output.getvalue(), "wishlist_cutouts")
                        print(f"✅ Rembg cutout created")
                    except:
                        cutout_url = original_url
                        print(f"⚠️ Using original as cutout")
        
        # Convert price to float
        price_float = None
        if request.price:
            try:
                price_str = str(request.price).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                price_float = float(price_str)
            except:
                price_float = None
        
        # Create Favorite record
        favorite = Favorite(
            user_id=user.id,
            product_id=request.product_id,
            title=request.title,
            image_url=original_url,  # Original image (for VTO)
            canvas_image_url=cutout_url,  # Segmented cutout (for canvas)
            brand=request.brand,
            retailer=request.retailer,
            price=price_float,
            product_url=request.source_url,
            created_at=datetime.utcnow()
        )
        
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        
        print(f"✅ Saved to database: ID {favorite.id}")
        
        return WishlistAddResponse(
            success=True,
            id=favorite.id,
            image_url=cutout_url,
            image_original_url=original_url,
            title=request.title,
            price=price_float,
            brand=request.brand,
            retailer=request.retailer,
            source_url=request.source_url
        )
        
    except Exception as e:
        print(f"❌ Wishlist save error: {e}")
        import traceback
        traceback.print_exc()
        return WishlistAddResponse(
            success=False,
            error=str(e)
        )


# ============== GET WISHLIST ITEMS ==============

@router.get("/items", response_model=List[WishlistItemResponse])
async def get_wishlist_items(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get all wishlist items for the authenticated user"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    items = db.query(Favorite).filter(Favorite.user_id == user.id).order_by(Favorite.created_at.desc()).all()
    
    return [
        WishlistItemResponse(
            id=item.id,
            title=item.title,
            price=item.price,
            brand=item.brand,
            retailer=item.retailer,
            image_url=item.image_url,
            canvas_image_url=item.canvas_image_url,
            product_url=item.product_url,
            created_at=item.created_at.isoformat() if item.created_at else None
        )
        for item in items
    ]


# ============== DELETE WISHLIST ITEM ==============

@router.delete("/items/{item_id}")
async def delete_wishlist_item(
    item_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Remove item from wishlist"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    item = db.query(Favorite).filter(
        Favorite.id == item_id,
        Favorite.user_id == user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    
    return {"success": True, "message": "Item removed from wishlist"}


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "storage": "postgresql",
        "extraction_tiers": ["schema_org", "open_graph", "heuristic", "manual", "api_product"],
        "segmentation": ["sam3", "rembg_fallback"],
        "endpoints": [
            "POST /wishlist/scrape - Scrape URL for preview (no save)",
            "POST /wishlist/add - Save item to wishlist",
            "GET /wishlist/items - Get user's wishlist",
            "DELETE /wishlist/items/{id} - Remove item"
        ],
        "features": [
            "url_keyword_extraction",
            "image_caching",
            "sam3_garment_segmentation",
            "dual_image_storage",
            "price_snapshot",
            "direct_image_processing",
            "product_card_support",
            "postgresql_storage"
        ]
    }
