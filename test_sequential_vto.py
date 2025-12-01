"""
Sequential VTO: Apply one garment at a time
This should preserve identity much better!
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 Sequential VTO: One Garment at a Time")
print("=" * 70)


async def apply_single_garment(person_img, garment_img, garment_name):
    """Apply ONE garment while preserving identity"""
    
    prompt = f"""Inpaint task: Replace ONLY the {garment_name} in this photo.

CRITICAL RULES:
- Keep face IDENTICAL
- Keep hair IDENTICAL  
- Keep body IDENTICAL
- Keep background IDENTICAL
- Keep pose IDENTICAL
- ONLY change the {garment_name} region

Replace the current {garment_name} with the new one shown.
Everything else must remain pixel-perfect identical.

This is precision inpainting - not generation."""

    response = model.generate_content(
        [prompt, person_img, garment_img],
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
    
    # Start with original photo
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        current_photo = f.read()
    
    print("\n📸 Starting with original photo...")
    
    # Step 1: Apply shirt
    print("\n🎨 Step 1: Applying shirt only...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    
    current_img = Image.open(io.BytesIO(current_photo))
    shirt_img = Image.open(io.BytesIO(shirt))
    
    result1 = await apply_single_garment(current_img, shirt_img, "shirt")
    
    if result1:
        with open('sequential_step1_shirt.png', 'wb') as f:
            f.write(result1)
        print("✅ Step 1 complete: sequential_step1_shirt.png")
        
        # Step 2: Apply shorts to the result from step 1
        print("\n👖 Step 2: Applying shorts to shirt result...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        
        current_img = Image.open(io.BytesIO(result1))
        shorts_img = Image.open(io.BytesIO(shorts))
        
        result2 = await apply_single_garment(current_img, shorts_img, "shorts")
        
        if result2:
            with open('sequential_step2_shorts.png', 'wb') as f:
                f.write(result2)
            print("✅ Step 2 complete: sequential_step2_shorts.png")
            
            # Step 3: Apply boots to the result from step 2
            print("\n👢 Step 3: Applying boots to shorts result...")
            with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
                boots = f.read()
            
            current_img = Image.open(io.BytesIO(result2))
            boots_img = Image.open(io.BytesIO(boots))
            
            result3 = await apply_single_garment(current_img, boots_img, "boots")
            
            if result3:
                with open('sequential_final.png', 'wb') as f:
                    f.write(result3)
                print("✅ Step 3 complete: sequential_final.png")
                
                print("\n" + "="*70)
                print("✅ SEQUENTIAL VTO COMPLETE!")
                print("="*70)
                print("\nCheck these files to see identity preservation:")
                print("1. sequential_step1_shirt.png - Should have good face preservation")
                print("2. sequential_step2_shorts.png - Face should still be good")
                print("3. sequential_final.png - Final with all items")
                print("\n💡 This approach should preserve identity MUCH better!")


import asyncio
asyncio.run(main())
