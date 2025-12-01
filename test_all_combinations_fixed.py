"""
Test ALL possible combinations to find the winner
"""
import requests
import base64
import os
import time
from PIL import Image
import io
import google.generativeai as genai

print("=" * 70)
print("🔬 TESTING ALL VTO COMBINATIONS")
print("=" * 70)

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'
os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'


def call_fashn(person_path, garment_path, output_name):
    """Call FASHN AI and return result"""
    print(f"\n🔄 FASHN AI: {output_name}...")
    
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
                        img_bytes = requests.get(img_url).content
                        
                        with open(output_name, 'wb') as f:
                            f.write(img_bytes)
                        print(f"✅ Saved: {output_name}")
                        return img_bytes
    
    print(f"❌ FASHN failed")
    return None


def call_gemini(prompt, images, output_name, temp=0.2):
    """Call Gemini and return result"""
    print(f"\n🎨 Gemini: {output_name}...")
    
    # Build content list: prompt first, then images
    content = [prompt] + images
    
    response = gemini_model.generate_content(
        content,
        generation_config=genai.types.GenerationConfig(
            temperature=temp,
            top_p=0.6,
            top_k=15,
        )
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open(output_name, 'wb') as f:
                            f.write(part.inline_data.data)
                        print(f"✅ Saved: {output_name}")
                        return part.inline_data.data
    
    print(f"❌ Gemini failed")
    return None


# ==========================================
# TEST 1: Gemini Mannequin → FASHN Swap
# ==========================================
print("\n" + "=" * 70)
print("TEST 1: Gemini Full Outfit on Mannequin → FASHN Face Swap")
print("=" * 70)

# Load garments
with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

mannequin_prompt = """Create a fashion mannequin wearing all three items:
- Polka dot shirt
- Black leather shorts
- Tan cowboy boots

Full body standing pose, clean gray studio background.
Perfect garment rendering with all details."""

result = call_gemini(mannequin_prompt, [shirt, shorts, boots], 'test1_step1_mannequin.png', temp=0.4)

if result:
    with open('temp_mannequin_outfit.png', 'wb') as f:
        f.write(result)
    
    fashn_result = call_fashn(
        base_path + 'IMG_6033.jpeg',
        'temp_mannequin_outfit.png',
        'test1_step2_fashn_swap.png'
    )
    
    print("\n💰 Cost: $0.10 + $0.075 = $0.175")


# ==========================================
# TEST 2: FASHN Sequential
# ==========================================
print("\n" + "=" * 70)
print("TEST 2: FASHN Sequential - Shirt only (FASHN doesn't do bottoms)")
print("=" * 70)

shirt_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'test2_fashn_shirt_only.png'
)

print("\n💰 Cost: $0.075")


# ==========================================
# TEST 3: FASHN Shirt → Gemini Completes
# ==========================================
print("\n" + "=" * 70)
print("TEST 3: FASHN Shirt → Gemini Adds Shorts+Boots")
print("=" * 70)

shirt_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'test3_step1_shirt.png'
)

if shirt_result:
    shirt_img = Image.open(io.BytesIO(shirt_result))
    
    complete_prompt = """This person is wearing a polka dot shirt. Add these items:
- Black leather shorts
- Tan cowboy boots

CRITICAL: Keep face, hair, upper body, and polka dot shirt EXACTLY as shown.
Only add the shorts and boots.
Professional studio background."""

    gemini_result = call_gemini(
        complete_prompt,
        [shirt_img, shorts, boots],
        'test3_step2_complete.png'
    )
    
    print("\n💰 Cost: $0.075 + $0.10 = $0.175")


# ==========================================
# TEST 4: FASHN with Composite Image
# ==========================================
print("\n" + "=" * 70)
print("TEST 4: FASHN with Pre-Made Full Outfit Image")
print("=" * 70)

# Use the mannequin image from test 1 if available
if os.path.exists('test1_step1_mannequin.png'):
    fashn_result = call_fashn(
        base_path + 'IMG_6033.jpeg',
        'test1_step1_mannequin.png',
        'test4_fashn_full_outfit.png'
    )
    print("\n💰 Cost: $0.075")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("✅ TESTS COMPLETE!")
print("=" * 70)
print("\nCompare:")
print("  TEST 1: test1_step2_fashn_swap.png ($0.175)")
print("  TEST 2: test2_fashn_shirt_only.png ($0.075)")
print("  TEST 3: test3_step2_complete.png ($0.175)")
print("  TEST 4: test4_fashn_full_outfit.png ($0.075)")
print("\n💡 Which has best face + clothes quality?")
print("=" * 70)

