"""
Vision Service - Clothing Analysis using Gemini 2.0 Flash (REST API)
Cost: ~$0.002 per analysis
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
    
    def detect_image_type(self, image_source: str) -> Dict[str, Any]:
        """
        Detect if image contains a single clothing item or a full outfit
        Returns: {type: "single_item"|"outfit", items: [...]}
        """
        try:
            image_data, mime_type = self._image_to_base64(image_source)
            
            prompt = """Analyze this image and determine if it shows:
1. A SINGLE clothing item (just one piece of clothing, flat lay or on hanger)
2. A FULL OUTFIT (multiple clothing items, person wearing clothes, or styled outfit)

Return ONLY a JSON object:
{
  "type": "single_item" or "outfit",
  "items": [
    {
      "description": "specific item description for SAM segmentation (e.g., 'blue denim jacket', 'white longsleeve top', 'black skinny jeans')",
      "category": "tops|bottoms|outerwear|footwear|accessories|dresses"
    }
  ]
}

For single_item: items array has 1 item
For outfit: items array has all visible clothing items (2-6 typically)

Be specific in descriptions - include color and style for accurate segmentation.
Return ONLY the JSON, no other text."""

            result_text = self._call_gemini(prompt, image_data, mime_type)
            return json.loads(result_text)
            
        except Exception as e:
            print(f"Image type detection error: {e}")
            return {"type": "single_item", "items": []}
    
    def analyze_clothing(self, image_source: str) -> Dict[str, Any]:
        """
        Analyze a clothing item image and extract tags
        Returns: {category, description, color}
        """
        try:
            image_data, mime_type = self._image_to_base64(image_source)
            
            prompt = """Analyze this clothing item and return ONLY a JSON object with these fields:
{
  "category": "tops|bottoms|outerwear|footwear|accessories|dresses (REQUIRED - must be one of these)",
  "description": "specific item type like: wide leg pants, skinny jeans, denim jacket, longsleeve top, mini skirt, etc.",
  "color": "primary color (black, white, blue, light blue, navy, red, green, pink, brown, grey, beige, cream, etc.)"
}

Return ONLY the JSON, no other text or markdown."""

            result_text = self._call_gemini(prompt, image_data, mime_type)
            return json.loads(result_text)
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return {
                "category": "unknown",
                "description": "unknown", 
                "color": "unknown"
            }
    
    def analyze_clothing_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze clothing from raw bytes (for segmented items)"""
        try:
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = "image/png"
            
            prompt = """Analyze this clothing item and return ONLY a JSON object with these fields:
{
  "category": "tops|bottoms|outerwear|footwear|accessories|dresses (REQUIRED - must be one of these)",
  "description": "specific item type like: wide leg pants, skinny jeans, denim jacket, longsleeve top, mini skirt, etc.",
  "color": "primary color (black, white, blue, light blue, navy, red, green, pink, brown, grey, beige, cream, etc.)"
}

Return ONLY the JSON, no other text or markdown."""

            result_text = self._call_gemini(prompt, image_data, mime_type)
            return json.loads(result_text)
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return {
                "category": "unknown",
                "description": "unknown", 
                "color": "unknown"
            }


# Singleton instance
_vision_service = None

def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
