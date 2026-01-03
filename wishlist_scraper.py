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
    image_url: Optional[str] = None  # SAM3 segmented garment (for canvas)
    image_original_url: Optional[str] = None  # Original image with model (for VTO)
    title: Optional[str] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    retailer: Optional[str] = None
    source_url: Optional[str] = None
    category: Optional[str] = None
    price_snapshot_date: Optional[str] = None
    extraction_method: Optional[str] = None  # schema_org, open_graph, heuristic, manual
    capture_method: Optional[str] = None  # url, upload, url+upload
    segmentation_method: Optional[str] = None  # sam3, rembg, none
    needs_user_input: bool = False  # True if extraction failed - return partial data for editing
    error: Optional[str] = None


def map_to_sam_prompt(product_title: str, category: str = None) -> str:
    """
    Map product info to SAM3 text prompt
    Uses simple category words that SAM3 understands well
    """
    text = (product_title or "").lower() + " " + (category or "").lower()
    
    # Check for specific garment types
    if any(word in text for word in ['jean', 'trouser', 'pant', 'short', 'skirt', 'chino', 'jogger', 'legging']):
        return 'bottoms'
    elif any(word in text for word in ['dress', 'jumpsuit', 'romper', 'playsuit']):
        return 'dress'
    elif any(word in text for word in ['jacket', 'coat', 'blazer', 'cardigan', 'gilet', 'vest', 'parka', 'bomber']):
        return 'jacket'
    elif any(word in text for word in ['shirt', 'blouse', 'polo']):
        return 'shirt'
    elif any(word in text for word in ['sweater', 'hoodie', 'jumper', 'knit', 'sweatshirt', 'pullover', 'fleece']):
        return 'sweater'
    elif any(word in text for word in ['t-shirt', 'tee', 'top', 'tank', 'cami', 'vest']):
        return 'top'
    elif any(word in text for word in ['shoe', 'sneaker', 'boot', 'heel', 'loafer', 'trainer', 'sandal', 'pump']):
        return 'shoes'
    elif any(word in text for word in ['hat', 'cap', 'beanie', 'beret']):
        return 'hat'
    elif any(word in text for word in ['bag', 'purse', 'handbag', 'tote', 'clutch', 'backpack']):
        return 'bag'
    elif any(word in text for word in ['scarf', 'tie', 'belt', 'glove']):
        return 'accessory'
    elif any(word in text for word in ['sunglasses', 'glasses', 'eyewear']):
        return 'sunglasses'
    elif any(word in text for word in ['watch', 'bracelet', 'necklace', 'ring', 'earring', 'jewel']):
        return 'jewelry'
    else:
        # Default - try to segment any garment
        return 'garment'


