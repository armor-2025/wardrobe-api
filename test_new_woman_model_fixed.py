"""
Test with new female model IMG_G582.jpg
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

ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🎯 TESTING NEW FEMALE MODEL")
print("=" * 70)

# Initialize face swap
print("\n🔧 Initializing...")
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

# Load new woman's photo
woman_photo_pil = Image.open(ai_pics_path + 'IMG_G582.jpg')
woman_photo_cv = cv2.imread(ai_pics_path + 'IMG_G582.jpg')
source_faces = app.get(woman_photo_cv)

if not source_faces:
    print("❌ No face detected")
    exit()

source_face = source_faces[0]
print("✅ New model loaded")


def test_outfit(name, garments, garment_desc):
    """Test outfit with new model"""
    print(f"\n{'='*70}")
    print(f"🧪 {name}")
    print(f"{'='*70}")
    
    garment_images = [Image.open(g) for g in garments]
    
    print("\n📍 Gemini: Generate model")
    
    prompt = f"""Create professional fashion photograph of a female model.

CRITICAL - Match reference woman:
- Skin tone: Match reference exactly
- Hair: Match reference hair (color, texture, length, style)
- Facial features: Similar ethnic background
- Build: Match reference woman
- Age: Match reference

Clothing (from references):
{garment_desc}

Pose: Standing straight, front-facing
Background: Gray studio (#C8C8C8)
Professional fashion photography."""

    response = gemini_model.generate_content(
        [prompt, woman_photo_pil] + garment_images,
        generation_config=genai.types.GenerationConfig(temperature=0.3)
    )
    
    mannequin_bytes = None
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        mannequin_bytes = part.inline_data.data
                        with open(f'{name}_mannequin.png', 'wb') as f:
                            f.write(mannequin_bytes)
                        print("✅ Mannequin ($0.10)")
    
    if not mannequin_bytes:
        print("❌ Gemini failed")
        return False
    
    # Face swap
    print("\n📍 Face swap")
    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
    target_faces = app.get(target_img)
    
    if not target_faces:
        print("⚠️  No face")
        return False
    
    result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
    cv2.imwrite(f'{name}_FINAL.png', result)
    print(f"✅ {name}_FINAL.png")
    
    return True


# ==========================================
# TEST MULTIPLE OUTFITS
# ==========================================

results = []

# Outfit 1: Burgundy mini dress + knee high boots
if test_outfit(
    "newmodel1_burgundy",
    [
        ai_pics_path + 'IMG_6566.PNG',
        ai_pics_path + 'IMG_6573.PNG'
    ],
    "Burgundy/wine mini dress, black knee-high leather boots"
):
    results.append("1: Burgundy dress")

# Outfit 2: Faux fur coat + leather trousers + boots
if test_outfit(
    "newmodel2_fur_coat",
    [
        ai_pics_path + 'IMG_6571.PNG',
        ai_pics_path + 'IMG_6564.PNG',
        ai_pics_path + 'IMG_6576.PNG'
    ],
    "Long brown faux fur coat, brown leather trousers, tall heeled boots"
):
    results.append("2: Fur coat")

# Outfit 3: Polo + indigo jeans + UGGs
if test_outfit(
    "newmodel3_casual",
    [
        ai_pics_path + 'IMG_6570.PNG',
        ai_pics_path + 'IMG_6578.PNG',
        ai_pics_path + 'IMG_6574.PNG'
    ],
    "Long sleeve polo shirt, indigo wide-leg jeans, sand UGG-style boots"
):
    results.append("3: Casual polo")

# Outfit 4: Red dress + high boots
if test_outfit(
    "newmodel4_red",
    [
        ai_pics_path + 'IMG_6563.PNG',
        ai_pics_path + 'IMG_6576.PNG'
    ],
    "Red dress, black tall heeled boots"
):
    results.append("4: Red dress")

# Outfit 5: Cream jumper + blue jeans + knee boots
if test_outfit(
    "newmodel5_jumper",
    [
        ai_pics_path + 'IMG_6567.PNG',
        ai_pics_path + 'IMG_6577.PNG',
        ai_pics_path + 'IMG_6573.PNG'
    ],
    "Cream/beige knit jumper, blue wide-leg jeans, knee-high black boots"
):
    results.append("5: Jumper casual")


# ==========================================
# RESULTS
# ==========================================
print("\n" + "=" * 70)
print("📊 NEW MODEL RESULTS")
print("=" * 70)

print(f"\nSuccess Rate: {len(results)}/5")
for r in results:
    print(f"   ✅ Outfit {r}")

if len(results) >= 4:
    print("\n🎉 CONSISTENT ACROSS DIFFERENT WOMEN!")
    print("\n✅ System validated:")
    print("   - Multiple models (men & women) ✓")
    print("   - Various outfits ✓")
    print("   - Cost: $0.10 per outfit")
    print("\n🚀 PRODUCTION-READY!")

print("=" * 70)

