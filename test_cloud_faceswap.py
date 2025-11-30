"""
Test cloud face swap APIs for better skin tone/hair preservation
"""
import os
import requests
import base64
from PIL import Image
import io

base_path = '/Users/gavinwalker/Downloads/files (4)/'

print("=" * 70)
print("🔬 CLOUD FACE SWAP API OPTIONS")
print("=" * 70)

print("\n1️⃣ AKOOL Face Swap (FREE TIER)")
print("   - Best for preserving skin tone")
print("   - Free: 10 swaps/day")
print("   - Sign up: https://www.akool.com/")
print("")
print("   Code:")
print("""
import requests

response = requests.post(
    'https://openapi.akool.com/api/open/v3/faceswap/highquality/specifyimage',
    headers={'Authorization': 'Bearer YOUR_KEY'},
    json={
        'source_image': 'base64_your_face',
        'target_image': 'base64_mannequin'
    }
)
""")

print("\n2️⃣ DEEPSWAP API")
print("   - Very good skin tone matching")
print("   - $0.02 per swap")
print("   - https://www.deepswap.ai/")

print("\n3️⃣ REFACE API")
print("   - Professional quality")
print("   - Best hair preservation")
print("   - $0.02 per swap")
print("   - https://reface.ai/")

print("\n4️⃣ FACESWAPPER.AI")
print("   - Simple API")
print("   - Good skin tone")
print("   - $0.01 per swap")
print("   - https://faceswapper.ai/api")

print("\n" + "=" * 70)
print("💡 RECOMMENDED: Try Akool (Free)")
print("=" * 70)

print("\nSteps:")
print("1. Sign up at https://www.akool.com/")
print("2. Get API key from dashboard")
print("3. Test with one of our perfect Gemini mannequins")

print("\nOr I can help you set up any of these APIs!")
print("=" * 70)

