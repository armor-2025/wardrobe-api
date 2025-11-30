"""
Sequential approach using FASHN for each garment type
"""
import requests
import base64
import os
import time
from PIL import Image
import io

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("=" * 70)
print("🔬 FASHN Sequential: Tops → Bottoms")
print("=" * 70)

def call_fashn(person_path, garment_path, category, output_name):
    """Call FASHN with specific category"""
    with open(person_path, 'rb') as f:
        person_b64 = base64.b64encode(f.read()).decode('utf-8')
    with open(garment_path, 'rb') as f:
        garment_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    print(f"\n   Calling FASHN with category: {category}")
    
    response = requests.post(
        'https://api.fashn.ai/v1/run',
        headers={'Authorization': f'Bearer {FASHN_API_KEY}', 'Content-Type': 'application/json'},
        json={
            "model_image": f"data:image/jpeg;base64,{person_b64}",
            "garment_image": f"data:image/png;base64,{garment_b64}",
            "category": category,
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
                        print(f"   ✅ Saved: {output_name}")
                        return img_bytes
                    elif status_data.get('status') == 'failed':
                        print(f"   ❌ Failed: {status_data.get('error')}")
                        return None
    
    print(f"   ❌ Error: {response.status_code}")
    return None


# ==========================================
# APPROACH 1: FASHN tops → FASHN bottoms
# ==========================================
print("\n🧪 APPROACH 1: FASHN for tops, then FASHN for bottoms")

# Step 1: Apply shirt with FASHN
print("\n📍 Step 1: FASHN - Apply shirt")
step1 = call_fashn(
    base_path + 'IMG_6033.jpeg',
    base_path + 'IMG_5937.PNG',
    'tops',
    'seq_step1_shirt.png'
)

if step1:
    # Step 2: Apply shorts with FASHN (using step 1 result)
    print("\n📍 Step 2: FASHN - Apply shorts to result")
    step2 = call_fashn(
        'seq_step1_shirt.png',
        base_path + 'IMG_5936.PNG',
        'bottoms',
        'seq_step2_shorts.png'
    )
    
    if step2:
        # Step 3: Try boots (might not work, but worth a shot)
        print("\n📍 Step 3: FASHN - Try boots")
        step3 = call_fashn(
            'seq_step2_shorts.png',
            base_path + 'IMG_5938.PNG',
            'bottoms',  # Or 'auto'
            'seq_step3_FINAL.png'
        )
        
        if step3:
            print("\n🎉 Full FASHN sequential worked!")
            print("💰 Cost: 3 × $0.075 = $0.225")
        else:
            print("\n⚠️ Boots didn't work, but we have shirt + shorts")
            print("💰 Cost: 2 × $0.075 = $0.15")


# ==========================================
# SUMMARY
# ==========================================
print("\n" + "=" * 70)
print("📊 FASHN SEQUENTIAL RESULTS")
print("=" * 70)

if os.path.exists('seq_step1_shirt.png'):
    print("\n✅ Step 1: seq_step1_shirt.png (shirt applied)")
if os.path.exists('seq_step2_shorts.png'):
    print("✅ Step 2: seq_step2_shorts.png (shorts applied)")
if os.path.exists('seq_step3_FINAL.png'):
    print("✅ Step 3: seq_step3_FINAL.png (boots applied)")

print("\n💡 If FASHN sequential works:")
print("   - Cost: $0.15-0.225 per outfit")
print("   - Perfect face preservation throughout")
print("   - Better than Gemini sequential ($0.40)")
print("=" * 70)

