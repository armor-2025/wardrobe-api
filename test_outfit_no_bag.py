"""
Test: Jumper + Jeans + Boots + Cap (skip bag)
"""
import os
import asyncio
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_item_max_detail(current_img, item_img, item_name, item_description):
    prompt = f"""Precision inpainting: Replace ONLY the {item_name}.

CRITICAL: Keep face, hair, body, background IDENTICAL.
Capture all texture details from new {item_name}.

{item_description}"""

    response = model.generate_content(
        [prompt, current_img, item_img],
        generation_config=genai.types.GenerationConfig(temperature=0.03, top_p=0.4, top_k=8)
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return part.inline_data.data
    return None


async def main():
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    
    print("=" * 70)
    print("🎨 Testing New Outfit: Jumper + Jeans + Boots + Cap")
    print("=" * 70)
    
    # Continue from jumper
    with open('new_outfit_step1_jumper.png', 'rb') as f:
        current = f.read()
    
    # Jeans
    print("\n👖 Adding white jeans...")
    with open(base_path + 'white jeans.png', 'rb') as f:
        jeans = f.read()
    current = await apply_item_max_detail(Image.open(io.BytesIO(current)), Image.open(io.BytesIO(jeans)), "jeans", "White denim jeans")
    with open('outfit_jeans.png', 'wb') as f:
        f.write(current)
    print("✅ Jeans applied")
    
    # Boots
    print("\n👢 Adding cowboy boots...")
    with open(base_path + 'IMG_5938.PNG', 'rb') as f:
        boots = f.read()
    current = await apply_item_max_detail(Image.open(io.BytesIO(current)), Image.open(io.BytesIO(boots)), "boots", "Tan leather cowboy boots with stitching")
    with open('outfit_boots.png', 'wb') as f:
        f.write(current)
    print("✅ Boots applied")
    
    # Cap
    print("\n🧢 Adding cap...")
    with open(base_path + 'IMG_5940.PNG', 'rb') as f:
        cap = f.read()
    current = await apply_item_max_detail(Image.open(io.BytesIO(current)), Image.open(io.BytesIO(cap)), "cap", "Baseball cap worn on head")
    with open('outfit_cap.png', 'wb') as f:
        f.write(current)
    print("✅ Cap applied")
    
    # Studio BG
    print("\n🎨 Adding studio background...")
    response = model.generate_content(
        ["Professional photo studio: Place person in clean gray studio background. Preserve face, hair, all clothing details.", Image.open(io.BytesIO(current))],
        generation_config=genai.types.GenerationConfig(temperature=0.25, top_p=0.6, top_k=15)
    )
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open('new_outfit_complete.png', 'wb') as f:
                            f.write(part.inline_data.data)
                        print("✅ Complete!")
    
    print("\n" + "=" * 70)
    print("✅ DONE: new_outfit_complete.png")
    print("💰 Cost: 5 steps × $0.10 = $0.50")
    print("=" * 70)


asyncio.run(main())
