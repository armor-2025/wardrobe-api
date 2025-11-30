"""
New approach: Layer/composite images programmatically
"""
import requests
import base64
import os
import time
from PIL import Image
import io
import numpy as np
import cv2
import google.generativeai as genai

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'
os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("=" * 70)
print("🔬 NEW APPROACH: Programmatic Compositing")
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
# STEP 1: Get perfect shirt from FASHN
# ==========================================
print("\n📍 STEP 1: FASHN - Perfect shirt + face")
fashn_shirt = call_fashn(base_path + 'IMG_6033.jpeg', base_path + 'IMG_5937.PNG')

if not fashn_shirt:
    print("❌ FASHN failed")
    exit()

with open('composite_fashn_shirt.png', 'wb') as f:
    f.write(fashn_shirt)
print("✅ FASHN result saved")


# ==========================================
# STEP 2: Get perfect clothes on mannequin from Gemini
# ==========================================
print("\n📍 STEP 2: Gemini - Perfect outfit on mannequin")

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    shirt_ref = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts_ref = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots_ref = Image.open(io.BytesIO(f.read()))

mannequin_prompt = """Generate fashion mannequin wearing complete outfit:
- White polka dot shirt
- Black leather shorts
- Tan cowboy boots

Full body standing pose, clean gray studio background.
Pixel-perfect garment rendering."""

response = gemini_model.generate_content(
    [mannequin_prompt, shirt_ref, shorts_ref, boots_ref],
    generation_config=genai.types.GenerationConfig(temperature=0.4)
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('composite_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Mannequin generated")


if not mannequin_bytes:
    print("❌ Mannequin generation failed")
    exit()


# ==========================================
# STEP 3: Ask Gemini to composite them intelligently
# ==========================================
print("\n📍 STEP 3: Gemini compositing (smart blend)")

fashn_img = Image.open(io.BytesIO(fashn_shirt))
mannequin_img = Image.open(io.BytesIO(mannequin_bytes))

composite_prompt = """Image compositing task:

IMAGE 1 (Person with perfect face/shirt): Use for head, torso, and shirt
IMAGE 2 (Mannequin with perfect outfit): Use for shorts and boots only

TASK: Create composite where:
- Head, face, hair from IMAGE 1 (exact copy)
- Shirt/torso from IMAGE 1 (exact copy)
- Shorts from IMAGE 2
- Boots from IMAGE 2
- Studio gray background

This is a cut-and-paste compositing job.
Take upper body from IMAGE 1, lower body from IMAGE 2.
Blend the waistline seamlessly.

Output: Person from IMAGE 1 wearing lower body garments from IMAGE 2."""

response_composite = gemini_model.generate_content(
    [composite_prompt, fashn_img, mannequin_img],
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response_composite, 'candidates') and response_composite.candidates:
    for candidate in response_composite.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('composite_gemini_blend.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: composite_gemini_blend.png")


# ==========================================
# STEP 4: Try programmatic composite with OpenCV
# ==========================================
print("\n📍 STEP 4: OpenCV programmatic composite")

fashn_cv = cv2.imdecode(np.frombuffer(fashn_shirt, np.uint8), cv2.IMREAD_COLOR)
mannequin_cv = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)

# Resize mannequin to match FASHN size
h, w = fashn_cv.shape[:2]
mannequin_cv = cv2.resize(mannequin_cv, (w, h))

# Simple horizontal split at waist (rough estimate at 55% height)
split_point = int(h * 0.55)

# Create composite: top from FASHN, bottom from mannequin
composite_cv = fashn_cv.copy()
composite_cv[split_point:, :] = mannequin_cv[split_point:, :]

# Smooth the transition with feathering
blend_height = 30
for i in range(blend_height):
    alpha = i / blend_height
    row = split_point - blend_height//2 + i
    if 0 <= row < h:
        composite_cv[row, :] = (
            fashn_cv[row, :] * (1 - alpha) +
            mannequin_cv[row, :] * alpha
        ).astype(np.uint8)

cv2.imwrite('composite_opencv_simple.png', composite_cv)
print("✅ Saved: composite_opencv_simple.png")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ COMPOSITING TESTS COMPLETE!")
print("=" * 70)
print("\nResults:")
print("  composite_fashn_shirt.png - FASHN (perfect face/shirt)")
print("  composite_mannequin.png - Gemini (perfect clothes)")
print("  composite_gemini_blend.png - Gemini composite attempt")
print("  composite_opencv_simple.png - OpenCV programmatic blend")
print("\n💡 The compositing approach bypasses Gemini's regeneration!")
print("\n💰 Cost: $0.075 (FASHN) + $0.10 (Gemini) = $0.175")
print("=" * 70)

