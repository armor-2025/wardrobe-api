"""
Test if Gemini can preserve EXACT hair style
"""
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

base_path = '/Users/gavinwalker/Downloads/files (4)/'
ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

print("=" * 70)
print("🧪 TESTING: Exact Hair Preservation")
print("=" * 70)

# Initialize face swap
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1, det_size=(640, 640))
swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)

your_photo_pil = Image.open(base_path + 'IMG_6033.jpeg')
your_photo_cv = cv2.imread(base_path + 'IMG_6033.jpeg')
source_faces = app.get(your_photo_cv)
source_face = source_faces[0]

# ==========================================
# TEST 1: Ultra-specific hair description
# ==========================================
print("\n🧪 TEST 1: Ultra-specific hair description")

shirt = Image.open(ai_pics_path + 'IMG_6541.PNG')
jeans = Image.open(ai_pics_path + 'IMG_6545.PNG')
trainers = Image.open(ai_pics_path + 'IMG_6536.PNG')

prompt1 = """Create professional fashion photograph of a male model.

CRITICAL - Match reference person EXACTLY:
- Skin tone: Light olive/Mediterranean (match reference)
- Hair: EXACT MATCH to reference - dark brown, short (2-3 inches), very curly/tight curls, slightly messy/natural texture, full volume, NOT styled or slicked down
- Facial hair: Light stubble (match reference)
- Build: Slim/athletic
- Face shape: Match reference person

Clothing:
- White crew neck t-shirt
- Black jeans
- Burgundy trainers

Pose: Standing straight, front-facing
Background: Gray studio
Lighting: Professional fashion photography

The hair texture and style must match the reference photo EXACTLY - curly, voluminous, natural."""

response = gemini_model.generate_content(
    [prompt1, your_photo_pil, shirt, jeans, trainers],
    generation_config=genai.types.GenerationConfig(temperature=0.2)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    
                    # Face swap
                    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
                    target_faces = app.get(target_img)
                    
                    if target_faces:
                        result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
                        cv2.imwrite('hair_test1_exact_description.png', result)
                        print("✅ hair_test1_exact_description.png")


# ==========================================
# TEST 2: Reference YOUR exact hair in prompt
# ==========================================
print("\n🧪 TEST 2: Direct reference to your hair")

prompt2 = """Create professional fashion photograph.

Use the reference person's appearance:
- Copy their exact skin tone
- Copy their exact hair (color, texture, curl pattern, length, volume)
- Copy their facial structure and features
- Same age/build

Dress them in:
- White t-shirt
- Black jeans  
- Burgundy trainers

Gray studio background. The model should look like the reference person wearing these clothes."""

response = gemini_model.generate_content(
    [prompt2, your_photo_pil, shirt, jeans, trainers],
    generation_config=genai.types.GenerationConfig(temperature=0.2)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    
                    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
                    target_faces = app.get(target_img)
                    
                    if target_faces:
                        result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
                        cv2.imwrite('hair_test2_copy_reference.png', result)
                        print("✅ hair_test2_copy_reference.png")


# ==========================================
# TEST 3: What we've been using (control)
# ==========================================
print("\n🧪 TEST 3: Current prompt (for comparison)")

prompt3 = """Create professional fashion photograph of a male model.

Match reference person:
- Skin tone: Light olive/Mediterranean complexion (match reference)
- Hair: Short, dark brown, curly/wavy texture (match reference)
- Facial hair: Light stubble
- Build: Slim/athletic

Clothing:
- White t-shirt
- Black jeans
- Burgundy trainers

Gray studio background."""

response = gemini_model.generate_content(
    [prompt3, your_photo_pil, shirt, jeans, trainers],
    generation_config=genai.types.GenerationConfig(temperature=0.3)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mannequin_bytes = part.inline_data.data
                    
                    target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
                    target_faces = app.get(target_img)
                    
                    if target_faces:
                        result = swapper.get(target_img, target_faces[0], source_face, paste_back=True)
                        cv2.imwrite('hair_test3_current.png', result)
                        print("✅ hair_test3_current.png")


print("\n" + "=" * 70)
print("📊 HAIR PRESERVATION ANALYSIS")
print("=" * 70)
print("\nCompare:")
print("   hair_test1_exact_description.png - Ultra-specific hair description")
print("   hair_test2_copy_reference.png - Asked to copy reference")
print("   hair_test3_current.png - Current prompt")
print("\n💡 Questions:")
print("   1. Does more specific description help?")
print("   2. Is Gemini matching or guessing?")
print("   3. Good enough for production?")
print("\n🤔 For female users with long/styled hair:")
print("   - May need different approach")
print("   - Or accept some hair variation")
print("   - Or use better face swap API")
print("=" * 70)

