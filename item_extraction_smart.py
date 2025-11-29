"""
Smart Item Extraction Router
Uses the best method for each upload type
"""
from typing import Dict, Any
from item_extraction_real import RealItemExtractor
from item_extraction_clarifai import ClarifaiExtractor
import os


class SmartExtractor:
    """
    Route to the best extraction method:
    - Single items (floor/flat lay) → rembg (FREE)
    - Full outfits → Clarifai API ($0.0008/image)
    """
    
    def __init__(self):
        self.rembg_extractor = RealItemExtractor()
        
        # Initialize Clarifai if API key available
        clarifai_key = os.getenv('CLARIFAI_API_KEY')
        if clarifai_key:
            print(f"✅ Clarifai enabled with key: {clarifai_key[:10]}...")
            self.clarifai_extractor = ClarifaiExtractor(api_key=clarifai_key)
            self.clarifai_enabled = True
        else:
            print("❌ Clarifai not enabled - no API key found")
            self.clarifai_enabled = False
    
    async def extract_items_from_photo(
        self,
        image_data: bytes,
        user_id: int,
        upload_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Extract items using best method
        
        Args:
            upload_type: "single_item", "full_outfit", or "auto"
        """
        
        print(f"🔍 Upload type: {upload_type}")
        print(f"🔍 Clarifai enabled: {self.clarifai_enabled}")
        
        # If Clarifai enabled and outfit photo, use it
        if self.clarifai_enabled and upload_type == "full_outfit":
            print("✅ Using Clarifai API!")
            return await self.clarifai_extractor.extract_items_from_photo(
                image_data, user_id
            )
        
        # Otherwise use free rembg (perfect for single items)
        print("ℹ️ Using free rembg")
        return await self.rembg_extractor.extract_items_from_photo(
            image_data, user_id
        )


# Helper function
def create_wardrobe_items_from_extraction(db, user_id: int, extraction_results: Dict[str, Any]) -> list:
    """Create wardrobe items from extraction"""
    from interaction_models import UserInteraction
    
    created_ids = []
    for item in extraction_results["items"]:
        interaction = UserInteraction(
            user_id=user_id,
            action_type="wardrobe_add",
            item_id=item["item_id"],
            item_type="product",
            weight=15.0,
            interaction_metadata={
                "category": item["category"],
                "attributes": item["detected_attributes"],
                "source": "outfit_photo_extraction"
            }
        )
        db.add(interaction)
        created_ids.append(item["item_id"])
    
    db.commit()
    return created_ids
