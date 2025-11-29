"""
Vision Service - Clothing Analysis using Gemini 2.0 Flash (REST API)
Cost: ~$0.002 per analysis
"""
import os
import json
import base64
import httpx
from typing import Dict, Any
from pathlib import Path
from PIL import Image
from io import BytesIO


class VisionService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
    
    def analyze_clothing(self, image_source: str) -> Dict[str, Any]:
        """
        Analyze a clothing item image and extract tags
        image_source can be either a URL or a local file path
        Returns: {category, description, color}
        """
        try:
            # Load image and convert to base64
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
            
            # Convert to base64
            buffer = BytesIO()
            img_format = img.format or 'PNG'
            img.save(buffer, format=img_format)
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Determine mime type
            mime_type = f"image/{img_format.lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"
            
            prompt = """Analyze this clothing item and return ONLY a JSON object with these fields:
{
  "category": "tops|bottoms|outerwear|footwear|accessories|dresses (REQUIRED - must be one of these)",
  "description": "specific item type like: wide leg pants, skinny jeans, denim jacket, longsleeve top, mini skirt, etc.",
  "color": "primary color (black, white, blue, light blue, navy, red, green, pink, brown, grey, beige, cream, etc.)"
}

Return ONLY the JSON, no other text or markdown."""

            # REST API request
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_data
                            }
                        }
                    ]
                }]
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()
                result = response.json()
            
            # Extract text from response
            result_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean up markdown if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            tags = json.loads(result_text)
            return tags
            
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
