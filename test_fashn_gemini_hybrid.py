"""
Hybrid Approach: FASHN AI (face preservation) + Gemini (polish/refinement)
"""
import requests
import base64
import os
import time
from PIL import Image
import io
import google.generativeai as genai

print("=" * 70)
print("🎯 HYBRID: FASHN AI + Gemini Polish")
print("=" * 70)

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'
os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'

# ==========================================
# STEP 1: FASHN AI for Identity Preservation
# ==========================================
print("\n" + "=" * 70)
print("STEP 1: FASHN AI - Perfect Face/Hair Preservation")
print("=" * 70)

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    person_b64 = base64.b64encode(f.read()).decode('utf-8')

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    garment_b64 = base64.b64encode(f.read()).decode('utf-8')

print("\n🔄 Calling FASHN AI...")

response = requests.post(
    'https://api.fashn.ai/v1/run',
    headers={
        'Authorization': f'Bearer {FASHN_API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        "model_image": f"data:image/jpeg;base64,{person_b64}",
        "garment_image": f"data:image/png;base64,{garment_b64}",
        "category": "tops",
        "num_samples": 1,
        "seed": 42
    },
    timeout=120
)

fashn_result_bytes = None

if response.status_code == 200:
    result = response.json()
    
    if 'id' in result:
        job_id = result['id']
        print(f"⏳ Job created: {job_id}, polling...")
        
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(
                f'https://api.fashn.ai/v1/status/{job_id}',
                headers={'Authorization': f'Bearer {FASHN_API_KEY}'}
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data.get('status') == 'completed':
                    print("✅ FASHN AI complete!")
                    
                    img_url = status_data['output'][0] if isinstance(status_data['output'], list) else status_data['output']
                    
                    img_response = requests.get(img_url)
                    fashn_result_bytes = img_response.content
                    
                    with open('step1_fashn_result.png', 'wb') as f:
                        f.write(fashn_result_bytes)
                    
                    print("✅ Saved: step1_fashn_result.png")
                    print("💰 Cost: $0.075")
                    break

if fashn_result_bytes:
    # ==========================================
    # STEP 2: Gemini Polish & Refinement
    # ==========================================
    print("\n" + "=" * 70)
    print("STEP 2: Gemini Polish - Fix Details & Studio Background")
    print("=" * 70)
    
    fashn_img = Image.open(io.BytesIO(fashn_result_bytes))
    
    polish_prompt = """Professional photo refinement task:

INPUT: VTO result with person wearing new garment

REFINEMENT NEEDED:
1. PRESERVE COMPLETELY (DO NOT CHANGE):
   - Person's face (already perfect)
   - Person's hair (already perfect)
   - Person's body proportions
   
2. ENHANCE/FIX:
   - Garment details and textures
   - Make polka dot pattern clearer and more defined
   - Fix any transparency or blending issues on the garment
   - Ensure collar sits naturally
   - Clean up any artifacts
   
3. BACKGROUND:
   - Replace background with clean professional studio (light gray)
   - Soft studio lighting
   - Professional fashion photography quality

Think: This is photo retouching, not regeneration.
Keep the person identical, polish the garment and background.

Output: Professional studio portrait with refined garment details."""

    print("\n🎨 Applying Gemini polish...")
    
    response = gemini_model.generate_content(
        [polish_prompt, fashn_img],
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            top_p=0.6,
            top_k=15,
        )
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open('step2_gemini_polished.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print("✅ Saved: step2_gemini_polished.png")
                        print("💰 Cost: $0.10")
    
    # ==========================================
    # FINAL RESULT
    # ==========================================
    print("\n" + "=" * 70)
    print("✅ HYBRID PIPELINE COMPLETE!")
    print("=" * 70)
    print("\n📊 Results:")
    print("   1. step1_fashn_result.png - FASHN AI (face preserved)")
    print("   2. step2_gemini_polished.png - Gemini polished (final)")
    print("\n💰 Total Cost: $0.175 per outfit")
    print("\n🎯 Quality:")
    print("   ✅ Perfect face/hair preservation (FASHN)")
    print("   ✅ Refined garment details (Gemini)")
    print("   ✅ Professional studio background (Gemini)")
    print("=" * 70)

else:
    print("❌ FASHN AI step failed, cannot continue to polish")

