"""
Test with polka dot shirt + preserve more detail
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_garment_detailed(current_img, garment_img, garment_name):
    """Apply garment with emphasis on preserving texture detail"""
    
    prompt = f"""Inpaint: Replace ONLY the {garment_name}.

CRITICAL:
- Keep face IDENTICAL
- Keep hair IDENTICAL
- Keep pose/body IDENTICAL
- Preserve ALL texture details from the new {garment_name}
- High detail rendering - capture every pattern, texture, wrinkle
- Match fabric texture precisely

Replace current {garment_name} with new one at FULL detail."""

    response = model.generate_content(
        [prompt, current_img, garment_img],
        generation_config=genai.types.GenerationConfig(
            temperature=0.05,
            top_p=0.5,
            top_k=10,
        )
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return part.inline_data.data
    return None


async def main():
    import asyncio
    
    print("=" * 70)
    print("🎨 Polka Dot Shirt VTO with Enhanced Detail")
    print("=" * 70)
    
    # Start with original
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        current_photo = f.read()
    
    # Step 1: Polka dot shirt
    print("\n👕 Step 1: Applying polka dot shirt...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    
    current_img = Image.open(io.BytesIO(current_photo))
    shirt_img = Image.open(io.BytesIO(shirt))
    
    result1 = await apply_garment_detailed(current_img, shirt_img, "shirt")
    
    if result1:
        with open('polkadot_step1_shirt.png', 'wb') as f:
            f.write(result1)
        print("✅ Saved: polkadot_step1_shirt.png")
        
        # Step 2: Shorts
        print("\n👖 Step 2: Applying leather shorts...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        
        current_img = Image.open(io.BytesIO(result1))
        shorts_img = Image.open(io.BytesIO(shorts))
        
        result2 = await apply_garment_detailed(current_img, shorts_img, "shorts")
        
        if result2:
            with open('polkadot_step2_shorts.png', 'wb') as f:
                f.write(result2)
            print("✅ Saved: polkadot_step2_shorts.png")
            
            # Step 3: Boots
            print("\n👢 Step 3: Applying boots...")
            with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
                boots = f.read()
            
            current_img = Image.open(io.BytesIO(result2))
            boots_img = Image.open(io.BytesIO(boots))
            
            result3 = await apply_garment_detailed(current_img, boots_img, "boots")
            
            if result3:
                with open('polkadot_step3_complete.png', 'wb') as f:
                    f.write(result3)
                print("✅ Saved: polkadot_step3_complete.png")
                
                # Step 4: Studio background
                print("\n🎨 Step 4: Adding studio background...")
                
                studio_img = Image.open(io.BytesIO(result3))
                
                studio_prompt = """Professional photo editing: Place this person in a clean photo studio.

PRESERVE:
- Person exactly as-is
- All clothing texture and detail
- Face and hair

ADD:
- Clean light gray studio background
- Soft professional lighting
- Natural shadows

High detail output - preserve all fabric textures."""

                response = model.generate_content(
                    [studio_prompt, studio_img],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        top_p=0.7,
                        top_k=20,
                    )
                )
                
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    with open('polkadot_final_studio.png', 'wb') as f:
                                        f.write(part.inline_data.data)
                                    print("✅ Saved: polkadot_final_studio.png")
                
                print("\n" + "="*70)
                print("✅ Complete! Check polkadot_final_studio.png")
                print("="*70)


import asyncio
asyncio.run(main())
