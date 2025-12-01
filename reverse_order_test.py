"""
REVERSE ORDER: Gemini perfect clothes FIRST, then FASHN face swap
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
print("🎯 REVERSE ORDER TEST")
print("=" * 70)
print("Step 1: Gemini creates perfect clothes on mannequin")
print("Step 2: FASHN swaps your face onto that mannequin")
print("=" * 70)

# ==========================================
# STEP 1: Gemini - Perfect clothes on mannequin
# ==========================================
print("\n📍 STEP 1: Gemini generates perfect outfit")

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

gemini_prompt = """Create a full-body fashion mannequin wearing this complete outfit:
- White polka dot shirt
- Black leather shorts  
- Tan cowboy boots

Standing pose, front-facing, clean gray studio background.
Render all garments with maximum detail - capture every texture, pattern, and detail from the reference images.
Professional fashion photography quality."""

response = gemini_model.generate_content(
    [gemini_prompt, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.4,
        top_p=0.8,
        top_k=40,
    )
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('reverse_step1_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Perfect mannequin created!")
                    print("💰 Cost: $0.10")

if not mannequin_bytes:
    print("❌ Gemini failed")
    exit()


# ==========================================
# STEP 2: FASHN - Swap your face onto mannequin
# ==========================================
print("\n📍 STEP 2: FASHN swaps your face onto the mannequin")

# Save mannequin as temporary file
with open('temp_mannequin_for_fashn.png', 'wb') as f:
    f.write(mannequin_bytes)

# Call FASHN with:
# - model_image = your original photo (the face we want)
# - garment_image = the complete mannequin outfit (the clothes we want)

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    your_photo_b64 = base64.b64encode(f.read()).decode('utf-8')

with open('temp_mannequin_for_fashn.png', 'rb') as f:
    mannequin_b64 = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    'https://api.fashn.ai/v1/run',
    headers={
        'Authorization': f'Bearer {FASHN_API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        "model_image": f"data:image/jpeg;base64,{your_photo_b64}",
        "garment_image": f"data:image/png;base64,{mannequin_b64}",
        "category": "tops",  # Or try "full_body" if supported
        "num_samples": 1
    },
    timeout=120
)

if response.status_code == 200:
    result = response.json()
    
    if 'id' in result:
        job_id = result['id']
        print(f"⏳ FASHN job created: {job_id}")
        print("   Waiting for face swap...")
        
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(
                f'https://api.fashn.ai/v1/status/{job_id}',
                headers={'Authorization': f'Bearer {FASHN_API_KEY}'}
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data.get('status') == 'completed':
                    print("✅ FASHN complete!")
                    
                    img_url = status_data['output'][0] if isinstance(status_data['output'], list) else status_data['output']
                    
                    final_img = requests.get(img_url).content
                    with open('reverse_step2_FINAL.png', 'wb') as f:
                        f.write(final_img)
                    
                    print("💰 Cost: $0.075")
                    print("\n" + "=" * 70)
                    print("🎉 REVERSE ORDER COMPLETE!")
                    print("=" * 70)
                    print("\n📊 Results:")
                    print("   reverse_step1_mannequin.png - Perfect clothes (Gemini)")
                    print("   reverse_step2_FINAL.png - Your face on perfect clothes!")
                    print("\n💰 Total Cost: $0.10 + $0.075 = $0.175")
                    print("\n💡 This might be THE solution!")
                    print("=" * 70)
                    break
                
                print(f"   Status: {status_data.get('status', 'processing')}...")
    else:
        print("❌ Unexpected FASHN response")
        print(result)
else:
    print(f"❌ FASHN API error: {response.status_code}")
    print(response.text)

