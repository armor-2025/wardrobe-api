"""
Seed Database with Test Creator Posts
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, User
from creator_models import CreatorPost, PostProduct
import uuid
from datetime import datetime, timedelta

def seed_creators():
    db = SessionLocal()
    
    print("🌱 Seeding creator posts...")
    
    # Get existing user (don't create new one)
    creator = db.query(User).first()
    
    if not creator:
        print("❌ No users found in database!")
        print("Please create a user first or use an existing one")
        db.close()
        return
    
    creator_id = str(creator.id)
    print(f"✅ Using existing user as creator: {creator.email}")
    
    # Sample product data
    sample_products = [
        {
            "name": "Zara Oversized Blazer",
            "brand": "Zara",
            "price": "$89.99",
            "image": "https://via.placeholder.com/300x400?text=Blazer",
            "link": "https://ltk.com/product/zara-blazer"
        },
        {
            "name": "Levi's 501 Jeans",
            "brand": "Levi's",
            "price": "$98.00",
            "image": "https://via.placeholder.com/300x400?text=Jeans",
            "link": "https://ltk.com/product/levis-jeans"
        },
        {
            "name": "Nike Air Force 1",
            "brand": "Nike",
            "price": "$110.00",
            "image": "https://via.placeholder.com/300x400?text=Sneakers",
            "link": "https://ltk.com/product/nike-af1"
        },
        {
            "name": "H&M Basic Tee",
            "brand": "H&M",
            "price": "$12.99",
            "image": "https://via.placeholder.com/300x400?text=Tee",
            "link": "https://ltk.com/product/hm-tee"
        },
        {
            "name": "Mango Crossbody Bag",
            "brand": "Mango",
            "price": "$45.99",
            "image": "https://via.placeholder.com/300x400?text=Bag",
            "link": "https://ltk.com/product/mango-bag"
        }
    ]
    
    # Create 15 test posts
    for i in range(15):
        post_id = str(uuid.uuid4())
        
        # Vary product count
        product_count = (i % 5) + 3  # 3-7 products per post
        
        # Create post
        post = CreatorPost(
            id=post_id,
            creator_id=creator_id,
            image_url=f"https://via.placeholder.com/600x800?text=Post+{i+1}",
            video_url=None if i % 3 != 0 else f"https://via.placeholder.com/video{i+1}.mp4",
            is_video=(i % 3 == 0),
            product_count=product_count,
            caption=f"Fall outfit inspo #{i+1} 🍂✨ #fashion #ootd #style",
            created_at=datetime.utcnow() - timedelta(days=i, hours=i),
            likes_count=150 + (i * 20),
            views_count=1000 + (i * 50)
        )
        
        db.add(post)
        
        # Add products to post
        for j in range(product_count):
            product_data = sample_products[j % len(sample_products)]
            
            product = PostProduct(
                post_id=post_id,
                product_id=str(uuid.uuid4()),
                product_name=product_data["name"],
                product_brand=product_data["brand"],
                product_image=product_data["image"],
                product_price=product_data["price"],
                affiliate_link=product_data["link"],
                commission_rate=0.10,
                position_x=0.2 + (j * 0.15),
                position_y=0.3 + (j * 0.1)
            )
            
            db.add(product)
        
        print(f"  ✅ Created post {i+1} with {product_count} products")
    
    db.commit()
    
    print(f"\n🎉 Successfully created 15 posts for creator!")
    print(f"\n📋 Creator Info:")
    print(f"   ID: {creator_id}")
    print(f"   Email: {creator.email}")
    print(f"\n🔗 Test these endpoints:")
    print(f"   GET http://localhost:8012/creators/{creator_id}")
    print(f"   GET http://localhost:8012/creators/{creator_id}/posts")
    
    db.close()

if __name__ == "__main__":
    seed_creators()
