"""
Hybrid Visual + Text Search System
Combines CLIP visual embeddings with Gemini text descriptions
"""
import os
import sys
import requests
import json
from PIL import Image
import io
import torch
import clip
import numpy as np
import google.generativeai as genai
from datetime import datetime
import base64

GEMINI_KEY = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'
genai.configure(api_key=GEMINI_KEY)

print("=" * 70)
print("🎯 HYBRID VISUAL + TEXT SEARCH")
print("=" * 70)

class HybridProductSearch:
    def __init__(self):
        print("\n🔧 Initializing...")
        self.device = "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Ready!")
    
    def describe_product(self, image_path):
        print("\n📝 Generating description with Gemini...")
        image = Image.open(image_path)
        
        prompt = """Analyze this clothing item. Provide a detailed, searchable description.

Include: item type, specific color, material, sleeve type, neckline, length, fit, key details.

Format: "[color] [material] [sleeve] [type] with [neckline] and [details]"

Example: "burgundy corduroy long sleeve mini dress with collar and button-down front"

Return ONLY the description."""
        
        response = self.gemini.generate_content([prompt, image])
        description = response.text.strip()
        if '```' in description:
            description = description.split('```')[0].strip()
        
        print(f"   ✅ {description}")
        return description
    
    def get_embeddings(self, image=None, text=None):
        if image:
            img_input = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                features = self.model.encode_image(img_input)
                features /= features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy()[0]
        elif text:
            text_input = clip.tokenize([text]).to(self.device)
            with torch.no_grad():
                features = self.model.encode_text(text_input)
                features /= features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy()[0]
    
    def search_google_shopping(self, query, num=30):
        print(f"\n🛍️  Searching Google Shopping: '{query}'")
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": num
        }
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
        print(f"   ✅ Found {len(products)} products")
        return products
    
    def hybrid_search(self, image_path):
        print(f"\n📸 Analyzing: {os.path.basename(image_path)}")
        
        query_image = Image.open(image_path).convert('RGB')
        description = self.describe_product(image_path)
        products = self.search_google_shopping(description, 30)
        
        if not products:
            return [], description
        
        print(f"\n🧮 Generating embeddings...")
        query_visual = self.get_embeddings(image=query_image)
        query_text = self.get_embeddings(text=description)
        print(f"   ✅ Embeddings ready")
        
        print(f"\n🔍 Calculating similarity...")
        results = []
        
        for i, product in enumerate(products[:20], 1):
            try:
                img_resp = requests.get(product['thumbnail'], timeout=5)
                prod_img = Image.open(io.BytesIO(img_resp.content)).convert('RGB')
                
                prod_visual = self.get_embeddings(image=prod_img)
                prod_text = self.get_embeddings(text=product['title'])
                
                vis_sim = float(np.dot(query_visual, prod_visual))
                txt_sim = float(np.dot(query_text, prod_text))
                combined = (0.7 * vis_sim) + (0.3 * txt_sim)
                
                results.append({
                    **product,
                    'visual_similarity': vis_sim,
                    'text_similarity': txt_sim,
                    'combined_score': combined,
                    'product_image': prod_img
                })
                
                print(f"   [{i}/20] {combined:.0%} (V:{vis_sim:.0%} T:{txt_sim:.0%}) - {product['title'][:40]}...")
            except:
                continue
        
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        return results, description

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python hybrid_visual_text_search.py 'image_path'")
        sys.exit(1)
    
    searcher = HybridProductSearch()
    results, desc = searcher.hybrid_search(sys.argv[1])
    
    print("\n" + "=" * 70)
    print("🏆 TOP 5 MATCHES")
    print("=" * 70)
    
    for i, r in enumerate(results[:5], 1):
        print(f"\n{i}. {r['title']}")
        print(f"   Combined: {r['combined_score']:.0%} (Visual: {r['visual_similarity']:.0%}, Text: {r['text_similarity']:.0%})")
        print(f"   {r['price']} - {r['source']}")
    
    print("\n✅ Done! Cost: ~$0.001")
