"""
Continue refining - getting very close!
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
print("🔬 KEEP REFINING: Focus on Shirt Detail Preservation")
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

# Get shirt from FASHN
print("\n📍 FASHN Shirt Application")
shirt_result = call_fashn(base_path + 'IMG_6033.jpeg', base_path + 'IMG_5937.PNG')

if not shirt_result:
    print("❌ FASHN failed")
    exit()

with open('iter_step1_shirt.png', 'wb') as f:
    f.write(shirt_result)

shirt_img = Image.open(io.BytesIO(shirt_result))

with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))


# ==========================================
# TEST G: Explicit "do not touch shirt" emphasis
# ==========================================
print("\n🧪 TEST G: Heavy shirt preservation emphasis")

prompt_g = """Garment replacement - ONLY change lower body.

CRITICAL - DO NOT TOUCH THESE AREAS:
❌ Do NOT modify the polka dot shirt in any way
❌ Do NOT change face or hair
❌ Do NOT alter upper body
❌ The shirt, face, and hair must remain pixel-identical

CURRENT STATE:
- Polka dot shirt (LOCKED - do not touch)
- Gray sweatpants (WILL REPLACE)
- Black socks (WILL REPLACE)

REPLACEMENT (lower body only):
✓ Black leather shorts with texture (from reference)
  - Loose fit, knee-length
  - Textured leather surface
✓ Tan cowboy boots (from reference)
  - Western style with stitching

This is LOWER BODY ONLY replacement.
Think of it as Photoshop: select lower body region, paste new garments.
Everything above the waist stays exactly the same.

Gray studio background."""

response_g = gemini_model.generate_content(
    [prompt_g, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.4,
        top_k=8,
    )
)

if hasattr(response_g, 'candidates') and response_g.candidates:
    for candidate in response_g.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('iter_testG_shirt_lock.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: iter_testG_shirt_lock.png")


# ==========================================
# TEST H: Reference the FASHN result explicitly
# ==========================================
print("\n🧪 TEST H: Explicitly reference current shirt state")

prompt_h = """Lower body garment replacement.

INPUT IMAGE DESCRIPTION:
This person is currently wearing a white polka dot shirt with black dots.
The shirt has a white collar and white sleeves.
This shirt is ALREADY PERFECT - do not change it.

TASK:
Replace only the lower body garments (below the waist):
- Remove: Gray sweatpants
- Add: Black textured leather shorts (loose fit, knee-length)
- Remove: Black socks  
- Add: Tan cowboy boots (western style)

Use the reference images to understand what the shorts and boots look like.

CRITICAL RULES:
1. The polka dot shirt in the input image is already correct
2. Keep it exactly as shown
3. Only edit below the waist
4. Maintain all face and hair details

Professional gray studio background.

This is selective region editing, not full image regeneration."""

response_h = gemini_model.generate_content(
    [prompt_h, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.03,
        top_p=0.35,
        top_k=6,
    )
)

if hasattr(response_h, 'candidates') and response_h.candidates:
    for candidate in response_h.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('iter_testH_reference.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: iter_testH_reference.png")


# ==========================================
# TEST I: Add shorts only first, verify shirt preservation
# ==========================================
print("\n🧪 TEST I: Shorts only first (verify shirt stays perfect)")

prompt_i1 = """Add black leather shorts ONLY.

PRESERVE EXACTLY:
- Face, hair
- Polka dot shirt (keep every dot)
- Upper body completely unchanged

CHANGE ONLY:
- Replace gray sweatpants with black leather shorts from reference
- Loose fit, textured leather
- Knee-length

Keep black socks for now.
Gray studio background."""

response_i1 = gemini_model.generate_content(
    [prompt_i1, shirt_img, shorts],
    generation_config=genai.types.GenerationConfig(
        temperature=0.03,
        top_p=0.35,
        top_k=6,
    )
)

if hasattr(response_i1, 'candidates') and response_i1.candidates:
    for candidate in response_i1.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    shorts_only_bytes = part.inline_data.data
                    with open('iter_testI_step1_shorts.png', 'wb') as f:
                        f.write(shorts_only_bytes)
                    print("✅ Saved: iter_testI_step1_shorts.png")
                    
                    # Now add boots
                    shorts_img = Image.open(io.BytesIO(shorts_only_bytes))
                    
                    prompt_i2 = """Replace footwear only.

PRESERVE:
- Everything currently visible (face, hair, shirt, shorts)

CHANGE:
- Replace black socks with tan cowboy boots from reference"""

                    response_i2 = gemini_model.generate_content(
                        [prompt_i2, shorts_img, boots],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.03,
                            top_p=0.35,
                            top_k=6,
                        )
                    )
                    
                    if hasattr(response_i2, 'candidates') and response_i2.candidates:
                        for candidate2 in response_i2.candidates:
                            if hasattr(candidate2, 'content') and candidate2.content:
                                for part2 in candidate2.content.parts:
                                    if hasattr(part2, 'inline_data') and part2.inline_data:
                                        with open('iter_testI_step2_complete.png', 'wb') as f:
                                            f.write(part2.inline_data.data)
                                        print("✅ Saved: iter_testI_step2_complete.png")


# ==========================================
# TEST J: Ultra-minimal prompt
# ==========================================
print("\n🧪 TEST J: Minimal prompt test")

prompt_j = """Replace gray pants with black leather shorts and add tan cowboy boots.
Keep everything else identical - especially the polka dot shirt.
Gray studio background."""

response_j = gemini_model.generate_content(
    [prompt_j, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.01,
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response_j, 'candidates') and response_j.candidates:
    for candidate in response_j.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('iter_testJ_minimal.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: iter_testJ_minimal.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ MORE REFINEMENT TESTS COMPLETE!")
print("=" * 70)
print("\nCompare:")
print("  G. iter_testG_shirt_lock.png - Heavy preservation emphasis")
print("  H. iter_testH_reference.png - Explicit current state")
print("  I. iter_testI_step2_complete.png - Sequential (shorts→boots)")
print("  J. iter_testJ_minimal.png - Minimal prompt")
print("\n💡 One of these should nail the shirt preservation!")
print("=" * 70)

