"""
More refined tests building on Test A success
"""
import requests
import base64
import os
import time
from PIL import Image
import io
import google.generativeai as genai

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'
os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("=" * 70)
print("🔬 MORE REFINEMENT: Focus on Texture Detail")
print("=" * 70)

def call_fashn(person_path, garment_path):
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

# Step 1: FASHN for shirt
print("\n📍 STEP 1: FASHN Shirt")
shirt_result = call_fashn(base_path + 'IMG_6033.jpeg', base_path + 'IMG_5937.PNG')

if not shirt_result:
    print("❌ FASHN failed")
    exit()

with open('new_step1_shirt.png', 'wb') as f:
    f.write(shirt_result)
print("✅ Saved: new_step1_shirt.png")

shirt_img = Image.open(io.BytesIO(shirt_result))

with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))


# ==========================================
# TEST D: Emphasis on preserving existing details + texture
# ==========================================
print("\n🧪 TEST D: Preserve shirt detail + capture shorts texture")

prompt_d = """Professional garment replacement with maximum detail preservation.

CURRENT IMAGE (input):
- Person wearing white polka dot shirt
- Gray sweatpants
- Black socks

PRESERVATION (DO NOT CHANGE):
✓ Face: Keep exact facial features
✓ Hair: Keep exact curly brown hair
✓ Polka dot shirt: Keep ALL polka dots, pattern, collar, fabric texture exactly as shown
✓ Body proportions: Natural size
✓ Pose: Same standing position

REPLACEMENT TASK (from reference images):
Replace ONLY lower body:
1. Black leather shorts (see reference image):
   - Material: Black leather with reptile/crocodile texture pattern
   - Fit: Loose, relaxed fit (NOT tight)
   - Length: Knee-length
   - Capture the textured surface detail from reference image
   - Should have visible texture/pattern on the leather

2. Tan cowboy boots (see reference image):
   - Western style with decorative stitching
   - Tan/brown leather color
   - Mid-calf height

CRITICAL DETAILS:
- The polka dot shirt MUST retain all its dots and detail
- The leather shorts MUST show texture/pattern from reference
- High detail rendering on all garments

Background: Professional gray studio (#D0D0D0)

This is precision editing - change only what's specified."""

response_d = gemini_model.generate_content(
    [prompt_d, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response_d, 'candidates') and response_d.candidates:
    for candidate in response_d.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('new_testD_detailed.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: new_testD_detailed.png")


# ==========================================
# TEST E: Two-pass approach (bottoms, then polish)
# ==========================================
print("\n🧪 TEST E: Two-pass refinement")

# Pass 1: Add bottoms
prompt_e1 = """Add lower body garments from reference images.

KEEP EXACT:
- Face, hair
- Polka dot shirt (keep all details)

REPLACE:
- Gray sweatpants → Black leather shorts (loose fit, textured leather)
- Black socks → Tan cowboy boots

Gray studio background."""

response_e1 = gemini_model.generate_content(
    [prompt_e1, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response_e1, 'candidates') and response_e1.candidates:
    for candidate in response_e1.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    pass1_bytes = part.inline_data.data
                    with open('new_testE_pass1.png', 'wb') as f:
                        f.write(pass1_bytes)
                    print("✅ Saved: new_testE_pass1.png")
                    
                    # Pass 2: Enhance texture details
                    pass1_img = Image.open(io.BytesIO(pass1_bytes))
                    
                    prompt_e2 = """Detail enhancement pass.

Enhance texture and detail quality:
- Sharpen polka dots on shirt
- Enhance leather texture on shorts (should show pattern/grain)
- Maintain all face/hair details
- Keep studio background

This is detail enhancement, not regeneration."""

                    response_e2 = gemini_model.generate_content(
                        [prompt_e2, pass1_img],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.05,
                            top_p=0.4,
                            top_k=8,
                        )
                    )
                    
                    if hasattr(response_e2, 'candidates') and response_e2.candidates:
                        for candidate2 in response_e2.candidates:
                            if hasattr(candidate2, 'content') and candidate2.content:
                                for part2 in candidate2.content.parts:
                                    if hasattr(part2, 'inline_data') and part2.inline_data:
                                        with open('new_testE_pass2_enhanced.png', 'wb') as f:
                                            f.write(part2.inline_data.data)
                                        print("✅ Saved: new_testE_pass2_enhanced.png")


# ==========================================
# TEST F: Use higher quality settings
# ==========================================
print("\n🧪 TEST F: Maximum quality settings")

prompt_f = """Ultra high-quality garment replacement.

SOURCE IMAGE: Person in polka dot shirt
REFERENCE IMAGES: Black textured leather shorts, tan cowboy boots

TASK: Replace lower body garments while preserving upper body completely.

ULTRA-DETAILED REQUIREMENTS:

PRESERVE (pixel-perfect):
- Face: Every facial feature exact
- Hair: Every curl and strand
- Polka dot shirt: Every dot, every fabric fold, collar detail
- Skin tone
- Body proportions

REPLACE with HIGH DETAIL:
- Black leather shorts from reference:
  * Must show leather grain/texture
  * Loose comfortable fit
  * Knee length
  * Study reference image texture carefully
  
- Tan cowboy boots from reference:
  * Capture all stitching details
  * Leather texture
  * Proper boot shape

Professional fashion photography quality.
Studio background: #D0D0D0 gray.

Render at maximum detail quality."""

response_f = gemini_model.generate_content(
    [prompt_f, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.08,
        top_p=0.45,
        top_k=12,
    )
)

if hasattr(response_f, 'candidates') and response_f.candidates:
    for candidate in response_f.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('new_testF_max_quality.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: new_testF_max_quality.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ NEW REFINEMENT TESTS COMPLETE!")
print("=" * 70)
print("\nCompare:")
print("  D. new_testD_detailed.png - Texture emphasis")
print("  E. new_testE_pass2_enhanced.png - Two-pass refinement")
print("  F. new_testF_max_quality.png - Maximum quality")
print("\n💡 Looking for:")
print("   ✅ Textured leather shorts (not plain)")
print("   ✅ Clear polka dots on shirt")
print("   ✅ Professional quality")
print("=" * 70)

