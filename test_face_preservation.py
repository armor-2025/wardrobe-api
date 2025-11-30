"""
Test different face preservation strategies
"""
import asyncio
from vto_system import VTOGenerator
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

async def test_strategy(strategy_name, prompt_modifier):
    print(f"\n{'='*60}")
    print(f"Testing: {strategy_name}")
    print('='*60)
    
    gen = VTOGenerator()
    
    # Load images
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        photo = f.read()
    
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
        shorts = f.read()
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
        boots = f.read()
    
    # Generate base
    base = await gen.generate_base_model(photo)
    
    # Apply outfit with modified strategy
    from PIL import Image
    import io
    import base64
    from image_cleaner import smart_garment_crop
    
    # Prepare images
    if ',' in base:
        model_b64 = base.split(',')[1]
    else:
        model_b64 = base
    
    model_bytes = base64.b64decode(model_b64)
    model_img = Image.open(io.BytesIO(model_bytes))
    
    garment_imgs = []
    for gb in [shirt, shorts, boots]:
        cleaned = smart_garment_crop(gb)
        garment_imgs.append(Image.open(io.BytesIO(cleaned)))
    
    # Use modified prompt
    prompt = prompt_modifier
    
    config = genai.types.GenerationConfig(temperature=0.3, top_p=0.8, top_k=40)
    content = [prompt, model_img] + garment_imgs
    
    response = gen.model.generate_content(content, generation_config=config)
    
    # Extract result
    result = None
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        mime = part.inline_data.mime_type
                        data = base64.b64encode(part.inline_data.data).decode('utf-8')
                        result = f"data:{mime};base64,{data}"
                        break
    
    if result:
        filename = f'face_test_{strategy_name.replace(" ", "_")}.html'
        with open(filename, 'w') as f:
            f.write(f'<h2>{strategy_name}</h2><img src="{result}" style="max-width:600px">')
        print(f'✅ Saved: {filename}')
    else:
        print('❌ Failed')

async def main():
    # Strategy 1: Ultra-explicit face preservation
    await test_strategy(
        "Ultra_Explicit",
        """CRITICAL INSTRUCTION: The person's FACE must remain COMPLETELY IDENTICAL.

DO NOT CHANGE:
- Face shape, structure, bone structure
- Eye shape, color, position
- Nose shape, size
- Mouth shape, lips
- Eyebrows shape, position
- Skin tone, complexion
- Hair color, texture, style
- Facial hair (beard/mustache)
- Age appearance

ONLY CHANGE: The clothing on the body

Apply these garments: white polka dot shirt, black leather shorts, brown cowboy boots.

Preserve face 100%. Return final image."""
    )
    
    # Strategy 2: Reference-based
    await test_strategy(
        "Reference_Based",
        """You are editing a photo for a virtual try-on system.

The model image shows the EXACT person who must appear in the final result.
Their face is the REFERENCE - it must not change AT ALL.

Task: Replace only the gray clothing with the new garments shown.
Face preservation: CRITICAL - use the model's face exactly as shown.
Garments: Apply shirt, shorts, and boots from the garment images.

Return final image with SAME FACE, new clothes."""
    )
    
    # Strategy 3: Step-by-step instruction
    await test_strategy(
        "Step_By_Step",
        """Follow these steps EXACTLY:

Step 1: Identify the person's face in the model image - memorize every detail
Step 2: Identify the garments in the garment images  
Step 3: Remove ONLY the gray clothing from the model
Step 4: Apply the new garments to the body
Step 5: VERIFY the face is still identical to step 1
Step 6: Return final image

The face in the output MUST match the face in the model image."""
    )
    
    # Strategy 4: Minimal prompt (sometimes less is more)
    await test_strategy(
        "Minimal",
        """Virtual try-on: Keep the person's face and body identical. Only replace their clothing with these garments. Return the final image."""
    )
    
    print("\n" + "="*60)
    print("✅ All tests complete! Compare results:")
    print("  - face_test_Ultra_Explicit.html")
    print("  - face_test_Reference_Based.html")
    print("  - face_test_Step_By_Step.html")
    print("  - face_test_Minimal.html")

asyncio.run(main())
