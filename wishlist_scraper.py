"""
Universal Wishlist - Tiered Product Extraction
1. Schema.org JSON-LD (best)
2. Open Graph meta tags (fallback)
3. Manual upload/edit (last resort)

Images are cached to Firebase (no hotlinking)
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

# Initialize Firebase if not already done
def init_firebase():
    if not firebase_admin._apps:
        cred_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if cred_json:
            cred_path = "/tmp/firebase_creds.json"
            with open(cred_path, "w") as f:
                f.write(cred_json)
            cred = credentials.Certificate(cred_path)
        else:
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                cred = None
        
        if cred:
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'your-online-wardrobe-jm85cl.firebasestorage.app'
            })
        else:
            firebase_admin.initialize_app(options={
                'storageBucket': 'your-online-wardrobe-jm85cl.firebasestorage.app'
            })

init_firebase()

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class WishlistAddRequest(BaseModel):
    url: Optional[str] = None
    image_base64: Optional[str] = None  # Manual image upload
    title: Optional[str] = None  # Manual override
    price: Optional[str] = None  # Manual override
    currency: Optional[str] = None
    category: Optional[str] = None
    user_id: str
    notes: Optional[str] = None
    remove_bg: bool = True  # Toggle background removal


class WishlistAddResponse(BaseModel):
    success: bool
    image_url: Optional[str] = None  # Cached Firebase URL (with bg removed if requested)
    image_original_url: Optional[str] = None  # Original cached image (no bg removal)
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
    needs_user_input: bool = False  # True if extraction failed - return partial data for editing
    error: Optional[str] = None


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


def remove_background(image_bytes: bytes) -> bytes:
    """Remove background using rembg"""
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
    
    Supports:
    - URL only: auto-extract image/title/price
    - Image only: manual upload
    - URL + Image: use uploaded image with URL as source link
    """
    try:
        image_bytes = None
        title = request.title
        price = request.price
        currency = request.currency
        category = request.category
        brand = None
        retailer = None
        extraction_method = None
        capture_method = None
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
        
        # Process the image
        print("☁️ Caching original to Firebase...")
        original_png = save_original(image_bytes)
        original_url = upload_to_firebase(original_png, request.user_id, "original")
        
        cutout_url = original_url
        if request.remove_bg:
            print("🎨 Removing background...")
            try:
                processed_image = remove_background(image_bytes)
                cutout_url = upload_to_firebase(processed_image, request.user_id, "cutout")
                print(f"✅ Cutout cached")
            except Exception as e:
                print(f"⚠️ Background removal failed: {e}, using original")
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
            capture_method=capture_method
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
        "features": ["image_caching", "background_removal_toggle", "price_snapshot", "partial_data_on_failure"]
    }
