"""
Creator Posts API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
import shutil

from database import get_db, User
from creator_models import CreatorPost, PostProduct

router = APIRouter(prefix="/creators", tags=["creators"])


# ==================== RESPONSE SCHEMAS ====================

class PostProductResponse(BaseModel):
    id: int
    product_id: str
    product_name: str
    product_brand: Optional[str]
    product_image: str
    product_price: str
    affiliate_link: str
    commission_rate: float
    position_x: Optional[float]
    position_y: Optional[float]
    
    class Config:
        from_attributes = True


class CreatorPostResponse(BaseModel):
    id: str
    creator_id: str
    image_url: str
    video_url: Optional[str]
    is_video: bool
    product_count: int
    caption: Optional[str]
    created_at: datetime
    likes_count: int
    views_count: int
    products: List[PostProductResponse] = []
    
    class Config:
        from_attributes = True


class CreatorProfileResponse(BaseModel):
    id: str
    username: str
    display_name: str
    profile_image_url: str
    bio: str
    followers_count: int
    posts_count: int
    
    class Config:
        from_attributes = True


class PostsListResponse(BaseModel):
    posts: List[CreatorPostResponse]
    total_count: int
    has_more: bool


# ==================== ENDPOINTS ====================

@router.get("/{creator_id}/posts", response_model=PostsListResponse)
def get_creator_posts(
    creator_id: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get posts for a specific creator"""
    total_count = db.query(CreatorPost).filter(
        CreatorPost.creator_id == creator_id
    ).count()
    
    posts = db.query(CreatorPost).filter(
        CreatorPost.creator_id == creator_id
    ).order_by(
        CreatorPost.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    has_more = (offset + limit) < total_count
    
    return {
        "posts": posts,
        "total_count": total_count,
        "has_more": has_more
    }


@router.get("/{creator_id}", response_model=CreatorProfileResponse)
def get_creator_profile(
    creator_id: str,
    db: Session = Depends(get_db)
):
    """Get creator profile information"""
    creator = db.query(User).filter(User.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    posts_count = db.query(CreatorPost).filter(
        CreatorPost.creator_id == creator_id
    ).count()
    
    return {
        "id": str(creator.id),
        "username": creator.email.split('@')[0] if creator.email else "unknown",
        "display_name": creator.name or "Unknown Creator",
        "profile_image_url": getattr(creator, 'profile_image_url', '') or "https://via.placeholder.com/150",
        "bio": getattr(creator, 'bio', '') or "Fashion creator",
        "followers_count": getattr(creator, 'followers_count', 0) or 0,
        "posts_count": posts_count
    }


@router.post("/{creator_id}/posts")
def create_post(
    creator_id: str,
    image_url: str = Form(...),
    product_count: int = Form(0),
    video_url: Optional[str] = Form(None),
    is_video: bool = Form(False),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new creator post"""
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    post = CreatorPost(
        id=str(uuid.uuid4()),
        creator_id=creator_id,
        image_url=image_url,
        video_url=video_url,
        is_video=is_video,
        product_count=product_count,
        caption=caption,
        created_at=datetime.utcnow()
    )
    
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return {
        "id": post.id,
        "message": "Post created successfully"
    }
