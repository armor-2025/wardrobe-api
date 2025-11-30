"""
Reverse Engineer: Use mannequin's perfect clothes + user's face
"""
import os
import cv2
import numpy as np
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 BREAKTHROUGH: Mannequin Clothes + User Face")
print("=" * 70)

# Step 1: Generate PERFECT clothes on mannequin (like we did before)
print("\n🎨 Step 1: Generating perfect clothes on mannequin...")

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

mannequin_prompt = """Create professional fashion photography showing these 3 garments on a model.

REQUIREMENTS:
- Full body standing pose, front-facing
- Professional studio with clean gray background
- Soft even lighting
- High detail rendering of garments:
  * White lace shirt with polka dots
  * Black leather textured shorts
  * Tan cowboy boots
  
Focus on PERFECT garment rendering.
Standard fashion model body type.
Neutral, generic face (we'll replace it).

Return ONLY the final image."""

response = model.generate_content(
    [mannequin_prompt, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(
        temperature=0.4,
        top_p=0.8,
        top_k=40,
    )
)

mannequin_result = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_result = part.inline_data.data
                    with open('breakthrough_step1_mannequin.png', 'wb') as f:
                        f.write(mannequin_result)
                    print("✅ Perfect clothes on mannequin saved!")

if mannequin_result:
    # Step 2: Swap user's face onto the mannequin with perfect clothes
    print("\n🔄 Step 2: Swapping your face onto the mannequin...")
    
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=-1)
    
    swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
    
    # Load images
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        user_photo = f.read()
    
    user_img = cv2.imdecode(np.frombuffer(user_photo, np.uint8), cv2.IMREAD_COLOR)
    mannequin_img = cv2.imdecode(np.frombuffer(mannequin_result, np.uint8), cv2.IMREAD_COLOR)
    
    # Detect faces
    user_faces = app.get(user_img)
    mannequin_faces = app.get(mannequin_img)
    
    if user_faces and mannequin_faces:
        source_face = user_faces[0]
        target_face = mannequin_faces[0]
        
        # Swap face
        result = swapper.get(mannequin_img, target_face, source_face, paste_back=True)
        
        cv2.imwrite('breakthrough_step2_face_swap.png', result)
        print("✅ Face swapped onto perfect clothes!")
        
        print("\n" + "="*70)
        print("🎯 BREAKTHROUGH RESULT!")
        print("="*70)
        print("\nThis approach:")
        print("✅ Perfect clothes (pixel-for-pixel from mannequin)")
        print("✅ Your actual face (from face swap)")
        print("✅ Only 2 steps ($0.20!)")
        print("\n💡 Check: breakthrough_step2_face_swap.png")
        print("="*70)
    else:
        print("❌ Could not detect faces")

