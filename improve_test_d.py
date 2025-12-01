"""
Improve Test D - Fix shirt detail preservation
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
print("🎯 IMPROVING TEST D - Fix Shirt Preservation")
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

# FASHN Shirt
print("\n📍 Step 1: FASHN shirt application")
shirt_result = call_fashn(base_path + 'IMG_6033.jpeg', base_path + 'IMG_5937.PNG')

if not shirt_result:
    print("❌ FASHN failed")
    exit()

with open('d_improve_step1.png', 'wb') as f:
    f.write(shirt_result)
print("✅ Shirt applied via FASHN")

shirt_img = Image.open(io.BytesIO(shirt_result))

with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))


# ==========================================
# VARIATION 1: Explicit "no buttons" instruction
# ==========================================
print("\n🧪 D1: Explicit pullover shirt preservation")

prompt_d1 = """Lower body garment replacement - preserve upper body exactly.

CURRENT IMAGE STATE:
- Person wearing WHITE POLKA DOT PULLOVER SHIRT (no buttons down the front)
- White collar
- Polka dots pattern throughout
- Currently wearing gray sweatpants and black socks

CRITICAL - UPPER BODY PRESERVATION:
✓ Face: Keep identical
✓ Hair: Keep identical  
✓ POLKA DOT SHIRT: Keep EXACTLY as shown
  - This is a PULLOVER shirt (no front buttons)
  - Keep all polka dots in same positions
  - Keep collar style
  - Do NOT convert to button-up shirt
  - Do NOT add buttons
  - Keep fabric folds and texture

LOWER BODY REPLACEMENT (from references):
✓ Black leather shorts:
  - Textured leather surface with visible grain/pattern
  - Loose, relaxed fit (NOT tight)
  - Knee-length
  
✓ Tan cowboy boots:
  - Western style with stitching details
  - Mid-calf height

Background: Professional gray studio (#D0D0D0)

This is SELECTIVE EDITING - only change below the waist.
The shirt must remain a pullover without buttons."""

response_d1 = gemini_model.generate_content(
    [prompt_d1, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.4,
        top_k=8,
    )
)

if hasattr(response_d1, 'candidates') and response_d1.candidates:
    for candidate in response_d1.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('d_improve_v1.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: d_improve_v1.png")


# ==========================================
# VARIATION 2: Reference original shirt image
# ==========================================
print("\n🧪 D2: Include original shirt as reference")

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    original_shirt = Image.open(io.BytesIO(f.read()))

prompt_d2 = """Lower body garment replacement.

INPUT IMAGE: Person wearing the polka dot shirt
REFERENCE 1: Original shirt design (shows pullover style, no buttons)
REFERENCE 2: Black leather shorts to add
REFERENCE 3: Tan cowboy boots to add

TASK:
The person is wearing the shirt from REFERENCE 1.
Keep this shirt EXACTLY as it appears in the input image - it's a pullover.
Replace only the gray pants with shorts and add boots.

PRESERVE COMPLETELY:
- Face, hair
- The polka dot PULLOVER shirt (no buttons on front)
- Upper body

REPLACE:
- Gray pants → Black textured leather shorts (loose fit)
- Black socks → Tan cowboy boots

Gray studio background."""

response_d2 = gemini_model.generate_content(
    [prompt_d2, shirt_img, original_shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.4,
        top_k=8,
    )
)

if hasattr(response_d2, 'candidates') and response_d2.candidates:
    for candidate in response_d2.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('d_improve_v2.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: d_improve_v2.png")


# ==========================================
# VARIATION 3: Ultra-low temperature (maximum consistency)
# ==========================================
print("\n🧪 D3: Ultra-conservative settings")

prompt_d3 = """Precision lower body garment replacement.

LOCKED REGIONS (do not modify):
- Face and hair
- White polka dot pullover shirt (current shirt has NO buttons)
- All upper body features

MODIFICATION REGION (waist down):
- Replace pants with black leather shorts (loose fit, textured)
- Replace footwear with tan cowboy boots

Reference images show the shorts and boots to apply.

Keep shirt exactly as shown in input - it's a pullover style.
Gray studio background."""

response_d3 = gemini_model.generate_content(
    [prompt_d3, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.01,  # Ultra-low
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response_d3, 'candidates') and response_d3.candidates:
    for candidate in response_d3.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('d_improve_v3.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: d_improve_v3.png")


# ==========================================
# VARIATION 4: Negative instruction emphasis
# ==========================================
print("\n🧪 D4: Strong negative instructions")

prompt_d4 = """Lower body garment edit ONLY.

WHAT NOT TO DO (critical):
❌ Do NOT change the shirt style
❌ Do NOT add buttons to the shirt
❌ Do NOT modify shirt from pullover to button-up
❌ Do NOT change polka dot pattern
❌ Do NOT alter face or hair
❌ Do NOT touch anything above the waist

WHAT TO DO:
✓ Replace gray sweatpants with black leather shorts from reference
✓ Replace black socks with tan cowboy boots from reference
✓ Add gray studio background

The shirt in the input is a pullover - keep it that way.
Only edit the lower body region."""

response_d4 = gemini_model.generate_content(
    [prompt_d4, shirt_img, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.02,
        top_p=0.35,
        top_k=6,
    )
)

if hasattr(response_d4, 'candidates') and response_d4.candidates:
    for candidate in response_d4.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('d_improve_v4.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: d_improve_v4.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ TEST D IMPROVEMENTS COMPLETE!")
print("=" * 70)
print("\nCompare these D variants:")
print("  d_improve_v1.png - Explicit pullover instructions")
print("  d_improve_v2.png - Include original shirt reference")
print("  d_improve_v3.png - Ultra-conservative settings")
print("  d_improve_v4.png - Strong negative instructions")
print("\n💡 Looking for:")
print("   ✅ Pullover shirt (NO buttons)")
print("   ✅ All polka dots preserved")
print("   ✅ Loose-fitting leather shorts with texture")
print("   ✅ Cowboy boots")
print("=" * 70)

