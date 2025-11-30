"""
Test new outfit: Adidas sweatshirt + black trousers + brown trainers
Using exact same FASHN + Gemini approach
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

print("=" * 70)
print("🧪 NEW OUTFIT TEST")
print("=" * 70)
print("Adidas sweatshirt + Black trousers + Brown trainers")
print("Method: FASHN shirt + Gemini bottoms (same as Test D)")
print("=" * 70)

# Paths
base_path = '/Users/gavinwalker/Downloads/files (4)/'
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

# Step 1: FASHN for sweatshirt
print("\n📍 STEP 1: FASHN - Apply Adidas sweatshirt")

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    person_b64 = base64.b64encode(f.read()).decode('utf-8')

with open(ai_pics_path + 'IMG_5747.jpg', 'rb') as f:
    sweatshirt_b64 = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    'https://api.fashn.ai/v1/run',
    headers={'Authorization': f'Bearer {FASHN_API_KEY}', 'Content-Type': 'application/json'},
    json={
        "model_image": f"data:image/jpeg;base64,{person_b64}",
        "garment_image": f"data:image/jpg;base64,{sweatshirt_b64}",
        "category": "tops",
        "num_samples": 1
    },
    timeout=120
)

fashn_result = None

if response.status_code == 200:
    result = response.json()
    if 'id' in result:
        job_id = result['id']
        print(f"⏳ Job: {job_id}")
        
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
                    fashn_result = requests.get(img_url).content
                    
                    with open('new_outfit_step1_fashn.png', 'wb') as f:
                        f.write(fashn_result)
                    print("✅ FASHN complete - face locked!")
                    print("💰 Cost: $0.075")
                    break

if not fashn_result:
    print("❌ FASHN failed")
    exit()

# Step 2: Gemini for trousers + trainers
print("\n📍 STEP 2: Gemini - Add trousers + trainers")

fashn_img = Image.open(io.BytesIO(fashn_result))

trousers = Image.open(ai_pics_path + 'Screenshot 2025-10-14 at 18.03.53.png')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

gemini_prompt = """Add bottoms and shoes from references.

PRESERVE EXACTLY:
- Face and hair (already perfect from FASHN)
- Adidas sweatshirt (already perfect from FASHN)
- Upper body completely unchanged

REPLACE:
- Gray sweatpants → Black trousers (from reference)
- Black socks → Brown/burgundy trainers (from reference)

CRITICAL:
- Keep face identical
- Keep sweatshirt identical (with Adidas logo and stripes)
- Only change lower body

Gray studio background.
High detail rendering."""

response = gemini_model.generate_content(
    [gemini_prompt, fashn_img, trousers, trainers],
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.5,
        top_k=10,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('new_outfit_FINAL.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ COMPLETE: new_outfit_FINAL.png")
                    print("💰 Cost: $0.10")
                    
                    print("\n" + "=" * 70)
                    print("✅ NEW OUTFIT TEST COMPLETE!")
                    print("=" * 70)
                    print("\n💰 Total Cost: $0.175")
                    print("\nCompare with test3_diff_pants_FINAL.png")
                    print("\n💡 If quality is similar → Approach is CONSISTENT!")
                    print("=" * 70)

