"""
Canvas/Outfit Builder Endpoints
Users create, save, and share outfit combinations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from database import get_db, User
from canvas_models import Canvas, CanvasLike, OutfitSuggestion, CanvasTemplate
from auth_service import get_current_user
from fastapi import Header

router = APIRouter(prefix="/canvas", tags=["canvas"])


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


# ==================== SCHEMAS ====================

class CanvasCreate(BaseModel):
    name: Optional[str] = "Untitled Outfit"
    description: Optional[str] = None
    items: List[str] = []
    item_positions: Optional[Dict[str, Dict[str, float]]] = {}
    occasion: Optional[str] = None
    season: Optional[str] = None
    tags: List[str] = []
    is_public: bool = False


class CanvasUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[str]] = None
    item_positions: Optional[Dict[str, Dict[str, float]]] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class CanvasResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    items: List[str]
    item_positions: Dict[str, Any]
    occasion: Optional[str]
    season: Optional[str]
    tags: List[str]
    thumbnail_url: Optional[str]
    view_count: int
    like_count: int
    save_count: int
    is_public: bool
    vto_generated: bool
    vto_image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== CANVAS CRUD ====================

@router.post("/", response_model=CanvasResponse)
async def create_canvas(
    canvas_data: CanvasCreate,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Create a new outfit canvas
    
    Users can drag & drop items to build outfits
    """
    canvas = Canvas(
        user_id=current_user.id,
        name=canvas_data.name,
        description=canvas_data.description,
        items=canvas_data.items,
        item_positions=canvas_data.item_positions or {},
        occasion=canvas_data.occasion,
        season=canvas_data.season,
        tags=canvas_data.tags,
        is_public=canvas_data.is_public
    )
    
    db.add(canvas)
    db.commit()
    db.refresh(canvas)
    
    # Track canvas creation as high-value interaction
    from interaction_models import UserInteraction
    interaction = UserInteraction(
        user_id=current_user.id,
        action_type="canvas_create",
        item_id=str(canvas.id),
        item_type="canvas",
        weight=20.0,  # Canvas creation = 20x weight!
        interaction_metadata={
            "item_count": len(canvas_data.items),
            "occasion": canvas_data.occasion
        }
    )
    db.add(interaction)
    db.commit()
    
    return canvas


@router.get("/my-canvases", response_model=List[CanvasResponse])
async def get_my_canvases(
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100)
):
    """
    Get all canvases created by current user
    """
    canvases = db.query(Canvas).filter(
        Canvas.user_id == current_user.id
    ).order_by(
        Canvas.updated_at.desc()
    ).limit(limit).all()
    
    return canvases


@router.get("/{canvas_id}", response_model=CanvasResponse)
async def get_canvas(
    canvas_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_user_from_token)
):
    """
    Get a specific canvas by ID
    """
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Check permissions
    if not canvas.is_public and canvas.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This canvas is private")
    
    # Increment view count
    canvas.view_count += 1
    db.commit()
    
    return canvas


