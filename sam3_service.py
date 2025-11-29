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
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
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
