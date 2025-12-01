"""
Test more outfit combinations from your wardrobe
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
print("🧪 MORE OUTFIT TESTS")
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


def test_simple_outfit(name, top, bottoms, shoes, description):
    """Simple outfit: base + bottoms (optimal quality)"""
    print(f"\n{'='*70}")
    print(f"🧪 {name}: {description}")
    print(f"{'='*70}")
    
    # Step 1: FASHN
    print(f"\n📍 FASHN: {os.path.basename(top)}")
    fashn_result = call_fashn(base_path + 'IMG_6033.jpeg', top)
    
    if not fashn_result:
        print("❌ FASHN failed")
        return False
    
    print("✅ Top applied")
    
    # Step 2: Gemini bottoms
    print(f"\n📍 Gemini: {os.path.basename(bottoms)} + {os.path.basename(shoes)}")
    
    current_img = Image.open(io.BytesIO(fashn_result))
    bottoms_img = Image.open(bottoms)
    shoes_img = Image.open(shoes)
    
    prompt = """Add bottoms and shoes.

PRESERVE: Face, hair, top, upper body
REPLACE: Gray sweatpants → bottoms, Black socks → shoes

Gray studio background."""

    response = gemini_model.generate_content(
        [prompt, current_img, bottoms_img, shoes_img],
        generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open(f'{name}_FINAL.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print(f"✅ {name}_FINAL.png")
                        print("💰 $0.175")
                        return True
    
    return False


def test_layered_outfit(name, base_top, bottoms, shoes, outer, description):
    """Layered outfit: base + bottoms + outer"""
    print(f"\n{'='*70}")
    print(f"🧪 {name}: {description}")
    print(f"{'='*70}")
    
    # Step 1: FASHN
    print(f"\n📍 FASHN: {os.path.basename(base_top)}")
    fashn_result = call_fashn(base_path + 'IMG_6033.jpeg', base_top)
    
    if not fashn_result:
        print("❌ FASHN failed")
        return False
    
    print("✅ Base top applied")
    
    # Step 2: Gemini bottoms
    print(f"\n📍 Gemini: Bottoms + Shoes")
    
    current_img = Image.open(io.BytesIO(fashn_result))
    bottoms_img = Image.open(bottoms)
    shoes_img = Image.open(shoes)
    
    prompt = """Add bottoms and shoes.
PRESERVE: Face, hair, top
REPLACE: Sweatpants → bottoms, Socks → shoes
Gray background."""

    response = gemini_model.generate_content(
        [prompt, current_img, bottoms_img, shoes_img],
        generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
    )
    
    bottoms_result = None
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        bottoms_result = part.inline_data.data
                        print("✅ Bottoms added")
    
    if not bottoms_result:
        return False
    
    # Step 3: Gemini outer layer
    print(f"\n📍 Gemini: {os.path.basename(outer)}")
    
    current_img = Image.open(io.BytesIO(bottoms_result))
    outer_img = Image.open(outer)
    
    prompt = """Add outer layer on top.
PRESERVE: Face, hair, base top underneath, bottoms, shoes
ADD: Outer layer from reference
Gray background."""

    response = gemini_model.generate_content(
        [prompt, current_img, outer_img],
        generation_config=genai.types.GenerationConfig(temperature=0.1, top_p=0.5, top_k=10)
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open(f'{name}_FINAL.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print(f"✅ {name}_FINAL.png")
                        print("💰 $0.275")
                        return True
    
    return False


# ==========================================
# SIMPLE OUTFITS (Best Quality)
# ==========================================

results = []

# Test 1: Polka dot + leather shorts + boots
if test_simple_outfit(
    "test_a_polka",
    base_path + 'IMG_5937.PNG',
    base_path + 'IMG_5936.PNG',
    base_path + 'IMG_5938.PNG',
    "Polka dot + Leather shorts + Cowboy boots"
):
    results.append("A: Polka dot outfit")

# Test 2: Adidas sweatshirt + trousers + trainers
if test_simple_outfit(
    "test_b_adidas",
    ai_pics_path + 'IMG_5747.jpg',
    ai_pics_path + 'blacktrousers.png',
    ai_pics_path + 'IMG_6536.PNG',
    "Adidas sweatshirt + Black trousers + Trainers"
):
    results.append("B: Adidas casual")

# Test 3: White long sleeve + jeans + boots
if test_simple_outfit(
    "test_c_longsleeve",
    ai_pics_path + 'IMG_6552.PNG',
    ai_pics_path + 'IMG_6545.PNG',
    base_path + 'IMG_5938.PNG',
    "White long sleeve + Black jeans + Cowboy boots"
):
    results.append("C: Long sleeve")

# Test 4: Hoodie + trousers + trainers
if test_simple_outfit(
    "test_d_hoodie",
    ai_pics_path + 'IMG_6540.PNG',
    ai_pics_path + 'blacktrousers.png',
    ai_pics_path + 'IMG_6536.PNG',
    "Hoodie + Black trousers + Trainers"
):
    results.append("D: Hoodie casual")


# ==========================================
# LAYERED OUTFITS
# ==========================================

# Test 5: White tee + jacket + jeans + trainers
if test_layered_outfit(
    "test_e_tee_jacket",
    ai_pics_path + 'IMG_6541.PNG',
    ai_pics_path + 'IMG_6545.PNG',
    ai_pics_path + 'IMG_6536.PNG',
    ai_pics_path + 'IMG_6555.PNG',
    "White tee + Jacket + Jeans + Trainers"
):
    results.append("E: Tee + Jacket")

# Test 6: Long sleeve + coat + trousers + boots
if test_layered_outfit(
    "test_f_longsleeve_coat",
    ai_pics_path + 'IMG_6552.PNG',
    ai_pics_path + 'blacktrousers.png',
    base_path + 'IMG_5938.PNG',
    ai_pics_path + 'IMG_6551.PNG',
    "Long sleeve + Coat + Trousers + Boots"
):
    results.append("F: Long sleeve + Coat")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("📊 COMPREHENSIVE TEST RESULTS")
print("=" * 70)

print(f"\nSuccess Rate: {len(results)}/6")
for r in results:
    print(f"   ✅ {r}")

if len(results) >= 5:
    print("\n🎉 EXCELLENT CONSISTENCY!")
    print("\n✅ System validated across:")
    print("   - Multiple tops (shirts, sweatshirts, hoodies)")
    print("   - Multiple bottoms (jeans, trousers, shorts)")
    print("   - Multiple shoes (boots, trainers)")
    print("   - Layered combinations (jacket, coat)")
    print("\n🚀 PRODUCTION-READY!")
    
print("=" * 70)

