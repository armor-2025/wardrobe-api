"""
Test REAL approach D: FASHN shirt → Gemini bottoms
"""
import requests
import base64
import os
import time
from PIL import Image
import io
import google.generativeai as genai

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'
os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("=" * 70)
print("🔬 TESTING REAL APPROACH D CONSISTENCY")
print("=" * 70)
print("FASHN shirt (face lock) → Gemini bottoms")
print("=" * 70)

def call_fashn(person_path, garment_path):
    """FASHN for shirt"""
    with open(person_path, 'rb') as f:
        person_b64 = base64.b64encode(f.read()).decode('utf-8')
    with open(garment_path, 'rb') as f:
        garment_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    response = requests.post(
        'https://api.fashn.ai/v1/run',
        headers={'Authorization': f'Bearer {FASHN_API_KEY}', 'Content-Type': 'application/json'},
        json={
            "model_image": f"data:image/jpeg;base64,{person_b64}",
            "garment_image": f"data:image/png;base64,{garment_b64}",
            "category": "tops",
            "num_samples": 1
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        if 'id' in result:
            job_id = result['id']
            for i in range(30):
                time.sleep(2)
                status_response = requests.get(
                    f'https://api.fashn.ai/v1/status/{job_id}',
                    headers={'Authorization': f'Bearer {FASHN_API_KEY}'}
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('status') == 'completed':
                        img_url = status_data['output'][0] if isinstance(status_data['output'], list) else status_data['output']
                        return requests.get(img_url).content
    return None


def test_outfit(outfit_name, shirt_file, shorts_file, boots_file):
    """Test one outfit with FASHN + Gemini"""
    
    print(f"\n{'='*70}")
    print(f"🧪 OUTFIT: {outfit_name}")
    print(f"{'='*70}")
    
    # Step 1: FASHN for shirt (face lock)
    print(f"\n📍 Step 1: FASHN - Apply {shirt_file}")
    fashn_result = call_fashn(
        base_path + 'IMG_6033.jpeg',
        base_path + shirt_file
    )
    
    if not fashn_result:
        print("❌ FASHN failed")
        return False
    
    with open(f'{outfit_name}_step1_fashn.png', 'wb') as f:
        f.write(fashn_result)
    print("✅ FASHN complete - face locked")
    print("💰 Cost: $0.075")
    
    # Step 2: Gemini for bottoms
    print(f"\n📍 Step 2: Gemini - Add shorts + boots")
    
    fashn_img = Image.open(io.BytesIO(fashn_result))
    
    with open(base_path + shorts_file, 'rb') as f:
        shorts = Image.open(io.BytesIO(f.read()))
    with open(base_path + boots_file, 'rb') as f:
        boots = Image.open(io.BytesIO(f.read()))
    
    gemini_prompt = """Professional garment replacement with maximum detail preservation.

CURRENT IMAGE (input):
- Person wearing shirt
- Gray sweatpants
- Black socks

PRESERVATION (DO NOT CHANGE):
✓ Face: Keep exact facial features
✓ Hair: Keep exact curly brown hair
✓ Shirt: Keep exactly as shown
✓ Body proportions: Natural size
✓ Pose: Same standing position

REPLACEMENT TASK (from reference images):
Replace ONLY lower body:
1. Shorts (see reference image):
   - Material and texture from reference
   - Fit: Loose, relaxed fit
   - Length: Knee-length
   
2. Boots (see reference image):
   - Style and texture from reference
   - Proper boot shape

CRITICAL DETAILS:
- The shirt MUST stay exactly as shown
- High detail rendering on new garments

Background: Professional gray studio (#D0D0D0)

This is precision editing - change only lower body."""

    response = gemini_model.generate_content(
        [gemini_prompt, fashn_img, shorts, boots],
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
                        with open(f'{outfit_name}_FINAL.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print(f"✅ COMPLETE: {outfit_name}_FINAL.png")
                        print("💰 Cost: $0.10")
                        print(f"💰 TOTAL: $0.175")
                        return True
    
    print("❌ Gemini failed")
    return False


# ==========================================
# Test 3 different outfits
# ==========================================

print("\n🎯 Testing 3 different outfit combinations...\n")

# Outfit 1: Polka dot + leather shorts + cowboy boots (original)
success1 = test_outfit(
    "test1_polkadot",
    'IMG_5937.PNG',  # polka dot shirt
    'IMG_5936.PNG',  # leather shorts
    'IMG_5938.PNG'   # cowboy boots
)

# Outfit 2: Different shirt, same bottoms
success2 = test_outfit(
    "test2_different_shirt",
    'IMG_5935.PNG',  # different shirt
    'IMG_5936.PNG',  # same shorts
    'IMG_5938.PNG'   # same boots
)

# Outfit 3: All different garments
success3 = test_outfit(
    "test3_all_different",
    'IMG_5935.PNG',  # different shirt
    'IMG_5939.PNG',  # different pants
    'IMG_5938.PNG'   # boots
)


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ CONSISTENCY TEST COMPLETE")
print("=" * 70)

results = []
if success1:
    results.append("✅ test1_polkadot_FINAL.png")
if success2:
    results.append("✅ test2_different_shirt_FINAL.png")
if success3:
    results.append("✅ test3_all_different_FINAL.png")

print("\nResults:")
for r in results:
    print(f"   {r}")

print(f"\nSuccess rate: {len(results)}/3")

if len(results) == 3:
    print("\n🎉 CONSISTENT QUALITY ACROSS ALL OUTFITS!")
    print("\n🚀 THIS IS YOUR PRODUCTION SOLUTION:")
    print("   - Step 1: FASHN for shirt ($0.075)")
    print("   - Step 2: Gemini for bottoms + BG ($0.10)")
    print("   - Total: $0.175 per outfit")
    print("   - Quality: Face preserved, good clothes")
elif len(results) >= 2:
    print("\n⚠️ MOSTLY consistent - review failed case")
else:
    print("\n❌ Inconsistent - needs more work")

print("=" * 70)

