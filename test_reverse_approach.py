"""
Reverse Approach: Person + Outfit = Final
Keep person pixel-perfect, generate clothes separately, combine
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 Reverse Approach: Refine the INPAINTING strategy")
print("=" * 70)

# The "inpainting" approach worked best, so let's refine it further
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    user_img = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt_img = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
    shorts_img = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
    boots_img = Image.open(io.BytesIO(f.read()))

# Refined inpainting prompt
prompt = """Professional photo editing task: Inpaint new garments onto this person.

SOURCE IMAGE: Person in their current clothes
TARGET GARMENTS: Shirt, shorts, boots to apply

INPAINTING RULES (CRITICAL):
1. Identify clothing regions ONLY (shirt area, pants area, shoes area)
2. Preserve EVERYTHING else pixel-for-pixel:
   - Exact face (every feature identical)
   - Exact hair (color, style, texture)
   - Exact skin tone
   - Body proportions
   - Background
3. Replace ONLY the identified clothing regions with new garments
4. Seamless blending at garment edges
5. Match lighting, shadows, and perspective to original photo

This is precise inpainting - think of it as cutting out old clothes and pasting in new ones while keeping the person completely unchanged.

VERIFICATION: Does the final face match the original? Must be YES.

Output: The edited photo with new garments, person preserved."""

print("\n🎨 Applying refined inpainting approach...")
print("   (This worked best in previous test)")

response = model.generate_content(
    [prompt, user_img, shirt_img, shorts_img, boots_img],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,  # Very low for precision
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    result = part.inline_data.data
                    with open('test_refined_inpainting.png', 'wb') as f:
                        f.write(result)
                    print("✅ Saved: test_refined_inpainting.png")
                    print("\n💡 This should be even better than the first inpainting attempt!")

print("=" * 70)
