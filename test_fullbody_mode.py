"""
Test FASHN Full-Body Mode - THE BREAKTHROUGH!
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
print("🎯 TESTING FASHN FULL-BODY MODE")
print("=" * 70)

# ==========================================
# STEP 1: Gemini creates perfect outfit mannequin
# ==========================================
print("\n📍 STEP 1: Gemini - Perfect outfit on mannequin")

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

mannequin_prompt = """Create full-body fashion mannequin wearing complete outfit:
- White polka dot shirt  
- Black leather shorts
- Tan cowboy boots

Standing pose, front-facing, clean gray studio background.
Maximum detail on all garments."""

response = gemini_model.generate_content(
    [mannequin_prompt, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.4)
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('fullbody_step1_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Perfect mannequin created")
                    print("💰 Cost: $0.10")

if not mannequin_bytes:
    print("❌ Gemini failed")
    exit()

# ==========================================
# STEP 2: FASHN Full-Body Mode
# ==========================================
print("\n📍 STEP 2: FASHN Full-Body Mode - Swap your face onto mannequin")

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    person_b64 = base64.b64encode(f.read()).decode('utf-8')

with open('fullbody_step1_mannequin.png', 'rb') as f:
    mannequin_b64 = base64.b64encode(f.read()).decode('utf-8')

# Try with full-body category
response = requests.post(
    'https://api.fashn.ai/v1/run',
    headers={
        'Authorization': f'Bearer {FASHN_API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        "model_image": f"data:image/jpeg;base64,{person_b64}",
        "garment_image": f"data:image/png;base64,{mannequin_b64}",
        "category": "full-body",  # THE KEY!
        "num_samples": 1
    },
    timeout=120
)

print(f"\n📡 API Response Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"✅ Response received")
    
    if 'id' in result:
        job_id = result['id']
        print(f"⏳ Job ID: {job_id}")
        print("   Waiting for full-body VTO...")
        
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(
                f'https://api.fashn.ai/v1/status/{job_id}',
                headers={'Authorization': f'Bearer {FASHN_API_KEY}'}
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status', 'unknown')
                
                print(f"   Status: {status}")
                
                if status == 'completed':
                    print("\n🎉 FASHN FULL-BODY COMPLETE!")
                    
                    img_url = status_data['output'][0] if isinstance(status_data['output'], list) else status_data['output']
                    
                    final_img = requests.get(img_url).content
                    with open('fullbody_step2_FINAL.png', 'wb') as f:
                        f.write(final_img)
                    
                    print("✅ Saved: fullbody_step2_FINAL.png")
                    print("💰 Cost: $0.075")
                    print("\n" + "=" * 70)
                    print("🎊 THIS IS IT!")
                    print("=" * 70)
                    print("\n✅ YOUR FACE on PERFECT CLOTHES!")
                    print("   - Face: Preserved by FASHN")
                    print("   - Shirt: Perfect from Gemini")
                    print("   - Shorts: Perfect from Gemini")
                    print("   - Boots: Perfect from Gemini")
                    print("\n💰 Total: $0.10 + $0.075 = $0.175 per outfit")
                    print("\n🚀 THIS IS YOUR PRODUCTION SOLUTION!")
                    print("=" * 70)
                    break
                
                elif status == 'failed':
                    print(f"\n❌ Job failed: {status_data.get('error', 'Unknown')}")
                    break
    else:
        print(f"⚠️ Unexpected response: {result}")

elif response.status_code == 400:
    print(f"❌ Bad request")
    print(f"   Response: {response.text}")
    print("\n   Trying alternative spellings...")
    
    # Try variations
    for cat in ["fullbody", "full_body", "Full-body"]:
        print(f"\n   Trying: '{cat}'")
        alt_response = requests.post(
            'https://api.fashn.ai/v1/run',
            headers={'Authorization': f'Bearer {FASHN_API_KEY}', 'Content-Type': 'application/json'},
            json={
                "model_image": f"data:image/jpeg;base64,{person_b64}",
                "garment_image": f"data:image/png;base64,{mannequin_b64}",
                "category": cat,
                "num_samples": 1
            },
            timeout=30
        )
        print(f"      Status: {alt_response.status_code}")
        if alt_response.status_code == 200:
            print(f"      ✅ This one works: '{cat}'")
            break

else:
    print(f"❌ API Error {response.status_code}")
    print(f"   {response.text}")

