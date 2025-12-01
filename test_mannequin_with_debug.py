"""
Test with better error handling
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎨 Testing Mannequin Generation")
print("=" * 70)

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("\n📦 Loading items...")
try:
    with open(base_path + 'IMG_5747.jpg', 'rb') as f:
        jumper = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'white jeans.png', 'rb') as f:
        jeans = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'IMG_5938.PNG', 'rb') as f:
        boots = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'IMG_5940.PNG', 'rb') as f:
        cap = Image.open(io.BytesIO(f.read()))
    print("✅ All items loaded")
except Exception as e:
    print(f"❌ Error loading files: {e}")
    exit()

prompt = """Show these 4 clothing items as a complete outfit on a fashion model:
- Jumper/sweater
- Pants  
- Boots
- Cap

Professional studio photo, clean gray background, full body shot."""

print("\n🎨 Calling Gemini API...")

try:
    response = model.generate_content(
        [prompt, jumper, jeans, boots, cap],
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
    )
    
    print("✅ API call returned")
    
    if hasattr(response, 'candidates') and response.candidates:
        print(f"✅ Found {len(response.candidates)} candidates")
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open('mannequin_test.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print("✅ Saved: mannequin_test.png")
                        print("💰 Cost: $0.10")
                        exit()
    
    print("❌ No image data in response")
    print(f"Response: {response}")
    
except Exception as e:
    print(f"❌ Error during generation: {e}")
    import traceback
    traceback.print_exc()

