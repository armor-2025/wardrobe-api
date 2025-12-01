"""
Test with explicit background cleaning step
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
print("🎯 TESTING WITH EXPLICIT BACKGROUND STEP")
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
# TEST: White long sleeve + jeans + boots
# ==========================================
print("\n🧪 Testing: White long sleeve + Jeans + Boots")

# Step 1: FASHN
print("\n📍 Step 1: FASHN - White long sleeve")
fashn_result = call_fashn(base_path + 'IMG_6033.jpeg', ai_pics_path + 'IMG_6552.PNG')

if not fashn_result:
    print("❌ FASHN failed")
    exit()

with open('bg_test_step1.png', 'wb') as f:
    f.write(fashn_result)
print("✅ Top applied")

# Step 2: Gemini bottoms
print("\n📍 Step 2: Gemini - Jeans + Boots")

current_img = Image.open(io.BytesIO(fashn_result))
jeans = Image.open(ai_pics_path + 'IMG_6545.PNG')
boots = Image.open(base_path + 'IMG_5938.PNG')

bottoms_prompt = """Add jeans and boots.

PRESERVE EXACTLY:
- Face and hair
- White long sleeve shirt
- Upper body pose

REPLACE:
- Gray sweatpants → Black jeans
- Black socks → Cowboy boots

Keep everything else identical."""

response = gemini_model.generate_content(
    [bottoms_prompt, current_img, jeans, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.05, top_p=0.3, top_k=5)
)

bottoms_result = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    bottoms_result = part.inline_data.data
                    with open('bg_test_step2.png', 'wb') as f:
                        f.write(bottoms_result)
                    print("✅ Bottoms added")

if not bottoms_result:
    print("❌ Gemini failed")
    exit()

# Step 3: DEDICATED BACKGROUND STEP
print("\n📍 Step 3: Gemini - Professional studio background")

current_img = Image.open(io.BytesIO(bottoms_result))

bg_prompt = """Professional fashion photography background transformation.

PRESERVE EXACTLY (pixel-perfect):
- The person (face, hair, body, pose)
- All clothing (exact colors, textures, details)
- Lighting on the person

CHANGE ONLY:
- Background → Solid neutral gray studio background (#C8C8C8)
- Professional fashion photography studio look
- Soft shadow under feet for depth
- No room elements (doors, furniture, walls)

This is ONLY a background replacement. The person and clothes must be IDENTICAL."""

response = gemini_model.generate_content(
    [bg_prompt, current_img],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('bg_test_FINAL_clean.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ COMPLETE: bg_test_FINAL_clean.png")
                    print("\n" + "=" * 70)
                    print("📊 COMPARISON")
                    print("=" * 70)
                    print("\nFiles:")
                    print("   bg_test_step2.png - Before background fix")
                    print("   bg_test_FINAL_clean.png - After background fix")
                    print("\n💰 Cost: $0.075 + $0.10 + $0.10 = $0.275")
                    print("\n💡 Does dedicated BG step fix the consistency?")
                    print("=" * 70)

