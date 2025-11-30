"""
Import ASOS products with CLIP embeddings
"""
import os
import requests
import clip
import torch
from PIL import Image
import io
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ASOS_API_KEY = "6b07df1199mshac1029ebcab9bf5p1fd595jsn07fabec323e5"
ASOS_API_HOST = "asos2.p.rapidapi.com"

print("=" * 70)
print("📦 IMPORTING ASOS PRODUCTS")
print("=" * 70)

# Initialize
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n🔧 Loading CLIP...")
device = "cpu"
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
print("✅ CLIP ready!")

def search_asos(query, limit=50):
    """Search ASOS for products"""
    url = f"https://{ASOS_API_HOST}/products/v2/list"
    querystring = {
        "store": "US",
        "offset": "0",
        "limit": str(limit),
        "country": "US",
        "q": query,
        "currency": "USD",
        "lang": "en-US"
    }
    headers = {
        "x-rapidapi-key": ASOS_API_KEY,
        "x-rapidapi-host": ASOS_API_HOST
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            return response.json().get('products', [])
    except:
        pass
    return []

def download_image(image_url, max_retries=3):
    """Download ASOS product image"""
    if not image_url:
        return None
    
    # Fix URL
    if image_url.startswith('//'):
        image_url = 'https:' + image_url
    elif not image_url.startswith('http'):
        image_url = 'https://' + image_url
    
    # Try smaller sizes first (faster)
    size_params = ['?$n_240w$', '?$n_320w$', '']
    
    for size in size_params:
        url = image_url.split('?')[0] + size
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    return Image.open(io.BytesIO(response.content))
            except:
                if attempt < max_retries - 1:
                    time.sleep(0.3)
                continue
        
    return None

def generate_clip_embedding(image):
    """Generate CLIP embedding for product image"""
    try:
        img_input = clip_preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            features = clip_model.encode_image(img_input)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].cpu().numpy().tolist()
    except:
        return None

def import_category(category_name, search_query, target_count=100):
    """Import products from a category"""
    print(f"\n{'='*70}")
    print(f"📦 Importing: {category_name}")
    print(f"{'='*70}")
    
    print(f"\n🔍 Searching ASOS for: '{search_query}'")
    products = search_asos(search_query, limit=target_count)
    print(f"✅ Found {len(products)} products")
    
    imported = 0
    skipped = 0
    failed = 0
    
    for idx, product in enumerate(products[:target_count], 1):
        product_id = str(product.get('id', ''))
        name = product.get('name', 'Unknown')
        
        print(f"\n[{idx}/{len(products[:target_count])}] {name[:50]}...")
        
        # Check if already exists
        existing = supabase.table('products').select("id").eq('product_id', product_id).execute()
        if existing.data:
            print(f"   ⏭️  Already exists")
            skipped += 1
            continue
        
        # Download image
        image_url = product.get('imageUrl', '')
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif not image_url.startswith('http'):
            image_url = 'https://' + image_url
        
        print(f"   📥 Downloading image...")
        img = download_image(product.get('imageUrl', ''))
        
        if not img:
            print(f"   ❌ Image download failed")
            failed += 1
            continue
        
        # Generate embedding
        print(f"   🔄 Generating CLIP embedding...")
        embedding = generate_clip_embedding(img)
        
        if not embedding:
            print(f"   ❌ Embedding generation failed")
            failed += 1
            continue
        
        # Extract price
        price_data = product.get('price', {}).get('current', {})
        price = price_data.get('value', 0)
        
        # Insert into database
        try:
            product_data = {
                'product_id': product_id,
                'name': name,
                'brand': product.get('brandName', 'ASOS'),
                'category': category_name,
                'price_usd': float(price) if price else None,
                'image_url': image_url,
                'affiliate_link': f"https://www.asos.com/us/prd/{product_id}",
                'retailer': 'ASOS',
                'clip_embedding': embedding,
                'in_stock': True,
                'is_active': True
            }
            
            supabase.table('products').insert(product_data).execute()
            print(f"   ✅ Imported!")
            imported += 1
            
        except Exception as e:
            print(f"   ❌ Database error: {str(e)[:50]}")
            failed += 1
        
        # Small delay to avoid rate limits
        time.sleep(0.2)
    
    print(f"\n{'='*70}")
    print(f"📊 {category_name} Summary:")
    print(f"   ✅ Imported: {imported}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ❌ Failed: {failed}")
    print(f"{'='*70}")
    
    return imported

# Categories to import
categories = [
    ('sweaters', 'womens sweater', 30),
    ('dresses', 'womens dress', 30),
    ('jeans', 'womens jeans', 20),
    ('shoes', 'womens shoes sneakers', 20),
]

print(f"\n🎯 Importing {sum(c[2] for c in categories)} products total")

total_imported = 0

for category, query, count in categories:
    imported = import_category(category, query, count)
    total_imported += imported

print("\n" + "=" * 70)
print("🎉 IMPORT COMPLETE!")
print("=" * 70)

print(f"\n📊 Final Stats:")
print(f"   Total imported: {total_imported}")

# Test search
print("\n🧪 Testing visual search...")
result = supabase.table('products').select("*").limit(5).execute()
print(f"✅ Database has {len(result.data)} products")

for p in result.data[:3]:
    print(f"   - {p['name'][:50]} ({p['category']}) - ${p['price_usd']}")

print("\n✅ Ready for visual search! 🚀")

