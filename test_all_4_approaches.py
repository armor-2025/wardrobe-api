"""
Test 4 Different Single-Call Approaches
"""
import os
import asyncio
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def test_approach(approach_num, prompt, person, garments):
    """Test a single approach"""
    print(f"\n{'='*70}")
    print(f"🧪 APPROACH {approach_num}")
    print('='*70)
    print(f"Prompt strategy: {prompt[:100]}...")
    print("\n🎨 Generating...")
    
    try:
        response = model.generate_content(
            [prompt, person] + garments,
            generation_config=genai.types.GenerationConfig(
                temperature=0.01,
                top_p=0.3,
                top_k=5,
            )
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            filename = f'approach_{approach_num}.png'
                            with open(filename, 'wb') as f:
                                f.write(part.inline_data.data)
                            print(f"✅ Saved: {filename}")
                            return True
        
        print(f"❌ No image generated")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    print("=" * 70)
    print("🔬 Testing 4 Single-Call Approaches")
    print("=" * 70)
    
    base_path = '/Users/gavinwalker/Downloads/files (4)/'
    
    # Load images
    print("\n📂 Loading images...")
    with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
        person = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'IMG_5747.jpg', 'rb') as f:
        jumper = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'white jeans.png', 'rb') as f:
        jeans = Image.open(io.BytesIO(f.read()))
    with open(base_path + 'IMG_5938.PNG', 'rb') as f:
        boots = Image.open(io.BytesIO(f.read()))
    
    garments = [jumper, jeans, boots]
    print("✅ All images loaded")
    
    # ==========================================
    # APPROACH 1: Two-Step Instructions
    # ==========================================
    prompt1 = """TWO-STEP TASK:

STEP 1 - ANALYZE AND LOCK THE PERSON:
This image shows a SPECIFIC INDIVIDUAL with unique features.
Memorize and lock these attributes:
- Exact face (every feature)
- Exact hair (curly brown, medium length)
- Exact body proportions
- Exact skin tone
These are FIXED and cannot be modified.

STEP 2 - CLOTHING REPLACEMENT ONLY:
Now replace ONLY their current clothes with these 3 new garments:
- Black Adidas jumper
- White jeans
- Tan cowboy boots

CRITICAL: This is a clothing swap on an existing person.
DO NOT regenerate the person.
DO NOT create a new person.
EDIT the existing person's clothing regions only.

Think: Photoshop's clothing replacement tool, not photo generation.

Output: Same person from input image, wearing new clothes, studio background."""

    await test_approach(1, prompt1, person, garments)
    
    # ==========================================
    # APPROACH 2: Reference + Target Format
    # ==========================================
    prompt2 = """REFERENCE-TARGET TASK:

REFERENCE IMAGE (Image 1): This person's identity - DO NOT MODIFY
- Face: REFERENCE ONLY - keep identical
- Hair: REFERENCE ONLY - keep identical  
- Body: REFERENCE ONLY - keep proportions

TARGET GARMENTS (Images 2, 3, 4): Clothes to apply
- Image 2: Jumper to wear
- Image 3: Jeans to wear
- Image 4: Boots to wear

TASK EXECUTION:
Take the person from REFERENCE IMAGE (keep them 100% identical).
Dress them in the TARGET GARMENTS.
Place in studio background.

The person's appearance is locked to the reference.
Only clothing changes.

Output: Reference person wearing target garments."""

    await test_approach(2, prompt2, person, garments)
    
    # ==========================================
    # APPROACH 3: Protected vs Editable Regions
    # ==========================================
    prompt3 = """REGION-BASED EDITING:

IMAGE ANALYSIS:
This image contains two types of regions:

PROTECTED REGIONS (DO NOT TOUCH):
- Face area: All facial features
- Hair area: Complete hair region
- Exposed skin: Arms, neck, legs
- These regions are LOCKED and uneditable

EDITABLE REGIONS (MODIFY THESE):
- Clothing areas only
- Current clothes will be replaced

EDITING TASK:
Replace content in EDITABLE REGIONS with these new garments:
- Garment 1: Black Adidas jumper
- Garment 2: White jeans
- Garment 3: Tan cowboy boots

PROTECTED REGIONS must remain pixel-identical.
Only EDITABLE REGIONS change.
Add clean studio background.

Output: Same protected regions, new editable regions."""

    await test_approach(3, prompt3, person, garments)
    
    # ==========================================
    # APPROACH 4: Copy-Paste Workflow
    # ==========================================
    prompt4 = """PHOTOSHOP COMPOSITE WORKFLOW:

STEP 1 - EXTRACT:
Extract and save the person's head region from input image:
- Face (exact copy)
- Hair (exact copy)
- Upper shoulders
Store this as LAYER_HEAD (to be reused)

STEP 2 - GENERATE:
Generate a body wearing these garments:
- Black Adidas jumper
- White jeans  
- Tan cowboy boots
Clean studio background
Store this as LAYER_BODY

STEP 3 - COMPOSITE:
Place LAYER_HEAD (from Step 1) onto LAYER_BODY (from Step 2)
Blend the neck/shoulder junction smoothly
The head must be the ORIGINAL from input - not generated

STEP 4 - OUTPUT:
Final composite image with:
- Original person's head (from input image)
- Generated body with new clothes
- Seamless blend

Think: You're compositing two layers, not generating from scratch."""

    await test_approach(4, prompt4, person, garments)
    
    # ==========================================
    # RESULTS SUMMARY
    # ==========================================
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    print("\nGenerated files:")
    print("  1. approach_1.png - Two-step instructions")
    print("  2. approach_2.png - Reference + target format")
    print("  3. approach_3.png - Protected regions")
    print("  4. approach_4.png - Copy-paste workflow")
    print("\nCompare with:")
    print("  - bottomup_final.png (sequential, $0.40)")
    print("\n💡 Check which approach preserves face best!")
    print("   If any work, we save 75% on costs ($0.10 vs $0.40)")
    print("=" * 70)


asyncio.run(main())
