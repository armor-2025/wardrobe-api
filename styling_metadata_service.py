"""
Styling Metadata Service - Extracts formality, silhouette, material for AI Styling
SEPARATE from vision_service.py - does NOT touch existing clothing analysis

Used for AI Outfit Generation feature (ALTA-style)
"""
import os
import json
from typing import Dict, Any
from pathlib import Path
from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import Part

# Initialize Vertex AI (same setup as vision_service)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

client = genai.Client()


class StylingMetadataService:
    """
    Extracts styling metadata for AI outfit generation.
    Runs as a SECOND Gemini call, separate from the main vision analysis.
    
    Extracts:
    - formality_level: casual, smart_casual, business_casual, formal, black_tie
    - silhouette: fitted, regular, relaxed, oversized, structured, flowy
    - material: cotton, wool, linen, denim, leather, silk, knit, synthetic, etc.
    - style_tags: minimal, classic, feminine, edgy, sporty, romantic, etc.
    - secondary_colours: accent/pattern colours
    - subcategory: specific item type (t-shirt, blouse, cardigan, etc.)
    """
    
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
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(buffer, format='JPEG')
        return buffer.getvalue(), "image/jpeg"
    
    async def extract_styling_metadata(self, image_source, category_hint: str = None, item_label: str = None) -> Dict[str, Any]:
        """
        Extract styling metadata from clothing image.
        
        Args:
            image_source: File path, URL, bytes, or PIL Image
            category_hint: Optional category from first Gemini call (e.g., "Tops")
        
        Returns:
            {
                "formality_level": "casual",
                "silhouette": "relaxed",
                "material": "cotton",
                "style_tags": ["minimal", "classic"],
                "secondary_colours": ["White"],
                "subcategory": "t-shirt"
            }
        """
        try:
            image_bytes, mime_type = self._image_to_bytes(image_source)
            image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            category_context = ""
            if item_label and category_hint:
                category_context = f"Focus ONLY on the {item_label} ({category_hint}) in this image. Ignore all other items."
            elif category_hint:
                category_context = f"This item is categorized as: {category_hint}"
            
            prompt = f"""Analyze this clothing image for styling metadata.
{category_context}

Return ONLY a JSON object with these fields:

{{
  "formality_level": "MUST be one of: casual, smart_casual, business_casual, formal, black_tie",
  "silhouette": "MUST be one of: fitted, regular, relaxed, oversized, structured, flowy",
  "material": "primary material (e.g., cotton, wool, linen, denim, leather, silk, knit, synthetic, velvet, satin, chiffon, tweed, corduroy, fleece, nylon, polyester)",
  "style_tags": ["array of 1-3 style tags from: minimal, classic, feminine, masculine, edgy, romantic, sporty, bohemian, preppy, streetwear, vintage, modern, elegant, casual"],
  "secondary_colours": ["array of accent/pattern colours if any, empty array if solid - use ONLY: Yellow, Blue, Navy, Beige, White, Bordeaux, Khaki, Coral, Ecru, Grey, Lavender, Magenta, Brown, Purple, Mustard, Orange, Black, Red, Pink, Turquoise, Green, Emerald Green, Baby Blue, Hot Pink, Light Green, Light Pink, Light Yellow, Gold, Silver, Multicolour"],
  "subcategory": "specific item type (see guide below)"
}}

FORMALITY GUIDE:
- casual: t-shirts, hoodies, sweatshirts, joggers, shorts, flip-flops, sneakers, baseball caps
- smart_casual: polo shirts, chinos, blouses, loafers, clean trainers, cardigans, casual dresses
- business_casual: dress shirts, tailored trousers, blazers, oxford shoes, pencil skirts, knit sweaters
- formal: suits, dress shoes, evening dresses, heels, ties, formal blouses
- black_tie: tuxedos, gowns, formal evening wear, bow ties

SILHOUETTE GUIDE:
- fitted: body-hugging, slim cut, tailored, skinny
- regular: standard fit, not tight or loose
- relaxed: slightly loose, comfortable, easy fit
- oversized: intentionally large, boxy, dropped shoulders
- structured: holds shape, padded shoulders (blazers, coats)
- flowy: loose and moves freely (maxi dresses, wide trousers, chiffon)

SUBCATEGORY EXAMPLES:
- Tops: t-shirt, blouse, shirt, polo, tank top, crop top, sweater, cardigan, hoodie, sweatshirt, vest, camisole
- Bottoms: jeans, trousers, chinos, shorts, skirt, mini skirt, midi skirt, maxi skirt, joggers, leggings, culottes
- Dresses: mini dress, midi dress, maxi dress, shirt dress, wrap dress, slip dress, bodycon dress, A-line dress
- Outerwear: jacket, blazer, coat, puffer jacket, denim jacket, leather jacket, bomber jacket, trench coat, cardigan, parka
- Footwear: sneakers, trainers, boots, ankle boots, heels, flats, loafers, sandals, slides, oxford shoes, brogues
- Accessories: bag, handbag, backpack, belt, scarf, hat, cap, beanie, sunglasses, glasses

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
            
            result = json.loads(text.strip())
            
            # Validate and provide defaults
            return {
                "formality_level": result.get("formality_level", "casual"),
                "silhouette": result.get("silhouette", "regular"),
                "material": result.get("material", "unknown"),
                "style_tags": result.get("style_tags", []),
                "secondary_colours": result.get("secondary_colours", []),
                "subcategory": result.get("subcategory", "unknown")
            }
            
        except Exception as e:
            print(f"Styling metadata extraction error: {e}")
            return {
                "formality_level": "casual",
                "silhouette": "regular",
                "material": "unknown",
                "style_tags": [],
                "secondary_colours": [],
                "subcategory": "unknown"
            }


# Singleton instance
_styling_metadata_service = None

def get_styling_metadata_service() -> StylingMetadataService:
    global _styling_metadata_service
    if _styling_metadata_service is None:
        _styling_metadata_service = StylingMetadataService()
    return _styling_metadata_service
