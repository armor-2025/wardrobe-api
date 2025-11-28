"""
Item Extraction Endpoints
Upload outfit photo → Get individual items
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from database import get_db, User
from auth_service import get_current_user
from item_extraction_smart import SmartExtractor as ItemExtractor, create_wardrobe_items_from_extraction

router = APIRouter(prefix="/extract", tags=["extraction"])


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

class ExtractionResult(BaseModel):
    original_photo: str
    items_detected: int
    items: List[Dict[str, Any]]


class ItemConfirmation(BaseModel):
    item_id: str
    confirmed: bool
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.post("/outfit-photo", response_model=ExtractionResult)
async def extract_items_from_outfit(
    file: UploadFile = File(...),
    upload_type: str = Form("auto"),
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Upload a full outfit photo and extract individual items
    
    Like ALTA app:
    1. User uploads photo of themselves in outfit
    2. AI detects each clothing item
    3. Segments each item (removes background)
    4. Returns PNG of each item for wardrobe
    
    Example:
    - Upload: Photo of you in t-shirt + jeans + shoes
    - Returns: 3 separate PNGs (shirt, jeans, shoes)
    """
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read image data
    image_data = await file.read()
    
    if len(image_data) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    # Extract items using AI
    extractor = ItemExtractor()
    results = await extractor.extract_items_from_photo(
        image_data=image_data,
        user_id=current_user.id,
        upload_type=upload_type
    )
    
    # Track this upload
    from interaction_models import UserInteraction
    interaction = UserInteraction(
        user_id=current_user.id,
        action_type="outfit_photo_upload",
        item_id="outfit-photo",
        item_type="photo",
        weight=10.0,
        interaction_metadata={
            "items_detected": results["items_detected"],
            "filename": file.filename
        }
    )
    db.add(interaction)
    db.commit()
    
    return results


@router.post("/confirm-items")
async def confirm_extracted_items(
    items: List[ItemConfirmation],
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Confirm which extracted items to add to wardrobe
    
    User reviews AI-detected items and:
    - Confirms/rejects each item
    - Adds name/brand if desired
    - Corrects category if wrong
    
    Confirmed items → Added to wardrobe
    """
    
    confirmed_items = []
    
    for item in items:
        if item.confirmed:
            # Create wardrobe item
            # In production, save to actual wardrobe table
            
            confirmed_items.append({
                "item_id": item.item_id,
                "name": item.name or f"Item {item.item_id}",
                "brand": item.brand or "Unknown",
                "category": item.category,
                "status": "added_to_wardrobe"
            })
            
            # Track confirmation
            from interaction_models import UserInteraction
            interaction = UserInteraction(
                user_id=current_user.id,
                action_type="wardrobe_add",
                item_id=item.item_id,
                item_type="product",
                weight=15.0,  # User owns this item!
                interaction_metadata={
                    "source": "outfit_extraction",
                    "name": item.name,
                    "brand": item.brand,
                    "category": item.category
                }
            )
            db.add(interaction)
    
    db.commit()
    
    return {
        "confirmed_count": len(confirmed_items),
        "items": confirmed_items,
        "message": f"Added {len(confirmed_items)} items to your wardrobe"
    }


@router.post("/batch-upload")
async def batch_upload_outfits(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Upload multiple outfit photos at once
    
    Great for:
    - Onboarding (upload all your favorite outfits)
    - Vacation packing (upload outfits you plan to bring)
    - Inspiration (save outfit photos from social media)
    """
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 photos at once")
    
    extractor = ItemExtractor()
    all_results = []
    
    for file in files:
        if not file.content_type.startswith('image/'):
            continue  # Skip non-images
        
        image_data = await file.read()
        
        results = await extractor.extract_items_from_photo(
            image_data=image_data,
            user_id=current_user.id
        )
        
        all_results.append({
            "filename": file.filename,
            "items_detected": results["items_detected"],
            "items": results["items"]
        })
    
    return {
        "photos_processed": len(all_results),
        "total_items_detected": sum(r["items_detected"] for r in all_results),
        "results": all_results
    }


@router.get("/extraction-stats")
async def get_extraction_stats(
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get stats on user's item extractions
    
    Shows:
    - Total outfit photos uploaded
    - Total items extracted
    - Items added to wardrobe
    - Success rate
    """
    from interaction_models import UserInteraction
    
    # Count outfit uploads
    uploads = db.query(UserInteraction).filter(
        UserInteraction.user_id == current_user.id,
        UserInteraction.action_type == "outfit_photo_upload"
    ).count()
    
    # Count items added from extraction
    wardrobe_adds = db.query(UserInteraction).filter(
        UserInteraction.user_id == current_user.id,
        UserInteraction.action_type == "wardrobe_add",
        UserInteraction.interaction_metadata.contains({"source": "outfit_extraction"})
    ).count()
    
    return {
        "outfit_photos_uploaded": uploads,
        "items_extracted_and_added": wardrobe_adds,
        "avg_items_per_photo": round(wardrobe_adds / uploads, 1) if uploads > 0 else 0
    }
