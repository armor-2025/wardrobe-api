"""
Test Multiple Prompt Strategies
Try to match ALTA's quality
"""
import os
import asyncio
from PIL import Image
import io
import base64
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')


async def test_strategy(name, prompt, user_img, garment_img, temp=0.4):
    """Test a specific prompt strategy"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print('='*70)
    
    try:
        response = model.generate_content(
            [prompt, user_img, garment_img],
            generation_config=genai.types.GenerationConfig(
                temperature=temp,
                top_p=0.8,
                top_k=40,
            )
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            result = part.inline_data.data
                            filename = f"test_{name.replace(' ', '_').lower()}.png"
                            with open(filename, 'wb') as f:
                                f.write(result)
                            print(f"✅ Saved: {filename}")
                            return
    except Exception as e:
        print(f"❌ Failed: {e}")


async def main():
    print("=" * 70)
    print("🧪 Testing Different Prompt Strategies")
    print("=" * 70)
    
    # Load images
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        user_img = Image.open(io.BytesIO(f.read()))
    
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        garment_img = Image.open(io.BytesIO(f.read()))
    
    # Strategy 1: Inpainting Language
    await test_strategy(
        "Inpainting",
        """Inpaint this image: replace ONLY the shirt region with the new garment.

Rules:
- Keep face, hair, body, pose, background identical
- Only modify the shirt area
- Seamless blending at edges
- Match lighting and perspective

This is precise inpainting, not generation.""",
        user_img, garment_img, temp=0.1
    )
    
    # Strategy 2: Identity Lock
    await test_strategy(
        "Identity_Lock",
        """CRITICAL: This person's identity is LOCKED and cannot be modified.

Face hash: [PRESERVE]
Hair signature: [PRESERVE]
Body fingerprint: [PRESERVE]

Task: Replace shirt only while keeping identity markers intact.
Think: You're a forensic photo editor maintaining identity evidence.""",
        user_img, garment_img, temp=0.05
    )
    
    # Strategy 3: Reference-Based
    await test_strategy(
        "Reference_Based",
        """You have a REFERENCE photo (image 1) showing a person.
You have a GARMENT photo (image 2) showing a shirt.

Create image 3 where:
- The person from image 1 is EXACTLY preserved (face, hair, everything)
- They are now wearing the garment from image 2
- Use image 1 as your reference for the person's appearance
- Do not deviate from the reference""",
        user_img, garment_img, temp=0.2
    )
    
    # Strategy 4: Negative Instructions
    await test_strategy(
        "Negative_Instructions",
        """Show this person wearing the new shirt.

DO NOT:
- Change face
- Change hair color or style
- Change skin tone
- Change body type
- Change background
- Generate a new person

DO:
- Replace shirt only
- Keep everything else identical""",
        user_img, garment_img, temp=0.3
    )
    
    # Strategy 5: Copy-Paste Language
    await test_strategy(
        "Copy_Paste",
        """Photoshop task:
1. Select shirt region in image 1
2. Delete it
3. Copy garment from image 2
4. Paste and transform to fit
5. Blend edges
6. Do NOT touch anything outside shirt region

Final check: Is the face identical? Yes/No - must be Yes.""",
        user_img, garment_img, temp=0.1
    )
    
    # Strategy 6: Minimal Words
    await test_strategy(
        "Minimal",
        """Person: [preserve exactly]
Shirt: [replace with new]
Everything else: [untouched]""",
        user_img, garment_img, temp=0.05
    )
    
    # Strategy 7: JSON-Style
    await test_strategy(
        "JSON_Style",
        """{
  "task": "garment_replacement",
  "preserve": ["face", "hair", "body", "background", "pose"],
  "modify": ["shirt"],
  "method": "precise_inpainting",
  "identity_preservation": "REQUIRED"
}""",
        user_img, garment_img, temp=0.1
    )
    
    print("\n" + "="*70)
    print("✅ All tests complete!")
    print("="*70)
    print("\nGenerated files:")
    print("- test_inpainting.png")
    print("- test_identity_lock.png")
    print("- test_reference_based.png")
    print("- test_negative_instructions.png")
    print("- test_copy_paste.png")
    print("- test_minimal.png")
    print("- test_json_style.png")
    print("\n💡 Compare all of them and see which preserves identity best!")

asyncio.run(main())
