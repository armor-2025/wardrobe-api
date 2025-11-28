"""
Styling / Dress Me Endpoints
Quick outfit building interface
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from database import get_db, User
from auth_service import get_current_user
from style_builder import StyleBuilder

router = APIRouter(prefix="/styling", tags=["styling"])


# Helper function for authentication
def get_user_from_token(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate user from Bearer token"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user


# ==================== DRESS ME INTERFACE ====================

@router.get("/dress-me")
async def get_dress_me_interface(
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db),
    new_item_id: Optional[str] = None,
    new_item_category: Optional[str] = None
):
    """
    Get "Dress Me" carousel interface (like Whering app)
    
    Returns items grouped by category for quick carousel browsing:
    - Top slot: Carousel of all tops
    - Bottom slot: Carousel of all bottoms  
    - Shoes slot: Carousel of all shoes
    - etc.
    
    User can quickly cycle through their wardrobe to build outfits
    
    Query params:
    - new_item_id: Feature a specific item (e.g. "style this new top")
    - new_item_category: Category of featured item
    """
    builder = StyleBuilder(db)
    
    data = builder.build_dress_me_data(
        user_id=current_user.id,
        new_item_id=new_item_id,
        new_item_category=new_item_category
    )
    
    return data


@router.get("/templates")
async def get_canvas_templates(
    db: Session = Depends(get_db),
    occasion: Optional[str] = None
):
    """
    Get canvas templates with predefined layouts
    
    Templates show dotted outlines for where to place items
    Keeps canvas looking clean and organized (not random mess!)
    """
    templates = [
        {
            "id": "basic-outfit",
            "name": "Basic Outfit",
            "description": "Top, bottom, and shoes",
            "thumbnail": "https://example.com/templates/basic.jpg",
            "occasion": ["casual", "work"],
            "slots": [
                {
                    "category": "top",
                    "label": "Top",
                    "position": {"x": 0.5, "y": 0.35},
                    "required": True,
                    "size": {"width": 0.6, "height": 0.3}
                },
                {
                    "category": "bottom",
                    "label": "Bottom",
                    "position": {"x": 0.5, "y": 0.60},
                    "required": True,
                    "size": {"width": 0.6, "height": 0.3}
                },
                {
                    "category": "shoes",
                    "label": "Shoes",
                    "position": {"x": 0.5, "y": 0.85},
                    "required": True,
                    "size": {"width": 0.4, "height": 0.15}
                }
            ]
        },
        {
            "id": "layered-look",
            "name": "Layered Look",
            "description": "Jacket, top, bottom, shoes",
            "thumbnail": "https://example.com/templates/layered.jpg",
            "occasion": ["casual", "work", "going-out"],
            "slots": [
                {
                    "category": "outerwear",
                    "label": "Jacket/Coat",
                    "position": {"x": 0.5, "y": 0.20},
                    "required": False,
                    "size": {"width": 0.65, "height": 0.35}
                },
                {
                    "category": "top",
                    "label": "Top",
                    "position": {"x": 0.5, "y": 0.40},
                    "required": True,
                    "size": {"width": 0.55, "height": 0.25}
                },
                {
                    "category": "bottom",
                    "label": "Bottom",
                    "position": {"x": 0.5, "y": 0.65},
                    "required": True,
                    "size": {"width": 0.55, "height": 0.3}
                },
                {
                    "category": "shoes",
                    "label": "Shoes",
                    "position": {"x": 0.5, "y": 0.88},
                    "required": True,
                    "size": {"width": 0.4, "height": 0.12}
                }
            ]
        },
        {
            "id": "accessorized",
            "name": "Complete Look",
            "description": "Full outfit with accessories",
            "thumbnail": "https://example.com/templates/accessorized.jpg",
            "occasion": ["going-out", "event"],
            "slots": [
                {
                    "category": "top",
                    "label": "Top",
                    "position": {"x": 0.5, "y": 0.30},
                    "required": True,
                    "size": {"width": 0.5, "height": 0.25}
                },
                {
                    "category": "bottom",
                    "label": "Bottom",
                    "position": {"x": 0.5, "y": 0.55},
                    "required": True,
                    "size": {"width": 0.5, "height": 0.3}
                },
                {
                    "category": "shoes",
                    "label": "Shoes",
                    "position": {"x": 0.5, "y": 0.80},
                    "required": True,
                    "size": {"width": 0.35, "height": 0.12}
                },
                {
                    "category": "bag",
                    "label": "Bag",
                    "position": {"x": 0.75, "y": 0.50},
                    "required": False,
                    "size": {"width": 0.25, "height": 0.2}
                },
                {
                    "category": "accessories",
                    "label": "Accessories",
                    "position": {"x": 0.25, "y": 0.30},
                    "required": False,
                    "size": {"width": 0.2, "height": 0.15}
                }
            ]
        },
        {
            "id": "dress-look",
            "name": "Dress Look",
            "description": "Dress or one-piece outfit",
            "thumbnail": "https://example.com/templates/dress.jpg",
            "occasion": ["date", "event", "going-out"],
            "slots": [
                {
                    "category": "dress",
                    "label": "Dress",
                    "position": {"x": 0.5, "y": 0.45},
                    "required": True,
                    "size": {"width": 0.6, "height": 0.6}
                },
                {
                    "category": "shoes",
                    "label": "Shoes",
                    "position": {"x": 0.5, "y": 0.85},
                    "required": True,
                    "size": {"width": 0.35, "height": 0.12}
                },
                {
                    "category": "outerwear",
                    "label": "Jacket (Optional)",
                    "position": {"x": 0.5, "y": 0.15},
                    "required": False,
                    "size": {"width": 0.65, "height": 0.25}
                }
            ]
        }
    ]
    
    # Filter by occasion if provided
    if occasion:
        templates = [t for t in templates if occasion in t.get("occasion", [])]
    
    return {"templates": templates, "count": len(templates)}


@router.post("/canvas-from-template/{template_id}")
async def create_canvas_from_template(
    template_id: str,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Create a new canvas from a template
    Canvas will have predefined layout with dotted guides
    """
    from canvas_models import Canvas
    
    canvas = Canvas(
        user_id=current_user.id,
        name=f"Outfit from {template_id}",
        items=[],
        item_positions={},
        is_public=False
    )
    
    db.add(canvas)
    db.commit()
    db.refresh(canvas)
    
    return {
        "canvas_id": canvas.id,
        "template_id": template_id,
        "message": "Canvas created from template"
    }
