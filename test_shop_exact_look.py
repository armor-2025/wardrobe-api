"""
Test Shop the Exact Look with Mush screenshot
"""
import os
import google.generativeai as genai
from PIL import Image
import json

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("=" * 70)
print("🧪 TESTING: Shop the Exact Look")
print("=" * 70)

# Use the green blazer photo from Mush
image_path = '/mnt/user-data/uploads/IMG_6593.PNG'
image = Image.open(image_path)

print("\n📸 Analyzing celebrity photo...")

gemini = genai.GenerativeModel('gemini-2.5-flash-image')

prompt = """Analyze this fashion photo and identify each clothing item worn by the person.

For each item, provide:
1. Item type (blazer, trousers, shoes, bag, sunglasses, etc.)
2. Extremely detailed visual description:
   - Exact color and shade
   - Material/texture (wool, leather, cotton, etc.)
   - Style details (oversized, fitted, cropped, etc.)
   - Special features (buttons, lapels, pockets, belt, etc.)
   - Pattern or finish

Be very specific about visual appearance - this will be used for visual search.

Return as JSON array:
[
  {
    "type": "blazer",
    "description": "emerald green oversized single-breasted blazer with notched lapels and silver button closure"
  },
  ...
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

except Exception as e:
    print(f"\n⚠️  Could not parse JSON: {e}")
    print("This is fine - we can handle text parsing")

print("\n" + "="*70)
print("💡 WHAT HAPPENS NEXT")
print("="*70)

print("""
For each item Gemini found, we would:

1. Crop the item from the photo (using bbox or segmentation)
2. Generate CLIP visual embedding from cropped image
3. Search product database: 
   SELECT * FROM products
   WHERE category = 'blazers'
   ORDER BY image_embedding <=> query_embedding
   LIMIT 20
4. Return products that LOOK most visually similar

This is pure visual matching - no tags involved!
""")

print("\n💰 COST:")
print("="*70)
print("""
Per celebrity photo analysis:
- Gemini analysis: $0.10
- CLIP embeddings: $0.00 (runs locally)
- Database search: $0.00 (Supabase free tier)
────────────────────────────
TOTAL: $0.10 per search
""")

