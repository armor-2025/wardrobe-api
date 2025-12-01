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

ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

your_photo_pil = Image.open(ai_pics_path + 'IMG_6603.JPG')
your_photo_cv = cv2.imread(ai_pics_path + 'IMG_6603.JPG')
source_faces = app.get(your_photo_cv)
source_face = source_faces[0]

print("=" * 70)
print("🧪 COMPARING: WITH HEIGHT vs WITHOUT HEIGHT")
print("=" * 70)
print("Testing same outfit twice:")
print("  A) With height: 'curvy plus build, tall height'")
print("  B) Without height: 'curvy plus build'")
print("=" * 70 + "\n")

def test_outfit(name, body_prompt, include_height_in_name):
    print(f"Testing: {name}")
    
    garment1 = Image.open(ai_pics_path + 'IMG_6567.PNG')
    garment2 = Image.open(ai_pics_path + 'IMG_6578.PNG')
    garment3 = Image.open(ai_pics_path + 'IMG_6574.PNG')
    
    prompt = f"""FULL-LENGTH professional fashion photograph from HEAD TO FEET.

CRITICAL - Match reference person exactly:
- Skin tone: Match reference photo exactly
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: YES - match reference glasses exactly
- Facial features: Match reference ethnicity and features exactly
- Body type and height: {body_prompt}
- Age: Match reference age

Clothing (COMPLETE outfit from top to bottom):
- Top: Cream chunky knit oversized sweater
- Bottoms: Indigo wide-leg jeans (full length to ankles)
- Footwear: Sand/beige UGG-style boots

COMPOSITION REQUIREMENTS (CRITICAL):
- FULL BODY SHOT: Must show entire person from head to feet
- Include complete legs and footwear in frame
- Framing: Show full outfit from top of head to bottom of shoes
- Camera angle: Full-length body shot (not cropped at legs or knees)
- Ensure feet and shoes are fully visible

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that authentically represents the reference person with their exact appearance and body type wearing the complete outfit."""
    
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
            filename = f'COMPARE_{name}.png'
            cv2.imwrite(filename, result)
            print(f"   ✅ {filename}\n")
            return True
    print(f"   ❌ Failed\n")
    return False

# Test A: With height
test_outfit(
    "A_with_tall_height",
    "curvy plus build, fuller figure, tall height over 5'8\", longer proportions and limbs",
    True
)

# Test B: Without height  
test_outfit(
    "B_without_height",
    "curvy plus build, fuller figure",
    False
)

print("=" * 70)
print("RESULTS")
print("=" * 70)
print("\nCompare side-by-side:")
print("  COMPARE_A_with_tall_height.png")
print("  COMPARE_B_without_height.png")
print("\nLook for:")
print("  • Leg length difference?")
print("  • Overall height proportions?")
print("  • Body type consistency?")
print("  • Face quality difference?")
print("=" * 70)
