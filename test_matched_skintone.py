"""
Test Gemini with specific skin tone instructions
"""
import os
import cv2
import numpy as np
from PIL import Image
import io
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

base_path = '/Users/gavinwalker/Downloads/files (4)/'
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🎯 TESTING: Gemini with Skin Tone Matching")
print("=" * 70)

# Load your photo
your_photo_pil = Image.open(base_path + 'IMG_6033.jpeg')

# Initialize face swap
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

your_photo_cv = cv2.imread(base_path + 'IMG_6033.jpeg')
source_faces = app.get(your_photo_cv)
source_face = source_faces[0]

# Test with specific skin tone instructions
print("\n📍 Gemini: Generate model with YOUR skin tone")

shirt = Image.open(base_path + 'IMG_5937.PNG')
shorts = Image.open(base_path + 'IMG_5936.PNG')
boots = Image.open(base_path + 'IMG_5938.PNG')

prompt = """Create professional fashion photograph of a male model.

CRITICAL - Match reference person exactly:
- Skin tone: Light olive/Mediterranean complexion (match reference photo)
- Hair: Short, dark brown, curly/wavy texture (match reference)
- Facial hair: Light stubble (match reference)
- Build: Slim/athletic
- Age: Mid-20s

Clothing (from garment references):
- White polka dot shirt
- Black leather shorts
- Tan cowboy boots

Pose: Standing straight, front-facing, arms at sides
Background: Professional gray studio
Lighting: Soft, even, fashion photography

This model should look ethnically similar to the reference person."""

response = gemini_model.generate_content(
    [prompt, your_photo_pil, shirt, shorts, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.3)
)

mannequin_bytes = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    with open('matched_mannequin.png', 'wb') as f:
                        f.write(mannequin_bytes)
                    print("✅ Mannequin with matched skin tone")

if mannequin_bytes:
    # Face swap
    print("\n📍 Face swap onto matched mannequin")
    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
    target_faces = app.get(target_img)
    
    if target_faces:
        result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
        cv2.imwrite('matched_FINAL.png', result)
        print("✅ matched_FINAL.png")
        
        print("\n" + "=" * 70)
        print("📊 COMPARE")
        print("=" * 70)
        print("\nPrevious: outfit1_polkadot_FINAL.png")
        print("New:      matched_FINAL.png")
        print("\nDoes skin tone matching help?")
        print("=" * 70)

