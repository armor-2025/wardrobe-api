"""
NEW APPROACH: Gemini perfect clothes + Face swap
"""
import os
from PIL import Image
import io
import cv2
import numpy as np
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 FACE SWAP APPROACH")
print("=" * 70)
print("Step 1: Gemini creates PERFECT outfit on mannequin")
print("Step 2: Face swap YOUR face onto it")
print("=" * 70)

# Step 1: Gemini creates perfect outfit
print("\n📍 STEP 1: Gemini - Perfect outfit")

ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

sweatshirt = Image.open(ai_pics_path + 'IMG_5747.jpg')
trousers = Image.open(ai_pics_path + 'blacktrousers.png')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

prompt = """Create full-body fashion mannequin wearing:
- Black Adidas sweatshirt (with logo and white stripes)
- Black wide-leg trousers
- Brown/burgundy Adidas trainers

Standing pose, front-facing, gray studio background.
Maximum detail on all garments - capture every logo, stripe, texture."""

response = gemini_model.generate_content(
    [prompt, sweatshirt, trousers, trainers],
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
                    print("✅ Perfect mannequin created")
                    print("💰 Cost: $0.10")

if not mannequin_bytes:
    print("❌ Gemini failed")
    exit()

# Step 2: Face swap
print("\n📍 STEP 2: Face swap using InsightFace...")

try:
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    
    # Initialize face swap model
    print("   Loading face swap model...")
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=-1, det_size=(640, 640))
    
    swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
    
    # Load images
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    source_img = cv2.imread(base_path + 'IMG_6033.jpeg')  # Your photo
    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)  # Mannequin
    
    # Detect faces
    print("   Detecting faces...")
    source_faces = app.get(source_img)
    target_faces = app.get(target_img)
    
    if not source_faces:
        print("   ❌ No face found in your photo")
        exit()
    
    if not target_faces:
        print("   ❌ No face found in mannequin")
        exit()
    
    print(f"   ✅ Found faces: {len(source_faces)} source, {len(target_faces)} target")
    
    # Swap faces
    print("   Swapping faces...")
    source_face = source_faces[0]
    target_face = target_faces[0]
    
    result = swapper.get(target_img, target_face, source_face, paste_back=True)
    
    cv2.imwrite('faceswap_FINAL.png', result)
    print("✅ Face swap complete!")
    print("💰 Cost: ~$0.00 (local processing)")
    
    print("\n" + "=" * 70)
    print("🎉 FACE SWAP APPROACH COMPLETE!")
    print("=" * 70)
    print("\n💰 Total Cost: $0.10")
    print("\nResult: faceswap_FINAL.png")
    print("   - YOUR face")
    print("   - PERFECT Adidas sweatshirt (from Gemini)")
    print("   - PERFECT trousers (from Gemini)")
    print("   - PERFECT trainers (from Gemini)")
    print("\n💡 If this works, you just found a $0.10 solution!")
    print("=" * 70)

except ImportError:
    print("\n⚠️  InsightFace not installed")
    print("\nInstall with:")
    print("  pip install insightface onnxruntime --break-system-packages")
    print("\nThis approach swaps YOUR face onto Gemini's perfect clothes!")
    print("Cost would be: $0.10 (Gemini) + ~$0.00 (face swap)")

