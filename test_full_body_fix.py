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

print("🧪 TESTING FIXED FULL-BODY PROMPT")
print("=" * 70)

# Test with outfit that should have shoes
garment1 = Image.open(ai_pics_path + 'IMG_6567.PNG')  # Cream jumper
garment2 = Image.open(ai_pics_path + 'IMG_6578.PNG')  # Jeans
garment3 = Image.open(ai_pics_path + 'IMG_6574.PNG')  # Sand UGG boots

# FIXED PROMPT - Forces full body with shoes
prompt = """Create a FULL-LENGTH professional fashion photograph of a person from HEAD TO FEET.

CRITICAL - Match reference person exactly:
- Skin tone: Match reference photo exactly
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: YES - match reference glasses
- Facial features: Match reference ethnicity and features exactly
- Build: curvy plus build, fuller frame
- Age: Match reference age

Clothing (COMPLETE outfit from top to bottom):
- Top: Cream chunky knit oversized sweater
- Bottoms: Indigo wide-leg jeans (full length, reaching to ankles)
- Footwear: Sand/beige UGG-style boots

COMPOSITION REQUIREMENTS:
- FULL BODY SHOT: Must show entire person from head to feet
- Include complete legs and footwear in frame
- Framing: Show full outfit from top of head to bottom of shoes
- Pose: Standing straight, arms naturally at sides
- Camera angle: Full-length body shot (not cropped at legs)

Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a complete head-to-toe fashion photograph showing the entire outfit and person."""

response = gemini_model.generate_content(
    [prompt, your_photo_pil, garment1, garment2, garment3],
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
        cv2.imwrite('FIXED_full_body_with_shoes.png', result)
        print("✅ FIXED_full_body_with_shoes.png")
        print("\n👀 Check if shoes are visible now!")
    else:
        print("❌ No face detected")
else:
    print("❌ Generation failed")

print("=" * 70)
