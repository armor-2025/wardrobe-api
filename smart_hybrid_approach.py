"""
Smart hybrid: FASHN locks the identity, then careful Gemini refinement
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
print("🎯 SMART HYBRID: FASHN Identity Lock → Minimal Gemini Touch")
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


# ==========================================
# STEP 1: FASHN for identity lock
# ==========================================
print("\n📍 STEP 1: FASHN - Lock identity with shirt")
fashn_result = call_fashn(base_path + 'IMG_6033.jpeg', base_path + 'IMG_5937.PNG')

if not fashn_result:
    print("❌ FASHN failed")
    exit()

with open('smart_step1_fashn.png', 'wb') as f:
    f.write(fashn_result)
print("✅ Identity locked")

fashn_img = Image.open(io.BytesIO(fashn_result))

# Load reference garments
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts_ref = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots_ref = Image.open(io.BytesIO(f.read()))


# ==========================================
# TEST 1: Minimal intervention - just swap bottoms
# ==========================================
print("\n🧪 TEST 1: Minimal Gemini touch - swap bottoms only")

prompt_1 = """Swap lower body garments.

Current: Gray sweatpants, black socks
New: Black leather shorts, tan cowboy boots (from references)

Change ONLY the pants and footwear regions.
Everything else stays identical.
Gray studio background."""

response_1 = gemini_model.generate_content(
    [prompt_1, fashn_img, shorts_ref, boots_ref],
    generation_config=genai.types.GenerationConfig(
        temperature=0.01,
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response_1, 'candidates') and response_1.candidates:
    for candidate in response_1.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('smart_test1_minimal.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: smart_test1_minimal.png")


# ==========================================
# TEST 2: Just background change, keep everything else
# ==========================================
print("\n🧪 TEST 2: Add studio background only, keep all garments")

prompt_2 = """Change background to professional gray studio.
Keep the person and all their clothes exactly as shown.
This is ONLY a background replacement."""

response_2 = gemini_model.generate_content(
    [prompt_2, fashn_img],
    generation_config=genai.types.GenerationConfig(
        temperature=0.01,
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response_2, 'candidates') and response_2.candidates:
    for candidate in response_2.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    bg_only_bytes = part.inline_data.data
                    with open('smart_test2_bg_only.png', 'wb') as f:
                        f.write(bg_only_bytes)
                    print("✅ Saved: smart_test2_bg_only.png")
                    
                    # Now add bottoms to this
                    bg_img = Image.open(io.BytesIO(bg_only_bytes))
                    
                    prompt_2b = """Add shorts and boots from references.
Keep face, hair, and shirt exactly as shown."""

                    response_2b = gemini_model.generate_content(
                        [prompt_2b, bg_img, shorts_ref, boots_ref],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.01,
                            top_p=0.3,
                            top_k=5,
                        )
                    )
                    
                    if hasattr(response_2b, 'candidates') and response_2b.candidates:
                        for candidate2 in response_2b.candidates:
                            if hasattr(candidate2, 'content') and candidate2.content:
                                for part2 in candidate2.content.parts:
                                    if hasattr(part2, 'inline_data') and part2.inline_data:
                                        with open('smart_test2_then_bottoms.png', 'wb') as f:
                                            f.write(part2.inline_data.data)
                                        print("✅ Saved: smart_test2_then_bottoms.png")


# ==========================================
# TEST 3: Try FASHN for BOTH shirt AND shorts
# ==========================================
print("\n🧪 TEST 3: Can FASHN do both top and bottom?")

# Try using the shorts+boots composite as "garment"
# First create a composite image
from PIL import Image

# Stack shorts and boots vertically
shorts_pil = Image.open(base_path + 'IMG_5936.PNG')
boots_pil = Image.open(base_path + 'IMG_5938.PNG')

# Resize to same width
target_w = 800
shorts_pil = shorts_pil.resize((target_w, int(shorts_pil.height * target_w / shorts_pil.width)))
boots_pil = boots_pil.resize((target_w, int(boots_pil.height * target_w / boots_pil.width)))

# Stack
total_h = shorts_pil.height + boots_pil.height
composite_bottom = Image.new('RGB', (target_w, total_h), (240, 240, 240))
composite_bottom.paste(shorts_pil, (0, 0))
composite_bottom.paste(boots_pil, (0, shorts_pil.height))
composite_bottom.save('temp_bottom_composite.png')

# Try FASHN with this (probably won't work, but worth trying)
fashn_bottoms = call_fashn(
    'smart_step1_fashn.png',  # Use FASHN result as base
    'temp_bottom_composite.png'
)

if fashn_bottoms:
    with open('smart_test3_fashn_bottoms.png', 'wb') as f:
        f.write(fashn_bottoms)
    print("✅ Saved: smart_test3_fashn_bottoms.png")
else:
    print("⚠️  FASHN doesn't support this")


# ==========================================
# TEST 4: Ultra-simple instruction test
# ==========================================
print("\n🧪 TEST 4: One-word instruction")

prompt_4 = """Shorts. Boots. Gray background."""

response_4 = gemini_model.generate_content(
    [prompt_4, fashn_img, shorts_ref, boots_ref],
    generation_config=genai.types.GenerationConfig(
        temperature=0.005,  # Almost deterministic
        top_p=0.2,
        top_k=3,
    )
)

if hasattr(response_4, 'candidates') and response_4.candidates:
    for candidate in response_4.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('smart_test4_oneword.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: smart_test4_oneword.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ SMART HYBRID TESTS COMPLETE!")
print("=" * 70)
print("\nCompare:")
print("  smart_test1_minimal.png - Minimal intervention")
print("  smart_test2_then_bottoms.png - BG first, then bottoms")
print("  smart_test3_fashn_bottoms.png - FASHN for bottoms (if worked)")
print("  smart_test4_oneword.png - Ultra-simple prompt")
print("\n💡 Looking for the magic combination!")
print("=" * 70)

