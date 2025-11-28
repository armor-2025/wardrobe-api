"""
Canvas/Outfit Builder Models
Users create outfits by combining items on a digital canvas
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Canvas(Base):
    """
    User's outfit creation canvas
    A canvas contains multiple items arranged together
    """
    __tablename__ = "canvases"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Canvas Info
    name = Column(String(200))  # "Work Outfit #1", "Date Night Look"
    description = Column(Text)
    
    # Items on canvas (product IDs)
    items = Column(JSON, default=list)  # ["blazer-123", "jeans-456", "shoes-789"]
    
    # Item positions (for visual layout)
    item_positions = Column(JSON, default=dict)  # {"blazer-123": {"x": 0.5, "y": 0.3}}
    
    # Metadata
    occasion = Column(String(50))  # work, casual, formal, date
    season = Column(String(20))    # spring, summer, fall, winter
    tags = Column(JSON, default=list)  # ["minimalist", "professional"]
    
    # Visual
    thumbnail_url = Column(String(500))  # Screenshot/render of the canvas
    background_color = Column(String(20), default="#FFFFFF")
    
    # Stats
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)  # How many others saved this outfit
    
    # Privacy
    is_public = Column(Boolean, default=False)  # Can others see this?
    is_featured = Column(Boolean, default=False)  # Featured by platform
    
    # VTO Integration (Premium)
    vto_generated = Column(Boolean, default=False)
    vto_image_url = Column(String(500))  # AI-generated try-on image
    vto_model_id = Column(String(100))   # Which model/photo was used
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    likes = relationship("CanvasLike", back_populates="canvas", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Canvas {self.id} - {self.name}>"


class CanvasLike(Base):
    """
    Users can like other people's outfit canvases
    """
    __tablename__ = "canvas_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    canvas = relationship("Canvas", back_populates="likes")
    
    def __repr__(self):
        return f"<CanvasLike user:{self.user_id} canvas:{self.canvas_id}>"


class OutfitSuggestion(Base):
    """
    AI-generated outfit suggestions
    "Complete this outfit" recommendations
    """
    __tablename__ = "outfit_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.id"), nullable=False, index=True)
    
    # What's missing?
    missing_category = Column(String(50))  # "shoes", "outerwear", "accessories"
    
    # Suggested items
    suggested_items = Column(JSON, default=list)  # List of product IDs
    
    # Why this suggestion?
    suggestion_reason = Column(Text)  # "These shoes complete your look"
    match_score = Column(Float)
    
    # Performance
    shown_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    added_count = Column(Integer, default=0)  # How many times suggestion was used
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<OutfitSuggestion canvas:{self.canvas_id} category:{self.missing_category}>"


class CanvasTemplate(Base):
    """
    Pre-made outfit templates for inspiration
    "Start with this look and customize"
    """
    __tablename__ = "canvas_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, nullable=True)  # References creators.id (optional)  # Optional - from creator
    
    # Template Info
    name = Column(String(200))
    description = Column(Text)
    thumbnail_url = Column(String(500))
    
    # Style
    style_tags = Column(JSON, default=list)  # ["minimalist", "workwear"]
    occasion = Column(String(50))
    season = Column(String(20))
    
    # Items (placeholders)
    item_categories = Column(JSON, default=list)  # ["top", "bottom", "shoes"]
    
    # Stats
    use_count = Column(Integer, default=0)  # How many people used this template
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CanvasTemplate {self.id} - {self.name}>"
