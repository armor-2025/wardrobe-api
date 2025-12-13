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
        img.save(buffer, format='JPEG')
        return buffer.getvalue(), "image/jpeg"
    
    async def analyze_upload(self, image_source) -> Dict[str, Any]:
        """
        Analyze uploaded image to detect single item vs outfit
        Returns: {type: 'single_item'|'outfit', items: [...]}
        """
        try:
            image_bytes, mime_type = self._image_to_bytes(image_source)
            image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            prompt = """Analyze this fashion image. Determine if it shows:
1. A SINGLE clothing item (product photo, flat lay of ONE item)
2. An OUTFIT (multiple items worn together OR multiple items in photo)

ONLY include these categories:
- Tops (t-shirts, shirts, blouses, sweaters, hoodies)
- Bottoms (jeans, trousers, shorts, skirts)
- Dresses/Jumpsuits
- Outerwear (jackets, coats, blazers)
- Shoes (sneakers, boots, heels, sandals)
- Bags (handbags, backpacks)
- Accessories (scarves, belts, hats, glasses, sunglasses)

EXCLUDE - do NOT include:
- Jewelry (necklaces, earrings, bracelets, rings, watches)
- Socks
- Underwear
- Partially visible items

Return JSON only:
{
    "type": "single_item" or "outfit",
    "items": [
        {
            "label": "item type (e.g., 'dress', 'jeans', 'sneakers')",
            "category": "tops/bottoms/dresses/outerwear/shoes/bags/accessories",
            "color": "primary color",
            "description": "brief description"
        }
    ]
}

For single_item: return 1 item in array
For outfit: return only MAIN visible clothing items"""

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
    
    async def analyze_garment(self, image_source) -> Dict[str, Any]:
        """Analyze a single garment for detailed attributes"""
        try:
            image_bytes, mime_type = self._image_to_bytes(image_source)
            image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            prompt = """Analyze this clothing item. Return JSON only:
{
    "category": "tops/bottoms/dresses/outerwear/shoes/accessories",
    "subcategory": "specific type (e.g., t-shirt, jeans, sneakers)",
    "color": "primary color",
    "color_hex": "#XXXXXX",
    "pattern": "solid/striped/floral/etc",
    "material": "cotton/denim/leather/etc",
    "style": "casual/formal/athletic/etc",
    "description": "brief description for search"
}"""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image_part]
            )
            
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            return json.loads(text.strip())
            
        except Exception as e:
            print(f"Garment analysis error: {e}")
            return {}


_vision_service = None

def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
