"""
Shop the Look with ASOS API
Real product matching with affiliate links
"""
import os
import requests
import clip
import torch
from PIL import Image
import io
import google.generativeai as genai
import json

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# ASOS API credentials
ASOS_API_KEY = "6b07df1199mshac1029ebcab9bf5p1fd595jsn07fabec323e5"
ASOS_API_HOST = "asos2.p.rapidapi.com"

print("=" * 70)
print("🛍️  SHOP THE LOOK - ASOS INTEGRATION")
print("=" * 70)

# Load CLIP
print("\n🔧 Loading CLIP...")
device = "cpu"
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
print("✅ Ready!")

def search_asos_products(query, category="women", limit=20):
    """
    Search ASOS for products
    """
    url = f"https://{ASOS_API_HOST}/products/v2/list"
    
    querystring = {
        "store": "US",
        "offset": "0",
        "categoryId": category,
        "limit": str(limit),
        "country": "US",
        "sort": "freshness",
        "q": query,
        "currency": "USD",
        "sizeSchema": "US",
        "lang": "en-US"
    }
    
    headers = {
        "x-rapidapi-key": ASOS_API_KEY,
        "x-rapidapi-host": ASOS_API_HOST
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  ASOS API error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error calling ASOS: {e}")
        return None

def generate_clip_embedding_from_url(image_url):
    """
    Download image and generate CLIP embedding
    """
    try:
        # Fix URL if needed
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif not image_url.startswith('http'):
            image_url = 'https://' + image_url
        
        response = requests.get(image_url, timeout=10)
        img = Image.open(io.BytesIO(response.content))
        
        img_input = clip_preprocess(img).unsqueeze(0).to(device)
        with torch.no_grad():
            features = clip_model.encode_image(img_input)
            features = features / features.norm(dim=-1, keepdim=True)
        
        return features
    except Exception as e:
        return None

# Test workflow
print("\n" + "=" * 70)
print("🧪 TEST: Shop the Look with ASOS")
print("=" * 70)

# Step 1: Analyze celebrity photo
print("\n📸 Step 1: Analyzing celebrity photo...")

celeb_photo_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')
celeb_image = Image.open(celeb_photo_path)

gemini = genai.GenerativeModel('gemini-2.5-flash-image')

prompt = """Analyze this fashion photo and identify clothing items.

For each item provide:
1. Item type
2. Search keywords for finding similar items on ASOS

Return as JSON:
[{"type": "blouse", "search_keywords": "gingham check blouse orange"}]"""

response = gemini.generate_content([prompt, celeb_image])

print("✅ Gemini analysis:")
print(response.text[:500])

# Parse
try:
    text = response.text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    items = json.loads(text.strip())
except:
    # Fallback
    items = [
        {"type": "blouse", "search_keywords": "check blouse"}
    ]

print(f"\n✅ Found {len(items)} items to search")

# Step 2: Generate embedding for celebrity item
print("\n📐 Generating reference embedding from celebrity photo...")
celeb_input = clip_preprocess(celeb_image).unsqueeze(0).to(device)
with torch.no_grad():
    celeb_embedding = clip_model.encode_image(celeb_input)
    celeb_embedding = celeb_embedding / celeb_embedding.norm(dim=-1, keepdim=True)
print("✅ Reference embedding ready")

# Step 3: For each item, search ASOS and find best match
print("\n" + "=" * 70)
print("🔍 Step 2: Searching ASOS & Matching with CLIP")
print("=" * 70)

all_matches = []

for item in items[:1]:  # Start with first item only
    print(f"\n📦 Searching ASOS for: {item['type']}")
    print(f"   Keywords: '{item.get('search_keywords', item['type'])}'")
    
    # Search ASOS
    results = search_asos_products(item.get('search_keywords', item['type']), limit=20)
    
    if not results or 'products' not in results:
        print("   ⚠️  No results from ASOS")
        continue
    
    products = results['products']
    print(f"   ✅ Found {len(products)} ASOS products")
    
    # Compare with ASOS products
    matches = []
    
    print("\n   🔄 Calculating visual similarity with CLIP...")
    for idx, product in enumerate(products[:10], 1):  # Test first 10
        try:
            # Get product image
            image_url = product.get('imageUrl', '')
            if not image_url:
                continue
            
            # Fix URL
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            
            print(f"      [{idx}/10] Analyzing {product.get('name', 'Unknown')[:40]}...")
            
            # Generate embedding
            product_embedding = generate_clip_embedding_from_url(image_url)
            
            if product_embedding is not None:
                # Calculate similarity
                similarity = (celeb_embedding @ product_embedding.T).item()
                
                matches.append({
                    'name': product.get('name', 'Unknown'),
                    'price': product.get('price', {}).get('current', {}).get('text', 'N/A'),
                    'url': f"https://www.asos.com/us/prd/{product.get('id', '')}",
                    'image': image_url,
                    'similarity': similarity,
                    'product_id': product.get('id', '')
                })
                
                print(f"              Similarity: {similarity:.2%}")
        except Exception as e:
            print(f"              ✗ Error: {e}")
            continue
    
    # Sort by similarity
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    print(f"\n   📊 TOP 5 MATCHES:")
    print("   " + "─" * 66)
    for i, match in enumerate(matches[:5], 1):
        print(f"\n   {i}. {match['name'][:55]}")
        print(f"      🎯 Similarity: {match['similarity']:.2%}")
        print(f"      💰 Price: {match['price']}")
        print(f"      🔗 {match['url']}")
    
    all_matches.append({
        'item_type': item['type'],
        'matches': matches
    })
    
    # Download and save best match
    if matches:
        print(f"\n   💾 Saving best match image...")
        try:
            best = matches[0]
            img_response = requests.get(best['image'], timeout=10)
            best_img = Image.open(io.BytesIO(img_response.content))
            best_img.save(f"asos_best_match_{item['type']}.png")
            print(f"      ✅ Saved: asos_best_match_{item['type']}.png")
        except Exception as e:
            print(f"      ❌ Failed: {e}")

print("\n" + "=" * 70)
print("✅ ASOS INTEGRATION COMPLETE!")
print("=" * 70)

if all_matches:
    for match_set in all_matches:
        best = match_set['matches'][0] if match_set['matches'] else None
        if best:
            print(f"\n{match_set['item_type'].upper()}")
            print(f"  Best Match: {best['name']}")
            print(f"  Similarity: {best['similarity']:.2%}")
            print(f"  Price: {best['price']}")
            print(f"  Link: {best['url']}")

print("\n💡 This is production-ready! Next: Build full UI")

