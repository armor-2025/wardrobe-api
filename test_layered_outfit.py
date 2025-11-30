"""
Test layered outfit: Grey jumper + Gilet + Black jeans + Trainers
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
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🧪 LAYERED OUTFIT TEST")
print("=" * 70)
print("Grey jumper + Gilet + Black jeans + Trainers")
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
# STEP 1: FASHN - Grey jumper (base layer)
# ==========================================
print("\n📍 STEP 1: FASHN - Apply grey jumper")

fashn_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    ai_pics_path + 'IMG_6546.PNG'
)

if not fashn_result:
    print("❌ FASHN failed")
    exit()

with open('layered_step1_jumper.png', 'wb') as f:
    f.write(fashn_result)
print("✅ Grey jumper applied, face locked")
print("💰 Cost: $0.075")


# ==========================================
# STEP 2: Gemini - Add gilet over jumper
# ==========================================
print("\n📍 STEP 2: Gemini - Add gilet over jumper")

jumper_img = Image.open(io.BytesIO(fashn_result))
gilet = Image.open(ai_pics_path + 'IMG_6544.PNG')

gilet_prompt = """Add gilet/vest over the grey jumper.

PRESERVE EXACTLY:
- Face and hair
- Grey jumper underneath (visible at collar and sleeves)
- Body and pose

ADD:
- Gilet/vest on top (from reference)
- Must layer naturally over the jumper
- Collar of jumper should show

This is layering, not replacement.
Gray studio background."""

response = gemini_model.generate_content(
    [gilet_prompt, jumper_img, gilet],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

layered_result = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    layered_result = part.inline_data.data
                    with open('layered_step2_gilet.png', 'wb') as f:
                        f.write(layered_result)
                    print("✅ Gilet layered over jumper")
                    print("💰 Cost: $0.10")

if not layered_result:
    print("❌ Gemini failed on gilet")
    # Continue without gilet
    layered_result = fashn_result


# ==========================================
# STEP 3: Gemini - Add jeans + trainers
# ==========================================
print("\n📍 STEP 3: Gemini - Add black jeans + trainers")

current_img = Image.open(io.BytesIO(layered_result))
jeans = Image.open(ai_pics_path + 'IMG_6545.PNG')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

bottoms_prompt = """Add bottoms and shoes from references.

PRESERVE EXACTLY:
- Face and hair (perfect)
- Grey jumper + gilet (perfect)
- Upper body completely

REPLACE:
- Gray sweatpants → Black jeans (from reference)
- Black socks → Brown/burgundy Adidas trainers (from reference)

Keep all upper body layers intact.
Gray studio background.
High detail."""

response = gemini_model.generate_content(
    [bottoms_prompt, current_img, jeans, trainers],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('layered_outfit_FINAL.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ COMPLETE: layered_outfit_FINAL.png")
                    print("💰 Cost: $0.10")
                    
                    print("\n" + "=" * 70)
                    print("✅ LAYERED OUTFIT COMPLETE!")
                    print("=" * 70)
                    print("\n💰 Total Cost:")
                    print("   FASHN (jumper): $0.075")
                    print("   Gemini (gilet): $0.10")
                    print("   Gemini (bottoms): $0.10")
                    print("   TOTAL: $0.275")
                    print("\n💡 Layering adds complexity but shows versatility!")
                    print("=" * 70)

