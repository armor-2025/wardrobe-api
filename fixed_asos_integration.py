"""
Fixed ASOS Integration - proper image URL handling
"""
import os
import requests
import clip
import torch
from PIL import Image
import io
import json

ASOS_API_KEY = "6b07df1199mshac1029ebcab9bf5p1fd595jsn07fabec323e5"
ASOS_API_HOST = "asos2.p.rapidapi.com"

print("=" * 70)
print("🛍️  FIXED ASOS INTEGRATION")
print("=" * 70)

def fix_asos_image_url(image_url):
    """
    ASOS returns incomplete URLs, need to add proper format
    Example: images.asos-media.com/products/xxx/209699831-1-rustyred
    Should be: https://images.asos-media.com/products/xxx/209699831-1-rustyred?$n_640w$
    """
    if not image_url:
        return None
    
    # Add protocol if missing
    if image_url.startswith('//'):
        image_url = 'https:' + image_url
    elif not image_url.startswith('http'):
        image_url = 'https://' + image_url
    
    # Add image size parameter for faster loading
    if '?' not in image_url:
        image_url = image_url + '?$n_640w$'
    
    return image_url

# Load CLIP
print("\n🔧 Loading CLIP...")
device = "cpu"
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
print("✅ Ready!")

# Test with one product
print("\n1️⃣ Testing ASOS API...")

url = f"https://{ASOS_API_HOST}/products/v2/list"

querystring = {
    "store": "US",
    "offset": "0",
    "limit": "10",
    "country": "US",
    "q": "orange blouse",
    "currency": "USD",
    "lang": "en-US"
}

headers = {
    "x-rapidapi-key": ASOS_API_KEY,
    "x-rapidapi-host": ASOS_API_HOST
}

response = requests.get(url, headers=headers, params=querystring, timeout=10)

if response.status_code != 200:
    print(f"❌ ASOS API error: {response.status_code}")
    exit()

data = response.json()
products = data.get('products', [])

print(f"✅ Found {len(products)} products")

# Load reference image
print("\n2️⃣ Loading reference image...")
celeb_photo_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')
celeb_image = Image.open(celeb_photo_path)

celeb_input = clip_preprocess(celeb_image).unsqueeze(0).to(device)
with torch.no_grad():
    celeb_embedding = clip_model.encode_image(celeb_input)
    celeb_embedding = celeb_embedding / celeb_embedding.norm(dim=-1, keepdim=True)

print("✅ Reference embedding ready")

# Process ASOS products
print("\n3️⃣ Comparing with ASOS products...")

matches = []

for idx, product in enumerate(products, 1):
    name = product.get('name', 'Unknown')
    print(f"\n[{idx}/{len(products)}] {name[:50]}")
    
    # Get and fix image URL
    raw_url = product.get('imageUrl', '')
    image_url = fix_asos_image_url(raw_url)
    
    if not image_url:
        print("   ❌ No image URL")
        continue
    
    print(f"   Downloading: {image_url[:60]}...")
    
    try:
        # Download with retry
        for attempt in range(2):
            try:
                img_response = requests.get(image_url, timeout=15)
                if img_response.status_code == 200:
                    break
            except:
                if attempt == 0:
                    print("   ⚠️  Retry...")
                    continue
                else:
                    raise
        
        if img_response.status_code != 200:
            print(f"   ❌ Status: {img_response.status_code}")
            continue
        
        # Load image
        img = Image.open(io.BytesIO(img_response.content))
        
        # Generate embedding
        img_input = clip_preprocess(img).unsqueeze(0).to(device)
        with torch.no_grad():
            features = clip_model.encode_image(img_input)
            features = features / features.norm(dim=-1, keepdim=True)
        
        # Calculate similarity
        similarity = (celeb_embedding @ features.T).item()
        
        matches.append({
            'name': name,
            'price': product.get('price', {}).get('current', {}).get('text', 'N/A'),
            'url': f"https://www.asos.com/us/prd/{product.get('id', '')}",
            'image': image_url,
            'similarity': similarity,
            'id': product.get('id', '')
        })
        
        print(f"   ✅ Similarity: {similarity:.2%}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:80]}")
        continue

# Sort by similarity
matches.sort(key=lambda x: x['similarity'], reverse=True)

print("\n" + "=" * 70)
print("📊 TOP MATCHES FROM ASOS")
print("=" * 70)

for i, match in enumerate(matches[:5], 1):
    print(f"\n{i}. {match['name'][:60]}")
    print(f"   🎯 Similarity: {match['similarity']:.2%}")
    print(f"   💰 Price: {match['price']}")
    print(f"   🔗 {match['url']}")

# Save best match
if matches:
    print("\n💾 Saving best match image...")
    try:
        best = matches[0]
        img_response = requests.get(best['image'], timeout=15)
        img = Image.open(io.BytesIO(img_response.content))
        img.save('asos_best_match.png')
        print("✅ Saved: asos_best_match.png")
    except Exception as e:
        print(f"❌ Error saving: {e}")

print("\n" + "=" * 70)
print("✅ SUCCESS!")
print("=" * 70)

if matches and matches[0]['similarity'] > 0.70:
    print(f"\n🎯 Found good match: {matches[0]['similarity']:.2%} similar")
    print("This is production-ready!")
else:
    print("\n⚠️  Matches are moderate")
    print("May need to refine search keywords or expand product catalog")

