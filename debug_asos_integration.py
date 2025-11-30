"""
Debug ASOS integration - check what's happening
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
print("🔍 DEBUGGING ASOS INTEGRATION")
print("=" * 70)

# Test ASOS API first
print("\n1️⃣ Testing ASOS API...")

url = f"https://{ASOS_API_HOST}/products/v2/list"

querystring = {
    "store": "US",
    "offset": "0",
    "limit": "5",
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

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    products = data.get('products', [])
    
    print(f"✅ Found {len(products)} products")
    
    if products:
        print("\n📦 First product:")
        product = products[0]
        print(f"   Name: {product.get('name', 'N/A')}")
        print(f"   ID: {product.get('id', 'N/A')}")
        print(f"   Price: {product.get('price', {}).get('current', {}).get('text', 'N/A')}")
        print(f"   Image URL: {product.get('imageUrl', 'N/A')}")
        
        # Test image download
        print("\n2️⃣ Testing image download...")
        image_url = product.get('imageUrl', '')
        
        if image_url:
            # Fix URL
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif not image_url.startswith('http'):
                image_url = 'https://' + image_url
            
            print(f"   Full URL: {image_url}")
            
            try:
                img_response = requests.get(image_url, timeout=10)
                print(f"   Image status: {img_response.status_code}")
                
                if img_response.status_code == 200:
                    img = Image.open(io.BytesIO(img_response.content))
                    print(f"   ✅ Image loaded: {img.size}")
                    img.save('test_asos_product.png')
                    print(f"   ✅ Saved: test_asos_product.png")
                    
                    # Test CLIP
                    print("\n3️⃣ Testing CLIP embedding...")
                    device = "cpu"
                    clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
                    
                    img_input = clip_preprocess(img).unsqueeze(0).to(device)
                    with torch.no_grad():
                        features = clip_model.encode_image(img_input)
                        features = features / features.norm(dim=-1, keepdim=True)
                    
                    print(f"   ✅ Embedding generated: {features.shape}")
                    print(f"   First 5 values: {features[0][:5].numpy()}")
                    
                else:
                    print(f"   ❌ Failed to download image")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print("   ❌ No image URL in product data")
    else:
        print("❌ No products in response")
        print(f"Response keys: {data.keys()}")
else:
    print(f"❌ API Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

print("\n" + "=" * 70)
print("💡 DIAGNOSIS")
print("=" * 70)

