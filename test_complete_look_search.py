"""
Complete Look Search - 3 items from one photo
Handles ASOS timeout issues
"""
import os
import requests
import clip
import torch
from PIL import Image
import io
import google.generativeai as genai
import json
import time

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

ASOS_API_KEY = "6b07df1199mshac1029ebcab9bf5p1fd595jsn07fabec323e5"
ASOS_API_HOST = "asos2.p.rapidapi.com"

print("=" * 70)
print("🛍️  COMPLETE LOOK SEARCH - 3 ITEMS")
print("=" * 70)

# Load models
print("\n🔧 Loading CLIP...")
device = "cpu"
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
print("✅ Ready!")

gemini = genai.GenerativeModel('gemini-2.5-flash-image')

# Load the look image from AI OUTFIT PICS folder
look_image_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6596.jpg')
look_image = Image.open(look_image_path)

print(f"\n📸 Analyzing look from: {look_image_path.split('/')[-1]}")

# Analyze with Gemini
prompt = """Analyze this fashion photo and identify the main clothing items.

For each item provide:
1. Item type (sweater, jeans, shorts, shoes, etc.)
2. Detailed description
3. ASOS search keywords
4. Bounding box [x, y, width, height] as percentages

Return as JSON:
[
  {"type": "sweater", "description": "...", "search_keywords": "striped sweater", "bbox": [x,y,w,h]},
  {"type": "shorts", "description": "...", "search_keywords": "denim shorts", "bbox": [x,y,w,h]},
  {"type": "shoes", "description": "...", "search_keywords": "sneakers", "bbox": [x,y,w,h]}
]"""

response = gemini.generate_content([prompt, look_image])

print("\n✅ Gemini Analysis:")
print(response.text)

# Parse items
try:
    text = response.text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    items = json.loads(text.strip())
except Exception as e:
    print(f"\n⚠️  Using fallback: {e}")
    items = [
        {"type": "sweater", "search_keywords": "striped sweater burgundy", "bbox": [20, 15, 60, 35]},
        {"type": "shorts", "search_keywords": "denim shorts light wash", "bbox": [20, 50, 60, 25]},
        {"type": "shoes", "search_keywords": "white sneakers burgundy stripe", "bbox": [20, 75, 60, 20]}
    ]

print(f"\n✅ Found {len(items)} items to search")

# For each item, crop and generate embedding
item_embeddings = []

for item in items:
    print(f"\n📐 Processing {item['type']}...")
    
    # Crop item
    if 'bbox' in item and item['bbox']:
        width, height = look_image.size
        bbox = item['bbox']
        x = int(bbox[0] / 100 * width)
        y = int(bbox[1] / 100 * height)
        w = int(bbox[2] / 100 * width)
        h = int(bbox[3] / 100 * height)
        cropped = look_image.crop((x, y, x + w, y + h))
        cropped.save(f"cropped_{item['type']}.png")
        print(f"   ✅ Cropped and saved")
    else:
        cropped = look_image
    
    # Generate embedding
    img_input = clip_preprocess(cropped).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = clip_model.encode_image(img_input)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    
    item_embeddings.append({
        'type': item['type'],
        'keywords': item.get('search_keywords', item['type']),
        'embedding': embedding,
        'cropped': cropped
    })
    
    print(f"   ✅ Embedding ready")

print("\n" + "=" * 70)
print("🔍 SEARCHING ASOS FOR EACH ITEM")
print("=" * 70)

def search_asos(query, limit=20):
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

def download_asos_image(image_url, max_retries=2):
    """Download ASOS image with retry and fallback"""
    if not image_url:
        return None
    
    # Fix URL
    if image_url.startswith('//'):
        image_url = 'https:' + image_url
    elif not image_url.startswith('http'):
        image_url = 'https://' + image_url
    
    # Try different image sizes
    size_params = ['?$n_320w$', '?$n_240w$', '?$XXL$', '']
    
    for size in size_params:
        url = image_url.split('?')[0] + size
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return Image.open(io.BytesIO(response.content))
            except:
                time.sleep(0.5)
                continue
    
    return None

all_results = []

for item_data in item_embeddings:
    print(f"\n🔍 Searching for: {item_data['type']}")
    print(f"   Keywords: '{item_data['keywords']}'")
    
    # Search ASOS
    products = search_asos(item_data['keywords'], limit=15)
    print(f"   ✅ Found {len(products)} ASOS products")
    
    if not products:
        continue
    
    # Compare with CLIP
    matches = []
    print(f"\n   Comparing with CLIP...")
    
    for idx, product in enumerate(products[:10], 1):
        name = product.get('name', 'Unknown')
        image_url = product.get('imageUrl', '')
        
        print(f"      [{idx}/10] {name[:45]}... ", end='')
        
        # Download image
        img = download_asos_image(image_url)
        
        if img:
            try:
                # Generate embedding
                img_input = clip_preprocess(img).unsqueeze(0).to(device)
                with torch.no_grad():
                    features = clip_model.encode_image(img_input)
                    features = features / features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity
                similarity = (item_data['embedding'] @ features.T).item()
                
                matches.append({
                    'name': name,
                    'price': product.get('price', {}).get('current', {}).get('text', 'N/A'),
                    'url': f"https://www.asos.com/us/prd/{product.get('id', '')}",
                    'similarity': similarity
                })
                
                print(f"{similarity:.1%}")
            except Exception as e:
                print(f"✗")
        else:
            print(f"✗ timeout")
    
    # Sort by similarity
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    all_results.append({
        'item_type': item_data['type'],
        'matches': matches
    })
    
    if matches:
        print(f"\n   🎯 Top 3 Matches:")
        for i, m in enumerate(matches[:3], 1):
            print(f"      {i}. {m['name'][:50]}")
            print(f"         {m['similarity']:.1%} similar - {m['price']}")

print("\n" + "=" * 70)
print("📊 FINAL RESULTS - COMPLETE LOOK")
print("=" * 70)

for result in all_results:
    print(f"\n{result['item_type'].upper()}")
    if result['matches']:
        best = result['matches'][0]
        print(f"  Best Match: {best['name'][:60]}")
        print(f"  Similarity: {best['similarity']:.2%}")
        print(f"  Price: {best['price']}")
        print(f"  Link: {best['url']}")
        print(f"  Alternatives: {len(result['matches']) - 1} more options")
    else:
        print(f"  No matches found")

print("\n" + "=" * 70)
print("💡 COMPLETE 'SHOP THE LOOK' WORKFLOW")
print("=" * 70)

print("""
What just happened:
1. ✅ Gemini segmented the look into 3 items
2. ✅ CLIP generated visual embeddings for each
3. ✅ Searched ASOS for each item
4. ✅ Compared ASOS products with vector similarity
5. ✅ Returned best visual matches

This is pure visual search using 512-dimensional vectors! 🎯
""")

