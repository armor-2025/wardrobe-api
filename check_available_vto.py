"""
Try different VTO models available on Replicate
"""
import replicate
import os
import base64
import requests

os.environ['REPLICATE_API_TOKEN'] = os.getenv('REPLICATE_API_TOKEN', '')

print("=" * 70)
print("🔍 Testing Available VTO Models")
print("=" * 70)

# Load images
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    user_photo = f.read()

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = f.read()

user_b64 = f"data:image/jpeg;base64,{base64.b64encode(user_photo).decode()}"
shirt_b64 = f"data:image/png;base64,{base64.b64encode(shirt).decode()}"

# Try different models
models_to_try = [
    {
        "name": "Outfit Anyone",
        "model": "samin/outfit-anyone:eb6e9c8b6cb81e97d0e0f624f35e10f7e8aeffd90b0f3ca19e4c3ef81e8ffb97",
        "input": {
            "model_image": user_b64,
            "garment_image": shirt_b64,
        }
    },
    {
        "name": "Magic Clothing",
        "model": "viktorfa/magic-clothing:2a7f3b9ad6f63d6d0e65844ba72b2cc7a0c3e2c7a23f6c6e2d9c4a6f9d9e8c1a",
        "input": {
            "person_img": user_b64,
            "cloth_img": shirt_b64,
        }
    },
]

for model_info in models_to_try:
    print(f"\n{'='*70}")
    print(f"🧪 Testing: {model_info['name']}")
    print('='*70)
    
    try:
        output = replicate.run(
            model_info['model'],
            input=model_info['input']
        )
        
        result_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else str(output))
        
        print(f"✅ Success! Downloading...")
        response = requests.get(result_url)
        
        filename = f"vto_{model_info['name'].replace(' ', '_').lower()}.png"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Saved: {filename}")
        break  # If one works, stop trying
        
    except Exception as e:
        print(f"❌ {model_info['name']} failed: {e}")
        continue

print("\n" + "=" * 70)
