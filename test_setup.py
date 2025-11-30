#!/usr/bin/env python3
"""
Quick setup script for AI Interaction Tracking System
Run this to test the tracking system locally
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from interaction_models import Base, UserInteraction, UserStyleProfile, ProductAnalytics, ACTION_WEIGHTS
from profile_builder import rebuild_user_profile
import json

# Create test database
engine = create_engine('sqlite:///test_tracking.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def setup_test_database():
    """Create test database with sample data"""
    print("🔧 Setting up test database...")
    
    db = SessionLocal()
    
    # Create a test user (assuming User model exists)
    # For testing, we'll just use user_id = 1
    test_user_id = 1
    
    # Simulate user interactions
    print("📊 Creating sample interactions...")
    
    interactions = [
        # User searches for jackets
        UserInteraction(
            user_id=test_user_id,
            action_type='search',
            metadata={'query': 'black leather jacket'},
            weight=ACTION_WEIGHTS['search']
        ),
        
        # User views a product
        UserInteraction(
            user_id=test_user_id,
            action_type='view_product',
            item_id='prod_001',
            item_type='product',
            metadata={'brand': 'Zara', 'price': 89.99, 'category': 'jackets'},
            weight=ACTION_WEIGHTS['view_product']
        ),
        
        # User favorites the product
        UserInteraction(
            user_id=test_user_id,
            action_type='favorite_product',
            item_id='prod_001',
            item_type='product',
            metadata={
                'brand': 'Zara',
                'price': 89.99,
                'category': 'jackets',
                'color': 'black',
                'tags': ['minimalist', 'casual']
            },
            weight=ACTION_WEIGHTS['favorite_product']
        ),
        
        # User uploads wardrobe item
        UserInteraction(
            user_id=test_user_id,
            action_type='wardrobe_upload',
            item_id='wardrobe_001',
            item_type='wardrobe',
            metadata={
                'category': 'jeans',
                'color': 'black',
                'brand': 'Levis',
                'size': '28',
                'tags': ['casual', 'denim']
            },
            weight=ACTION_WEIGHTS['wardrobe_upload']
        ),
        
        # User follows a creator
        UserInteraction(
            user_id=test_user_id,
            action_type='follow_creator',
            item_id='creator_001',
            item_type='creator',
            metadata={
                'creator_name': 'StyleInfluencer',
                'creator_style': ['minimalist', 'streetwear', 'casual']
            },
            weight=ACTION_WEIGHTS['follow_creator']
        ),
        
        # User adds item to canvas
        UserInteraction(
            user_id=test_user_id,
            action_type='canvas_add',
            item_id='prod_001',
            item_type='product',
            metadata={'canvas_id': 'canvas_001'},
            weight=ACTION_WEIGHTS['canvas_add']
        ),
        
        # User searches again
        UserInteraction(
            user_id=test_user_id,
            action_type='search',
            metadata={'query': 'white t shirt minimalist'},
            weight=ACTION_WEIGHTS['search']
        ),
        
        # User favorites another product
        UserInteraction(
            user_id=test_user_id,
            action_type='favorite_product',
            item_id='prod_002',
            item_type='product',
            metadata={
                'brand': 'COS',
                'price': 35.00,
                'category': 'tops',
                'color': 'white',
                'tags': ['minimalist', 'basic']
            },
            weight=ACTION_WEIGHTS['favorite_product']
        ),
        
        # User clicks through to retailer (strong purchase intent!)
        UserInteraction(
            user_id=test_user_id,
            action_type='click_to_retailer',
            item_id='prod_002',
            item_type='product',
            metadata={
                'retailer': 'COS',
                'price': 35.00
            },
            weight=ACTION_WEIGHTS['click_to_retailer']
        ),
    ]
    
    for interaction in interactions:
        db.add(interaction)
    
    db.commit()
    print(f"✅ Created {len(interactions)} sample interactions")
    
    # Build user profile
    print("🧠 Building AI profile from interactions...")
    profile = rebuild_user_profile(db, test_user_id)
    
    print("\n" + "="*60)
    print("🎯 USER STYLE PROFILE GENERATED:")
    print("="*60)
    print(f"Favorite Colors: {profile.favorite_colors}")
    print(f"Favorite Brands: {profile.favorite_brands}")
    print(f"Favorite Categories: {profile.favorite_categories}")
    print(f"Style Keywords: {profile.style_keywords}")
    print(f"Size Preferences: {profile.size_preferences}")
    print(f"Budget Range: £{profile.budget_min} - £{profile.budget_max}")
    print(f"Average Price Point: £{profile.avg_price_point:.2f}")
    print(f"Shopping Frequency: {profile.shopping_frequency}")
    print(f"Engagement Score: {profile.engagement_score:.2f}")
    print(f"Followed Creator Styles: {profile.followed_creator_styles}")
    print("="*60)
    
    # Show interaction summary
    print("\n📊 INTERACTION SUMMARY:")
    print("="*60)
    
    action_counts = {}
    total_weight = 0
    
    for interaction in interactions:
        action_counts[interaction.action_type] = action_counts.get(interaction.action_type, 0) + 1
        total_weight += interaction.weight
    
    for action, count in action_counts.items():
        weight = ACTION_WEIGHTS.get(action, 1.0)
        print(f"  {action}: {count}x (weight: {weight})")
    
    print(f"\nTotal Interaction Weight: {total_weight}")
    print("="*60)
    
    # Show product analytics
    print("\n📈 PRODUCT ANALYTICS:")
    print("="*60)
    
    product_analytics = db.query(ProductAnalytics).all()
    for pa in product_analytics:
        print(f"\nProduct: {pa.product_id}")
        print(f"  Views: {pa.view_count}")
        print(f"  Favorites: {pa.favorite_count}")
        print(f"  Canvas Adds: {pa.canvas_add_count}")
        print(f"  Clicks to Retailer: {pa.click_through_count}")
        print(f"  Wishlist→Canvas Rate: {pa.wishlist_to_canvas_rate * 100:.1f}%")
    
    print("="*60)
    
    db.close()
    print("\n✅ Test setup complete!")
    print(f"\n💾 Database created: test_tracking.db")
    print("\n🚀 Next steps:")
    print("1. Review the generated profile above")
    print("2. Integrate the models into your app.py")
    print("3. Start tracking real user interactions!")
    print("4. Watch your AI get smarter over time 🧠")


if __name__ == "__main__":
    print("🎯 AI Interaction Tracking System - Test Setup")
    print("=" * 60)
    setup_test_database()
