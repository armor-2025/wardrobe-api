"""
Test: Can mannequin generate ALL items perfectly in one call?
Jumper + Jeans + Boots + Cap in single generation
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎨 Testing: ALL 4 Items on Mannequin in ONE Call")
print("=" * 70)

base_path = '/Users/gavinwalker/Downloads/files (4)/'

# Load ALL items
print("\n📦 Loading all garments...")
with open(base_path + 'IMG_5747.jpg', 'rb') as f:
    jumper = Image.open(io.BytesIO(f.read()))
with open(base_path + 'white jeans.png', 'rb') as f:
    jeans = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5940.PNG', 'rb') as f:
    cap = Image.open(io.BytesIO(f.read()))

print("✅ All items loaded")

# Generate ALL at once on mannequin
prompt = """Create professional fashion photography showing ALL 4 items as a complete outfit on a model:

ITEMS TO SHOW:
1. Black Adidas jumper/sweater with white stripes
2. Light gray/white sweatpants or jeans  
3. Tan/brown leather cowboy boots
4. Yellow/cream baseball cap

REQUIREMENTS:
- Full body standing pose, front-facing
- Professional studio with clean gray background (#E5E5E5)
- Soft even studio lighting
- High detail rendering - capture ALL texture details:
  * Adidas logo and stripes on jumper
  * Fabric texture on pants
  * Leather texture and stitching on boots
  * Cap details and fit
- Neutral fashion model
- ALL 4 items must be clearly visible and detailed

Focus on PERFECT rendering of all garments and accessories.

Return ONLY the final complete outfit image."""

print("\n🎨 Generating complete outfit in ONE call...")

response = model.generate_content(
    [prompt, jumper, jeans, boots, cap],
    generation_config=genai.types.GenerationConfig(
        temperature=0.4,
        top_p=0.8,
        top_k=40,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('mannequin_all_4_items.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: mannequin_all_4_items.png")
                    
                    print("\n" + "=" * 70)
                    print("📊 COMPARISON TEST")
                    print("=" * 70)
                    print("\nSequential (your face): new_outfit_complete.png")
                    print("   - Cost: $0.50 (5 steps)")
                    print("   - Face: Your actual face preserved")
                    print("   - Quality: Degrades slightly each step")
                    print("   - Cap had issues")
                    print("\nMannequin (one call): mannequin_all_4_items.png")
                    print("   - Cost: $0.10 (1 step!)")
                    print("   - Face: Generic mannequin")
                    print("   - Quality: Should be perfect clothes")
                    print("   - All items in one go")
                    print("\n💡 If mannequin looks perfect, we could use it")
                    print("   for the 'browse outfits' feature!")
                    print("=" * 70)

