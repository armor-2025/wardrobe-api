"""
Vision Service - Clothing Analysis using Gemini 2.0 Flash
Cost: ~$0.002 per analysis (cheaper than GPT-4o-mini at $0.005)
"""
import os
import json
import base64
import google.generativeai as genai
from typing import Dict, Any
from pathlib import Path
from PIL import Image


class VisionService:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def analyze_clothing(self, image_source: str) -> Dict[str, Any]:
        """
        Analyze a clothing item image and extract tags
        image_source can be either a URL or a local file path
        Returns: {category, color, fabric, pattern, style_tags}
        """
        try:
            # Load image
            if image_source.startswith('http://127.0.0.1') or image_source.startswith('http://localhost'):
                # Extract file path from localhost URL
                import urllib.parse
                parsed = urllib.parse.urlparse(image_source)
                file_path = Path(parsed.path.lstrip('/'))
                img = Image.open(file_path)
            elif image_source.startswith('http'):
                # Remote URL - download first
                import requests
                response = requests.get(image_source)
                from io import BytesIO
                img = Image.open(BytesIO(response.content))
            else:
                # Local file path
                img = Image.open(image_source)
            
            prompt = """Analyze this clothing item and return ONLY a JSON object with these fields:
{
  "category": "tops|bottoms|outerwear|footwear|accessories|dresses",
  "subcategory": "specific type like t-shirt, jeans, sneakers, blazer, etc.",
  "color": "primary color (red, blue, black, white, green, pink, brown, grey, yellow, orange, purple, beige, navy, cream, etc.)",
  "fabric": "denim|cotton|silk|leather|wool|cashmere|linen|polyester|nylon|suede|velvet|satin|knit|unknown",
  "pattern": "solid|striped|floral|checkered|polka-dot|animal-print|graphic|abstract|plain|other",
  "style_tags": ["casual", "formal", "vintage", "modern", "sporty", "elegant", "streetwear", "minimalist", etc. - up to 3 tags]
}

Return ONLY the JSON, no other text or markdown."""

            response = self.model.generate_content([prompt, img])
            
            # Parse response
            result_text = response.text.strip()
            
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
                "subcategory": "unknown", 
                "color": "unknown",
                "fabric": "unknown",
                "pattern": "unknown",
                "style_tags": []
            }


# Singleton instance
_vision_service = None

def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
