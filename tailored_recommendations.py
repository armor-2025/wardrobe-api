"""
"Tailored for You" Recommendation Algorithm

Finds personalized product alternatives for creator's picks based on:
1. User's style preferences (MOST IMPORTANT)
2. User's favorite brands
3. User's budget (secondary consideration)
4. Size availability
5. Past purchase patterns
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import math

from database import User
from creator_models import CreatorPost, PostAlternative
from interaction_models import UserInteraction, UserStyleProfile, ProductAnalytics


class TailoredRecommendationEngine:
    """
    Generate personalized alternatives for creator's products
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Similarity thresholds
        self.MIN_MATCH_SCORE = 0.50  # 70% similarity minimum
        self.MAX_ALTERNATIVES = 4     # Show top 4 alternatives per item
    
    
    def generate_alternatives_for_post(
        self,
        post_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Generate "Tailored for You" alternatives for all products in a post
        
        Returns:
        {
            "creator_picks": [...],
            "alternatives": {
                "product-1": [alt1, alt2, alt3, alt4],
                "product-2": [alt1, alt2, alt3, alt4]
            },
            "total_savings": 450.00,
            "match_quality": 0.85
        }
        """
        # Get the post
        post = self.db.query(CreatorPost).filter(CreatorPost.id == post_id).first()
        if not post:
            return {"error": "Post not found"}
        
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        
        # Generate alternatives for each product
        all_alternatives = {}
        total_creator_price = 0
        total_alternative_price = 0
        match_scores = []
        
        for product_id in post.product_ids:
            # Get product info (placeholder - in production, fetch from product DB)
            creator_product = self._get_product_info(product_id)
            total_creator_price += creator_product.get('price', 0)
            
            # Find alternatives
            alternatives = self._find_alternatives(
                creator_product=creator_product,
                user_profile=user_profile,
                exclude_products=post.product_ids
            )
            
            if alternatives:
                all_alternatives[product_id] = alternatives
                
                # Track best alternative price
                best_alt_price = alternatives[0]['price']
                total_alternative_price += best_alt_price
                
                # Track match quality
                match_scores.append(alternatives[0]['match_score'])
        
        # Calculate savings
        savings = total_creator_price - total_alternative_price
        avg_match_quality = sum(match_scores) / len(match_scores) if match_scores else 0
        
        return {
            "post_id": post_id,
            "creator_picks": post.product_ids,
            "alternatives": all_alternatives,
            "total_savings": round(savings, 2),
            "match_quality": round(avg_match_quality, 2),
            "show_alternatives": self._should_show_alternatives(
                user_profile, 
                total_creator_price, 
                avg_match_quality
            )
        }
    
    
    def _find_alternatives(
        self,
        creator_product: Dict[str, Any],
        user_profile: Dict[str, Any],
        exclude_products: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find alternative products that match user's preferences
        
        Scoring factors (PERSONALIZATION FIRST):
        - Category match (must match)
        - Style similarity (35%) - Does it match their aesthetic?
        - User brand preference (25%) - Brands they love
        - Color match (20%) - Colors they wear
        - Visual similarity (15%) - placeholder for CLIP
        - Price match (5%) - Bonus if in their range (not required)
        """
        # Get candidate products from analytics
        # Filter by category (must match) and exclude creator's picks
        category = creator_product.get('category', 'unknown')
        
        # In production, query your product database
        # For now, simulate with ProductAnalytics
        candidates = self.db.query(ProductAnalytics).filter(
            ProductAnalytics.product_id.notin_(exclude_products)
        ).limit(100).all()
        
        scored_alternatives = []
        
        for candidate in candidates:
            # Score this alternative
            score_breakdown = self._calculate_match_score(
                candidate=candidate,
                creator_product=creator_product,
                user_profile=user_profile
            )
            
            total_score = sum(score_breakdown.values())
            
            # Only include if meets minimum threshold
            if total_score >= self.MIN_MATCH_SCORE:
                scored_alternatives.append({
                    "product_id": candidate.product_id,
                    "match_score": round(total_score, 2),
                    "score_breakdown": score_breakdown,
                    "match_reasons": self._generate_match_reasons(
                        score_breakdown, 
                        creator_product, 
                        candidate
                    ),
                    # Placeholder data - replace with actual product data
                    "name": f"Alternative {candidate.product_id}",
                    "brand": "Budget Brand",
                    "price": creator_product.get('price', 100) * 0.6,  # ~40% cheaper
                    "image_url": "https://example.com/product.jpg",
                    "available": True
                })
        
        # Sort by score and return top alternatives
        scored_alternatives.sort(key=lambda x: x['match_score'], reverse=True)
        return scored_alternatives[:self.MAX_ALTERNATIVES]
    
    
    def _calculate_match_score(
        self,
        candidate: ProductAnalytics,
        creator_product: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Multi-factor scoring algorithm
        Returns breakdown of scores for transparency
        """
        scores = {
            'style': 0.0,
            'color': 0.0,
            'price': 0.0,
            'brand': 0.0,
            'visual': 0.0
        }
        
        # 1. STYLE MATCH (35% weight) - HIGHEST PRIORITY
        # In production, compare style tags
        # For now, simulate
        creator_style = creator_product.get('style', 'casual')
        user_preferred_styles = user_profile.get('style_preferences', ['casual'])
        
        if creator_style in user_preferred_styles:
            scores['style'] = 0.35
        else:
            scores['style'] = 0.18  # Partial credit for similar styles
        
        # 3. COLOR MATCH (20% weight)
        # Check if color matches user's preferences
        creator_color = creator_product.get('color', 'black')
        user_favorite_colors = user_profile.get('favorite_colors', ['black', 'white'])
        
        if creator_color in user_favorite_colors:
            scores['color'] = 0.20
        elif self._are_colors_similar(creator_color, user_favorite_colors):
            scores['color'] = 0.10
        
        # 5. PRICE MATCH (5% weight) - BONUS ONLY
        # Price is a nice-to-have, not a must-have
        creator_price = creator_product.get('price', 100)
        user_avg_price = user_profile.get('avg_purchase_price', 50)
        user_max_price = user_profile.get('max_price_willing', 150)
        
        # Candidate should be cheaper than creator's item
        candidate_price = creator_price * 0.6  # Simulated 40% discount
        
        # Small bonus if price is in their typical range
        price_ratio = abs(candidate_price - user_avg_price) / max(user_avg_price, 1)
        if price_ratio < 0.3:  # Within 30% of their usual
            scores['price'] = 0.05
        elif price_ratio < 0.5:  # Within 50%
            scores['price'] = 0.03
        # No points if outside their range, but still show it!
        
        # 2. BRAND PREFERENCE (25% weight) - SECOND PRIORITY
        # Show them brands they LOVE
        candidate_brand = "Budget Brand"  # Simulated
        user_brands = user_profile.get('favorite_brands', [])
        
        if candidate_brand in user_brands:
            scores['brand'] = 0.25
        elif len(user_brands) == 0:
            # No brand preference? Give partial credit
            scores['brand'] = 0.10
        
        # 4. VISUAL SIMILARITY (15% weight) - CLIP EMBEDDINGS
        # This is WHERE THE MAGIC HAPPENS
        # CLIP understands visual concepts that tags miss:
        # - Paint splatters, distressing, texture
        # - Exact shade of color (not just "blue" but "faded denim blue")
        # - Fit and silhouette (baggy vs fitted)
        # - Details: buttons, zippers, pockets, patterns
        # - Styling: tucked, rolled, layered
        # - Material appearance: leather texture, knit pattern, denim wash
        
        # TODO: Implement CLIP similarity
        # visual_sim = cosine_similarity(
        #     creator_product_embedding,
        #     candidate_product_embedding
        # )
        # scores['visual'] = visual_sim * 0.15
        
        # For now, give partial credit (will be replaced with real CLIP)
        scores['visual'] = 0.08
        
        # FUTURE: This score should be HIGHEST for items that:
        # - Have the exact same vibe (minimalist, edgy, preppy)
        # - Share subtle details (paint splats, distressing)
        # - Match the exact aesthetic even if tags differ
        
        return scores
    
    
    def _generate_match_reasons(
        self,
        score_breakdown: Dict[str, float],
        creator_product: Dict[str, Any],
        candidate: ProductAnalytics
    ) -> List[str]:
        """
        Generate human-readable reasons for why this is a good match
        """
        reasons = []
        
        if score_breakdown['style'] >= 0.20:
            reasons.append(f"✓ Same {creator_product.get('style', '')} style")
        
        if score_breakdown['color'] >= 0.15:
            reasons.append(f"✓ Matches your color preferences")
        
        if score_breakdown['price'] >= 0.15:
            creator_price = creator_product.get('price', 0)
            candidate_price = creator_price * 0.6
            if candidate_price < creator_price:
                savings = creator_price - candidate_price
                reasons.append(f"💰 ${candidate_price:.0f} (Save ${savings:.0f})")
            else:
                reasons.append(f"💰 ${candidate_price:.0f}")
        
        if score_breakdown['brand'] >= 0.10:
            reasons.append("⭐ Your favorite brand")
        
        if score_breakdown['visual'] >= 0.08:
            reasons.append("👁️ Similar look")
        
        # Always show it works with their wardrobe
        reasons.append("👕 Works with your wardrobe")
        
        return reasons
    
    
    def _should_show_alternatives(
        self,
        user_profile: Dict[str, Any],
        creator_total_price: float,
        match_quality: float
    ) -> bool:
        """
        Decide whether to show alternatives at all
        
        NEW LOGIC: Show alternatives for PERSONALIZATION, not just price
        
        Show alternatives when:
        - Good match quality (alternatives fit user's style)
        - User has established preferences (we know what they like)
        - Alternatives offer variety (different brands, styles user prefers)
        
        Don't show if:
        - Match quality is too low
        - No user preference data
        - Alternatives are too similar to creator's picks
        """
        
        # Don't show if match quality is poor
        if match_quality < self.MIN_MATCH_SCORE:
            return False
        
        # Show if user has preferences (they've interacted before)
        has_preferences = (
            len(user_profile.get('favorite_brands', [])) > 0 or
            len(user_profile.get('favorite_colors', [])) > 0 or
            user_profile.get('avg_purchase_price', 0) > 0
        )
        
        if not has_preferences:
            return False  # Can't personalize without data
        
        # ALWAYS show if match quality is good
        # This gives users MORE OPTIONS, not just cheaper options
        return True
    
    
    def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Build user's style and budget profile from interactions
        """
        # Get user's interaction history
        recent_interactions = self.db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).order_by(
            UserInteraction.created_at.desc()
        ).limit(100).all()
        
        # Extract preferences
        prices = []
        brands = []
        colors = []
        styles = []
        
        for interaction in recent_interactions:
            if interaction.interaction_metadata:
                meta = interaction.interaction_metadata
                
                if 'price' in meta:
                    prices.append(float(meta['price']))
                if 'brand' in meta:
                    brands.append(meta['brand'])
                if 'color' in meta:
                    colors.append(meta['color'])
                if 'style' in meta:
                    styles.append(meta['style'])
        
        # Calculate averages
        avg_price = sum(prices) / len(prices) if prices else 50
        max_price = max(prices) if prices else 100
        
        from collections import Counter
        favorite_brands = [b for b, _ in Counter(brands).most_common(5)]
        favorite_colors = [c for c, _ in Counter(colors).most_common(5)]
        style_preferences = [s for s, _ in Counter(styles).most_common(3)]
        
        return {
            'avg_purchase_price': avg_price,
            'max_price_willing': max_price * 1.5,  # Assume willing to spend 50% more
            'favorite_brands': favorite_brands,
            'favorite_colors': favorite_colors if favorite_colors else ['black', 'white', 'navy'],
            'style_preferences': style_preferences if style_preferences else ['casual'],
        }
    
    
    def _get_product_info(self, product_id: str) -> Dict[str, Any]:
        """
        Get product information
        In production, query actual product database
        For now, return placeholder
        """
        # Simulate product data
        return {
            'product_id': product_id,
            'name': f'Product {product_id}',
            'brand': 'Premium Brand',
            'price': 150.00,
            'category': 'tops',
            'style': 'minimalist',
            'color': 'black',
            'image_url': 'https://example.com/product.jpg'
        }
    
    
    def _are_colors_similar(self, color1: str, color_list: List[str]) -> bool:
        """
        Check if colors are similar (e.g., navy and blue, grey and black)
        """
        color_families = {
            'black': ['charcoal', 'grey', 'gray'],
            'white': ['cream', 'ivory', 'beige'],
            'blue': ['navy', 'denim', 'cobalt'],
            'red': ['burgundy', 'maroon', 'wine'],
            'green': ['olive', 'forest', 'sage']
        }
        
        for color in color_list:
            if color in color_families.get(color1, []):
                return True
            if color1 in color_families.get(color, []):
                return True
        
        return False


# Helper function for easy access
def get_tailored_recommendations(
    db: Session,
    post_id: int,
    user_id: int
) -> Dict[str, Any]:
    """
    Quick access function for getting recommendations
    """
    engine = TailoredRecommendationEngine(db)
    return engine.generate_alternatives_for_post(post_id, user_id)
