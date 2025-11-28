"""
VTO System - Final Working Version
"""
import os
import base64
from PIL import Image
import io
from typing import List
import google.generativeai as genai
from image_cleaner import smart_garment_crop


class VTOGenerator:
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    async def generate_base_model(self, user_image_bytes: bytes) -> str:
        """Generate base model - preserve clothing, change background/pose"""
        
        prompt = """Transform this photo into a professional fashion model shot. 

CRITICAL - PRESERVE EXACTLY:
- The person's face, hair, and identity
- The EXACT clothing they are wearing (keep all colors, patterns, styles)
- Their body type

ONLY CHANGE:
- Background: Replace with clean light gray studio backdrop (#f0f0f0)
- Pose: Adjust to standing straight, arms relaxed at sides
- Expression: Neutral, professional model expression
- Lighting: Soft, even studio lighting

This is for an e-commerce fashion photo. The person should look like a professional model, but their face and clothing must stay identical to the original photo.

Return ONLY the final image."""
        
        img = Image.open(io.BytesIO(user_image_bytes))
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
        
        response = self.model.generate_content(
            [prompt, img],
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
    
    async def apply_garment_to_model(self, model_data_url: str, garment_bytes: bytes) -> str:
        """Apply single garment"""
        
        if ',' in model_data_url:
            model_b64 = model_data_url.split(',')[1]
        else:
            model_b64 = model_data_url
        
        model_bytes = base64.b64decode(model_b64)
        model_img = Image.open(io.BytesIO(model_bytes))
        garment_img = Image.open(io.BytesIO(garment_bytes))
        
        prompt = """You are an expert virtual try-on AI. You will be given a 'model image' and a 'garment image'. Your task is to create a new photorealistic image where the person from the 'model image' is wearing the clothing from the 'garment image'.

**Crucial Rules:**
1. **Complete Garment Replacement:** You MUST completely REMOVE and REPLACE the clothing item worn by the person in the 'model image' with the new garment. No part of the original clothing (e.g., collars, sleeves, patterns) should be visible in the final image.
2. **Preserve the Model:** The person's face, hair, body shape, and pose from the 'model image' MUST remain unchanged.
3. **Preserve the Background:** The entire background from the 'model image' MUST be preserved perfectly.
4. **Apply the Garment:** Realistically fit the new garment onto the person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the original scene.
5. **Output:** Return ONLY the final, edited image. Do not include any text."""
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
        
        response = self.model.generate_content(
            [prompt, model_img, garment_img],
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
    
    async def apply_complete_outfit(self, model_data_url: str, garment_images: list) -> str:
        """Apply ALL garments in single step - BETTER QUALITY"""
        
        if ',' in model_data_url:
            model_b64 = model_data_url.split(',')[1]
        else:
            model_b64 = model_data_url
        
        model_bytes = base64.b64decode(model_b64)
        model_img = Image.open(io.BytesIO(model_bytes))
        
        garment_imgs = []
        for garment_bytes in garment_images:
            # Clean image - remove UI elements
            cleaned = smart_garment_crop(garment_bytes)
            garment_imgs.append(Image.open(io.BytesIO(cleaned)))
        
        prompt = f"""Apply COMPLETE OUTFIT to this model.

You receive:
- 1 model image (person in gray clothes)
- {len(garment_imgs)} garment images (shirt, shorts, boots)

Create ONE image showing person wearing ALL garments as complete outfit.

CRITICAL RULES:
1. Preserve EXACTLY: Face, hair, body, pose, background
2. Replace completely: Remove ALL gray clothing
3. Apply ALL garments: Show shirt + shorts + boots together
4. Realistic fit: Natural folds, shadows, lighting

Return ONLY final image."""
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
        
        content = [prompt, model_img] + garment_imgs
        
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


class VTOService:
    """VTO Service"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.generator = VTOGenerator()
    
    async def setup_user_model(self, user_id: int, photo_bytes: bytes):
        base_model = await self.generator.generate_base_model(photo_bytes)
        return {'success': True, 'base_model_image': base_model}
    
    async def generate_outfit_tryon(self, user_id: int, base_model_data_url: str, garment_images: List[bytes]):
        current = base_model_data_url
        for garment in garment_images:
            current = await self.generator.apply_garment_to_model(current, garment)
        return {'success': True, 'vto_image': current, 'cost': 0.05 * len(garment_images)}


POSE_OPTIONS = ["Slightly turned, 3/4 view", "Side profile view"]
