"""
Sequential approach - one item at a time for consistency
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
print("🧪 SEQUENTIAL MODEL GARMENTS TEST")
print("=" * 70)
print("Adding items ONE AT A TIME for consistency")
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
# STEP 1: FASHN - White long sleeve
# ==========================================
print("\n📍 STEP 1: FASHN - White long sleeve")

current = call_fashn(base_path + 'IMG_6033.jpeg', ai_pics_path + 'IMG_6552.PNG')

if not current:
    print("❌ Failed")
    exit()

with open('seq_step1_longsleeve.png', 'wb') as f:
    f.write(current)
print("✅ Long sleeve applied")


# ==========================================
# STEP 2: Gemini - Add jacket
# ==========================================
print("\n📍 STEP 2: Gemini - Add jacket ONLY")

current_img = Image.open(io.BytesIO(current))
jacket = Image.open(ai_pics_path + 'IMG_6555.PNG')

prompt = """Add jacket over long sleeve.

PRESERVE:
- Face, hair
- White long sleeve

ADD ONLY:
- Jacket from reference (extract from model photo)

Layer naturally. Gray background."""

response = gemini_model.generate_content(
    [prompt, current_img, jacket],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    current = part.inline_data.data
                    with open('seq_step2_jacket.png', 'wb') as f:
                        f.write(current)
                    print("✅ Jacket added")


# ==========================================
# STEP 3: Gemini - Add jeans
# ==========================================
print("\n📍 STEP 3: Gemini - Add jeans ONLY")

current_img = Image.open(io.BytesIO(current))
jeans = Image.open(ai_pics_path + 'IMG_6545.PNG')

prompt = """Replace bottoms.

PRESERVE:
- Face, hair
- Long sleeve + jacket

REPLACE ONLY:
- Gray sweatpants → Black jeans (from reference)

Gray background."""

response = gemini_model.generate_content(
    [prompt, current_img, jeans],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    current = part.inline_data.data
                    with open('seq_step3_jeans.png', 'wb') as f:
                        f.write(current)
                    print("✅ Jeans added")


# ==========================================
# STEP 4: Gemini - Add trainers
# ==========================================
print("\n📍 STEP 4: Gemini - Add trainers ONLY")

current_img = Image.open(io.BytesIO(current))
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

prompt = """Replace shoes.

PRESERVE:
- Everything above ankles

REPLACE ONLY:
- Black socks → Trainers (from reference)

Gray background."""

response = gemini_model.generate_content(
    [prompt, current_img, trainers],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    current = part.inline_data.data
                    with open('seq_step4_trainers.png', 'wb') as f:
                        f.write(current)
                    print("✅ Trainers added")


# ==========================================
# STEP 5: Gemini - Add beanie
# ==========================================
print("\n📍 STEP 5: Gemini - Add beanie")

current_img = Image.open(io.BytesIO(current))
beanie = Image.open(ai_pics_path + 'IMG_6553.PNG')

prompt = """Add beanie on head.

PRESERVE:
- Face
- All clothing

ADD:
- Beanie from reference (extract from model photo)
- Should fit naturally on head
- Hair may show slightly

Gray background."""

response = gemini_model.generate_content(
    [prompt, current_img, beanie],
    generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('seq_FINAL_complete.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ Beanie added")
                    print("\n" + "=" * 70)
                    print("✅ COMPLETE OUTFIT!")
                    print("=" * 70)
                    print("\n💰 Total Cost:")
                    print("   FASHN: $0.075")
                    print("   Gemini × 4: $0.40")
                    print("   TOTAL: $0.475")
                    print("\nResult: seq_FINAL_complete.png")
                    print("=" * 70)

