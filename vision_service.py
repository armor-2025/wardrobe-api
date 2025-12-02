"""
Vision Service - Clothing Analysis using Gemini 2.0 Flash (REST API)
Cost: ~$0.002 per analysis (ONE call per upload)
"""
import os
import json
import base64
import httpx
from typing import Dict, Any, List
from pathlib import Path
from PIL import Image
from io import BytesIO


class VisionService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
    
    def _image_to_base64(self, image_source: str) -> tuple:
        """Load image and convert to base64, returns (base64_data, mime_type)"""
        if image_source.startswith('http://127.0.0.1') or image_source.startswith('http://localhost'):
            import urllib.parse
            parsed = urllib.parse.urlparse(image_source)
            file_path = Path(parsed.path.lstrip('/'))
            img = Image.open(file_path)
        elif image_source.startswith('http'):
            import requests
            response = requests.get(image_source)
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(image_source)
        
        buffer = BytesIO()
        img_format = img.format or 'PNG'
        img.save(buffer, format=img_format)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        mime_type = f"image/{img_format.lower()}"
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
        
        return image_data, mime_type
    
    def _call_gemini(self, prompt: str, image_data: str, mime_type: str) -> str:
        """Make a call to Gemini API and return the text response"""
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_data}}
                ]
            }]
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.json()
        
        result_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean up markdown if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        return result_text
    
    def analyze_upload(self, image_source: str) -> Dict[str, Any]:
        """
        MAIN METHOD - Analyze uploaded image in ONE Gemini call
        Detects single item vs outfit AND extracts all item details
        
        Returns: {
            "type": "single_item" | "outfit",
            "items": [
                {
                    "label": "jacket",  # Simple word for SAM segmentation
                    "description": "oversized denim trucker style",  # Fit/style details (NO color)
                    "category": "outerwear",
                    "color": "blue"
                },
                ...
            ]
        }
        """
        try:
            image_data, mime_type = self._image_to_base64(image_source)
            
            prompt = """Analyze this image and determine if it shows:
1. A SINGLE clothing item (just one piece of clothing, flat lay, on hanger, or person wearing one main item)
2. A FULL OUTFIT (multiple distinct clothing items visible, person wearing complete outfit)

Return ONLY a JSON object:
{
  "type": "single_item" or "outfit",
  "items": [
    {
      "label": "simple item name for AI segmentation (e.g., 'jacket', 't-shirt', 'jeans', 'sneakers', 'dress')",
      "description": "fit and style details WITHOUT color (e.g., 'oversized denim trucker', 'graphic print crew neck', 'wide-leg drawstring', 'low-top suede')",
      "category": "tops|bottoms|outerwear|footwear|accessories|dresses",
      "color": "primary color (black, white, blue, navy, red, green, pink, brown, grey, beige, cream, burgundy, etc.)"
    }
  ]
}

CRITICAL RULES:
- "label" must be ONE simple word only for AI segmentation: shirt, pants, jacket, dress, skirt, shorts, coat, sweater, shoes, boots, hat, bag
- "description" MUST include the item type (e.g. "denim jacket", "graphic t-shirt", "wide leg jeans") plus style details
- "description" rules by category:
  * TOPS: Include item type. Only add "oversized" or "cropped" if clearly visible. Add "longsleeve" if longsleeve. Do NOT say "regular fit" for tops.
  * BOTTOMS: Include item type + fit (wide leg, slim, skinny, straight leg, tapered). E.g. "wide leg jeans", "slim chinos"
  * OUTERWEAR: Include item type + style. E.g. "denim trucker jacket", "oversized wool coat", "puffer jacket"
  * DRESSES: Include length + style. Add "longsleeve" if longsleeve. E.g. "midi wrap dress", "longsleeve maxi dress"
  * FOOTWEAR: Include style. E.g. "low-top sneakers", "leather boots", "suede loafers"
- "color" is a SEPARATE field - do NOT include color in description
- For single_item: items array has exactly 1 item
- For outfit: items array has all visible clothing items (typically 2-5 items)
- Category MUST be one of: tops, bottoms, outerwear, footwear, accessories, dresses
- Include bags if clearly visible. Don't include jewelry or small accessories unless prominently featured

EXAMPLES:
Good: {"label": "jacket", "description": "denim trucker jacket", "color": "blue", "category": "outerwear"}
Bad: {"label": "jacket", "description": "classic fit denim", "color": "blue", "category": "outerwear"}

Good: {"label": "pants", "description": "wide leg drawstring trousers", "color": "black", "category": "bottoms"}
Bad: {"label": "pants", "description": "wide leg drawstring", "color": "black", "category": "bottoms"}

Good: {"label": "shirt", "description": "graphic print t-shirt", "color": "white", "category": "tops"}
Bad: {"label": "shirt", "description": "crew neck graphic print", "color": "white", "category": "tops"}

Good: {"label": "shirt", "description": "longsleeve oxford shirt", "color": "blue", "category": "tops"}
Good: {"label": "dress", "description": "longsleeve midi wrap dress", "color": "green", "category": "dresses"}

Return ONLY valid JSON, no other text."""

            result_text = self._call_gemini(prompt, image_data, mime_type)
            return json.loads(result_text)
            
        except Exception as e:
            print(f"Upload analysis error: {e}")
            return {"type": "single_item", "items": []}
    
    def analyze_clothing(self, image_source: str) -> Dict[str, Any]:
        """
        Legacy method - Analyze a single clothing item
        Returns: {category, description, color, label}
        """
        result = self.analyze_upload(image_source)
        if result["items"]:
            item = result["items"][0]
            return {
                "category": item.get("category", "unknown"),
                "description": item.get("description", "unknown"),
                "color": item.get("color", "unknown"),
                "label": item.get("label", "clothing")
            }
        return {"category": "unknown", "description": "unknown", "color": "unknown", "label": "clothing"}


# Singleton instance
_vision_service = None

def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
