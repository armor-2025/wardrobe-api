"""
ULTIMATE Multi-Signal Product Search
Visual + Text + Metadata = Best Match Quality!
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
import webbrowser

GEMINI_KEY = 'YOUR_KEY_HERE'
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'
genai.configure(api_key=GEMINI_KEY)

print("=" * 70)
print("🎯 ULTIMATE MULTI-SIGNAL SEARCH")
print("=" * 70)
print("\n✨ Using:")
print("  • CLIP Visual Embeddings (40%)")
print("  • Text Description Matching (20%)")
print("  • Category Matching (15%)")
print("  • Color Matching (10%)")
print("  • Style/Features Matching (10%)")
print("  • Material Matching (5%)")
print("=" * 70)

class UltimateProductSearch:
    def __init__(self):
        print("\n🔧 Initializing...")
        self.device = "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Ready!")
    
    def extract_metadata(self, image_path):
        """Extract structured metadata using Gemini"""
        print("\n📊 Step 1: Extracting metadata with Gemini...")
        
        image = Image.open(image_path)
        
        prompt = """Analyze this clothing item and extract structured metadata.

Return ONLY valid JSON:
{
  "category": "dress",
  "primary_color": "burgundy",
  "material": "corduroy",
  "features": ["long_sleeve", "collar", "buttons"],
  "length": "mini",
  "description": "burgundy corduroy long sleeve mini dress with collar and button-down front"
}

