# profile_builder.py
# Background service to build user profiles from interactions

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from collections import Counter
import json

from interaction_models import UserInteraction, UserStyleProfile


def rebuild_user_profile(db: Session, user_id: int):
    """
    Analyze all user interactions and build a comprehensive style profile.
    This should run nightly for all users via background job.
    """
    
    # Get user's profile or create new one
    profile = db.query(UserStyleProfile).filter(
        UserStyleProfile.user_id == user_id
    ).first()
    
    if not profile:
        profile = UserStyleProfile(user_id=user_id)
        db.add(profile)
    
    # Analyze interactions from last 90 days (recent behavior matters most)
    cutoff_date = datetime.now() - timedelta(days=90)
    interactions = db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id,
        UserInteraction.created_at >= cutoff_date
    ).all()
    
    if not interactions:
        db.commit()
        return profile
    
    # ============================================
    # EXTRACT FAVORITE COLORS
    # ============================================
    colors = []
    for interaction in interactions:
        if interaction.action_type in ['favorite_product', 'wardrobe_upload', 'canvas_add']:
            metadata = interaction.metadata or {}
            if 'color' in metadata:
                # Weight by interaction importance
                colors.extend([metadata['color']] * int(interaction.weight))
            if 'colors' in metadata:  # Multiple colors
                colors.extend(metadata['colors'] * int(interaction.weight))
    
    if colors:
        color_counts = Counter(colors)
        profile.favorite_colors = [color for color, _ in color_counts.most_common(10)]
    
    
    # ============================================
    # EXTRACT FAVORITE BRANDS
    # ============================================
    brands = []
    for interaction in interactions:
        if interaction.action_type in ['favorite_product', 'click_to_retailer', 'purchase_complete']:
            metadata = interaction.metadata or {}
            if 'brand' in metadata:
                brands.extend([metadata['brand']] * int(interaction.weight))
    
    if brands:
        brand_counts = Counter(brands)
        profile.favorite_brands = [brand for brand, _ in brand_counts.most_common(10)]
    
    
    # ============================================
    # EXTRACT FAVORITE CATEGORIES
    # ============================================
    categories = []
    for interaction in interactions:
        if interaction.action_type in ['favorite_product', 'wardrobe_upload', 'canvas_add']:
            metadata = interaction.metadata or {}
            if 'category' in metadata:
                categories.extend([metadata['category']] * int(interaction.weight))
    
    if categories:
        category_counts = Counter(categories)
        profile.favorite_categories = [cat for cat, _ in category_counts.most_common(10)]
    
    
    # ============================================
    # EXTRACT STYLE KEYWORDS
    # ============================================
    keywords = []
    for interaction in interactions:
        metadata = interaction.metadata or {}
        
        # From searches
        if interaction.action_type == 'search' and 'query' in metadata:
            # Extract style words from search queries
            query_words = metadata['query'].lower().split()
            style_words = [w for w in query_words if w in STYLE_KEYWORDS]
            keywords.extend(style_words)
        
        # From tagged items
        if 'tags' in metadata:
            keywords.extend(metadata['tags'])
        
        # From followed creators
        if interaction.action_type == 'follow_creator' and 'creator_style' in metadata:
            keywords.extend(metadata['creator_style'])
    
    if keywords:
        keyword_counts = Counter(keywords)
        profile.style_keywords = [kw for kw, _ in keyword_counts.most_common(15)]
    
    
    # ============================================
    # EXTRACT SIZE PREFERENCES
    # ============================================
    sizes = {}
    for interaction in interactions:
        metadata = interaction.metadata or {}
        if 'size' in metadata and 'category' in metadata:
            category = metadata['category']
            size = metadata['size']
            if category not in sizes:
                sizes[category] = []
            sizes[category].append(size)
    
    # Most common size per category
    size_prefs = {}
    for category, size_list in sizes.items():
        size_counts = Counter(size_list)
        size_prefs[category] = size_counts.most_common(1)[0][0]
    
    profile.size_preferences = size_prefs
    
    
    # ============================================
    # CALCULATE BUDGET RANGE
    # ============================================
    prices = []
    for interaction in interactions:
        if interaction.action_type in ['favorite_product', 'click_to_retailer']:
            metadata = interaction.metadata or {}
            if 'price' in metadata:
                try:
                    price = float(metadata['price'])
                    prices.append(price)
                except:
                    pass
    
    if prices:
        profile.avg_price_point = sum(prices) / len(prices)
        profile.budget_min = min(prices)
        profile.budget_max = max(prices)
    
    
    # ============================================
    # CALCULATE ENGAGEMENT SCORE
    # ============================================
    total_weight = sum(i.weight for i in interactions)
    days_active = (datetime.now() - min(i.created_at for i in interactions)).days or 1
    profile.engagement_score = total_weight / days_active  # Average daily engagement
    
    
    # ============================================
    # EXTRACT FOLLOWED CREATOR STYLES
    # ============================================
    creator_styles = []
    for interaction in interactions:
        if interaction.action_type == 'follow_creator':
            metadata = interaction.metadata or {}
            if 'creator_style' in metadata:
                creator_styles.extend(metadata['creator_style'])
    
    if creator_styles:
        style_counts = Counter(creator_styles)
        profile.followed_creator_styles = [style for style, _ in style_counts.most_common(10)]
    
    
    # ============================================
    # IDENTIFY AVOIDED ITEMS
    # ============================================
    # What categories/colors appear in searches but NEVER get favorited?
    searched_items = set()
    favorited_items = set()
    
    for interaction in interactions:
        metadata = interaction.metadata or {}
        
        if interaction.action_type == 'search' and 'category' in metadata:
            searched_items.add(metadata['category'])
        
        if interaction.action_type in ['favorite_product', 'canvas_add'] and 'category' in metadata:
            favorited_items.add(metadata['category'])
    
    avoided = searched_items - favorited_items
    profile.avoided_categories = list(avoided)
    
    
    # ============================================
    # DETERMINE SHOPPING FREQUENCY
    # ============================================
    favorite_actions = [i for i in interactions if i.action_type in ['favorite_product', 'click_to_retailer']]
    if len(favorite_actions) > 30:
        profile.shopping_frequency = "high"
    elif len(favorite_actions) > 10:
        profile.shopping_frequency = "medium"
    else:
        profile.shopping_frequency = "low"
    
    
    # Update timestamp
    profile.last_analyzed_at = datetime.now()
    profile.updated_at = datetime.now()
    
    db.commit()
    db.refresh(profile)
    
    return profile


