"""
Test new outfit with renamed file
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🧪 NEW OUTFIT TEST")
print("=" * 70)

# Load FASHN result
print("\n📍 Loading FASHN result...")
with open('new_outfit_step1_fashn.png', 'rb') as f:
    fashn_result = f.read()

fashn_img = Image.open(io.BytesIO(fashn_result))
print("✅ FASHN loaded (Adidas sweatshirt with face locked)")

# Load garments
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("\n📍 Loading garments...")
trousers = Image.open(ai_pics_path + 'blacktrousers.png')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')
print("✅ Garments loaded")

# Gemini for bottoms
print("\n📍 Gemini - Adding trousers + trainers...")

prompt = """Add bottoms and shoes from references.

PRESERVE EXACTLY:
- Face and hair
- Adidas sweatshirt (black with white stripes and logo)
- Upper body

REPLACE:
- Gray sweatpants → Black trousers (from reference)
- Black socks → Brown/burgundy Adidas trainers (from reference)

Gray studio background.
High detail on all garments."""

response = gemini_model.generate_content(
    [prompt, fashn_img, trousers, trainers],
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('new_outfit_FINAL.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ COMPLETE: new_outfit_FINAL.png")
                    print("\n" + "=" * 70)
                    print("✅ NEW OUTFIT GENERATED!")
                    print("=" * 70)
                    print("\n💰 Cost: $0.075 (FASHN) + $0.10 (Gemini) = $0.175")
                    print("\n📊 Compare quality:")
                    print("   - test3_diff_pants_FINAL.png (polka dot shirt)")
                    print("   - new_outfit_FINAL.png (Adidas sweatshirt)")
                    print("\n💡 If both look good → APPROACH IS CONSISTENT!")
                    print("   Ready for production! 🚀")
                    print("=" * 70)

