"""
Creator Posts System - Database Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class CreatorPost(Base):
    """Creator posts (images/videos with tagged products)"""
    __tablename__ = "creator_posts"
    
    id = Column(String, primary_key=True)
    creator_id = Column(String, ForeignKey('users.id'), nullable=False)
    image_url = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    is_video = Column(Boolean, default=False)
    product_count = Column(Integer, default=0)
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    
    # No back_populates - one-way relationship only
    products = relationship("PostProduct", back_populates="post", cascade="all, delete-orphan")


class PostProduct(Base):
    """Products tagged in creator posts"""
    __tablename__ = "post_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, ForeignKey('creator_posts.id', ondelete='CASCADE'))
    product_id = Column(String)
    product_name = Column(String)
    product_brand = Column(String, nullable=True)
    product_image = Column(String)
    product_price = Column(String)
    affiliate_link = Column(String)
    commission_rate = Column(Float, default=0.10)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    
    post = relationship("CreatorPost", back_populates="products")
