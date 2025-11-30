"""
Test CLIP Visual Search - WITH HTML VIEWER
Creates a beautiful HTML page to view all results in your browser!
"""
import os
import sys
import requests
import json
from PIL import Image
import io
import torch
import clip
import base64
from datetime import datetime

# Set up API keys
SERPAPI_KEY = '0da357d5fb4a223dc85215b798a5c9c29201b8c8d2a3c7620266aa6176e667c8'

print("=" * 70)
print("🎯 CLIP VISUAL SEARCH - HTML VIEWER")
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

def image_to_base64(image):
    """Convert PIL image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def test_visual_search(image_path, search_query):
    """Complete visual search test with HTML output"""
    
    print("\n" + "=" * 70)
    print(f"📸 Testing with: {os.path.basename(image_path)}")
    print("=" * 70)
    
    # Step 1: Load query image
    print(f"\n📸 Step 1: Loading your image...")
    try:
        query_img = Image.open(image_path).convert('RGB')
        query_img.thumbnail((400, 400))  # Resize for display
        query_img_base64 = image_to_base64(query_img)
        print(f"   ✅ Image loaded")
    except Exception as e:
        print(f"   ❌ Error loading image: {e}")
        return
    
    # Step 2: Generate embedding
    print(f"\n🧮 Step 2: Generating CLIP embedding...")
    query_embedding = get_image_embedding(Image.open(image_path).convert('RGB'))
    print(f"   ✅ Embedding generated")
    
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
            product_img.thumbnail((300, 300))
            
            product_embedding = get_image_embedding(product_img)
            similarity = float((query_embedding @ product_embedding.T))
            
            results.append({
                **product,
                'similarity': similarity,
                'image_base64': image_to_base64(product_img)
            })
            
            print(f"   [{i}/15] {similarity:.1%} - {product['title'][:50]}...")
            
        except Exception as e:
            print(f"   [{i}/15] ❌ Skip")
            continue
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Step 5: Create HTML
    print(f"\n🌐 Step 5: Creating HTML page...")
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Search Results - {search_query}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        
        h1 {{
            font-size: 42px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .subtitle {{
            font-size: 18px;
            opacity: 0.9;
        }}
        
        .query-section {{
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .query-image {{
            text-align: center;
        }}
        
        .query-image img {{
            max-width: 400px;
            border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}
        
        .query-info {{
            text-align: center;
            margin-top: 20px;
        }}
        
        .query-info h2 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        
        .result-card {{
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
        }}
        
        .result-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        
        .rank-badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: #667eea;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            z-index: 10;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        
        .similarity-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(102, 126, 234, 0.95);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            z-index: 10;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        
        .product-image {{
            width: 100%;
            height: 300px;
            object-fit: cover;
            background: #f5f5f5;
        }}
        
        .product-info {{
            padding: 20px;
        }}
        
        .product-title {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .product-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .product-price {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .product-source {{
            font-size: 14px;
            color: #888;
            background: #f5f5f5;
            padding: 4px 12px;
            border-radius: 12px;
        }}
        
        .buy-button {{
            display: block;
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: opacity 0.3s ease;
        }}
        
        .buy-button:hover {{
            opacity: 0.9;
        }}
        
        .stats {{
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-around;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            font-size: 14px;
            color: #888;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Visual Search Results</h1>
            <p class="subtitle">Powered by CLIP AI • Finding visually similar products</p>
        </header>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(results)}</div>
                <div class="stat-label">Products Found</div>
            </div>
            <div class="stat">
                <div class="stat-value">{results[0]['similarity']:.0%}</div>
                <div class="stat-label">Best Match</div>
            </div>
            <div class="stat">
                <div class="stat-value">{search_query}</div>
                <div class="stat-label">Search Query</div>
            </div>
        </div>
        
        <div class="query-section">
            <div class="query-image">
                <img src="data:image/jpeg;base64,{query_img_base64}" alt="Your Image">
            </div>
            <div class="query-info">
                <h2>Your Image</h2>
                <p>Finding products that look similar to this...</p>
            </div>
        </div>
        
        <div class="results-grid">
"""
    
    for i, result in enumerate(results, 1):
        html += f"""
            <div class="result-card">
                <div class="rank-badge">{i}</div>
                <div class="similarity-badge">{result['similarity']:.0%} Match</div>
                <img class="product-image" src="data:image/jpeg;base64,{result['image_base64']}" alt="{result['title']}">
                <div class="product-info">
                    <h3 class="product-title">{result['title']}</h3>
                    <div class="product-meta">
                        <span class="product-price">{result['price']}</span>
                        <span class="product-source">{result['source']}</span>
                    </div>
                    <a href="{result['link']}" target="_blank" class="buy-button">
                        View Product →
                    </a>
                </div>
            </div>
"""
    
    html += """
        </div>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    filename = f"visual_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, 'w') as f:
        f.write(html)
    
    print(f"   ✅ HTML created: {filename}")
    
    # Open in browser
    import webbrowser
    webbrowser.open('file://' + os.path.abspath(filename))
    
    print("\n" + "=" * 70)
    print("✅ VISUAL SEARCH COMPLETE!")
    print("=" * 70)
    print(f"\n🌐 Opening results in your browser...")
    print(f"📄 File saved: {filename}")
    
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        search_query = sys.argv[2] if len(sys.argv) > 2 else "clothing"
        results = test_visual_search(image_path, search_query)
    else:
        print("\n💡 Usage: python test_clip_html_viewer.py 'image_path' 'search_query'")
        print("\n📝 Example:")
        print("   python test_clip_html_viewer.py '/Users/gavinwalker/Desktop/AI OUTFIT PICS/IMG_6563.PNG' 'red dress'")
