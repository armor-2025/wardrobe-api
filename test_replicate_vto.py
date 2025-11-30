"""
Test Replicate's virtual try-on models
"""
import replicate
import os
import requests
from PIL import Image
import io
import google.generativeai as genai

os.environ['REPLICATE_API_TOKEN'] = 'YOUR_TOKEN'  # Get from replicate.com
os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🔬 TESTING REPLICATE VTO MODELS")
print("=" * 70)

# ==========================================
# STEP 1: Gemini creates PERFECT outfit on mannequin
# ==========================================
print("\n📍 Step 1: Gemini - Perfect outfit on mannequin")

shirt = Image.open(base_path + 'IMG_5937.PNG')
shorts = Image.open(base_path + 'IMG_5936.PNG')
boots = Image.open(base_path + 'IMG_5938.PNG')

mannequin_prompt = """Create perfect full-body fashion mannequin:
- White polka dot shirt (exact pattern from reference)
- Black leather shorts (exact texture from reference)
- Tan cowboy boots (exact style from reference)

Standing pose, gray studio background.
Maximum detail - this is a reference image for virtual try-on."""

response = gemini_model.generate_content(
    [mannequin_prompt, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.4)
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('replicate_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Perfect mannequin created")
                    print("💰 Cost: $0.10")

if not mannequin_bytes:
    print("❌ Gemini failed")
    exit()

# ==========================================
# STEP 2: Try Replicate VTO models
# ==========================================
print("\n📍 Step 2: Testing Replicate VTO models...")

# Available VTO models on Replicate:
vto_models = [
    "cuuupid/idm-vton",  # IDM-VTON
    "viktorfa/oot_diffusion",  # OOTDiffusion
    "zsxkib/shop-app-viton-hd",  # VITON-HD
]

print("\n🔍 Available VTO models on Replicate:")
for i, model in enumerate(vto_models, 1):
    print(f"   {i}. {model}")

print("\n💡 To test these:")
print("   1. Sign up at replicate.com")
print("   2. Get API token")
print("   3. Try each model with:")
print("      - person_image: your photo")
print("      - garment_image: Gemini's perfect mannequin")

print("\n📝 Example code:")
print("""
import replicate

output = replicate.run(
    "cuuupid/idm-vton",
    input={
        "human_img": open("person.jpg", "rb"),
        "garm_img": open("mannequin.png", "rb"),
        "category": "full"
    }
)
""")

print("\n" + "=" * 70)
print("🎯 ALTERNATIVE APPROACHES TO TEST")
print("=" * 70)

print("\n1. **Replicate VTO models**")
print("   Cost: ~$0.01-0.05 per try-on")
print("   Gemini mannequin ($0.10) + Replicate VTO ($0.03) = $0.13 total")

print("\n2. **Runway ML Gen-2**")
print("   Advanced image-to-image")
print("   Cost: ~$0.05 per generation")

print("\n3. **Stability AI with ControlNet**")
print("   Preserve pose/structure while changing clothes")
print("   Cost: ~$0.02 per image")

print("\n4. **Open source: IDM-VTON (run locally)**")
print("   Free if you have GPU")
print("   GitHub: yisol/IDM-VTON")

print("\n" + "=" * 70)
print("💡 RECOMMENDATION")
print("=" * 70)
print("\nBased on our testing, here's what to try:")
print("\n🥇 Option 1: Test Replicate's IDM-VTON")
print("   - Specifically designed for virtual try-on")
print("   - Should preserve face better than Gemini")
print("   - Gemini mannequin + Replicate VTO = $0.13")

print("\n🥈 Option 2: Keep current approach but add:")
print("   - Face restoration API (CodeFormer/GFPGAN)")
print("   - After Gemini steps, restore face to original")
print("   - Cost: +$0.01-0.02")

print("\n🥉 Option 3: Hybrid approach")
print("   - FASHN for top (face lock)")
print("   - Replicate VTO for full outfit")
print("   - Compare quality")

print("\n📌 Want me to:")
print("   A) Help you set up Replicate and test IDM-VTON?")
print("   B) Test face restoration on current results?")
print("   C) Research more specialized fashion APIs?")
print("=" * 70)

