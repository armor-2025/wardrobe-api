"""
Outside the box: Face replacement on perfect mannequin
NOT virtual try-on - just swap the face!
"""
import os
import requests
import base64
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🎯 OUTSIDE THE BOX: Face Replacement")
print("=" * 70)
print("Approach: Perfect Gemini mannequin + Face swap APIs")
print("NOT virtual try-on - just face replacement!")
print("=" * 70)

# ==========================================
# STEP 1: Gemini creates perfect outfit
# ==========================================
print("\n📍 STEP 1: Gemini - Perfect outfit on mannequin")

shirt = Image.open(base_path + 'IMG_5937.PNG')
shorts = Image.open(base_path + 'IMG_5936.PNG')
boots = Image.open(base_path + 'IMG_5938.PNG')

mannequin_prompt = """Create full-body fashion photograph:

A male model wearing:
- White polka dot shirt (exact pattern from reference)
- Black leather shorts (exact texture from reference)
- Tan cowboy boots (exact details from reference)

CRITICAL for face swap:
- Model facing directly forward
- Clear, visible face with neutral expression
- Good lighting on face
- Standing straight, arms at sides
- Professional fashion photography
- Gray studio background

The model's face should be clearly visible and well-lit for face replacement."""

response = gemini_model.generate_content(
    [mannequin_prompt, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.4)
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('faceswap_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Mannequin with face created")
                    print("💰 Cost: $0.10")

if not mannequin_bytes:
    print("❌ Gemini failed")
    exit()

# ==========================================
# FACE SWAP API OPTIONS
# ==========================================
print("\n" + "=" * 70)
print("🔍 FACE SWAP API OPTIONS (Not VTO!)")
print("=" * 70)

print("\n1. **Picsi.ai Face Swap API**")
print("   - Specifically for face replacement")
print("   - Free tier: 50 swaps/month")
print("   - API: https://www.picsi.ai/api")
print("   - Cost: ~$0.01 per swap")

print("\n2. **DeepAR Face Swap API**")
print("   - Professional face replacement")
print("   - Used by Snapchat, Instagram")
print("   - Cost: Contact for pricing")

print("\n3. **Reface API**")
print("   - Face swap specialists")
print("   - https://reface.ai/")
print("   - Cost: ~$0.02 per swap")

print("\n4. **Akool Face Swap API**")
print("   - https://www.akool.com/")
print("   - Free tier available")
print("   - Cost: ~$0.01-0.02 per swap")

print("\n5. **Faceswap.dev API**")
print("   - Simple REST API")
print("   - https://faceswap.dev/")
print("   - Cost: ~$0.01 per swap")

print("\n" + "=" * 70)
print("💡 TESTING APPROACH")
print("=" * 70)

print("\nLet me test with InsightFace (local, free):")
print("This will show if face swap works in principle...")

try:
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    import cv2
    import numpy as np
    
    print("\n📍 STEP 2: InsightFace - Swap your face onto mannequin")
    
    # Load models
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=-1, det_size=(640, 640))
    swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
    
    # Load images
    source_img = cv2.imread(base_path + 'IMG_6033.jpeg')  # Your face
    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)  # Mannequin
    
    # Detect faces
    print("   Detecting faces...")
    source_faces = app.get(source_img)
    target_faces = app.get(target_img)
    
    if not source_faces:
        print("   ❌ No face in your photo")
    elif not target_faces:
        print("   ❌ No face in mannequin (Gemini didn't add face)")
        print("   💡 This is actually GOOD - we can use Gemini to:")
        print("      1. Generate headless mannequin with perfect clothes")
        print("      2. Then composite YOUR head/face onto it")
    else:
        print(f"   ✅ Faces detected: {len(source_faces)} source, {len(target_faces)} target")
        
        # Swap
        source_face = source_faces[0]
        target_face = target_faces[0]
        result = swapper.get(target_img, target_face, source_face, paste_back=True)
        
        cv2.imwrite('faceswap_RESULT.png', result)
        print("✅ Face swapped!")
        print("💰 Cost: $0.00 (local)")
        
        print("\n" + "=" * 70)
        print("🎉 FACE SWAP WORKS!")
        print("=" * 70)
        print("\n💰 Total: $0.10 (Gemini) + $0.00-0.02 (face swap)")
        print("   = $0.10-0.12 per outfit")
        print("\n📊 Files:")
        print("   faceswap_mannequin.png - Gemini mannequin")
        print("   faceswap_RESULT.png - Your face on mannequin")
        print("=" * 70)

except ImportError:
    print("\n⚠️ InsightFace not installed")
    print("\n💡 Alternative: Use cloud Face Swap APIs:")
    print("\nQuickest to test - Picsi.ai:")
    print("   1. Sign up at https://www.picsi.ai/")
    print("   2. Get API key")
    print("   3. Code:")
    print("""
import requests

response = requests.post(
    'https://api.picsi.ai/faceswap',
    headers={'Authorization': 'Bearer YOUR_KEY'},
    files={
        'source': open('your_face.jpg', 'rb'),
        'target': open('mannequin.png', 'rb')
    }
)
""")

print("\n" + "=" * 70)
print("🎯 THE INSIGHT")
print("=" * 70)
print("\nInstead of VTO (which struggles with clothes),")
print("use FACE SWAP (which is a solved problem!):")
print("\n1. Gemini: Perfect clothes on model/mannequin")
print("2. Face swap API: Your face → that model")
print("3. Done! Cost: ~$0.12")
print("\nThis sidesteps the entire VTO problem!")
print("=" * 70)

