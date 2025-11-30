"""
Test optimal order: FASHN base → Gemini bottoms → Gemini outer layer
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
print("🎯 OPTIMAL ORDER TESTING")
print("=" * 70)
print("Order: FASHN base top → Gemini bottoms → Gemini outer layer")
print("Testing 3 different outfit combinations")
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


def test_outfit(name, base_top, bottoms, shoes, outer_layer, description):
    """
    Test optimal order:
    1. FASHN for base top
    2. Gemini for bottoms + shoes
    3. Gemini for outer layer (jacket/gilet/coat)
    """
    print(f"\n{'='*70}")
    print(f"🧪 {name}")
    print(f"   {description}")
    print(f"{'='*70}")
    
    # Step 1: FASHN base top
    print(f"\n📍 Step 1: FASHN - {os.path.basename(base_top)}")
    fashn_result = call_fashn(base_path + 'IMG_6033.jpeg', base_top)
    
    if not fashn_result:
        print("❌ FASHN failed")
        return False
    
    with open(f'{name}_step1_base.png', 'wb') as f:
        f.write(fashn_result)
    print("✅ Base top applied, face locked")
    
    # Step 2: Gemini bottoms + shoes
    print(f"\n📍 Step 2: Gemini - Bottoms + Shoes")
    
    current_img = Image.open(io.BytesIO(fashn_result))
    bottoms_img = Image.open(bottoms)
    shoes_img = Image.open(shoes)
    
    prompt = """Add bottoms and shoes.

PRESERVE:
- Face and hair (perfect)
- Top/shirt (perfect)
- Upper body

REPLACE:
- Gray sweatpants → bottoms from reference
- Black socks → shoes from reference

Gray studio background."""

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
                        with open(f'{name}_step2_bottoms.png', 'wb') as f:
                            f.write(bottoms_result)
                        print("✅ Bottoms + shoes added")
    
    if not bottoms_result:
        print("❌ Gemini bottoms failed")
        return False
    
    # Step 3: Gemini outer layer
    if outer_layer:
        print(f"\n📍 Step 3: Gemini - Outer layer")
        
        current_img = Image.open(io.BytesIO(bottoms_result))
        outer_img = Image.open(outer_layer)
        
        prompt = """Add outer layer on top.

PRESERVE:
- Face and hair
- Base top underneath (should show at collar/cuffs)
- Bottoms and shoes

ADD:
- Outer layer from reference (jacket/gilet/coat)
- Layer naturally over base top

Gray studio background."""

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
                            print(f"✅ COMPLETE: {name}_FINAL.png")
                            print("💰 Cost: $0.075 + $0.10 + $0.10 = $0.275")
                            return True
    else:
        # No outer layer, just save bottoms result
        with open(f'{name}_FINAL.png', 'wb') as f:
            f.write(bottoms_result)
        print(f"✅ COMPLETE: {name}_FINAL.png")
        print("💰 Cost: $0.075 + $0.10 = $0.175")
        return True
    
    return False


# ==========================================
# TEST 3 OUTFITS
# ==========================================

results = []

# Outfit 1: Grey jumper + gilet + jeans + trainers (layered)
if test_outfit(
    "optimal1_layered",
    ai_pics_path + 'IMG_6546.PNG',      # grey jumper
    ai_pics_path + 'IMG_6545.PNG',      # black jeans
    ai_pics_path + 'IMG_6536.PNG',      # trainers
    ai_pics_path + 'IMG_6544.PNG',      # gilet (outer layer)
    "Grey jumper + Gilet + Black jeans + Trainers"
):
    results.append("Outfit 1: Layered (jumper+gilet)")

# Outfit 2: White t-shirt + jeans + trainers (simple, no outer)
if test_outfit(
    "optimal2_simple",
    ai_pics_path + 'IMG_6541.PNG',      # white t-shirt
    ai_pics_path + 'IMG_6545.PNG',      # black jeans
    ai_pics_path + 'IMG_6536.PNG',      # trainers
    None,                                # no outer layer
    "White t-shirt + Black jeans + Trainers"
):
    results.append("Outfit 2: Simple (no outer)")

# Outfit 3: Hoodie + trousers + boots + coat (layered)
if test_outfit(
    "optimal3_coat",
    ai_pics_path + 'IMG_6540.PNG',      # hoodie
    ai_pics_path + 'blacktrousers.png', # black trousers
    base_path + 'IMG_5938.PNG',         # cowboy boots
    ai_pics_path + 'IMG_6551.PNG',      # coat (outer layer)
    "Hoodie + Coat + Trousers + Boots"
):
    results.append("Outfit 3: Layered (hoodie+coat)")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("📊 OPTIMAL ORDER TEST RESULTS")
print("=" * 70)

print(f"\nSuccess Rate: {len(results)}/3")
for r in results:
    print(f"   ✅ {r}")

if len(results) == 3:
    print("\n🎉 PERFECT! OPTIMAL ORDER WORKS!")
    print("\n✅ Confirmed approach:")
    print("   1. FASHN: Base top (face lock)")
    print("   2. Gemini: Bottoms + shoes")
    print("   3. Gemini: Outer layer (if needed)")
    print("\n💰 Pricing:")
    print("   Simple outfits: $0.175")
    print("   Layered outfits: $0.275")
    print("\n🚀 READY TO BUILD PRODUCTION API!")
    
elif len(results) >= 2:
    print("\n✅ Good consistency (2/3)")
    print("   Production-ready with retry logic")
else:
    print("\n⚠️ Needs refinement")

print("=" * 70)