@router.put("/{canvas_id}", response_model=CanvasResponse)
async def update_canvas(
    canvas_id: int,
    canvas_data: CanvasUpdate,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Update canvas (add/remove items, change layout, etc.)
    """
    canvas = db.query(Canvas).filter(
        Canvas.id == canvas_id,
        Canvas.user_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Update fields
    if canvas_data.name is not None:
        canvas.name = canvas_data.name
    if canvas_data.description is not None:
        canvas.description = canvas_data.description
    if canvas_data.items is not None:
        canvas.items = canvas_data.items
    if canvas_data.item_positions is not None:
        canvas.item_positions = canvas_data.item_positions
    if canvas_data.occasion is not None:
        canvas.occasion = canvas_data.occasion
    if canvas_data.season is not None:
        canvas.season = canvas_data.season
    if canvas_data.tags is not None:
        canvas.tags = canvas_data.tags
    if canvas_data.is_public is not None:
        canvas.is_public = canvas_data.is_public
    
    canvas.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(canvas)
    
    return canvas


@router.delete("/{canvas_id}")
async def delete_canvas(
    canvas_id: int,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Delete a canvas
    """
    canvas = db.query(Canvas).filter(
        Canvas.id == canvas_id,
        Canvas.user_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    db.delete(canvas)
    db.commit()
    
    return {"message": "Canvas deleted"}


# ==================== CANVAS ADD ITEM ====================

@router.post("/{canvas_id}/items/{item_id}")
async def add_item_to_canvas(
    canvas_id: int,
    item_id: str,
    position: Optional[Dict[str, float]] = None,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Add an item to canvas
    Quick action: "Add to Canvas" button
    """
    canvas = db.query(Canvas).filter(
        Canvas.id == canvas_id,
        Canvas.user_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Add item if not already there
    if item_id not in canvas.items:
        canvas.items.append(item_id)
        
        # Set position
        if position:
            if not canvas.item_positions:
                canvas.item_positions = {}
            canvas.item_positions[item_id] = position
        
        canvas.updated_at = datetime.utcnow()
        db.commit()
        
        # Track as canvas add (20x weight)
        from interaction_models import UserInteraction
        interaction = UserInteraction(
            user_id=current_user.id,
            action_type="canvas_add",
            item_id=item_id,
            item_type="product",
            weight=20.0,
            interaction_metadata={"canvas_id": canvas_id}
        )
        db.add(interaction)
        db.commit()
    
    return {
        "message": "Item added to canvas",
        "canvas_id": canvas_id,
        "item_id": item_id,
        "total_items": len(canvas.items)
    }


@router.delete("/{canvas_id}/items/{item_id}")
async def remove_item_from_canvas(
    canvas_id: int,
    item_id: str,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Remove an item from canvas
    """
    canvas = db.query(Canvas).filter(
        Canvas.id == canvas_id,
        Canvas.user_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    if item_id in canvas.items:
        canvas.items.remove(item_id)
        
        # Remove position
        if canvas.item_positions and item_id in canvas.item_positions:
            del canvas.item_positions[item_id]
        
        canvas.updated_at = datetime.utcnow()
        db.commit()
    
    return {
        "message": "Item removed from canvas",
        "canvas_id": canvas_id,
        "total_items": len(canvas.items)
    }


# ==================== SOCIAL FEATURES ====================

@router.post("/{canvas_id}/like")
async def like_canvas(
    canvas_id: int,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Like someone's outfit canvas
    """
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Check if already liked
    existing_like = db.query(CanvasLike).filter(
        CanvasLike.canvas_id == canvas_id,
        CanvasLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        # Unlike
        db.delete(existing_like)
        canvas.like_count = max(0, canvas.like_count - 1)
        db.commit()
        return {"message": "Unliked", "like_count": canvas.like_count}
    else:
        # Like
        like = CanvasLike(canvas_id=canvas_id, user_id=current_user.id)
        db.add(like)
        canvas.like_count += 1
        db.commit()
        return {"message": "Liked", "like_count": canvas.like_count}


@router.get("/discover/public", response_model=List[CanvasResponse])
async def discover_public_canvases(
    db: Session = Depends(get_db),
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = Query(20, le=50)
):
    """
    Discover public outfit canvases
    Browse other people's style
    """
    query = db.query(Canvas).filter(Canvas.is_public == True)
    
    if occasion:
        query = query.filter(Canvas.occasion == occasion)
    if season:
        query = query.filter(Canvas.season == season)
    
    canvases = query.order_by(
        Canvas.like_count.desc(),
        Canvas.created_at.desc()
    ).limit(limit).all()
    
    return canvases


# ==================== AI SUGGESTIONS ====================

@router.get("/{canvas_id}/suggestions")
async def get_outfit_suggestions(
    canvas_id: int,
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get AI suggestions to complete this outfit
    "You might also need..."
    """
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Analyze what's on the canvas
    categories_present = _get_categories_from_items(canvas.items)
    
    # Determine what's missing
    essential_categories = ["top", "bottom", "shoes"]
    missing = [cat for cat in essential_categories if cat not in categories_present]
    
    suggestions = []
    
    for category in missing:
        # Get suggestions from recommendation engine
        # For now, return mock data
        suggestions.append({
            "category": category,
            "reason": f"Complete your outfit with {category}",
            "suggested_items": [
                {"product_id": f"{category}-001", "match_score": 0.85},
                {"product_id": f"{category}-002", "match_score": 0.82},
                {"product_id": f"{category}-003", "match_score": 0.78}
            ]
        })
    
    return {
        "canvas_id": canvas_id,
        "items_count": len(canvas.items),
        "suggestions": suggestions
    }


def _get_categories_from_items(item_ids: List[str]) -> List[str]:
    """
    Helper to determine what categories are already on canvas
    In production, query product database
    """
    # Mock implementation
    categories = []
    for item_id in item_ids:
        if "blazer" in item_id or "top" in item_id:
            categories.append("top")
        elif "jeans" in item_id or "pants" in item_id:
            categories.append("bottom")
        elif "shoes" in item_id:
            categories.append("shoes")
    
    return list(set(categories))


