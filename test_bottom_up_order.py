"""
Test BOTTOM-UP approach: Boots → Jeans → Jumper
Theory: Start with simple items, end with detailed ones
"""
import os
import asyncio
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def apply_item(current_img, item_img, item_name, item_desc):
    """Apply single item with max detail"""
    
    prompt = f"""Precision inpainting: Replace ONLY the {item_name}.

CRITICAL:
- Face: Keep pixel-perfect identical
- Hair: Preserve exact texture/color/curl
- Body: Same proportions
- Background: Unchanged

Apply new {item_name}: {item_desc}
High detail rendering."""

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
    print("=" * 70)
    print("🔄 Testing BOTTOM-UP Order")
    print("=" * 70)
    print("\nTheory: Start simple (boots), end complex (jumper)")
    print("This might preserve identity better!\n")
    
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    
    # Load original
    with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
        current = f.read()
    
    # Step 1: BOOTS FIRST (simple - leather texture)
    print("👢 Step 1: Applying boots FIRST...")
    with open(base_path + 'IMG_5938.PNG', 'rb') as f:
        boots = f.read()
    
    current = await apply_item(
        Image.open(io.BytesIO(current)),
        Image.open(io.BytesIO(boots)),
        "boots/shoes",
        "Tan cowboy boots"
    )
    
    if current:
        with open('bottomup_step1_boots.png', 'wb') as f:
            f.write(current)
        print("✅ Boots applied")
        
        # Step 2: JEANS (medium complexity)
        print("\n👖 Step 2: Applying jeans...")
        with open(base_path + 'white jeans.png', 'rb') as f:
            jeans = f.read()
        
        current = await apply_item(
            Image.open(io.BytesIO(current)),
            Image.open(io.BytesIO(jeans)),
            "pants/jeans",
            "White jeans"
        )
        
        if current:
            with open('bottomup_step2_jeans.png', 'wb') as f:
                f.write(current)
            print("✅ Jeans applied")
            
            # Step 3: JUMPER LAST (most complex - Adidas logo/stripes)
            print("\n👕 Step 3: Applying jumper LAST...")
            with open(base_path + 'IMG_5747.jpg', 'rb') as f:
                jumper = f.read()
            
            current = await apply_item(
                Image.open(io.BytesIO(current)),
                Image.open(io.BytesIO(jumper)),
                "top/jumper",
                "Black Adidas jumper with logo and stripes"
            )
            
            if current:
                with open('bottomup_step3_jumper.png', 'wb') as f:
                    f.write(current)
                print("✅ Jumper applied")
                
                # Step 4: Studio background
                print("\n🎨 Step 4: Studio background...")
                
                response = model.generate_content(
                    ["Professional studio: gray background, preserve all details", Image.open(io.BytesIO(current))],
                    generation_config=genai.types.GenerationConfig(temperature=0.25)
                )
                
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    with open('bottomup_final.png', 'wb') as f:
                                        f.write(part.inline_data.data)
                                    print("✅ Complete!")
                
                print("\n" + "=" * 70)
                print("📊 COMPARISON:")
                print("=" * 70)
                print("\nTop-down (shirt→pants→boots): 3 steps")
                print("Bottom-up (boots→pants→shirt): 3 steps")
                print("\n💡 Check if bottom-up preserves:")
                print("   - Better face preservation?")
                print("   - Better detail on complex jumper?")
                print("\nFiles to compare:")
                print("   - bottomup_final.png (NEW)")
                print("   - vto_maximum_detail_final.png (OLD top-down)")
                print("=" * 70)


asyncio.run(main())
