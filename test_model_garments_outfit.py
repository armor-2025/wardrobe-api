"""
Test outfit with garments photographed on models
Black jeans + White long sleeve + Jacket + Beanie
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
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🧪 MODEL GARMENTS TEST")
print("=" * 70)
print("Outfit: White long sleeve + Jacket + Black jeans + Beanie")
print("Testing garments photographed on models")
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
                    elif status_data.get('status') == 'failed':
                        print(f"   ❌ FASHN failed: {status_data.get('error')}")
                        return None
    return None


# ==========================================
# STEP 1: FASHN - White long sleeve (IMG_6552.PNG on model)
# ==========================================
print("\n📍 STEP 1: FASHN - White long sleeve (from model photo)")

fashn_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    ai_pics_path + 'IMG_6552.PNG'
)

if not fashn_result:
    print("❌ FASHN couldn't extract long sleeve from model photo")
    print("   Trying with flat-lay if available...")
    # Could fallback to IMG_6541.PNG (white t-shirt) if needed
    exit()

with open('model_step1_longsleeve.png', 'wb') as f:
    f.write(fashn_result)
print("✅ Long sleeve applied from model photo!")
print("💰 Cost: $0.075")


# ==========================================
# STEP 2: Gemini - Add jacket over long sleeve (IMG_6555.PNG on model)
# ==========================================
print("\n📍 STEP 2: Gemini - Add jacket from model photo")

longsleeve_img = Image.open(io.BytesIO(fashn_result))
jacket = Image.open(ai_pics_path + 'IMG_6555.PNG')

jacket_prompt = """Add jacket over the white long sleeve.

PRESERVE EXACTLY:
- Face and hair
- White long sleeve underneath
- Body and pose

ADD:
- Jacket on top (from reference image - extract garment from model)
- Layer naturally over long sleeve
- Long sleeve should show at collar and cuffs

Gray studio background."""

response = gemini_model.generate_content(
    [jacket_prompt, longsleeve_img, jacket],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

jacket_result = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    jacket_result = part.inline_data.data
                    with open('model_step2_jacket.png', 'wb') as f:
                        f.write(jacket_result)
                    print("✅ Jacket layered from model photo!")
                    print("💰 Cost: $0.10")

if not jacket_result:
    print("❌ Gemini couldn't add jacket")
    jacket_result = fashn_result


# ==========================================
# STEP 3: Gemini - Add black jeans + beanie
# ==========================================
print("\n📍 STEP 3: Gemini - Add black jeans + beanie")

current_img = Image.open(io.BytesIO(jacket_result))
jeans = Image.open(ai_pics_path + 'IMG_6545.PNG')  # Black jeans (flat lay)
beanie = Image.open(ai_pics_path + 'IMG_6553.PNG')  # Beanie on model

bottoms_prompt = """Add bottoms and beanie from references.

PRESERVE EXACTLY:
- Face and hair
- White long sleeve + jacket (already layered)
- Upper body

ADD:
- Black jeans (from reference)
- Beanie on head (from reference - extract from model photo)

REPLACE:
- Gray sweatpants → Black jeans

Gray studio background.
High detail."""

response = gemini_model.generate_content(
    [bottoms_prompt, current_img, jeans, beanie],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('model_outfit_FINAL.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ COMPLETE: model_outfit_FINAL.png")
                    print("💰 Cost: $0.10")
                    
                    print("\n" + "=" * 70)
                    print("✅ MODEL GARMENTS OUTFIT COMPLETE!")
                    print("=" * 70)
                    print("\n💰 Total Cost:")
                    print("   FASHN (long sleeve from model): $0.075")
                    print("   Gemini (jacket from model): $0.10")
                    print("   Gemini (jeans + beanie): $0.10")
                    print("   TOTAL: $0.275")
                    print("\n📊 Quality check:")
                    print("   ✓ Can FASHN extract garments from model photos?")
                    print("   ✓ Can Gemini extract garments from model photos?")
                    print("   ✓ Does it match quality of flat-lay images?")
                    print("\n💡 If successful, users can upload any product photos!")
                    print("=" * 70)

