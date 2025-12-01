"""
VTO on White Mannequin
Professional product photography approach
"""
import os
import base64
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎨 VTO on Professional White Mannequin")
print("=" * 70)

# Load garments
print("\n📦 Loading garments...")
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = f.read()
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
    shorts = f.read()
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
    boots = f.read()

garments = [Image.open(io.BytesIO(g)) for g in [shirt, shorts, boots]]

prompt = """Create a professional product photography image showing these 3 clothing items on a WHITE PLASTIC MANNEQUIN.

CRITICAL REQUIREMENTS:

1. MANNEQUIN SPECIFICATIONS:
   - Pure white/off-white plastic mannequin (like in retail stores)
   - Smooth, matte finish (not glossy)
   - Featureless head (no facial features, just smooth egg-shaped)
   - Full body with arms and legs
   - Professional retail display mannequin style
   - Standing straight, arms slightly away from body

2. CLOTHING DISPLAY:
   - All 3 garments fitted properly on the mannequin
   - Shirt, shorts, and boots clearly visible
   - Natural draping and fit
   - Professional product photography styling

3. PHOTOGRAPHY:
   - Clean light gray studio background (#f0f0f0)
   - Soft, even studio lighting (no harsh shadows)
   - Centered composition, full body shot
   - High-quality professional fashion photography
   - Focus on showcasing the clothes

Think: high-end retail store window display or premium e-commerce product photo.

The mannequin should look elegant and professional, not human-like.

Return ONLY the final image."""

print("\n🎨 Generating mannequin display...")

response = model.generate_content(
    [prompt] + garments,
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
                    result_bytes = part.inline_data.data
                    
                    with open('vto_white_mannequin.png', 'wb') as f:
                        f.write(result_bytes)
                    
                    print("✅ Saved: vto_white_mannequin.png")
                    print("\n💡 This should show a clean, professional mannequin display!")
                    print("   Perfect for product browsing without identity issues.")

print("\n" + "=" * 70)
