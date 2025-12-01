"""
Single call but with EXTREME identity preservation instructions
"""
import os
import asyncio
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

async def main():
    print("=" * 70)
    print("🎯 Test: ALL items in ONE call + Identity Lock")
    print("=" * 70)
    
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    
    # Load person
    with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
        person = Image.open(io.BytesIO(f.read()))
    
    # Load garments
    with open(base_path + 'IMG_5747.jpg', 'rb') as f:
        jumper = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'white jeans.png', 'rb') as f:
        jeans = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'IMG_5938.PNG', 'rb') as f:
        boots = Image.open(io.BytesIO(f.read()))
    
    prompt = """CRITICAL TASK: Clothing replacement with identity preservation.

INPUT IMAGE: This is a REFERENCE photo of a real person.
GARMENT IMAGES: 3 clothing items to apply.

ABSOLUTE REQUIREMENTS - IDENTITY LOCK:

1. FACE (NON-NEGOTIABLE):
   - This person's face is FIXED and cannot be altered
   - Every facial feature must remain pixel-identical
   - Facial structure, eyes, nose, mouth, jawline: LOCKED
   - Think: You're a photo forensics expert - the face is evidence that cannot be tampered with

2. HAIR (NON-NEGOTIABLE):
   - Hair color: Brown/dark - LOCKED
   - Hair texture: Curly/wavy - LOCKED  
   - Hair style: Medium length, messy curls - LOCKED
   - This hair is unique and must be preserved exactly

3. BODY STRUCTURE (NON-NEGOTIABLE):
   - Body proportions: LOCKED
   - Height/build: LOCKED
   - Skin tone: LOCKED
   - Pose: LOCKED

TASK - CLOTHING ONLY:
Replace current clothes with these 3 NEW items:
- Jumper: Black Adidas with white stripes and logo
- Jeans: White/cream colored jeans
- Boots: Tan leather cowboy boots

TECHNICAL EXECUTION:
- This is precision inpainting, not generation
- Change ONLY fabric regions
- Preserve person completely
- Professional studio background
- High detail on all garments

VERIFICATION CHECK:
After generation, if face/hair differ from input = FAIL
The person must be 100% recognizable as the same individual.

Return: Same person, new clothes, studio background."""

    print("\n🎨 Generating with EXTREME identity lock...")
    
    response = model.generate_content(
        [prompt, person, jumper, jeans, boots],
        generation_config=genai.types.GenerationConfig(
            temperature=0.01,  # ULTRA low
            top_p=0.3,
            top_k=5,
        )
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open('test_single_call_identity.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print("✅ Saved: test_single_call_identity.png")
                        print("\n💰 Cost: $0.10 (ONE call!)")
                        print("\n📊 If this works, we just 4x cheaper!")

asyncio.run(main())
