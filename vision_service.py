"""
Vision Service - Clothing Analysis using Vertex AI Gemini
Production-ready for Google Cloud
"""
import os
import json
import base64
from typing import Dict, Any, List
from pathlib import Path
from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import Part

# Initialize Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

client = genai.Client()


class VisionService:
    def __init__(self):
        pass
    
    def _image_to_bytes(self, image_source) -> tuple:
        """Load image and return (bytes, mime_type)"""
        if isinstance(image_source, bytes):
            return image_source, "image/jpeg"
        
        if isinstance(image_source, str):
            if image_source.startswith('http://127.0.0.1') or image_source.startswith('http://localhost'):
                import urllib.parse
                parsed = urllib.parse.urlparse(image_source)
                file_path = Path(parsed.path.lstrip('/'))
                img = Image.open(file_path)
            elif image_source.startswith('http'):
                import requests
                response = requests.get(image_source)
                return response.content, "image/jpeg"
            else:
                img = Image.open(image_source)
        else:
            img = image_source  # Assume PIL Image
        
        buffer = BytesIO()
        if img.mode == "RGBA": img = img.convert("RGB")
        img.save(buffer, format='JPEG')
        return buffer.getvalue(), "image/jpeg"
    
    async def analyze_upload(self, image_source) -> Dict[str, Any]:
        """
        MAIN METHOD - Analyze uploaded image in ONE Gemini call
        Detects single item vs outfit AND extracts all item details
        
        Returns: {
            "type": "single_item" | "outfit",
            "items": [
                {
                    "label": "jacket",  # Simple word for SAM segmentation
                    "description": "oversized denim trucker style",  # Fit/style details (NO color)
                    "category": "Outerwear",
                    "color": "blue"
                },
                ...
            ]
        }
        """
        try:
            image_bytes, mime_type = self._image_to_bytes(image_source)
            image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
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
      "category": "MUST be one of: Outerwear, Tops, Bottoms, Dresses, Footwear, Accessories",
      "color": "MUST be one of: Yellow, Blue, Navy, Beige, White, Bordeaux, Khaki, Coral, Ecru, Grey, Lavender, Magenta, Brown, Purple, Mustard, Orange, Black, Red, Pink, Turquoise, Green, Emerald Green, Baby Blue, Hot Pink, Light Green, Light Pink, Light Yellow, Neon Green, Neon Orange, Neon Yellow, Copper, Indigo, Gold, Silver, Multicolour, Neon Blue, No Colour"
    }
  ]
}

CRITICAL RULES:
- "label" must be ONE simple word only for AI segmentation: shirt, pants, jacket, dress, skirt, shorts, coat, sweater, shoes, boots, hat, bag, scarf, belt, glasses
- "description" MUST include the item type (e.g. "denim jacket", "graphic t-shirt", "wide leg jeans") plus style details
- "description" rules by category:
  * TOPS: Include item type. Only add "oversized" or "cropped" if clearly visible. Add "longsleeve" if longsleeve. Do NOT say "regular fit" for tops.
  * BOTTOMS: Include item type + fit (wide leg, slim, skinny, straight leg, tapered). E.g. "wide leg jeans", "slim chinos"
  * OUTERWEAR: Include item type + style. E.g. "denim trucker jacket", "oversized wool coat", "puffer jacket"
  * DRESSES: Include length + style. Add "longsleeve" if longsleeve. E.g. "midi wrap dress", "longsleeve maxi dress"
  * FOOTWEAR: Include style. E.g. "low-top sneakers", "leather boots", "suede loafers"
  * ACCESSORIES: Include style. E.g. "wool beanie", "leather belt", "silk scarf", "aviator sunglasses"
- "color" is a SEPARATE field - do NOT include color in description
- For single_item: items array has exactly 1 item
- For outfit: items array has all visible clothing items (typically 2-5 items)
- Category MUST be one of: tops, bottoms, outerwear, footwear, accessories, dresses, bags

INCLUDE: Bags, scarves, belts, hats, glasses, sunglasses if visible
EXCLUDE: Jewelry (necklaces, earrings, bracelets, rings, watches), socks, underwear, partially visible items

EXAMPLES:
Good: {"label": "jacket", "description": "denim trucker jacket", "color": "blue", "category": "Outerwear"}
Bad: {"label": "jacket", "description": "classic fit denim", "color": "blue", "category": "Outerwear"}

Good: {"label": "pants", "description": "wide leg drawstring trousers", "color": "black", "category": "Bottoms"}
Bad: {"label": "pants", "description": "wide leg drawstring", "color": "black", "category": "Bottoms"}

Good: {"label": "shirt", "description": "graphic print t-shirt", "color": "white", "category": "Tops"}
Bad: {"label": "shirt", "description": "crew neck graphic print", "color": "white", "category": "Tops"}

Good: {"label": "shirt", "description": "longsleeve oxford shirt", "color": "blue", "category": "Tops"}
Good: {"label": "dress", "description": "longsleeve midi wrap dress", "color": "green", "category": "dresses"}

Return ONLY valid JSON, no other text."""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image_part]
            )
            
            text = response.text.strip()
            # Clean up JSON
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            return json.loads(text.strip())
            
        except Exception as e:
            print(f"Upload analysis error: {e}")
            return {"type": "single_item", "items": []}
    
    async def analyze_clothing(self, image_source) -> Dict[str, Any]:
        """
        Legacy method - Analyze a single clothing item
        Returns: {category, description, color, label}
        """
        result = await self.analyze_upload(image_source)
        if result["items"]:
            item = result["items"][0]
            return {
                "category": item.get("category", "unknown"),
                "description": item.get("description", "unknown"),
                "color": item.get("color", "unknown"),
                "label": item.get("label", "clothing")
            }
        return {"category": "unknown", "description": "unknown", "color": "unknown", "label": "clothing"}


_vision_service = None

def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
