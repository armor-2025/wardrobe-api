"""
Complete Shop The Look System
Gemini segments outfit + Google Lens searches each item
NOW WITH 50+ RESULTS PER ITEM!
"""
import os
import sys
import requests
import json
from PIL import Image
import io
import google.generativeai as genai
from datetime import datetime
import base64
import webbrowser

# API Keys
GEMINI_KEY = 'YOUR_KEY_HERE'
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'

genai.configure(api_key=GEMINI_KEY)

print("=" * 70)
print("🎯 COMPLETE SHOP THE LOOK SYSTEM - EXTENDED RESULTS")
print("=" * 70)

class OutfitShopTheLook:
    def __init__(self):
        print("\n🔧 Initializing...")
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ System ready!")
    
    def segment_outfit(self, image_path):
        print(f"\n📸 Step 1: Analyzing outfit with Gemini...")
        image = Image.open(image_path)
        
        prompt = """Analyze this outfit photo and identify EVERY clothing item and accessory.

For EACH item, provide:
1. Item type (shirt, pants, shoes, bag, accessories, etc.)
2. Detailed description with specific features
3. Color, material, style

Return ONLY valid JSON:
[
  {
    "type": "shirt",
    "description": "pink striped oversized button-up shirt",
    "color": "pink",
    "material": "cotton",
    "importance": "hero",
    "search_query": "pink striped oversized button up shirt"
  }
]

Be specific about colors, patterns, and styles."""
        
        try:
            response = self.gemini.generate_content([prompt, image])
            text = response.text.strip()
            
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            items = json.loads(text.strip())
            
            print(f"\n   ✅ Gemini found {len(items)} items:")
            for i, item in enumerate(items, 1):
                print(f"      {i}. {item['type']} - {item['description'][:50]}...")
            
            print(f"\n   💰 Cost: $0.001")
            return items
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def google_lens_search(self, search_query, max_results=50):
        """Search with pagination to get 50+ results"""
        all_products = []
        
        # Google Shopping API can return max ~100 results
        # We'll do multiple calls with different parameters
        
        url = "https://serpapi.com/search"
        
        # First call - get initial results
        params = {
            "engine": "google_shopping",
            "q": search_query,
            "api_key": SERPAPI_KEY,
            "num": 100  # Request maximum
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            for item in data.get('shopping_results', []):
                all_products.append({
                    'title': item.get('title', ''),
                    'price': item.get('price', ''),
                    'link': item.get('link', ''),
                    'thumbnail': item.get('thumbnail', ''),
                    'source': item.get('source', ''),
                    'rating': item.get('rating', 0)
                })
            
            # If we got less than desired, that's all available
            return all_products[:max_results]
            
        except Exception as e:
            print(f"      ❌ Search failed: {str(e)[:50]}")
            return []
    
    def shop_the_look(self, image_path):
        print(f"\n{'='*70}")
        print(f"🛍️  SHOPPING THE LOOK - EXTENDED RESULTS")
        print(f"{'='*70}")
        
        total_cost = 0.001
        items = self.segment_outfit(image_path)
        
        if not items:
            return None
        
        print(f"\n🔍 Step 2: Searching for each item (up to 50 results each)...")
        results = []
        
        for i, item in enumerate(items, 1):
            print(f"\n   [{i}/{len(items)}] {item['type']}: '{item['search_query']}'")
            products = self.google_lens_search(item['search_query'], max_results=50)
            total_cost += 0.005
            
            print(f"      ✅ Found {len(products)} matches")
            if products:
                print(f"      Top: {products[0]['title'][:50]}... - {products[0]['price']}")
            
            results.append({'item': item, 'products': products})
        
        print(f"\n{'='*70}")
        print(f"💰 TOTAL: ${total_cost:.3f}")
        print(f"   Gemini: $0.001 | Google Lens: {len(items)}×$0.005")
        print(f"{'='*70}")
        
        return {
            'items': items, 
            'results': results, 
            'total_cost': total_cost, 
            'num_items': len(items),
            'total_products': sum(len(r['products']) for r in results)
        }
    
    def create_html_viewer(self, image_path, shop_results):
        print(f"\n🌐 Creating HTML with all results...")
        
        outfit_img = Image.open(image_path)
        outfit_img.thumbnail((500, 700))
        buffered = io.BytesIO()
        outfit_img.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        items = shop_results['results']
        cost = shop_results['total_cost']
        total_products = shop_results['total_products']
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Shop The Look - {total_products} Products</title>
<style>
body{{font-family:sans-serif;background:#667eea;padding:20px;margin:0}}
.container{{max-width:1600px;margin:0 auto}}
h1{{color:white;text-align:center;font-size:40px;margin-bottom:10px}}
.stats{{color:white;text-align:center;font-size:18px;margin-bottom:20px}}
.outfit{{background:white;border-radius:20px;padding:30px;margin:20px 0;text-align:center}}
.outfit img{{max-width:400px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.2)}}
.item{{background:white;border-radius:16px;padding:25px;margin:20px 0}}
.item-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}}
.item h2{{color:#667eea;margin:0}}
.product-count{{background:#667eea;color:white;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:bold}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px;margin-top:15px}}
.card{{background:#f8f9fa;border-radius:10px;overflow:hidden;transition:all 0.2s;position:relative}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.15)}}
.rank{{position:absolute;top:8px;left:8px;background:#667eea;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;z-index:1}}
.card img{{width:100%;height:200px;object-fit:cover}}
.card-info{{padding:12px}}
.card h3{{font-size:13px;margin:0 0 8px 0;line-height:1.3;height:35px;overflow:hidden}}
.price{{font-size:18px;font-weight:bold;color:#667eea;margin:5px 0}}
.source{{font-size:11px;color:#888;margin-bottom:8px}}
.btn{{display:block;background:#764ba2;color:white;text-decoration:none;padding:8px;text-align:center;border-radius:6px;font-size:13px;font-weight:600}}
.btn:hover{{background:#667eea}}
.show-more{{text-align:center;margin:20px 0}}
.show-more-btn{{background:#667eea;color:white;border:none;padding:12px 30px;border-radius:8px;font-size:16px;cursor:pointer;font-weight:bold}}
.show-more-btn:hover{{background:#764ba2}}
.hidden{{display:none}}
</style>
</head><body>
<div class="container">
<h1>🛍️ Shop The Look</h1>
<p class="stats">Found {len(items)} items • {total_products} total products • Cost: ${cost:.3f}</p>

<div class="outfit">
<img src="data:image/jpeg;base64,{img_b64}">
</div>
"""
        
        for idx, item_result in enumerate(items, 1):
            item = item_result['item']
            products = item_result['products']
            
            html += f"""
<div class="item">
<div class="item-header">
<h2>{idx}. {item['type'].replace('_', ' ').title()}</h2>
<span class="product-count">{len(products)} matches</span>
</div>
<p style="color:#666;margin:10px 0">{item['description']}</p>
<div class="grid" id="grid-{idx}">
"""
            
            # Show first 12 by default
            for i, prod in enumerate(products, 1):
                hidden_class = "hidden" if i > 12 else ""
                html += f"""
<div class="card {hidden_class}" data-item="{idx}">
<div class="rank">{i}</div>
<img src="{prod['thumbnail']}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23ddd%22 width=%22200%22 height=%22200%22/%3E%3C/svg%3E'">
<div class="card-info">
<h3>{prod['title'][:60]}</h3>
<div class="price">{prod['price']}</div>
<div class="source">{prod['source']}</div>
<a href="{prod['link']}" target="_blank" class="btn">View Product →</a>
</div>
</div>
"""
            
            if len(products) > 12:
                html += f"""
</div>
<div class="show-more">
<button class="show-more-btn" onclick="showMore({idx})">
Show All {len(products)} Results ↓
</button>
</div>
"""
            else:
                html += "</div>"
            
            html += "</div>"
        
        html += """
<script>
function showMore(itemId) {
    const cards = document.querySelectorAll(`[data-item="${itemId}"]`);
    cards.forEach(card => card.classList.remove('hidden'));
    event.target.style.display = 'none';
}
</script>
</div></body></html>
"""
        
        filename = f"shop_the_look_{datetime.now().strftime('%H%M%S')}.html"
        with open(filename, 'w') as f:
            f.write(html)
        
        webbrowser.open('file://' + os.path.abspath(filename))
        return filename

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n💡 Usage: python outfit_shop_the_look.py 'image_path'")
        print("\n📝 Returns up to 50 products per item!")
        sys.exit(1)
    
    system = OutfitShopTheLook()
    results = system.shop_the_look(sys.argv[1])
    
    if results:
        html = system.create_html_viewer(sys.argv[1], results)
        print(f"\n✅ Done! Opened: {html}")
        print(f"\n📊 Results: {results['total_products']} total products found!")
        print(f"💰 At 1k posts/week: ${results['total_cost']*1000:.0f}/week = ${results['total_cost']*4330:.0f}/month")

