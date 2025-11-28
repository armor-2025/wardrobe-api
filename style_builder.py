"""
Style Builder / "Dress Me" Feature
Quick outfit building by cycling through wardrobe items by category
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from database import User
from interaction_models import UserInteraction


class StyleBuilder:
    """
    Build outfits by cycling through items in each category
    User can quickly mix & match their wardrobe
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_outfit_slots(self) -> List[Dict[str, Any]]:
        """
        Define the outfit structure with templates
        Returns positions for clean canvas layout
        """
        return [
            {
                "category": "outerwear",
                "label": "Jacket / Coat",
                "position": {"x": 0.5, "y": 0.15},
                "optional": True,
                "size": "large"
            },
            {
                "category": "top",
                "label": "Top / Shirt",
                "position": {"x": 0.5, "y": 0.35},
                "optional": False,
                "size": "medium"
            },
            {
                "category": "bottom",
                "label": "Pants / Skirt",
                "position": {"x": 0.5, "y": 0.60},
                "optional": False,
                "size": "medium"
            },
            {
                "category": "shoes",
                "label": "Footwear",
                "position": {"x": 0.5, "y": 0.85},
                "optional": False,
                "size": "small"
            },
            {
                "category": "accessories",
                "label": "Bag / Accessories",
                "position": {"x": 0.8, "y": 0.5},
                "optional": True,
                "size": "small"
            }
        ]
    
    def get_items_by_category(
        self,
        user_id: int,
        category: str,
        include_wishlist: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all user's items in a specific category
        Returns items from:
        - Wardrobe (owned)
        - Wishlist (saved/favorited)
        - Recent interactions
        
        For carousel - user cycles through these quickly
        """
        # Get items from user interactions
        # In production, query actual wardrobe/wishlist tables
        
        interactions = self.db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.item_type == "product"
        ).order_by(
            UserInteraction.created_at.desc()
        ).limit(50).all()
        
        # Filter by category and group
        items_by_source = {
            "owned": [],
            "wishlist": [],
            "browsed": []
        }
        
        for interaction in interactions:
            item_data = {
                "product_id": interaction.item_id,
                "image_url": f"https://example.com/{interaction.item_id}.jpg",
                "name": f"Product {interaction.item_id}",
                "brand": "Brand Name",
                "price": 50.00,
                "in_wardrobe": False,
                "in_wishlist": False
            }
            
            # Categorize by interaction type
            if interaction.action_type == "purchase_complete":
                item_data["in_wardrobe"] = True
                items_by_source["owned"].append(item_data)
            elif interaction.action_type in ["favorite_product", "canvas_add"]:
                item_data["in_wishlist"] = True
                items_by_source["wishlist"].append(item_data)
            else:
                items_by_source["browsed"].append(item_data)
        
        # Return in order: owned first, then wishlist, then browsed
        all_items = (
            items_by_source["owned"] +
            (items_by_source["wishlist"] if include_wishlist else []) +
            items_by_source["browsed"][:5]  # Only recent browsed items
        )
        
        return all_items
    
    def build_dress_me_data(
        self,
        user_id: int,
        new_item_id: Optional[str] = None,
        new_item_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all data needed for "Dress Me" carousel interface
        
        Args:
            user_id: User building the outfit
            new_item_id: Optional - item user wants to style (e.g. new purchase)
            new_item_category: Category of new item
        
        Returns:
            Data for carousel UI with all categories
        """
        slots = self.get_outfit_slots()
        
        dress_me_data = {
            "slots": [],
            "featured_item": None
        }
        
        # If there's a featured item (e.g. "style this new top")
        if new_item_id and new_item_category:
            dress_me_data["featured_item"] = {
                "product_id": new_item_id,
                "category": new_item_category,
                "position": self._get_position_for_category(new_item_category)
            }
        
        # For each slot, get user's items in that category
        for slot in slots:
            category = slot["category"]
            
            # Skip if this is the featured item category
            if new_item_category and category == new_item_category:
                continue
            
            items = self.get_items_by_category(user_id, category)
            
            dress_me_data["slots"].append({
                "category": category,
                "label": slot["label"],
                "position": slot["position"],
                "optional": slot["optional"],
                "items": items,
                "item_count": len(items)
            })
        
        return dress_me_data
    
    def _get_position_for_category(self, category: str) -> Dict[str, float]:
        """Get canvas position for a category"""
        slots = self.get_outfit_slots()
        for slot in slots:
            if slot["category"] == category:
                return slot["position"]
        return {"x": 0.5, "y": 0.5}
