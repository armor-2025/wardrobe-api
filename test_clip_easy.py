"""
Test CLIP Visual Search - Easy Version
Just run this and provide an image path when prompted!
"""
import os
import sys
import requests
import json
from PIL import Image
import io
import torch
import clip

# Set up API keys
GEMINI_KEY = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'

print("=" * 70)
print("🎯 CLIP VISUAL SEARCH - EASY TEST")
print("=" * 70)

# Load CLIP model
print("\n🔧 Loading CLIP model...")
device = "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)
print("✅ CLIP model loaded!")

def get_image_embedding(image):
    """Generate CLIP embedding for an image"""
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)
    return image_features.cpu().numpy()[0]

def search_google_shopping(query, num_results=20):
    """Search Google Shopping via SerpApi"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results
    }
    
    print(f"   🔍 Searching Google Shopping...")
    response = requests.get(url, params=params)
    data = response.json()
    
    products = []
    for item in data.get('shopping_results', []):
        products.append({
            'title': item.get('title', ''),
            'price': item.get('price', ''),
            'link': item.get('link', ''),
            'thumbnail': item.get('thumbnail', ''),
            'source': item.get('source', '')
        })
    
    return products

def test_visual_search(image_path, search_query):
    """Complete visual search test"""
    
    print("\n" + "=" * 70)
    print(f"📸 Testing with: {os.path.basename(image_path)}")
    print("=" * 70)
    
    # Step 1: Load query image
    print(f"\n📸 Step 1: Loading your image...")
    try:
        query_img = Image.open(image_path).convert('RGB')
        print(f"   ✅ Image loaded: {query_img.size}")
    except Exception as e:
        print(f"   ❌ Error loading image: {e}")
        return
    
    # Step 2: Generate embedding
    print(f"\n🧮 Step 2: Generating CLIP embedding...")
    query_embedding = get_image_embedding(query_img)
    print(f"   ✅ Embedding generated: {query_embedding.shape}")
    
    # Step 3: Search Google Shopping
    print(f"\n🛍️  Step 3: Searching for similar products...")
    print(f"   Query: '{search_query}'")
    products = search_google_shopping(search_query, num_results=20)
    print(f"   ✅ Found {len(products)} products")
    
    # Step 4: Calculate visual similarity
    print(f"\n🔍 Step 4: Comparing visual similarity...")
    results = []
    
    for i, product in enumerate(products[:15], 1):
        try:
            img_response = requests.get(product['thumbnail'], timeout=5)
            product_img = Image.open(io.BytesIO(img_response.content)).convert('RGB')
            product_embedding = get_image_embedding(product_img)
            similarity = float((query_embedding @ product_embedding.T))
            
            results.append({
                **product,
                'similarity': similarity
            })
            
            print(f"   [{i}/15] {similarity:.1%} - {product['title'][:50]}...")
            
        except Exception as e:
            print(f"   [{i}/15] ❌ Skip - {str(e)[:40]}")
            continue
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    print("\n" + "=" * 70)
    print("🏆 TOP 5 VISUAL MATCHES")
    print("=" * 70)
    
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   ├─ Similarity: {result['similarity']:.1%} ⭐")
        print(f"   ├─ Price: {result['price']}")
        print(f"   ├─ Source: {result['source']}")
        print(f"   └─ Link: {result['link'][:60]}...")
    
    print("\n" + "=" * 70)
    print("✅ VISUAL SEARCH COMPLETE!")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        search_query = sys.argv[2] if len(sys.argv) > 2 else "clothing"
        results = test_visual_search(image_path, search_query)
    else:
        print("\n💡 Usage: python test_clip_easy.py 'image_path' 'search_query'")
        print("\n📝 Example:")
        print("   python test_clip_easy.py '/Users/gavinwalker/Desktop/AI OUTFIT PICS/IMG_6563.PNG' 'red dress'")
