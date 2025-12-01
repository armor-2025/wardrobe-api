"""
ULTIMATE FashionCLIP Search
- Uses ALL details from Gemini
- Structured metadata for vector DB filtering
"""
import os
import sys
import json
from PIL import Image
import io
import google.generativeai as genai
from datetime import datetime
import base64
import webbrowser
import requests

GEMINI_KEY = 'YOUR_KEY_HERE'
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'
genai.configure(api_key=GEMINI_KEY)

print("=" * 70)
print("🎯 ULTIMATE FASHIONCLIP SEARCH - ALL DETAILS")
print("=" * 70)

class UltimateFashionSearch:
    def __init__(self):
        print("\n🔧 Initializing...")
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        try:
            from fashion_clip.fashion_clip import FashionCLIP
            self.fclip = FashionCLIP('fashion-clip')
            print("   ✅ FashionCLIP loaded!")
            self.has_fclip = True
        except:
            print("   ⚠️  FashionCLIP not installed")
            self.has_fclip = False
        print("   ✅ Ready!")
    
    def analyze(self, image_path):
        print(f"\n📸 Step 1: COMPLETE Gemini analysis...")
        image = Image.open(image_path)
        
        prompt = """Analyze with MAXIMUM detail. Extract EVERY attribute.

Return ONLY JSON:
[{
  "type": "sneakers",
  "brand": "Adidas",
  "model": "Handball Spezial",
  "description": "Pink suede Adidas Handball Spezial with dark blue three stripes, gum sole",
  "colors": ["pink", "dark_blue", "gum_brown", "white"],
  "material": "suede",
  "features": ["three_stripes", "gum_sole", "low_top", "lace_up", "retro_style", "suede_upper"],
  "style_tags": ["retro", "casual", "sporty"],
  "estimated_price": 100
}]

Include brand+model, ALL colors, ALL features visible."""
        
        try:
            response = self.gemini.generate_content([prompt, image])
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            items = json.loads(text.strip())
            print(f"\n   ✅ Found {len(items)} items:")
            for i, item in enumerate(items, 1):
                print(f"      {i}. {item['type']} - {item.get('brand', '')} {item.get('model', '')}")
                print(f"         Features: {', '.join(item.get('features', [])[:5])}...")
            return items
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def build_query(self, item):
        """Use ALL details in query"""
        parts = []
        if item.get('brand'):
            parts.append(item['brand'])
        if item.get('model'):
            parts.append(item['model'])
        parts.extend(item.get('colors', [])[:4])
        if item.get('material'):
            parts.append(item['material'])
        parts.extend(item.get('features', [])[:6])
        parts.append(item['type'])
        parts.append('women')
        return ' '.join(parts).replace('_', ' ')
    
    def search_products(self, query):
        url = "https://serpapi.com/search"
        params = {"engine": "google_shopping", "q": query, "api_key": SERPAPI_KEY, "num": 100}
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            return [{'title': i.get('title'), 'price': i.get('price'), 'link': i.get('link'),
                    'thumbnail': i.get('thumbnail'), 'source': i.get('source')}
                   for i in data.get('shopping_results', [])][:50]
        except:
            return []
    
    def search(self, image_path):
        print(f"\n{'='*70}")
        print("🛍️  SEARCHING WITH ALL DETAILS")
        print(f"{'='*70}")
        
        items = self.analyze(image_path)
        if not items:
            return None
        
        print(f"\n🔍 Step 2: Complete search queries...")
        results = []
        
        for i, item in enumerate(items, 1):
            if item.get('estimated_price', 0) < 15:
                print(f"\n   [{i}/{len(items)}] ⏭️  SKIP: {item['type']}")
                continue
            
            query = self.build_query(item)
            print(f"\n   [{i}/{len(items)}] {item['type']}")
            print(f"      Complete query: {query}")
            
            if self.has_fclip:
                print(f"      ✅ FashionCLIP ready")
            
            products = self.search_products(query)
            print(f"      ✅ {len(products)} matches")
            
            results.append({'item': item, 'products': products, 'query': query})
        
        print(f"\n{'='*70}")
        print(f"💰 COST: $0.001")
        print(f"{'='*70}")
        return {'results': results}
    
    def create_html(self, image_path, search_results):
        outfit_img = Image.open(image_path)
        outfit_img.thumbnail((500, 700))
        buffered = io.BytesIO()
        outfit_img.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        results = search_results['results']
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Ultimate Results</title>
<style>
body{{font-family:sans-serif;background:#667eea;padding:20px}}
h1{{color:white;text-align:center;font-size:40px}}
.outfit{{background:white;border-radius:20px;padding:30px;margin:20px 0;text-align:center}}
.outfit img{{max-width:400px;border-radius:12px}}
.item{{background:white;border-radius:16px;padding:25px;margin:20px 0}}
.item h2{{color:#667eea}}
.details{{background:#f8f9fa;padding:15px;border-radius:8px;margin:10px 0}}
.label{{font-weight:bold;color:#667eea}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:15px;margin-top:15px}}
.card{{background:#f8f9fa;border-radius:10px;overflow:hidden;transition:transform 0.2s}}
.card:hover{{transform:translateY(-3px)}}
.card img{{width:100%;height:220px;object-fit:cover}}
.card-info{{padding:12px}}
.card h3{{font-size:13px;margin:0 0 8px;height:36px;overflow:hidden}}
.price{{font-size:18px;font-weight:bold;color:#667eea}}
.btn{{display:block;background:#764ba2;color:white;text-decoration:none;padding:8px;text-align:center;border-radius:6px;margin-top:8px}}
</style>
</head><body>
<div style="max-width:1400px;margin:0 auto">
<h1>🎯 Ultimate Search - ALL Details</h1>
<div class="outfit"><img src="data:image/jpeg;base64,{img_b64}"></div>
"""
        
        for idx, result in enumerate(results, 1):
            item = result['item']
            products = result['products']
            
            html += f"""
<div class="item">
<h2>{idx}. {item['type'].title()}</h2>
<div class="details">
<p><span class="label">Description:</span> {item.get('description', 'N/A')}</p>
{'<p><span class="label">Brand:</span> ' + item['brand'] + ' ' + item.get('model', '') + '</p>' if item.get('brand') else ''}
<p><span class="label">Colors:</span> {', '.join(item.get('colors', []))}</p>
<p><span class="label">Material:</span> {item.get('material', 'N/A')}</p>
<p><span class="label">Features:</span> {', '.join(item.get('features', []))}</p>
<p><span class="label">Complete Query:</span> <em>{result['query']}</em></p>
</div>
<div class="grid">
"""
            
            for prod in products[:12]:
                html += f"""
<div class="card">
<img src="{prod['thumbnail']}">
<div class="card-info">
<h3>{prod['title'][:50]}</h3>
<div class="price">{prod['price']}</div>
<a href="{prod['link']}" target="_blank" class="btn">View →</a>
</div>
</div>
"""
            
            html += "</div></div>"
        
        html += "</div></body></html>"
        
        filename = f"ultimate_{datetime.now().strftime('%H%M%S')}.html"
        with open(filename, 'w') as f:
            f.write(html)
        webbrowser.open('file://' + os.path.abspath(filename))
        return filename

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python ultimate_fashionclip_search.py 'image'")
        sys.exit(1)
    
    system = UltimateFashionSearch()
    results = system.search(sys.argv[1])
    
    if results:
        html = system.create_html(sys.argv[1], results)
        print(f"\n✅ Done: {html}")

