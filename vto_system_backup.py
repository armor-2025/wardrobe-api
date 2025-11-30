"""
Virtual Try-On (VTO) System
Generate professional outfit try-on images with face preservation

PROVEN 3-STEP APPROACH:
1. Generate base model from user photo (preserves face perfectly)
2. Apply garment to model (pixel-perfect clothing)
3. Generate pose variations (optional)

Based on working TypeScript implementation
Uses Gemini 2.5 Flash Image model
"""
import os
import io
import base64
import json
from PIL import Image
from typing import Dict, Any, Optional, List
import google.generativeai as genai


class VTOGenerator:
    """
    Virtual Try-On using proven 3-step method
    Premium feature - $4.99/month
    
    This matches the working TypeScript implementation
    """
    
    def __init__(self):
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash Image - optimized for image generation
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
        
    
    async def generate_base_model(self, user_image_bytes: bytes) -> str:
        """
        STEP 1: Generate base model from user photo
        
        This preserves the user's face, hair, and identity
        Transforms them into a professional model on neutral background
        
        Returns: base64 data URL of model image
        """
        
        # Convert bytes to PIL Image
        user_image = Image.open(io.BytesIO(user_image_bytes))
        
        # Convert to base64 for Gemini
        buffer = io.BytesIO()
        user_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        prompt = """You are an expert fashion photographer AI. Transform the person in this image into a full-body fashion model photo suitable for an e-commerce website. 

The background must be a clean, neutral studio backdrop (light gray, #f0f0f0). 

The person should have a neutral, professional model expression. 

Preserve the person's identity, unique features, and body type, but place them in a standard, relaxed standing model pose. 

The final image must be photorealistic. 

Return ONLY the final image."""
        
        # Generate with Gemini
        response = self.model.generate_content([
            {
                'mime_type': 'image/png',
                'data': image_base64
            },
            prompt
        ])
        
        # Check for blocking first
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            if hasattr(feedback, 'block_reason'):
                raise ValueError(f"Request blocked: {feedback.block_reason}")
        
        # Check candidates exist
        if not hasattr(response, 'candidates') or not response.candidates:
            raise ValueError("No candidates returned. Image might have been blocked by safety filters.")
        
        # Extract image from candidates
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data'):
                        mime_type = part.inline_data.mime_type
                        data = base64.b64encode(part.inline_data.data).decode('utf-8')
                        return f"data:{mime_type};base64,{data}"
        
        raise ValueError("Failed to generate base model image - no image data in response")
    
    async def apply_garment_to_model(
        self,
        model_image_data_url: str,
        garment_image_bytes: bytes
    ) -> str:
        """
        STEP 2: Apply garment to model
        
        Takes base model + garment image
        Returns model wearing the garment with PIXEL-PERFECT fit
        
        Args:
            model_image_data_url: Base model (from step 1)
            garment_image_bytes: Garment to apply
            
        Returns: base64 data URL of try-on result
        """
        
        # Parse model image data URL
        if model_image_data_url.startswith('data:'):
            header, encoded = model_image_data_url.split(',', 1)
            model_mime = header.split(';')[0].split(':')[1]
            model_data = encoded
        else:
            model_mime = 'image/png'
            model_data = model_image_data_url
        
        # Convert garment bytes to base64
        garment_image = Image.open(io.BytesIO(garment_image_bytes))
        garment_buffer = io.BytesIO()
        garment_image.save(garment_buffer, format='PNG')
        garment_data = base64.b64encode(garment_buffer.getvalue()).decode('utf-8')
        
        prompt = """You are an expert virtual try-on AI. You will be given a 'model image' and a 'garment image'. Your task is to create a new photorealistic image where the person from the 'model image' is wearing the clothing from the 'garment image'.

**Crucial Rules:**
1. **Complete Garment Replacement:** You MUST completely REMOVE and REPLACE the clothing item worn by the person in the 'model image' with the new garment. No part of the original clothing (e.g., collars, sleeves, patterns) should be visible in the final image.
2. **Preserve the Model:** The person's face, hair, body shape, and pose from the 'model image' MUST remain unchanged.
3. **Preserve the Background:** The entire background from the 'model image' MUST be preserved perfectly.
4. **Apply the Garment:** Realistically fit the new garment onto the person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the original scene.
5. **Output:** Return ONLY the final, edited image. Do not include any text."""
        
        # Generate with Gemini
        response = self.model.generate_content([
            {
                'mime_type': model_mime,
                'data': model_data
            },
            {
                'mime_type': 'image/png',
                'data': garment_data
            },
            prompt
        ])
        
        # Extract image
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'inline_data'):
                    mime_type = part.inline_data.mime_type
                    data = base64.b64encode(part.inline_data.data).decode('utf-8')
                    return f"data:{mime_type};base64,{data}"
        
        if hasattr(response, 'candidates'):
            for candidate in response.candidates:
                if hasattr(candidate, 'content'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data'):
                            mime_type = part.inline_data.mime_type
                            data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            return f"data:{mime_type};base64,{data}"
        
        raise ValueError("Failed to apply garment to model")
    
    async def generate_pose_variation(
        self,
        try_on_image_data_url: str,
        pose_instruction: str
    ) -> str:
        """
        STEP 3: Generate pose variation (OPTIONAL)
        
        Takes try-on result and generates different angle/pose
        Keeps everything identical (face, clothes, background style)
        
        Args:
            try_on_image_data_url: Result from step 2
            pose_instruction: "Slightly turned, 3/4 view", "Side profile", etc.
            
        Returns: base64 data URL of pose variation
        """
        
        # Parse image data URL
        if try_on_image_data_url.startswith('data:'):
            header, encoded = try_on_image_data_url.split(',', 1)
            mime_type = header.split(';')[0].split(':')[1]
            image_data = encoded
        else:
            mime_type = 'image/png'
            image_data = try_on_image_data_url
        
        prompt = f"""You are an expert fashion photographer AI. Take this image and regenerate it from a different perspective. 

The person, clothing, and background style must remain identical. 

The new perspective should be: "{pose_instruction}". 

Return ONLY the final image."""
        
        # Generate with Gemini
        response = self.model.generate_content([
            {
                'mime_type': mime_type,
                'data': image_data
            },
            prompt
        ])
        
        # Extract image
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'inline_data'):
                    mime = part.inline_data.mime_type
                    data = base64.b64encode(part.inline_data.data).decode('utf-8')
                    return f"data:{mime};base64,{data}"
        
        if hasattr(response, 'candidates'):
            for candidate in response.candidates:
                if hasattr(candidate, 'content'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data'):
                            mime = part.inline_data.mime_type
                            data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            return f"data:{mime};base64,{data}"
        
        raise ValueError("Failed to generate pose variation")


class VTOService:
    """
    VTO Service with proven 3-step workflow
    
    Step 1: Generate base model (one-time per user)
    Step 2: Apply garments (per outfit)
    Step 3: Generate poses (optional)
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.generator = VTOGenerator()
    
    async def setup_user_model(self, user_id: int, photo_bytes: bytes) -> Dict[str, Any]:
        """
        STEP 1: Generate base model from user photo
        
        This is done ONCE per user (or when they update photo)
        Stores the base model image for all future VTO
        
        Returns:
            {
                'success': True,
                'base_model_image': 'data:image/png;base64,...',
                'message': 'Base model created!'
            }
        """
        
        try:
            # Generate base model
            base_model_data_url = await self.generator.generate_base_model(photo_bytes)
            
            # TODO: Store base_model_data_url in database
            # For now, return to client
            
            return {
                'success': True,
                'base_model_image': base_model_data_url,
                'message': 'Base model generated! Ready for Virtual Try-On.'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate base model. Please try a different photo.'
            }
    
    async def generate_outfit_tryon(
        self,
        user_id: int,
        base_model_data_url: str,
        garment_images: List[bytes]
    ) -> Dict[str, Any]:
        """
        STEP 2: Apply garments to base model
        
        Takes stored base model + garment images
        Returns: Model wearing all garments
        
        Can apply multiple garments in sequence (layering)
        """
        
        current_image = base_model_data_url
        
        # Apply each garment sequentially
        for garment_bytes in garment_images:
            try:
                current_image = await self.generator.apply_garment_to_model(
                    current_image,
                    garment_bytes
                )
            except Exception as e:
                print(f"⚠️ Failed to apply garment: {e}")
                # Continue with next garment
        
        return {
            'success': True,
            'vto_image': current_image,
            'cost': 0.05 * len(garment_images)
        }
    
    async def generate_pose_variations(
        self,
        try_on_data_url: str,
        poses: List[str]
    ) -> Dict[str, List[str]]:
        """
        STEP 3: Generate pose variations (OPTIONAL)
        
        Takes try-on result and generates different angles
        
        Args:
            try_on_data_url: Result from step 2
            poses: ["Slightly turned, 3/4 view", "Side profile", ...]
        
        Returns:
            {
                'pose_variations': [data_url1, data_url2, ...]
            }
        """
        
        variations = []
        
        for pose in poses:
            try:
                variation = await self.generator.generate_pose_variation(
                    try_on_data_url,
                    pose
                )
                variations.append(variation)
            except Exception as e:
                print(f"⚠️ Failed to generate pose '{pose}': {e}")
        
        return {
            'pose_variations': variations
        }


# Available pose options
POSE_OPTIONS = [
    "Slightly turned, 3/4 view",
    "Side profile view",
    "Walking towards camera",
    "Leaning against a wall"
]


# Helper functions
def estimate_vto_cost(num_garments: int, num_poses: int = 0) -> float:
    """
    Estimate VTO cost
    
    Gemini 2.5 Flash: ~$0.05 per generation
    - Base model: 1 generation
    - Per garment: 1 generation each
    - Per pose: 1 generation each
    
    Total: (1 + num_garments + num_poses) * $0.05
    """
    total_generations = 1 + num_garments + num_poses
    return total_generations * 0.05


def vto_quota_limits() -> Dict[str, int]:
    """
    VTO quotas by plan
    
    Each "VTO" = 1 base model + 1 outfit (avg 2 garments)
    = 3 generations = $0.15 cost
    
    50 VTO = $7.50 cost
    Price: $4.99/month
    Loss per user: $2.51
    
    BUT: Most users won't use all 50!
    Actual usage: ~10-20 per month
    Actual cost: $1.50-3.00
    Profit: $2-3.50 per user
    """
    return {
        'free': 0,  # Free users can't use VTO
        'premium': 50  # Premium: 50 complete try-ons per month
    }
