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


def call_gemini(input_img, prompt, output_name, temp=0.2):
    """Call Gemini and return result"""
    print(f"\n🎨 Gemini: {output_name}...")
    
    response = gemini_model.generate_content(
        [prompt, input_img],
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
print("Theory: Gemini makes perfect clothes, FASHN adds your face")

# Load garments
with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5936.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

# Step 1: Gemini creates perfect outfit on mannequin
mannequin_prompt = """Create a fashion mannequin wearing all three items:
- Polka dot shirt
- Black leather shorts
- Tan cowboy boots

Full body standing pose, clean gray studio background.
Perfect garment rendering with all details."""

result = call_gemini([mannequin_prompt, shirt, shorts, boots], mannequin_prompt, 'test1_step1_mannequin.png', temp=0.4)

if result:
    # Step 2: FASHN swaps your face onto mannequin
    mannequin_img = Image.open(io.BytesIO(result))
    
    # Save mannequin as garment image for FASHN
    with open('temp_mannequin_outfit.png', 'wb') as f:
        f.write(result)
    
    # Try FASHN with mannequin as "garment"
    fashn_result = call_fashn(
        base_path + 'IMG_6033.jpeg',
        'temp_mannequin_outfit.png',
        'test1_step2_fashn_swap.png'
    )
    
    print("\n💰 Cost: $0.10 (Gemini) + $0.075 (FASHN) = $0.175")


# ==========================================
# TEST 2: FASHN Sequential (3 separate calls)
# ==========================================
print("\n" + "=" * 70)
print("TEST 2: FASHN Sequential - Shirt → Shorts → Boots")
print("=" * 70)
print("Theory: Use FASHN for each item, preserves face throughout")

# Step 1: Shirt
shirt_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'test2_step1_shirt.png'
)

if shirt_result:
    # Save step 1 result
    with open('temp_step1.jpg', 'wb') as f:
        f.write(shirt_result)
    
    # Step 2: Shorts (on shirt result)
    # Note: FASHN might not support bottoms, but let's try
    shorts_result = call_fashn(
        'temp_step1.jpg',
        base_path + 'IMG_5936.PNG',
        'test2_step2_shorts.png'
    )
    
    if shorts_result:
        with open('temp_step2.jpg', 'wb') as f:
            f.write(shorts_result)
        
        # Step 3: Boots
        boots_result = call_fashn(
            'temp_step2.jpg',
            base_path + 'IMG_5938.PNG',
            'test2_step3_boots.png'
        )
        
        print("\n💰 Cost: 3 × $0.075 = $0.225")


# ==========================================
# TEST 3: FASHN Shirt → Gemini Completes Outfit
# ==========================================
print("\n" + "=" * 70)
print("TEST 3: FASHN Shirt (face lock) → Gemini Adds Shorts+Boots")
print("=" * 70)
print("Theory: FASHN locks face with shirt, Gemini completes outfit")

# Step 1: FASHN for shirt
shirt_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'test3_step1_shirt.png'
)

if shirt_result:
    # Step 2: Gemini adds shorts and boots while preserving face
    shirt_img = Image.open(io.BytesIO(shirt_result))
    
    complete_prompt = """This person is wearing a polka dot shirt. Add these items:
- Black leather shorts
- Tan cowboy boots

CRITICAL: Keep face, hair, and shirt EXACTLY as shown.
Only add the shorts and boots.
Professional studio background."""

    gemini_result = call_gemini(
        [complete_prompt, shirt_img, shorts, boots],
        complete_prompt,
        'test3_step2_complete.png'
    )
    
    print("\n💰 Cost: $0.075 (FASHN) + $0.10 (Gemini) = $0.175")


# ==========================================
# TEST 4: Pure FASHN with Composite Garment Image
# ==========================================
print("\n" + "=" * 70)
print("TEST 4: FASHN with Pre-Composited Full Outfit Image")
print("=" * 70)
print("Theory: Create composite garment image, FASHN applies all at once")

# Create composite garment image using PIL
print("\n🔧 Creating composite garment image...")
shirt_img = Image.open(base_path + 'IMG_5937.PNG')
shorts_img = Image.open(base_path + 'IMG_5936.PNG')  
boots_img = Image.open(base_path + 'IMG_5938.PNG')

# Resize all to same width
target_width = 800
shirt_img = shirt_img.resize((target_width, int(shirt_img.height * target_width / shirt_img.width)))
shorts_img = shorts_img.resize((target_width, int(shorts_img.height * target_width / shorts_img.width)))
boots_img = boots_img.resize((target_width, int(boots_img.height * target_width / boots_img.width)))

# Stack vertically
total_height = shirt_img.height + shorts_img.height + boots_img.height
composite = Image.new('RGB', (target_width, total_height), (240, 240, 240))
composite.paste(shirt_img, (0, 0))
composite.paste(shorts_img, (0, shirt_img.height))
composite.paste(boots_img, (0, shirt_img.height + shorts_img.height))

composite.save('temp_composite_outfit.png')
print("✅ Composite garment created")

# Try FASHN with composite
fashn_result = call_fashn(
    base_path + 'IMG_6033.jpeg',
    'temp_composite_outfit.png',
    'test4_fashn_composite.png'
)

print("\n💰 Cost: $0.075")


# ==========================================
# RESULTS SUMMARY
# ==========================================
print("\n" + "=" * 70)
print("✅ ALL TESTS COMPLETE!")
print("=" * 70)
print("\n📊 Compare these results:")
print("\nTEST 1: Gemini mannequin → FASHN swap ($0.175)")
print("   test1_step1_mannequin.png")
print("   test1_step2_fashn_swap.png")
print("\nTEST 2: FASHN sequential 3x ($0.225)")
print("   test2_step1_shirt.png → test2_step2_shorts.png → test2_step3_boots.png")
print("\nTEST 3: FASHN shirt → Gemini complete ($0.175)")
print("   test3_step1_shirt.png")
print("   test3_step2_complete.png")
print("\nTEST 4: FASHN with composite garment ($0.075)")
print("   test4_fashn_composite.png")
print("\n💡 Check which preserves face AND has best clothes quality!")
print("=" * 70)