Return ONLY JSON, no markdown."""
        
        response = self.gemini.generate_content([prompt, image])
        text = response.text.strip()
        
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        try:
            metadata = json.loads(text.strip())
            print(f"   ✅ Category: {metadata.get('category')}, Color: {metadata.get('primary_color')}, Material: {metadata.get('material')}")
            return metadata
        except:
            return {"category": "unknown", "description": text, "features": [], "primary_color": "unknown", "material": "unknown"}
    
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
        print(f"\n🛍️  Step 2: Searching: '{query}'")
        url = "https://serpapi.com/search"
        params = {"engine": "google_shopping", "q": query, "api_key": SERPAPI_KEY, "num": num}
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
    
    def extract_product_metadata(self, title):
        title_lower = title.lower()
        metadata = {'features': [], 'colors': [], 'materials': []}
        
        if 'long sleeve' in title_lower: metadata['features'].append('long_sleeve')
        if 'collar' in title_lower: metadata['features'].append('collar')
        if 'button' in title_lower: metadata['features'].append('buttons')
        
        for color in ['burgundy', 'navy', 'black', 'red', 'wine', 'fig']:
            if color in title_lower: metadata['colors'].append(color)
        
        for material in ['corduroy', 'cord', 'cotton', 'silk', 'denim']:
            if material in title_lower: metadata['materials'].append(material)
        
        return metadata
    
    def calculate_score(self, query_meta, prod_visual, prod_text, prod_title):
        scores = {}
        
        # Visual (40%)
        scores['visual'] = float(np.dot(query_meta['visual'], prod_visual)) * 0.40
        
        # Text (20%)
        scores['text'] = float(np.dot(query_meta['text'], prod_text)) * 0.20
        
        # Category (15%)
        query_cat = query_meta['metadata'].get('category', '').lower()
        scores['category'] = (1.0 if query_cat in prod_title.lower() else 0.0) * 0.15
        
        # Color (10%)
        prod_meta = self.extract_product_metadata(prod_title)
        query_color = query_meta['metadata'].get('primary_color', '').lower()
        scores['color'] = (1.0 if query_color in prod_meta['colors'] else 0.0) * 0.10
        
        # Features (10%)
        query_features = set(query_meta['metadata'].get('features', []))
        prod_features = set(prod_meta['features'])
        if query_features and prod_features:
            scores['features'] = (len(query_features & prod_features) / len(query_features)) * 0.10
        else:
            scores['features'] = 0.0
        
        # Material (5%)
        query_material = query_meta['metadata'].get('material', '').lower()
        scores['material'] = (1.0 if query_material in prod_meta['materials'] else 0.0) * 0.05
        
        return sum(scores.values()), scores
    
    def ultimate_search(self, image_path):
        print(f"\n📸 Analyzing: {os.path.basename(image_path)}")
        
        query_image = Image.open(image_path).convert('RGB')
        metadata = self.extract_metadata(image_path)
        description = metadata.get('description', '')
        
        print(f"\n🧮 Step 3: Generating embeddings...")
        query_visual = self.get_embeddings(image=query_image)
        query_text = self.get_embeddings(text=description)
        
        query_meta = {'visual': query_visual, 'text': query_text, 'metadata': metadata}
        
        products = self.search_google_shopping(description, 30)
        if not products: return [], metadata
        
        print(f"\n🔍 Step 4: Calculating scores...")
        results = []
        
        for i, product in enumerate(products[:20], 1):
            try:
                img_resp = requests.get(product['thumbnail'], timeout=5)
                prod_img = Image.open(io.BytesIO(img_resp.content)).convert('RGB')
                prod_visual = self.get_embeddings(image=prod_img)
                prod_text = self.get_embeddings(text=product['title'])
                
                total, breakdown = self.calculate_score(query_meta, prod_visual, prod_text, product['title'])
                
                results.append({**product, 'total_score': total, 'score_breakdown': breakdown, 'product_image': prod_img})
                print(f"   [{i}/20] {total:.0%} - {product['title'][:50]}...")
            except:
                continue
        
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results, metadata
    
    def create_html(self, image_path, results, query_meta):
        print(f"\n🌐 Creating HTML...")
        
        query_img = Image.open(image_path).convert('RGB')
        query_img.thumbnail((400, 400))
        buffered = io.BytesIO()
        query_img.save(buffered, format="JPEG")
        query_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        for r in results:
            buffered = io.BytesIO()
            r['product_image'].save(buffered, format="JPEG")
            r['image_base64'] = base64.b64encode(buffered.getvalue()).decode()
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Ultimate Search</title>
<style>
body{{font-family:sans-serif;background:#667eea;padding:20px}}
.container{{max-width:1400px;margin:0 auto}}
h1{{color:white;text-align:center}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:30px}}
.card{{background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.1)}}
.card:hover{{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,0.2)}}
img{{width:100%;height:300px;object-fit:cover}}
.info{{padding:15px}}
.title{{font-weight:bold;margin-bottom:10px}}
.score{{background:#667eea;color:white;padding:8px;border-radius:8px;text-align:center;margin:10px 0}}
.btn{{display:block;background:#764ba2;color:white;text-align:center;padding:12px;text-decoration:none;border-radius:8px;margin-top:10px}}
.btn:hover{{background:#667eea}}
</style>
</head><body>
<div class="container">
<h1>🎯 Ultimate Multi-Signal Search</h1>
<div class="grid">
"""
        
        for i, r in enumerate(results[:15], 1):
            html += f"""
<div class="card">
<img src="data:image/jpeg;base64,{r['image_base64']}">
<div class="info">
<div class="score">#{i} - {r['total_score']:.0%} Match</div>
<div class="title">{r['title']}</div>
<div><strong>{r['price']}</strong> - {r['source']}</div>
<a href="{r['link']}" target="_blank" class="btn">View Product →</a>
</div>
</div>
"""
        
        html += "</div></div></body></html>"
        
        filename = f"ultimate_search_{datetime.now().strftime('%H%M%S')}.html"
        with open(filename, 'w') as f:
            f.write(html)
        
        webbrowser.open('file://' + os.path.abspath(filename))
        return filename

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python ultimate_multi_signal_search.py 'image_path'")
        sys.exit(1)
    
    searcher = UltimateProductSearch()
    results, metadata = searcher.ultimate_search(sys.argv[1])
    
    print("\n🏆 TOP 5:")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r['title'][:60]} - {r['total_score']:.0%}")
    
    html_file = searcher.create_html(sys.argv[1], results, metadata)
    print(f"\n✅ Opened in browser: {html_file}")