async def segment_with_sam3(image_bytes: bytes, text_prompt: str) -> Optional[bytes]:
    """
    Use SAM3 to segment a specific item from an image using text prompt
    Returns the segmented image as PNG bytes, or None if failed
    """
    if not ROBOFLOW_API_KEY:
        print("  ⚠️ No ROBOFLOW_API_KEY - skipping SAM3 segmentation")
        return None
    
    try:
        print(f"  🎯 SAM3 segmenting: '{text_prompt}'")
        
        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "image": {
                "type": "base64",
                "value": image_b64
            },
            "prompts": [
                {"type": "text", "text": text_prompt}
            ]
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SAM3_API_URL}?api_key={ROBOFLOW_API_KEY}",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
        
        # Parse SAM3 response - get the mask
        if not result.get('outputs') or len(result['outputs']) == 0:
            print("  ⚠️ SAM3 returned no outputs")
            return None
        
        # Get the first output (best match)
        output = result['outputs'][0]
        
        # Check if we have mask data
        if 'mask' not in output:
            print("  ⚠️ SAM3 output has no mask")
            return None
        
        # Decode the mask
        mask_b64 = output['mask']
        mask_bytes = base64.b64decode(mask_b64)
        
        # Load original image and mask
        original = Image.open(BytesIO(image_bytes)).convert('RGBA')
        mask = Image.open(BytesIO(mask_bytes)).convert('L')
        
        # Resize mask to match original if needed
        if mask.size != original.size:
            mask = mask.resize(original.size, Image.LANCZOS)
        
        # Apply mask as alpha channel
        original.putalpha(mask)
        
        # Crop to bounding box (remove transparent edges)
        bbox = original.getbbox()
        if bbox:
            original = original.crop(bbox)
        
        # Save as PNG
        buffer = BytesIO()
        original.save(buffer, format='PNG', optimize=True)
        
        print(f"  ✅ SAM3 segmentation complete")
        return buffer.getvalue()
        
    except Exception as e:
        print(f"  ❌ SAM3 error: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_schema_org(soup: BeautifulSoup) -> dict:
    """
    TIER 1: Extract from schema.org JSON-LD Product data
    Most reliable when present
    """
    result = {"success": False}
    
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
            if isinstance(data, dict) and '@graph' in data:
                data = data['@graph']
            
            if isinstance(data, dict):
                data = [data]
            
            for item in data:
                if isinstance(item, dict) and item.get('@type') in ['Product', 'ClothingStore', 'IndividualProduct']:
                    result["success"] = True
                    result["title"] = item.get('name')
                    result["brand"] = item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand')
                    result["description"] = item.get('description')
                    
                    img = item.get('image')
                    if isinstance(img, list):
                        result["image_url"] = img[0] if img else None
                    elif isinstance(img, dict):
                        result["image_url"] = img.get('url')
                    else:
                        result["image_url"] = img
                    
                    offers = item.get('offers', {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    
                    result["price"] = offers.get('price')
                    result["currency"] = offers.get('priceCurrency')
                    result["availability"] = offers.get('availability')
                    
                    # Try to extract category
                    result["category"] = item.get('category')
                    
                    return result
                    
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    
    return result


def extract_open_graph(soup: BeautifulSoup) -> dict:
    """
    TIER 2: Extract from Open Graph and meta tags
    """
    result = {"success": False}
    
    og_image = soup.find('meta', property='og:image')
    og_title = soup.find('meta', property='og:title')
    og_site = soup.find('meta', property='og:site_name')
    og_price = soup.find('meta', property='product:price:amount')
    og_currency = soup.find('meta', property='product:price:currency')
    og_category = soup.find('meta', property='product:category')
    
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    
    meta_title = soup.find('title')
    
    image_url = None
    if og_image and og_image.get('content'):
        image_url = og_image['content']
    elif twitter_image and twitter_image.get('content'):
        image_url = twitter_image['content']
    
    title = None
    if og_title and og_title.get('content'):
        title = og_title['content']
    elif twitter_title and twitter_title.get('content'):
        title = twitter_title['content']
    elif meta_title:
        title = meta_title.string
    
    if image_url or title:
        result["success"] = True
        result["image_url"] = image_url
        result["title"] = title
        result["retailer"] = og_site['content'] if og_site and og_site.get('content') else None
        result["price"] = og_price['content'] if og_price and og_price.get('content') else None
        result["currency"] = og_currency['content'] if og_currency and og_currency.get('content') else None
        result["category"] = og_category['content'] if og_category and og_category.get('content') else None
    
    return result


def extract_heuristic(soup: BeautifulSoup, base_url: str) -> dict:
    """
    TIER 3: Heuristic extraction - look for common patterns
    """
    result = {"success": False}
    
    image_url = None
    
    selectors = [
        ('img', {'class': re.compile(r'product.*image|main.*image|hero.*image', re.I)}),
        ('img', {'id': re.compile(r'product.*image|main.*image', re.I)}),
        ('img', {'data-testid': re.compile(r'product', re.I)}),
    ]
    
    for tag, attrs in selectors:
        img = soup.find(tag, attrs)
        if img:
            image_url = img.get('src') or img.get('data-src')
            if image_url:
                break
    
    if not image_url:
        product_area = soup.find(['main', 'article', 'div'], class_=re.compile(r'product|pdp', re.I))
        if product_area:
            imgs = product_area.find_all('img')
            for img in imgs:
                src = img.get('src') or img.get('data-src')
                if src and not any(x in src.lower() for x in ['icon', 'logo', 'badge', 'rating']):
                    image_url = src
                    break
    
    price = None
    price_patterns = [
        soup.find(class_=re.compile(r'price|cost', re.I)),
        soup.find(attrs={'data-price': True}),
        soup.find(string=re.compile(r'[£$€]\s*[\d,]+\.?\d*'))
    ]
    
    for p in price_patterns:
        if p:
            if hasattr(p, 'get_text'):
                price_text = p.get_text(strip=True)
            else:
                price_text = str(p)
            match = re.search(r'([£$€])\s*([\d,]+\.?\d*)', price_text)
            if match:
                result["currency"] = {"£": "GBP", "$": "USD", "€": "EUR"}.get(match.group(1), match.group(1))
                result["price"] = match.group(2).replace(',', '')
                break
    
    if image_url:
        result["success"] = True
        result["image_url"] = image_url
    
    return result


def download_image(url: str, base_url: str = None) -> bytes:
    """Download image, handling relative URLs"""
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/') and base_url:
        parsed = urlparse(base_url)
        url = f"{parsed.scheme}://{parsed.netloc}{url}"
    
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.content


def remove_background_rembg(image_bytes: bytes) -> bytes:
    """Fallback: Remove background using rembg (simple removal, keeps model)"""
    output = remove(image_bytes)
    
    img = Image.open(BytesIO(output))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def save_original(image_bytes: bytes) -> bytes:
    """Save original image as PNG without bg removal"""
    img = Image.open(BytesIO(image_bytes))
    if img.mode == 'RGBA':
        pass
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def upload_to_firebase(image_bytes: bytes, user_id: str, subfolder: str = "") -> str:
    """Cache image to Firebase Storage"""
    bucket = storage.bucket()
    folder = f"wishlist/{user_id}"
    if subfolder:
        folder = f"{folder}/{subfolder}"
    filename = f"{folder}/{uuid.uuid4()}.png"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type='image/png')
    blob.make_public()
    return blob.public_url


def get_retailer_from_url(url: str) -> str:
    """Extract retailer name from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    domain = re.sub(r'^www\.', '', domain)
    domain = re.sub(r'\.(com|co\.uk|net|org)$', '', domain)
    return domain.title()


@router.post("/add", response_model=WishlistAddResponse)
async def add_wishlist_item(request: WishlistAddRequest):
    """
    Add item to wishlist with tiered extraction:
    1. Schema.org JSON-LD (best)
    2. Open Graph meta tags
    3. Heuristic extraction
    4. Manual upload fallback
    
    Images processed with:
    - SAM3 text-prompted segmentation (extracts garment only)
    - Fallback to rembg if SAM3 fails
    
    Two images saved:
    - image_original_url: Full image with model (for VTO)
    - image_url: Segmented garment only (for canvas)
    """
    try:
        # Handle FlutterFlow sending "null" string instead of actual null
        if request.url and str(request.url).lower() == "null":
            request.url = None
            source_url = None
        if request.image_base64 and str(request.image_base64).lower() == "null":
            request.image_base64 = None
        if request.title and str(request.title).lower() == "null":
            request.title = None
            title = None
        if request.price and str(request.price).lower() == "null":
            request.price = None
            price = None
            
        image_bytes = None
        title = request.title if request.title else None
        price = request.price if request.price else None
        currency = request.currency
        category = request.category
        brand = None
        retailer = None
        extraction_method = None
        capture_method = None
        segmentation_method = None
        source_url = request.url
        
        # Determine capture method
        has_url = request.url is not None and len(request.url) > 0
        has_image = request.image_base64 is not None and len(request.image_base64) > 0
        
        if has_url and has_image:
            capture_method = "url+upload"
        elif has_url:
            capture_method = "url"
        elif has_image:
            capture_method = "upload"
        
        # Get retailer from URL if provided
        if has_url:
            retailer = get_retailer_from_url(request.url)
        
        # MODE 1: User uploaded an image (takes priority)
        if has_image:
            print(f"📸 Manual upload for user {request.user_id}")
            image_bytes = base64.b64decode(request.image_base64)
            extraction_method = "manual_upload"
            
            # If URL also provided, try to extract metadata only (not image)
            if has_url:
                try:
                    response = requests.get(request.url, headers=HEADERS, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Try Schema.org for metadata
                        result = extract_schema_org(soup)
                        if result["success"]:
                            if not title:
                                title = result.get("title")
                            if not price:
                                price = result.get("price")
                            if not currency:
                                currency = result.get("currency")
                            if not category:
                                category = result.get("category")
                            brand = result.get("brand")
                        else:
                            # Try OG
                            result = extract_open_graph(soup)
                            if result["success"]:
                                if not title:
                                    title = result.get("title")
                                if not price:
                                    price = result.get("price")
                                if not currency:
                                    currency = result.get("currency")
                except Exception as e:
                    print(f"  ⚠️ Couldn't fetch metadata from URL: {e}")
        
        # MODE 2: URL only - extract everything
        elif has_url:
            print(f"🔗 Auto-extract from: {request.url}")
            
            try:
                response = requests.get(request.url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                print(f"❌ Failed to fetch page: {e}")
                return WishlistAddResponse(
                    success=False,
                    needs_user_input=True,
                    error="Couldn't access this page. Try uploading a screenshot instead.",
                    source_url=source_url,
                    retailer=retailer,
                    capture_method=capture_method
                )
            
            extracted_image_url = None
            
            # TIER 1: Schema.org
            print("  → Trying Schema.org JSON-LD...")
            result = extract_schema_org(soup)
            if result["success"]:
                print(f"  ✅ Schema.org: {result.get('title', '')[:50]}")
                extraction_method = "schema_org"
                extracted_image_url = result.get("image_url")
                if not title:
                    title = result.get("title")
                if not price:
                    price = result.get("price")
                if not currency:
                    currency = result.get("currency")
                if not category:
                    category = result.get("category")
                brand = result.get("brand")
            
            # TIER 2: Open Graph
            if not extracted_image_url:
                print("  → Trying Open Graph...")
                result = extract_open_graph(soup)
                if result["success"]:
                    print(f"  ✅ Open Graph: {result.get('title', '')[:50]}")
                    extraction_method = "open_graph"
                    extracted_image_url = result.get("image_url")
                    if not title:
                        title = result.get("title")
                    if not price:
                        price = result.get("price")
                    if not currency:
                        currency = result.get("currency")
                    if not category:
                        category = result.get("category")
                    if result.get("retailer"):
                        retailer = result.get("retailer")
            
            # TIER 3: Heuristic
            if not extracted_image_url:
                print("  → Trying heuristic...")
                result = extract_heuristic(soup, request.url)
                if result["success"]:
                    print(f"  ✅ Heuristic found image")
                    extraction_method = "heuristic"
                    extracted_image_url = result.get("image_url")
                    if not price:
                        price = result.get("price")
                    if not currency:
                        currency = result.get("currency")
            
            # Download the extracted image
            if extracted_image_url:
                try:
                    print(f"  📥 Downloading: {extracted_image_url[:60]}...")
                    image_bytes = download_image(extracted_image_url, request.url)
                except Exception as e:
                    print(f"  ❌ Download failed: {e}")
                    # Return partial data so user can still add manually
                    return WishlistAddResponse(
                        success=False,
                        needs_user_input=True,
                        title=title,
                        price=str(price) if price else None,
                        currency=currency,
                        category=category,
                        brand=brand,
                        retailer=retailer,
                        source_url=source_url,
                        error="Found image but couldn't download. Upload a screenshot instead.",
                        extraction_method=extraction_method,
                        capture_method=capture_method
                    )
            else:
                print("  ❌ No image found")
                # Return partial data
                return WishlistAddResponse(
                    success=False,
                    needs_user_input=True,
                    title=title,
                    price=str(price) if price else None,
                    currency=currency,
                    category=category,
                    brand=brand,
                    retailer=retailer,
                    source_url=source_url,
                    error="Couldn't find product image. Please upload a screenshot.",
                    extraction_method="none",
                    capture_method=capture_method
                )
        
        else:
            return WishlistAddResponse(
                success=False,
                error="Please provide a URL or upload an image"
            )
        
        # ==========================================
        # PROCESS IMAGE: Save original + Segment garment
        # ==========================================
        
        # Step 1: Save original to Firebase (for VTO - keeps model)
        print("☁️ Caching original to Firebase...")
        original_png = save_original(image_bytes)
        original_url = upload_to_firebase(original_png, request.user_id, "original")
        
        # Step 2: Segment garment (for canvas - garment only)
        cutout_url = original_url  # Default to original if segmentation disabled/fails
        
        if request.remove_bg:
            # Determine SAM3 prompt from product title/category
            sam_prompt = map_to_sam_prompt(title, category)
            print(f"🎯 Segmenting with SAM3 prompt: '{sam_prompt}'")
            
            # Try SAM3 first
            segmented_image = await segment_with_sam3(image_bytes, sam_prompt)
            
            if segmented_image:
                segmentation_method = "sam3"
                cutout_url = upload_to_firebase(segmented_image, request.user_id, "cutout")
                print(f"✅ SAM3 cutout cached")
            else:
                # Fallback to rembg (removes bg but keeps model)
                print("  ⚠️ SAM3 failed, falling back to rembg...")
                try:
                    processed_image = remove_background_rembg(image_bytes)
                    segmentation_method = "rembg"
                    cutout_url = upload_to_firebase(processed_image, request.user_id, "cutout")
                    print(f"✅ rembg cutout cached")
                except Exception as e:
                    print(f"⚠️ rembg also failed: {e}, using original")
                    segmentation_method = "none"
                    cutout_url = original_url
        
        print(f"✅ Done!")
        
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
            segmentation_method=segmentation_method
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
            "image_caching",
            "sam3_garment_segmentation",
            "dual_image_storage",
            "price_snapshot",
            "partial_data_on_failure"
        ]
    }
