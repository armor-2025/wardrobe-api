"""
REVERSED: FASHN for bottoms (simpler) + Gemini for top (more detail)
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
print("🔄 REVERSED ORDER TEST")
print("=" * 70)
print("Step 1: FASHN for bottoms (trousers) - Face lock")
print("Step 2: Gemini for top (sweatshirt) - Perfect detail")
print("=" * 70)

# ==========================================
# STEP 1: FASHN for BOTTOMS (trousers)
# ==========================================
print("\n📍 STEP 1: FASHN - Apply trousers")

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    person_b64 = base64.b64encode(f.read()).decode('utf-8')

with open(ai_pics_path + 'blacktrousers.png', 'rb') as f:
    trousers_b64 = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    'https://api.fashn.ai/v1/run',
    headers={'Authorization': f'Bearer {FASHN_API_KEY}', 'Content-Type': 'application/json'},
    json={
        "model_image": f"data:image/jpeg;base64,{person_b64}",
        "garment_image": f"data:image/png;base64,{trousers_b64}",
        "category": "bottoms",  # BOTTOMS not tops!
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
                    
                    with open('reversed_step1_fashn_bottoms.png', 'wb') as f:
                        f.write(fashn_result)
                    print("✅ FASHN complete - face locked with trousers!")
                    print("💰 Cost: $0.075")
                    break
                elif status_data.get('status') == 'failed':
                    print(f"❌ Failed: {status_data.get('error')}")
                    break

if not fashn_result:
    print("❌ FASHN failed")
    exit()

# ==========================================
# STEP 2: Gemini for TOP (sweatshirt + trainers)
# ==========================================
print("\n📍 STEP 2: Gemini - Apply sweatshirt + trainers")

fashn_img = Image.open(io.BytesIO(fashn_result))
sweatshirt = Image.open(ai_pics_path + 'IMG_5747.jpg')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

prompt = """Add top and shoes from references.

PRESERVE EXACTLY:
- Face and hair (perfect from FASHN)
- Black trousers (perfect from FASHN)

REPLACE:
- Gray t-shirt → Black Adidas sweatshirt (from reference)
  * Must show Adidas logo clearly
  * Must show white stripes on sleeves
  * All details from reference
- Black socks → Brown/burgundy Adidas trainers (from reference)

CRITICAL: Render the Adidas sweatshirt with maximum detail - logo, stripes, texture.
Gray studio background."""

response = gemini_model.generate_content(
    [prompt, fashn_img, sweatshirt, trainers],
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
                    with open('reversed_FINAL.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    print("✅ COMPLETE: reversed_FINAL.png")
                    print("💰 Cost: $0.10")
                    print("\n" + "=" * 70)
                    print("✅ REVERSED ORDER COMPLETE!")
                    print("=" * 70)
                    print("\n💰 Total: $0.175")
                    print("\nCompare sweatshirt detail:")
                    print("   - new_outfit_FINAL.png (FASHN did sweatshirt)")
                    print("   - reversed_FINAL.png (Gemini did sweatshirt)")
                    print("\n💡 Gemini should have PERFECT Adidas logo detail!")
                    print("=" * 70)

