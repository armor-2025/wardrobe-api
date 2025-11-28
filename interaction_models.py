# interaction_models.py
# Add these models to your database.py file

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from database import Base

class UserInteraction(Base):
    """
    Tracks every user action for AI personalization.
    This is the foundation for your recommendation engine.
    """
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Interaction type
    action_type = Column(String, nullable=False, index=True)  # 'favorite', 'search', 'view', 'click', 'canvas_add', etc.
    
    # Context
    item_id = Column(String, nullable=True, index=True)  # Product ID, post ID, creator ID, etc.
    item_type = Column(String, nullable=True)  # 'product', 'post', 'creator', 'outfit'
    
    # Metadata
    interaction_metadata = Column(JSON, nullable=True)  # Flexible field for action-specific data
    
    # Weighting (for AI scoring)
    weight = Column(Float, default=1.0)  # How important is this action?
    
    # Source tracking
    source = Column(String, nullable=True)  # 'feed', 'search', 'creator_profile', 'wishlist', etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Add indexes for common queries
    __table_args__ = (
        Index('idx_user_action_time', 'user_id', 'action_type', 'created_at'),
        Index('idx_item_type', 'item_type', 'item_id'),
    )


class UserStyleProfile(Base):
    """
    Aggregated user preferences - built from interactions.
    Updated nightly by background job.
    """
    __tablename__ = "user_style_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    
    # Style attributes (learned from interactions)
    favorite_colors = Column(JSON, default=list)  # ["black", "white", "beige"]
    favorite_brands = Column(JSON, default=list)  # ["Zara", "ASOS", "COS"]
    favorite_categories = Column(JSON, default=list)  # ["dresses", "jackets"]
    style_keywords = Column(JSON, default=list)  # ["minimalist", "streetwear", "vintage"]
    
    # Size preferences
    size_preferences = Column(JSON, default=dict)  # {"tops": "M", "bottoms": "28", "shoes": "9"}
    
    # Budget insights
    avg_price_point = Column(Float, nullable=True)  # Average price of favorited items
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    
    # Behavioral patterns
    shopping_frequency = Column(String, nullable=True)  # "high", "medium", "low"
    favorite_shopping_times = Column(JSON, default=list)  # ["evening", "weekend"]
    
    # Social behavior
    followed_creator_styles = Column(JSON, default=list)  # Style tags from followed creators
    engagement_score = Column(Float, default=0.0)  # Overall activity level
    
    # Avoided items (learned from never-favorited)
    avoided_categories = Column(JSON, default=list)
    avoided_colors = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)  # When profile was last rebuilt


class ProductAnalytics(Base):
    """
    Aggregate product performance - valuable for retailers!
    Updated daily.
    """
    __tablename__ = "product_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, nullable=False, index=True)
    
    # Engagement metrics
    view_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    canvas_add_count = Column(Integer, default=0)
    click_through_count = Column(Integer, default=0)  # Clicks to retailer
    
    # Conversion signals
    wishlist_to_canvas_rate = Column(Float, default=0.0)  # High = strong purchase intent
    avg_time_spent = Column(Float, default=0.0)  # Seconds
    
    # Demographics (who's interested?)
    interested_demographics = Column(JSON, default=dict)  # {"age_18_24": 45, "age_25_34": 55}
    
    # Price tracking
    current_price = Column(Float, nullable=True)
    price_history = Column(JSON, default=list)  # [{"date": "2025-10-31", "price": 49.99}]
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_product_engagement', 'favorite_count', 'canvas_add_count'),
    )


# Action weights for AI scoring
# INTENT-BASED WEIGHTING (aligned with recommendation engine)
ACTION_WEIGHTS = {
    # === HIGH BUYING INTENT ===
    'canvas_add': 20,              # Virtual try-on - about to buy!
    'click_to_retailer': 18,       # Shopping cart - on retailer site
    'favorite_product': 15,        # Clear want - "I want this item"
    'favorite_from_creator': 16,   # Want + trust signal
    
    # === LEARNING/TRACKING (not for re-recommendation) ===
    'purchase_complete': 50,       # Track for learning, but suppress item
    'wardrobe_upload': 20,         # Owned item - learn style
    'outfit_create': 30,           # Style preferences
    'follow_creator': 15,          # Discovery path
    
    # === DISCOVERY SIGNALS ===
    'search': 17,                  # 🔍 VERY HIGH - Active, specific intent!
    'view_product': 3,             # Browsing
    'view_post': 2,                # Scrolling
    'share': 12,                   # Engagement
    'comment': 8,                  # Engagement
}
