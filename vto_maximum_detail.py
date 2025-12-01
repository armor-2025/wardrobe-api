"""
Optimized Sequential VTO with Maximum Detail Preservation
Focus on keeping garment textures sharp through all steps
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_garment_max_detail(current_img, garment_img, garment_name, garment_description):
    """Apply garment with maximum detail preservation"""
    
    prompt = f"""Precision inpainting: Replace ONLY the {garment_name} with exact detail preservation.

SOURCE GARMENT DETAILS:
{garment_description}

CRITICAL REQUIREMENTS:
1. IDENTITY LOCK:
   - Face: Keep every facial feature pixel-perfect
   - Hair: Preserve exact texture, color, curl pattern
   - Body: Maintain exact proportions and pose
   - Background: Keep completely unchanged

2. GARMENT APPLICATION:
   - Capture EVERY texture detail from source garment
   - Preserve all patterns, prints, textures at maximum resolution
   - Maintain fabric properties (lace, leather texture, etc.)
   - Keep all wrinkles, folds, and material characteristics
   - High-fidelity rendering - no simplification

3. TECHNICAL:
   - Maximum detail output
   - Sharp edges and clear textures
   - No blurring or smoothing
   - Preserve micro-details

Replace {garment_name} region only. Everything else untouched."""

    response = model.generate_content(
        [prompt, current_img, garment_img],
        generation_config=genai.types.GenerationConfig(
            temperature=0.03,  # Even lower for precision
            top_p=0.4,
            top_k=8,
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
    print("🎨 MAXIMUM DETAIL Sequential VTO")
    print("=" * 70)
    
    # Load original
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        current_photo = f.read()
    
    # Step 1: Polka dot shirt with lace detail
    print("\n👕 Step 1: Applying polka dot lace shirt...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    
    current_img = Image.open(io.BytesIO(current_photo))
    shirt_img = Image.open(io.BytesIO(shirt))
    
    result1 = await apply_garment_max_detail(
        current_img, 
        shirt_img, 
        "shirt",
        "White sheer lace shirt with brown polka dot pattern, decorative eyelet lace details, white collar, 3/4 sleeves with cuffs"
    )
    
    if result1:
        with open('detail_step1_shirt.png', 'wb') as f:
            f.write(result1)
        print("✅ Step 1 complete: detail_step1_shirt.png")
        
        # Step 2: Leather shorts
        print("\n👖 Step 2: Applying leather shorts...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        
        current_img = Image.open(io.BytesIO(result1))
        shorts_img = Image.open(io.BytesIO(shorts))
        
        result2 = await apply_garment_max_detail(
            current_img,
            shorts_img,
            "shorts",
            "Black leather shorts with snake/crocodile embossed texture, wide leg cut, above-knee length, matte finish with visible scale pattern"
        )
        
        if result2:
            with open('detail_step2_shorts.png', 'wb') as f:
                f.write(result2)
            print("✅ Step 2 complete: detail_step2_shorts.png")
            
            # Step 3: Cowboy boots
            print("\n👢 Step 3: Applying cowboy boots...")
            with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
                boots = f.read()
            
            current_img = Image.open(io.BytesIO(result2))
            boots_img = Image.open(io.BytesIO(boots))
            
            result3 = await apply_garment_max_detail(
                current_img,
                boots_img,
                "boots",
                "Tan/brown leather cowboy boots with decorative stitching patterns, pointed toe, stacked heel, knee-high length"
            )
            
            if result3:
                with open('detail_step3_boots.png', 'wb') as f:
                    f.write(result3)
                print("✅ Step 3 complete: detail_step3_boots.png")
                
                # Step 4: Studio background with detail preservation
                print("\n🎨 Step 4: Professional studio setting...")
                
                current_img = Image.open(io.BytesIO(result3))
                
                studio_prompt = """Professional fashion photography post-production:

PRESERVE COMPLETELY:
- Person's face and hair (exact match)
- ALL garment details and textures:
  * Lace patterns and eyelet details on shirt
  * Snake/croc texture on leather shorts
  * Stitching patterns on cowboy boots
- Body proportions and pose
- Sharpness and detail quality

APPLY:
- Clean light gray studio background (#E5E5E5)
- Professional studio lighting setup
- Soft shadows beneath for depth
- High-end fashion photography quality

DO NOT:
- Blur or smooth any textures
- Simplify patterns or details
- Change garment colors or materials

Output: Professional studio portrait with maximum detail preservation."""

                response = model.generate_content(
                    [studio_prompt, current_img],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.25,
                        top_p=0.6,
                        top_k=15,
                    )
                )
                
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    with open('vto_maximum_detail_final.png', 'wb') as f:
                                        f.write(part.inline_data.data)
                                    print("✅ Step 4 complete: vto_maximum_detail_final.png")
                
                print("\n" + "="*70)
                print("✅ MAXIMUM DETAIL VTO COMPLETE!")
                print("="*70)
                print("\n📊 Check progression:")
                print("   1. detail_step1_shirt.png")
                print("   2. detail_step2_shorts.png")
                print("   3. detail_step3_boots.png")
                print("   4. vto_maximum_detail_final.png")
                print("\n💡 Each step optimized for detail preservation!")
                print("="*70)


import asyncio
asyncio.run(main())
