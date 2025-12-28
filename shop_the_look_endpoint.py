"""
Shop the Look - Complete Pipeline
=================================
Gemini detects items + bounding boxes → Crop each item → Vertex visual search

Flow:
1. User uploads outfit photo
2. Gemini identifies all items WITH bounding box coordinates
3. Crop each item from original image
4. Vertex visual search finds matches for each cropped item
5. Returns grouped results with affiliate links
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional
from PIL import Image
import io
import google.generativeai as genai

from vertex_retail_search import get_retail_search

# Configure Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU")
genai.configure(api_key=GEMINI_API_KEY)


class ShopTheLook:
    """
    Complete Shop the Look pipeline with visual search
    """
    
    def __init__(self):
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.retail_search = get_retail_search()
        print("✅ Shop the Look initialized")
    
    def detect_items_with_boxes(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Use Gemini to identify all clothing items WITH bounding boxes
        
        Returns list of items with:
        - category
        - description
        - bounding_box: {x_min, y_min, x_max, y_max} as percentages (0-100)
        """
        
        width, height = image.size
        
        prompt = """Analyze this outfit photo and identify EVERY clothing item and fashion accessory.

For EACH item, return a JSON object with:
{
    "category": "item type (jacket, dress, jeans, sneakers, handbag, sunglasses, etc.)",
    "description": "brief description for display (e.g., 'Black leather biker jacket')",
    "color": "primary color",
    "bounding_box": {
        "x_min": percentage from left edge (0-100),
        "y_min": percentage from top edge (0-100),
        "x_max": percentage from left edge (0-100),
        "y_max": percentage from top edge (0-100)
    }
}

IMPORTANT RULES:
- Bounding box values are PERCENTAGES (0-100), not pixels
- x_min/y_min is top-left corner, x_max/y_max is bottom-right corner
- Make boxes tight around each item but include the WHOLE item
- Only include clothing and fashion accessories (no phones, electronics)
- Be precise with bounding boxes - they will be used to crop the image

Example for a jacket in the upper portion of image:
{
    "category": "jacket",
    "description": "Black oversized leather jacket",
    "color": "black",
    "bounding_box": {"x_min": 15, "y_min": 10, "x_max": 85, "y_max": 55}
}

Return ONLY a JSON array, no other text."""

        response = self.gemini.generate_content([prompt, image])
        
        try:
            text = response.text.strip()
            # Clean markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            items = json.loads(text.strip())
            
            # Convert percentage boxes to pixel coordinates
            for item in items:
                if "bounding_box" in item:
                    box = item["bounding_box"]
                    item["pixel_box"] = {
                        "x_min": int(box["x_min"] * width / 100),
                        "y_min": int(box["y_min"] * height / 100),
                        "x_max": int(box["x_max"] * width / 100),
                        "y_max": int(box["y_max"] * height / 100)
                    }
            
            print(f"📸 Detected {len(items)} items with bounding boxes")
            return items
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Gemini response: {e}")
            print(f"   Response: {response.text[:500]}")
            return []
    
    def crop_item(self, image: Image.Image, pixel_box: Dict[str, int], padding: int = 10) -> Image.Image:
        """
        Crop an item from the original image using pixel coordinates
        
        Args:
            image: Original PIL Image
            pixel_box: {x_min, y_min, x_max, y_max} in pixels
            padding: Extra pixels around the box
        """
        width, height = image.size
        
        # Add padding but stay within bounds
        x_min = max(0, pixel_box["x_min"] - padding)
        y_min = max(0, pixel_box["y_min"] - padding)
        x_max = min(width, pixel_box["x_max"] + padding)
        y_max = min(height, pixel_box["y_max"] + padding)
        
        cropped = image.crop((x_min, y_min, x_max, y_max))
        return cropped
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.save(buffer, format="JPEG", quality=90)
        return base64.b64encode(buffer.getvalue()).decode()
    
    def visual_search_item(
        self,
        cropped_image: Image.Image,
        item_info: Dict[str, Any],
        visitor_id: str = "anonymous",
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Visual search for a single cropped item
        """
        
        image_base64 = self.image_to_base64(cropped_image)
        
        # Optional: filter by category if available
        filters = {}
        if item_info.get("category"):
            filters["category"] = item_info["category"]
        
        try:
            results = self.retail_search.visual_search(
                image_base64=image_base64,
                visitor_id=visitor_id,
                page_size=page_size,
                filters=filters if filters else None
            )
            
            return {
                "item": {
                    "category": item_info.get("category"),
                    "description": item_info.get("description"),
                    "color": item_info.get("color")
                },
                "matches": results,
                "match_count": len(results)
            }
            
        except Exception as e:
            print(f"⚠️ Visual search failed for {item_info.get('category')}: {e}")
            return {
                "item": item_info,
                "matches": [],
                "match_count": 0,
                "error": str(e)
            }
    
    def shop_the_look(
        self,
        image_bytes: bytes,
        visitor_id: str = "anonymous",
        matches_per_item: int = 10,
        return_crops: bool = False
    ) -> Dict[str, Any]:
        """
        Complete Shop the Look pipeline
        
        1. Gemini detects items with bounding boxes
        2. Crop each item from original image
        3. Vertex visual search for each crop
        4. Return grouped results
        
        Args:
            image_bytes: Raw image bytes
            visitor_id: User ID for personalization
            matches_per_item: How many matches per item
            return_crops: If True, include base64 crops in response
        
        Returns:
            {
                "items_found": 5,
                "total_matches": 47,
                "results": [
                    {
                        "item": {"category": "jacket", "description": "...", "color": "..."},
                        "crop_base64": "..." (if return_crops=True),
                        "matches": [...]
                    }
                ]
            }
        """
        
        print("\n" + "="*50)
        print("🛍️ SHOP THE LOOK - VISUAL SEARCH")
        print("="*50)
        
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        print(f"📷 Image: {image.size[0]}x{image.size[1]}")
        
        # Step 1: Detect items with bounding boxes
        print("\n📸 Step 1: Detecting items with Gemini...")
        items = self.detect_items_with_boxes(image)
        
        if not items:
            return {
                "items_found": 0,
                "total_matches": 0,
                "results": [],
                "error": "No items detected in image"
            }
        
        print(f"   Found {len(items)} items:")
        for item in items:
            box = item.get("pixel_box", {})
            print(f"   - {item.get('category')}: {item.get('description', '')[:40]}...")
            print(f"     Box: ({box.get('x_min')}, {box.get('y_min')}) to ({box.get('x_max')}, {box.get('y_max')})")
        
        # Step 2: Crop and search each item
        print(f"\n🔍 Step 2: Visual search for each item...")
        results = []
        total_matches = 0
        
        for item in items:
            if "pixel_box" not in item:
                print(f"   ⚠️ Skipping {item.get('category')} - no bounding box")
                continue
            
            # Crop the item
            cropped = self.crop_item(image, item["pixel_box"])
            print(f"   Cropped {item.get('category')}: {cropped.size[0]}x{cropped.size[1]}")
            
            # Visual search
            search_result = self.visual_search_item(
                cropped_image=cropped,
                item_info=item,
                visitor_id=visitor_id,
                page_size=matches_per_item
            )
            
            # Optionally include crop in response
            if return_crops:
                search_result["crop_base64"] = self.image_to_base64(cropped)
            
            results.append(search_result)
            total_matches += search_result.get("match_count", 0)
            print(f"   → {search_result.get('match_count', 0)} matches found")
        
        print(f"\n✅ Complete! {len(results)} items, {total_matches} total matches")
        
        return {
            "items_found": len(results),
            "total_matches": total_matches,
            "results": results
        }


# Singleton
_instance = None

def get_shop_the_look():
    global _instance
    if _instance is None:
        _instance = ShopTheLook()
    return _instance


# ==================== TEST ====================

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("🛍️ SHOP THE LOOK - VISUAL SEARCH TEST")
    print("="*60)
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\n📷 Testing with: {image_path}")
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        stl = ShopTheLook()
        results = stl.shop_the_look(image_bytes, return_crops=False)
        
        print("\n" + "="*60)
        print("📊 RESULTS")
        print("="*60)
        
        print(f"\nItems found: {results['items_found']}")
        print(f"Total matches: {results['total_matches']}")
        
        for r in results.get("results", []):
            item = r.get("item", {})
            print(f"\n🏷️ {item.get('category', 'Unknown')}: {item.get('description', '')}")
            print(f"   Matches: {r.get('match_count', 0)}")
            for match in r.get("matches", [])[:3]:
                print(f"   - {match.get('title', 'Unknown')} | £{match.get('price', '?')}")
    else:
        print("\nUsage: python3 shop_the_look_endpoint.py <image_path>")
        print("\nVerifying setup...")
        stl = ShopTheLook()
        print("✅ Setup verified!")
