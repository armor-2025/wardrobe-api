"""
SAM 3 Service - Clothing Segmentation using Roboflow SAM 3 API
Text-prompt based segmentation for outfit extraction
"""
import os
import httpx
import base64
import json
from typing import List, Dict, Any
from PIL import Image
from io import BytesIO


class SAM3Service:
    def __init__(self):
        self.api_key = os.getenv('ROBOFLOW_API_KEY', 'ec64q9NexYmlF1Z1s7KB')
        self.api_url = "https://serverless.roboflow.com/sam3/concept_segment"
    
    async def segment_item(self, image_data: bytes, text_prompt: str) -> Dict[str, Any]:
        """
        Segment a single item from an image using SAM 3 text prompt
        """
        try:
            # Resize image to known size for consistent SAM coordinates
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(image_data))
            original_size = img.size  # (width, height)
            
            # Resize to max 1024 on longest side (SAM works better with this)
            max_size = 1024
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Convert back to bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            resized_bytes = buffer.getvalue()
            
            image_b64 = base64.b64encode(resized_bytes).decode('utf-8')
            
            payload = {
                "image": {
                    "type": "base64",
                    "value": image_b64
                },
                "prompts": [
                    {"type": "text", "text": text_prompt}
                ]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}?api_key={self.api_key}",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            # Add original and resized dimensions to result for scaling
            result["original_size"] = original_size
            result["resized_size"] = img.size
            
            return {"success": True, "prompt": text_prompt, "result": result}
            
        except Exception as e:
            print(f"SAM 3 segmentation error: {e}")
            return {"success": False, "prompt": text_prompt, "error": str(e)}
    
    async def segment_outfit(self, image_data: bytes, item_descriptions: List[str]) -> List[Dict[str, Any]]:
        """Segment multiple items from an outfit photo"""
        results = []
        for description in item_descriptions:
            result = await self.segment_item(image_data, description)
            results.append(result)
        return results


_sam3_service = None

def get_sam3_service() -> SAM3Service:
    global _sam3_service
    if _sam3_service is None:
        _sam3_service = SAM3Service()
    return _sam3_service
