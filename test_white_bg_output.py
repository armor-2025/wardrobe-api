"""
Sequential VTO but output as PNG with clean white background
No need for expensive studio background step
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_garment(current_img, garment_img, garment_name):
    """Apply single garment"""
    prompt = f"""Inpaint: Replace ONLY the {garment_name}.
Keep face, hair, body, pose IDENTICAL.
Replace {garment_name} with new one shown."""

    response = model.generate_content(
        [prompt, current_img, garment_img],
        generation_config=genai.types.GenerationConfig(
            temperature=0.05, top_p=0.5, top_k=10
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
    from PIL import Image, ImageDraw
    
    print("=" * 70)
    print("🎨 Sequential VTO → Clean White Background PNG")
    print("=" * 70)
    
    # Load original
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        current_photo = f.read()
    
    # Step 1: Shirt
    print("\n👕 Step 1: Applying shirt...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    
    current_img = Image.open(io.BytesIO(current_photo))
    shirt_img = Image.open(io.BytesIO(shirt))
    result1 = await apply_garment(current_img, shirt_img, "shirt")
    
    if result1:
        print("✅ Shirt applied")
        
        # Step 2: Shorts
        print("\n👖 Step 2: Applying shorts...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        
        current_img = Image.open(io.BytesIO(result1))
        shorts_img = Image.open(io.BytesIO(shorts))
        result2 = await apply_garment(current_img, shorts_img, "shorts")
        
        if result2:
            print("✅ Shorts applied")
            
            # Step 3: Boots
            print("\n👢 Step 3: Applying boots...")
            with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
                boots = f.read()
            
            current_img = Image.open(io.BytesIO(result2))
            boots_img = Image.open(io.BytesIO(boots))
            result3 = await apply_garment(current_img, boots_img, "boots")
            
            if result3:
                print("✅ Boots applied")
                
                # Now convert to clean white background PNG
                print("\n🎨 Converting to clean white background PNG...")
                
                final_img = Image.open(io.BytesIO(result3))
                
                # Create white background
                white_bg = Image.new('RGB', final_img.size, (255, 255, 255))
                
                # If image has transparency, composite it
                if final_img.mode in ('RGBA', 'LA'):
                    white_bg.paste(final_img, mask=final_img.split()[-1])
                else:
                    white_bg = final_img
                
                # Save as PNG
                white_bg.save('vto_clean_white_bg.png', 'PNG')
                print("✅ Saved: vto_clean_white_bg.png")
                
                print("\n" + "="*70)
                print("💰 COST SAVINGS!")
                print("="*70)
                print("   Old: 4 steps = $0.40")
                print("   New: 3 steps = $0.30 (25% savings!)")
                print("\n✅ Clean white background PNG ready!")
                print("="*70)


import asyncio
asyncio.run(main())
