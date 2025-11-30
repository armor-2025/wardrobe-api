"""
Test Kolors Virtual Try-On
Newer model, supposedly better quality than IDM-VTON
"""
import replicate
import os
import base64
import requests

os.environ['REPLICATE_API_TOKEN'] = os.getenv('REPLICATE_API_TOKEN', '')

print("=" * 70)
print("🧪 Testing Kolors Virtual Try-On")
print("=" * 70)

# Load images
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    user_photo = f.read()

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = f.read()

user_b64 = f"data:image/jpeg;base64,{base64.b64encode(user_photo).decode()}"
shirt_b64 = f"data:image/png;base64,{base64.b64encode(shirt).decode()}"

print("\n🔄 Running Kolors VTO...")

try:
    output = replicate.run(
        "kwai-kolors/kolors-virtual-try-on:ab1e7d8d82b5e99b6aa04937f311b0b31e3c03dd9e92d8ce7e6c63eb81f4a950",
        input={
            "mask_image": shirt_b64,
            "human_image": user_b64,
            "garment_image": shirt_b64
        }
    )
    
    result_url = output if isinstance(output, str) else output[0]
    
    print(f"📥 Downloading result...")
    response = requests.get(result_url)
    
    with open('kolors_vto_result.png', 'wb') as f:
        f.write(response.content)
    
    print("✅ Saved: kolors_vto_result.png")
    print("\n💡 Kolors is newer tech, should preserve identity better!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nLet me try OOTDiffusion instead...")

print("\n" + "=" * 70)
