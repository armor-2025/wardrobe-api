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

print("=" * 70)
print("🎯 TESTING GLASSES MODEL - LARGER BODY TYPE")
print("=" * 70)

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

your_photo_pil = Image.open(ai_pics_path + 'IMG_6603.JPG')
your_photo_cv = cv2.imread(ai_pics_path + 'IMG_6603.JPG')
source_faces = app.get(your_photo_cv)
source_face = source_faces[0]
print("✅ Ready\n")

def test_outfit(name, garments, desc):
    print(f"🧪 {name}")
    garment_images = [Image.open(g) for g in garments]
    
    prompt = f"""Create professional fashion photograph of a person.

CRITICAL - Match reference person exactly:
- Skin tone: Match reference photo exactly
- Hair: Match reference (color, texture, length)
- Glasses: YES - black frame glasses (match reference)
- Build: Match reference body type
- Age: Match reference

Clothing: {desc}

Pose: Standing straight, front-facing, arms at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography

This model should look ethnically similar to the reference person."""
    
    response = gemini_model.generate_content(
        [prompt, your_photo_pil] + garment_images,
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
            cv2.imwrite(f'glasses_{name}.png', result)
            print(f"   ✅ glasses_{name}.png\n")
            return True
    return False

results = []

if test_outfit("outfit1_red_dress", [ai_pics_path + 'IMG_6563.PNG'], "Red dress, knee-length"):
    results.append("1")

if test_outfit("outfit2_green_dress", [ai_pics_path + 'IMG_6565.PNG'], "Green mini dress"):
    results.append("2")

if test_outfit("outfit3_jumper", [ai_pics_path + 'IMG_6567.PNG', ai_pics_path + 'IMG_6578.PNG'], "Cream knit jumper, indigo wide-leg jeans"):
    results.append("3")

if test_outfit("outfit4_leather", [ai_pics_path + 'IMG_6564.PNG'], "Brown leather trousers, black turtleneck"):
    results.append("4")

if test_outfit("outfit5_jacket", [ai_pics_path + 'IMG_6555.PNG', ai_pics_path + 'IMG_6577.PNG'], "Navy bomber jacket, blue wide-leg jeans"):
    results.append("5")

print("=" * 70)
print(f"📊 Success: {len(results)}/5")
print("=" * 70)
print("\nFiles saved with 'glasses_' prefix")
print("Open folder to view results!")
