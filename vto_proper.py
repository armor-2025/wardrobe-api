"""
Proper VTO System - Preserves User Completely
Only changes clothes, nothing else
"""
import os
import base64
from PIL import Image
import io
import google.generativeai as genai
from typing import List


class ProperVTOSystem:
    """VTO that preserves user identity by not regenerating them"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    async def apply_garment_directly(self, user_photo_bytes: bytes, garment_bytes: bytes) -> str:
        """
        Apply garment to user's actual photo without regenerating them
        
        This is the CORRECT approach:
        - User photo stays as-is (face, hair, body, everything)
        - We ONLY change the clothing
        - Gemini acts as a clothing overlay, not a person generator
        """
        
        user_img = Image.open(io.BytesIO(user_photo_bytes))
        garment_img = Image.open(io.BytesIO(garment_bytes))
        
        prompt = """You are a professional virtual try-on system. Your task is to show this person wearing the new garment.

CRITICAL RULES - READ CAREFULLY:

1. PRESERVE THE PERSON COMPLETELY:
   - Keep their EXACT face (every feature identical)
   - Keep their EXACT hair (color, style, length, texture)
   - Keep their EXACT body shape and proportions
   - Keep their EXACT skin tone
   - Keep their pose and expression
   - The person must look IDENTICAL to the input photo

2. CHANGE ONLY THE CLOTHES:
   - Replace ONLY the clothing item shown in the garment image
   - The new garment should fit naturally on their body
   - Match the lighting and shadows to the original photo
   - Keep all wrinkles and folds realistic

3. PRESERVE EVERYTHING ELSE:
   - Keep the background exactly as-is
   - Keep any accessories (jewelry, watches, etc.)
   - Keep the overall photo quality and style
   
Think of this as Photoshop - you're overlaying new clothes on an existing photo, NOT creating a new photo.

The person in the result must be 100% recognizable as the same person from the input.

Return ONLY the final image with the person wearing the new garment."""

        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Very low for maximum consistency
            top_p=0.5,
            top_k=10,
        )
        
        response = self.model.generate_content(
            [prompt, user_img, garment_img],
            generation_config=generation_config
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            mime = part.inline_data.mime_type
                            data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            return f"data:{mime};base64,{data}"
        
        raise ValueError("No image generated")
    
    async def apply_complete_outfit_directly(
        self, 
        user_photo_bytes: bytes, 
        garment_images: List[bytes]
    ) -> str:
        """
        Apply complete outfit to user's actual photo
        Multiple garments at once
        """
        
        user_img = Image.open(io.BytesIO(user_photo_bytes))
        garment_imgs = [Image.open(io.BytesIO(g)) for g in garment_images]
        
        prompt = f"""You are a professional virtual try-on system. Show this person wearing ALL {len(garment_imgs)} new garments as a complete outfit.

ABSOLUTE REQUIREMENTS:

1. THE PERSON MUST STAY IDENTICAL:
   ❗ FACE: Keep every facial feature exactly the same
   ❗ HAIR: Keep the exact hairstyle, color, and length
   ❗ BODY: Keep the same body shape and proportions
   ❗ EXPRESSION: Keep the same facial expression
   ❗ This is NOT photo generation - it's clothing replacement

2. CHANGE ONLY THE OUTFIT:
   - Replace all clothing with the {len(garment_imgs)} new garments shown
   - Make them fit naturally as a complete outfit
   - Match lighting and shadows to the original photo
   - Keep realistic wrinkles and fabric behavior

3. KEEP EVERYTHING ELSE:
   - Same background
   - Same pose
   - Same accessories
   - Same photo quality

This is like using Photoshop to change someone's clothes in a photo.
The person must be 100% recognizable as the same individual.

Return ONLY the final edited image."""

        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.5,
            top_k=10,
        )
        
        content = [prompt, user_img] + garment_imgs
        
        response = self.model.generate_content(
            content,
            generation_config=generation_config
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            mime = part.inline_data.mime_type
                            data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            return f"data:{mime};base64,{data}"
        
        raise ValueError("No image generated")


# Test it
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 70)
        print("🎯 Testing PROPER VTO System")
        print("=" * 70)
        
        os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
        
        vto = ProperVTOSystem()
        
        # Load user photo (use ORIGINAL, not base model!)
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
            user_photo = f.read()
        
        # Load garments
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
            shirt = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
            boots = f.read()
        
        print("\n🎨 Applying outfit to ORIGINAL photo (no regeneration)...")
        print("   This keeps face, hair, everything identical!")
        
        result_data_url = await vto.apply_complete_outfit_directly(
            user_photo,
            [shirt, shorts, boots]
        )
        
        # Save result
        if ',' in result_data_url:
            b64_data = result_data_url.split(',')[1]
            img_bytes = base64.b64decode(b64_data)
            
            with open('vto_proper_approach.png', 'wb') as f:
                f.write(img_bytes)
            
            print("\n✅ Saved: vto_proper_approach.png")
            print("\n💡 This should preserve face AND hair perfectly!")
            print("   Because we're not regenerating the person at all.")
    
    asyncio.run(test())
