"""
SAM 3 Service - Clothing Segmentation using Roboflow SAM 3 API
Text-prompt based segmentation for outfit extraction

UPDATED: Fixed prompt format per Roboflow docs
- Prompts should be {"text": "item"} not {"type": "text", "text": "item"}
- Added format parameter for mask output
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
        self.api_key = os.getenv('ROBOFLOW_API_KEY')
        self.api_url = "https://serverless.roboflow.com/sam3/concept_segment"
    
    async def segment_item(self, image_data: bytes, text_prompt: str) -> Dict[str, Any]:
        """
        Segment a single item from an image using SAM 3 text prompt
        """
        try:
            # Send original image to SAM - it returns coordinates in original image space
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # FIXED: Correct prompt format per Roboflow docs
            # Should be {"text": "item"} NOT {"type": "text", "text": "item"}
            payload = {
                "format": "polygon",  # Request polygon format for masks
                "image": {
                    "type": "base64",
                    "value": image_b64
                },
                "prompts": [
                    {"text": text_prompt}  # FIXED: removed "type" field
                ]
            }
            
            print(f"  📤 SAM3 request: prompt='{text_prompt}'")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}?api_key={self.api_key}",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            # Log response structure for debugging
            if "prompt_results" in result:
                pr = result["prompt_results"]
                if pr and len(pr) > 0:
                    preds = pr[0].get("predictions", [])
                    print(f"  📥 SAM3 response: {len(preds)} predictions found")
                else:
                    print(f"  📥 SAM3 response: no prompt_results")
            elif "outputs" in result:
                print(f"  📥 SAM3 response (legacy): {len(result.get('outputs', []))} outputs")
            else:
                print(f"  📥 SAM3 response keys: {list(result.keys())}")
            
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
