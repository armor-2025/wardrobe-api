"""
Test: Jumper + White Jeans + Cowboy Boots + Cap + Bag
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_item_max_detail(current_img, item_img, item_name, item_description):
    """Apply item with maximum detail preservation"""
    
    prompt = f"""Precision inpainting: Replace ONLY the {item_name} with exact detail preservation.

SOURCE ITEM DETAILS:
{item_description}

CRITICAL REQUIREMENTS:
1. IDENTITY LOCK:
   - Face: Keep every facial feature pixel-perfect
   - Hair: Preserve exact texture, color, curl pattern
   - Body: Maintain exact proportions and pose
   - Background: Keep completely unchanged

2. ITEM APPLICATION:
   - Capture EVERY texture detail from source item
   - Preserve all patterns, prints, textures at maximum resolution
   - High-fidelity rendering - no simplification

Replace {item_name} region only. Everything else untouched."""

    response = model.generate_content(
        [prompt, current_img, item_img],
        generation_config=genai.types.GenerationConfig(
            temperature=0.03,
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
    print("🎨 Testing: Jumper + Jeans + Boots + Cap + Bag")
    print("=" * 70)
    
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    
    # Start from step 1 result
    with open('new_outfit_step1_jumper.png', 'rb') as f:
        result1 = f.read()
    
    # Step 2: White jeans
    print("\n👖 Step 2: Applying white jeans...")
    with open(base_path + 'white jeans.png', 'rb') as f:
        jeans = f.read()
    
    current_img = Image.open(io.BytesIO(result1))
    jeans_img = Image.open(io.BytesIO(jeans))
    
    result2 = await apply_item_max_detail(
        current_img,
        jeans_img,
        "pants/jeans",
        "White denim jeans"
    )
    
    if result2:
        with open('new_outfit_step2_jeans.png', 'wb') as f:
            f.write(result2)
        print("✅ White jeans applied")
        
        # Step 3: Cowboy boots
        print("\n👢 Step 3: Applying cowboy boots...")
        with open(base_path + 'IMG_5938.PNG', 'rb') as f:
            boots = f.read()
        
        current_img = Image.open(io.BytesIO(result2))
        boots_img = Image.open(io.BytesIO(boots))
        
        result3 = await apply_item_max_detail(
            current_img,
            boots_img,
            "boots/shoes",
            "Tan/brown leather cowboy boots with decorative stitching"
        )
        
        if result3:
            with open('new_outfit_step3_boots.png', 'wb') as f:
                f.write(result3)
            print("✅ Boots applied")
            
            # Step 4: Cap
            print("\n🧢 Step 4: Adding cap...")
            with open(base_path + 'IMG_5940.PNG', 'rb') as f:
                cap = f.read()
            
            current_img = Image.open(io.BytesIO(result3))
            cap_img = Image.open(io.BytesIO(cap))
            
            result4 = await apply_item_max_detail(
                current_img,
                cap_img,
                "cap/hat",
                "Baseball cap - worn on head"
            )
            
            if result4:
                with open('new_outfit_step4_cap.png', 'wb') as f:
                    f.write(result4)
                print("✅ Cap applied")
                
                # Step 5: Bag
                print("\n👜 Step 5: Adding bag...")
                with open(base_path + 'Screenshot 2025-10-14 at 13.13.00.png', 'rb') as f:
                    bag = f.read()
                
                current_img = Image.open(io.BytesIO(result4))
                bag_img = Image.open(io.BytesIO(bag))
                
                result5 = await apply_item_max_detail(
                    current_img,
                    bag_img,
                    "bag/accessory",
                    "Bag - carried in hand or over shoulder"
                )
                
                if result5:
                    with open('new_outfit_step5_bag.png', 'wb') as f:
                        f.write(result5)
                    print("✅ Bag applied")
                    
                    # Step 6: Studio background
                    print("\n🎨 Step 6: Adding studio background...")
                    
                    current_img = Image.open(io.BytesIO(result5))
                    
                    studio_prompt = """Professional fashion photography post-production:

PRESERVE COMPLETELY:
- Person's face and hair (exact match)
- ALL garment and accessory details
- Body proportions and pose

APPLY:
- Clean light gray studio background
- Professional studio lighting
- Soft shadows for depth

Output: Professional studio portrait with maximum detail."""

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
                                        with open('new_outfit_final.png', 'wb') as f:
                                            f.write(part.inline_data.data)
                                        print("✅ Final result: new_outfit_final.png")
                    
                    print("\n" + "="*70)
                    print("✅ COMPLETE!")
                    print("="*70)
                    print("\n💰 Cost: 6 steps × $0.10 = $0.60")
                    print("="*70)


import asyncio
asyncio.run(main())