# ============================================
# STYLE KEYWORD DICTIONARY
# ============================================
STYLE_KEYWORDS = {
    # Core styles
    'minimalist', 'minimal', 'classic', 'elegant', 'sophisticated',
    'casual', 'streetwear', 'urban', 'sporty', 'athletic',
    'bohemian', 'boho', 'hippie', 'vintage', 'retro',
    'preppy', 'prepster', 'ivy', 'collegiate',
    'edgy', 'punk', 'grunge', 'alternative',
    'romantic', 'feminine', 'girly', 'pretty',
    'masculine', 'tomboy', 'androgynous',
    'professional', 'business', 'corporate', 'formal',
    'artsy', 'creative', 'eclectic',
    
    # Fashion movements
    'y2k', '90s', '80s', '70s', 'mod',
    'cottagecore', 'dark academia', 'light academia',
    'coastal', 'coastal grandmother', 'clean girl',
    'quiet luxury', 'old money', 'stealth wealth',
    'goth', 'emo', 'scene',
    
    # Aesthetics
    'monochrome', 'colorful', 'neutral', 'earthy',
    'luxury', 'designer', 'high end',
    'affordable', 'budget', 'cheap chic',
    'sustainable', 'ethical', 'eco friendly',
    'secondhand', 'vintage', 'thrifted',
    
    # Vibes
    'trendy', 'fashion forward', 'cutting edge',
    'timeless', 'classic', 'staple',
    'comfortable', 'cozy', 'relaxed',
    'statement', 'bold', 'dramatic',
    'understated', 'subtle', 'quiet',
}


# ============================================
# BATCH PROFILE REBUILD (For Nightly Job)
# ============================================

def rebuild_all_profiles(db: Session, batch_size: int = 100):
    """
    Rebuild profiles for all active users.
    Run this as a nightly background job.
    """
    from database import User
    
    # Get users who have interacted in last 30 days
    cutoff = datetime.now() - timedelta(days=30)
    active_user_ids = db.query(UserInteraction.user_id).filter(
        UserInteraction.created_at >= cutoff
    ).distinct().all()
    
    active_user_ids = [uid[0] for uid in active_user_ids]
    
    print(f"Rebuilding profiles for {len(active_user_ids)} active users...")
    
    for i, user_id in enumerate(active_user_ids):
        try:
            rebuild_user_profile(db, user_id)
            
            if (i + 1) % batch_size == 0:
                print(f"Processed {i + 1}/{len(active_user_ids)} users")
                db.commit()  # Commit in batches
                
        except Exception as e:
            print(f"Error rebuilding profile for user {user_id}: {e}")
            continue
    
    db.commit()
    print("Profile rebuild complete!")


if __name__ == "__main__":
    # For testing: rebuild a single user's profile
    from database import SessionLocal
    
    db = SessionLocal()
    user_id = 1  # Test user
    
    profile = rebuild_user_profile(db, user_id)
    print(f"Profile rebuilt for user {user_id}")
    print(f"Favorite colors: {profile.favorite_colors}")
    print(f"Favorite brands: {profile.favorite_brands}")
    print(f"Style keywords: {profile.style_keywords}")
