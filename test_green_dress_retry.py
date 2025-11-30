import os
import cv2
import numpy as np
from PIL import Image
import io
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')

ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

your_photo_pil = Image.open(ai_pics_path + 'IMG_6603.JPG')
your_photo_cv = cv2.imread(ai_pics_path + 'IMG_6603.JPG')
source_faces = app.get(your_photo_cv)
source_face = source_faces[0]

print("🧪 RETESTING GREEN DRESS (3 attempts)")
print("=" * 70)

for i in range(1, 4):
    print(f"\nAttempt {i}/3:")
    
    garment = Image.open(ai_pics_path + 'IMG_6565.PNG')
    
    prompt = """Create professional fashion photograph of a person.

CRITICAL - Match reference person exactly:
- Skin tone: Match reference photo exactly
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: YES - match reference glasses
- Facial features: Match reference ethnicity and features exactly
- Build: curvy plus build, fuller frame
- Age: Match reference age

Clothing: Green mini dress

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that authentically represents the reference person with curvy/plus body type wearing the green dress."""
    
    response = gemini_model.generate_content(
        [prompt, your_photo_pil, garment],
        generation_config=genai.types.GenerationConfig(temperature=0.3)
    )
    
    mannequin_bytes = None
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        mannequin_bytes = part.inline_data.data
    
    if mannequin_bytes:
        target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
        target_faces = app.get(target_img)
        if target_faces:
            result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
            cv2.imwrite(f'green_dress_retry_{i}.png', result)
            print(f"   ✅ green_dress_retry_{i}.png")
        else:
            print(f"   ❌ No face detected")
    else:
        print(f"   ❌ Generation failed")

print("\n" + "=" * 70)
print("Open folder to compare all 3 attempts")
