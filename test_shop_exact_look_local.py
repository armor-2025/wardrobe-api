"""
Test Shop the Exact Look with local image
"""
import os
import google.generativeai as genai
from PIL import Image
import json
import sys

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("=" * 70)
print("🧪 TESTING: Shop the Exact Look")
print("=" * 70)

# Let user specify image or use default
if len(sys.argv) > 1:
    image_path = sys.argv[1]
else:
    # Default to one of your existing photos
    image_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')

print(f"\n📸 Using image: {image_path}")

if not os.path.exists(image_path):
    print(f"❌ File not found: {image_path}")
    print("\nUsage: python test_shop_exact_look_local.py <path_to_image>")
    print("\nOr drop any fashion photo here and I'll analyze it!")
    exit()

image = Image.open(image_path)
print("✅ Image loaded")

print("\n🤖 Analyzing with Gemini...")

gemini = genai.GenerativeModel('gemini-2.5-flash-image')

prompt = """Analyze this fashion photo and identify each clothing item worn by the person.

For each item, provide:
1. Item type (blazer, trousers, dress, shoes, bag, sunglasses, etc.)
2. Extremely detailed visual description for visual search:
   - Exact color and shade
   - Material/texture (wool, leather, cotton, silk, denim, etc.)
   - Style details (oversized, fitted, cropped, slim, wide-leg, etc.)
   - Special features (buttons, lapels, pockets, belt, zipper, collar style, etc.)
   - Pattern or finish (solid, textured, shiny, matte, etc.)
   - Cut and silhouette

Be VERY specific about visual appearance - this will be used to find visually similar products.

Return as JSON array:
[
  {
    "type": "blazer",
    "description": "emerald green oversized single-breasted wool blazer with peak lapels, single button closure, and structured shoulders"
  }
]"""

response = gemini.generate_content([prompt, image])

print("\n✅ Gemini Analysis:")
print("="*70)
print(response.text)

# Try to parse JSON
try:
    text = response.text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    items = json.loads(text.strip())
    
    print("\n📋 Parsed Items:")
    print("="*70)
    for i, item in enumerate(items, 1):
        print(f"\n{i}. {item['type'].upper()}")
        print(f"   Description: {item['description']}")
        
    print("\n" + "="*70)
    print("🔍 VISUAL SEARCH PROCESS")
    print("="*70)
    
    for item in items:
        print(f"\n{item['type'].upper()}:")
        print(f"   1. Crop this item from photo")
        print(f"   2. Generate CLIP embedding from cropped image")
        print(f"   3. Query database:")
        print(f"      SELECT * FROM products")
        print(f"      WHERE category = '{item['type']}s'")
        print(f"      ORDER BY image_embedding <=> clip_embedding")
        print(f"      LIMIT 20")
        print(f"   4. Return visually similar items")

except Exception as e:
    print(f"\n⚠️  Could not parse JSON: {e}")

print("\n" + "="*70)
print("💡 NEXT: Install CLIP for Visual Embeddings")
print("="*70)

print("""
Want me to:
A) Install CLIP and generate actual embeddings
B) Set up Supabase database for products
C) Build product import with CLIP embeddings
D) Create complete API
""")

