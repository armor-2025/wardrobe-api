"""
Refine TEST 3: Better prompts and garment handling
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
print("🔬 REFINING TEST 3: Better Gemini Instructions")
print("=" * 70)

# ==========================================
# STEP 1: FASHN for shirt (we know this works)
# ==========================================
print("\n📍 STEP 1: FASHN AI - Shirt Application")

def call_fashn(person_path, garment_path, output_name):
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
                        img_bytes = requests.get(img_url).content
                        
                        with open(output_name, 'wb') as f:
                            f.write(img_bytes)
                        print(f"✅ Saved: {output_name}")
                        return img_bytes
    return None

shirt_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'refine_step1_shirt.png'
)

if not shirt_result:
    print("❌ FASHN failed, cannot continue")
    exit()

# ==========================================
# STEP 2: Multiple Gemini Refinement Tests
# ==========================================
print("\n📍 STEP 2: Testing Different Gemini Approaches")

shirt_img = Image.open(io.BytesIO(shirt_result))

with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))


# ==========================================
# TEST A: Ultra-detailed description
# ==========================================
print("\n🧪 TEST A: Ultra-detailed garment descriptions")

prompt_a = """Professional photo editing task - add garments to this person.

CURRENT IMAGE ANALYSIS:
- Person wearing white polka dot shirt (KEEP EXACTLY AS IS)
- Gray sweatpants (WILL BE REPLACED)
- Face and hair are PERFECT (DO NOT CHANGE)

NEW GARMENTS TO ADD (from reference images):
1. BLACK LEATHER SHORTS (replacing gray sweatpants):
   - Material: Black leather with subtle texture/pattern
   - Style: Relaxed fit, knee-length shorts
   - Waist: Should sit naturally at waist
   - NOT tight or fitted - loose, comfortable fit
   - These are SHORTS not tight cycling shorts

2. TAN COWBOY BOOTS (replacing black socks):
   - Material: Tan/brown leather
   - Style: Western cowboy boots with decorative stitching
   - Height: Mid-calf height
   - Visible under the shorts

CRITICAL PRESERVATION:
- Face: Keep pixel-perfect identical
- Hair: Keep exact curls and color
- Polka dot shirt: Keep exactly as shown
- Body proportions: Maintain natural size
- Pose: Keep same standing pose

CHANGES ONLY:
- Replace gray sweatpants with black leather shorts (loose fit)
- Replace black socks with tan cowboy boots
- Change background to professional gray studio

The shorts should look natural and comfortable, NOT skin-tight.
Reference the garment images for exact appearance.

Output: Professional studio portrait, same person, new bottoms and shoes."""

response_a = gemini_model.generate_content(
    [prompt_a, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.15,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response_a, 'candidates') and response_a.candidates:
    for candidate in response_a.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('refine_testA_detailed.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: refine_testA_detailed.png")


# ==========================================
# TEST B: Simple inpainting instructions
# ==========================================
print("\n🧪 TEST B: Simple inpainting-style instructions")

prompt_b = """Inpainting task: Replace ONLY the lower body garments.

MASK REGIONS (what to change):
- Pants/bottoms area: Replace with black leather shorts
- Feet area: Replace with tan cowboy boots

PROTECTED REGIONS (DO NOT TOUCH):
- Face, hair, entire head
- Torso and polka dot shirt
- Arms and hands
- Body proportions

NEW GARMENTS (see reference images):
- Black leather shorts: Loose-fitting, knee-length
- Tan cowboy boots: Western style

Add gray studio background.
This is selective editing, not full regeneration."""

response_b = gemini_model.generate_content(
    [prompt_b, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.4,
        top_k=8,
    )
)

if hasattr(response_b, 'candidates') and response_b.candidates:
    for candidate in response_b.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('refine_testB_inpainting.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: refine_testB_inpainting.png")


# ==========================================
# TEST C: Bottom-up sequential with Gemini
# ==========================================
print("\n🧪 TEST C: Add bottoms first, then boots")

prompt_c1 = """Add black leather shorts to this person.

KEEP IDENTICAL:
- Face and hair (exact match)
- Polka dot shirt (exact match)
- Body size and proportions

CHANGE:
- Replace gray sweatpants with black leather shorts from reference image
- The shorts are loose-fitting, knee-length
- Natural, relaxed fit

Background: gray studio."""

response_c1 = gemini_model.generate_content(
    [prompt_c1, shirt_img, shorts],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.4,
        top_k=8,
    )
)

if hasattr(response_c1, 'candidates') and response_c1.candidates:
    for candidate in response_c1.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    shorts_added_bytes = part.inline_data.data
                    with open('refine_testC_step1_shorts.png', 'wb') as f:
                        f.write(shorts_added_bytes)
                    print("✅ Saved: refine_testC_step1_shorts.png")
                    
                    # Now add boots
                    shorts_img = Image.open(io.BytesIO(shorts_added_bytes))
                    
                    prompt_c2 = """Add cowboy boots to this person.

KEEP IDENTICAL:
- Face, hair, shirt, shorts (exact match)

CHANGE ONLY:
- Replace black socks/shoes with tan cowboy boots from reference
- Western style boots, mid-calf height"""

                    response_c2 = gemini_model.generate_content(
                        [prompt_c2, shorts_img, boots],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.05,
                            top_p=0.4,
                            top_k=8,
                        )
                    )
                    
                    if hasattr(response_c2, 'candidates') and response_c2.candidates:
                        for candidate2 in response_c2.candidates:
                            if hasattr(candidate2, 'content') and candidate2.content:
                                for part2 in candidate2.content.parts:
                                    if hasattr(part2, 'inline_data') and part2.inline_data:
                                        with open('refine_testC_step2_complete.png', 'wb') as f:
                                            f.write(part2.inline_data.data)
                                        print("✅ Saved: refine_testC_step2_complete.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ REFINEMENT TESTS COMPLETE!")
print("=" * 70)
print("\nCompare these refined results:")
print("  A. refine_testA_detailed.png - Ultra-detailed descriptions")
print("  B. refine_testB_inpainting.png - Simple inpainting style")
print("  C. refine_testC_step2_complete.png - Sequential (shorts→boots)")
print("\n💡 Which has:")
print("   ✅ Loose-fitting shorts (not tight)?")
print("   ✅ Proper shirt fit?")
print("   ✅ Perfect face/hair/background?")
print("=" * 70)

