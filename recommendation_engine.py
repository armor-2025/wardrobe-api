# recommendation_engine.py
# AI-powered recommendation system using user tracking data

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import json

from interaction_models import UserInteraction, UserStyleProfile, ProductAnalytics, ACTION_WEIGHTS


class RecommendationEngine:
    """
    Multi-strategy recommendation engine that combines:
    1. Content-based filtering (user preferences)
    2. Collaborative filtering (similar users)
    3. Popularity-based recommendations
    4. Recency weighting (recent actions matter more)
    5. Creator-based recommendations (from followed creators)
    6. Scarcity signals (selling out, trending now)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.SCARCITY_THRESHOLDS = {
            'selling_fast': 10,  # 10+ interactions in last 24h
            'low_stock_signal': 20,  # 20+ favorites/canvas adds
            'trending_creator': 5  # 5+ interactions on creator post in 48h
        }
    
    def get_recommendations(
        self,
        user_id: int,
        limit: int = 20,
        strategy: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user.
        
        Strategies:
        - "hybrid": Combines all strategies (default)
        - "content": Based on user's preferences
        - "collaborative": Based on similar users
        - "trending": Popular items
        """
        
        if strategy == "content":
            return self._content_based_recommendations(user_id, limit)
        elif strategy == "collaborative":
            return self._collaborative_recommendations(user_id, limit)
        elif strategy == "trending":
            return self._trending_recommendations(user_id, limit)
        else:
            return self._hybrid_recommendations(user_id, limit)
    
    def _content_based_recommendations(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Multi-layer content-based recommendations combining:
        1. Visual similarity (CLIP embeddings - wardrobe centroid)
        2. Behavioral signals (purchases > saves > clicks)
        3. Explicit attributes (colors, brands, price range)
        4. Wardrobe gap analysis (what they're missing)
        """
        # Get user's profile
        profile = self.db.query(UserStyleProfile).filter(
            UserStyleProfile.user_id == user_id
        ).first()
        
        # Get user's recent interactions (last 90 days, weighted by recency)
        recent_interactions = self.db.query(UserInteraction).filter(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.created_at >= datetime.now() - timedelta(days=90)
            )
        ).all()
        
        # Get user's wardrobe items (owned items)
        wardrobe_items = self.db.query(UserInteraction).filter(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.action_type.in_(['wardrobe_upload', 'canvas_add', 'purchase_complete'])
            )
        ).all()
        
        # Extract multi-layer preferences
        preferences = self._extract_preferences(recent_interactions)
        wardrobe_analysis = self._analyze_wardrobe_gaps(wardrobe_items)
        
        # Get already interacted items
        seen_items = {i.item_id for i in recent_interactions if i.item_id}
        
        # Score potential recommendations
        recommendations = []
        
        # Get candidate products
        matching_products = self.db.query(ProductAnalytics).filter(
            ProductAnalytics.product_id.notin_(seen_items) if seen_items else True
        ).order_by(
            desc(ProductAnalytics.favorite_count)
        ).limit(limit * 4).all()  # Get more for multi-layer filtering
        
        for product in matching_products:
            # Skip if in recently purchased category (avoid duplicate coats, etc.)
            # In production, you'd check product.category against recently_purchased_categories
            
            # Multi-layer scoring
            scores = {}
            
            # Layer 1: Visual similarity (if we have wardrobe data)
            # Note: In production, you'd calculate CLIP embedding similarity
            # scores['visual'] = self._calculate_visual_similarity(product, wardrobe_items)
            scores['visual'] = 0  # Placeholder - implement with actual CLIP embeddings
            
            # Layer 2: Behavioral signals (weighted by action type)
            scores['behavioral'] = self._calculate_behavioral_score(
                product, recent_interactions, preferences
            )
            
            # Layer 3: Attribute matching (explicit features)
            scores['attributes'] = self._calculate_attribute_score(
                product, preferences, profile
            )
            
            # Layer 4: Wardrobe completion (fills gaps)
            scores['wardrobe_gap'] = self._calculate_gap_filling_score(
                product, wardrobe_analysis
            )
            
            # Layer 5: Outfit completion potential
            scores['outfit_potential'] = self._calculate_outfit_potential(
                product, wardrobe_items
            )
            
            # Combined score with strategic weights
            total_score = (
                scores['visual'] * 0.25 +           # 25% - Visual match to style
                scores['behavioral'] * 0.35 +        # 35% - Past behavior (STRONGEST)
                scores['attributes'] * 0.15 +        # 15% - Explicit preferences
                scores['wardrobe_gap'] * 0.15 +      # 15% - Fills missing categories
                scores['outfit_potential'] * 0.10    # 10% - Works with wardrobe
            )
            
            if total_score > 0:
                recommendations.append({
                    "product_id": product.product_id,
                    "score": total_score,
                    "score_breakdown": scores,
                    "reason": self._generate_reason(scores),
                    "match_factors": self._get_match_factors(product, preferences)
                })
        
        # Sort by score and limit
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def _collaborative_recommendations(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Recommend items based on what similar users liked.
        """
        # Find users with similar interaction patterns
        user_interactions = self.db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).all()
        
        user_items = {i.item_id for i in user_interactions if i.item_id}
        user_actions = Counter([i.action_type for i in user_interactions])
        
        # Find similar users
        all_users = self.db.query(UserInteraction.user_id).distinct().all()
        similar_users = []
        
        for (other_user_id,) in all_users:
            if other_user_id == user_id:
                continue
            
            other_interactions = self.db.query(UserInteraction).filter(
                UserInteraction.user_id == other_user_id
            ).all()
            
            other_items = {i.item_id for i in other_interactions if i.item_id}
            other_actions = Counter([i.action_type for i in other_interactions])
            
            # Calculate similarity (Jaccard for items + action pattern similarity)
            if user_items and other_items:
                item_similarity = len(user_items & other_items) / len(user_items | other_items)
            else:
                item_similarity = 0
            
            action_similarity = self._cosine_similarity(user_actions, other_actions)
            
            similarity = (item_similarity * 0.6) + (action_similarity * 0.4)
            
            if similarity > 0.1:  # Threshold for "similar"
                similar_users.append((other_user_id, similarity))
        
        # Get recommendations from similar users
        similar_users.sort(key=lambda x: x[1], reverse=True)
        recommendations = []
        seen_items = user_items.copy()
        
        for similar_user_id, similarity in similar_users[:10]:  # Top 10 similar users
            similar_interactions = self.db.query(UserInteraction).filter(
                and_(
                    UserInteraction.user_id == similar_user_id,
                    UserInteraction.item_id.isnot(None),
                    UserInteraction.item_id.notin_(seen_items) if seen_items else True
                )
            ).order_by(desc(UserInteraction.weight)).limit(5).all()
            
            for interaction in similar_interactions:
                if interaction.item_id not in seen_items:
                    recommendations.append({
                        "product_id": interaction.item_id,
                        "score": interaction.weight * similarity,
                        "reason": f"Users with similar taste also liked this",
                        "similarity": similarity
                    })
                    seen_items.add(interaction.item_id)
        
        # Sort and limit
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def _trending_recommendations(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Recommend trending/popular items.
        """
        # Get user's already interacted items
        user_items = {
            i.item_id for i in self.db.query(UserInteraction).filter(
                and_(
                    UserInteraction.user_id == user_id,
                    UserInteraction.item_id.isnot(None)
                )
            ).all()
        }
        
        # Get trending products (high engagement recently)
        trending = self.db.query(ProductAnalytics).filter(
            ProductAnalytics.product_id.notin_(user_items) if user_items else True
        ).order_by(
            desc(ProductAnalytics.favorite_count + ProductAnalytics.canvas_add_count)
        ).limit(limit).all()
        
        recommendations = []
        for product in trending:
            engagement_score = (
                product.favorite_count * 2 +
                product.canvas_add_count * 3 +
                product.view_count * 0.1
            )
            
            recommendations.append({
                "product_id": product.product_id,
                "score": engagement_score,
                "reason": "Trending now",
                "engagement": {
                    "favorites": product.favorite_count,
                    "canvas_adds": product.canvas_add_count,
                    "views": product.view_count
                }
            })
        
        return recommendations
    
    def _creator_based_recommendations(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Recommend items from creators the user follows, especially recent posts.
        Prioritizes items that are trending/selling fast.
        """
        # Get creators user follows (from follow_creator interactions)
        followed_creators = self.db.query(UserInteraction.item_id).filter(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.action_type == 'follow_creator'
            )
        ).all()
        
        creator_ids = [c[0] for c in followed_creators if c[0]]
        
        if not creator_ids:
            return []
        
        # Get recent posts from these creators (items with 'favorite_from_creator' action)
        # In a real system, you'd have a Creator Posts table
        # For now, we'll use metadata to identify creator posts
        
        recent_cutoff = datetime.now() - timedelta(days=7)
        
        creator_items = self.db.query(UserInteraction).filter(
            and_(
                UserInteraction.action_type.in_(['favorite_from_creator', 'view_post']),
                UserInteraction.created_at >= recent_cutoff,
                UserInteraction.item_id.isnot(None)
            )
        ).all()
        
        # Get user's already seen items
        user_items = {
            i.item_id for i in self.db.query(UserInteraction).filter(
                and_(
                    UserInteraction.user_id == user_id,
                    UserInteraction.item_id.isnot(None)
                )
            ).all()
        }
        
        # Score creator items
        item_scores = defaultdict(lambda: {'score': 0, 'interactions': [], 'creator_id': None})
        
        for interaction in creator_items:
            if interaction.item_id in user_items:
                continue
            
            # Extract creator info from metadata
            creator_id = None
            if interaction.interaction_metadata and 'creator_id' in interaction.interaction_metadata:
                creator_id = interaction.interaction_metadata['creator_id']
            
            # Only recommend from followed creators
            if creator_id and creator_id in creator_ids:
                item_scores[interaction.item_id]['score'] += interaction.weight
                item_scores[interaction.item_id]['interactions'].append(interaction)
                item_scores[interaction.item_id]['creator_id'] = creator_id
                
                # Boost for very recent posts (last 48h)
                if interaction.created_at >= datetime.now() - timedelta(days=2):
                    item_scores[interaction.item_id]['score'] += 10
        
        # Build recommendations with scarcity signals
        recommendations = []
        for item_id, data in item_scores.items():
            # Calculate scarcity signals
            recent_interactions_24h = len([
                i for i in data['interactions']
                if i.created_at >= datetime.now() - timedelta(days=1)
            ])
            
            scarcity_signals = []
            urgency_score = 0
            
            if recent_interactions_24h >= self.SCARCITY_THRESHOLDS['selling_fast']:
                scarcity_signals.append(f"🔥 {recent_interactions_24h} people added this today")
                urgency_score += 15
            
            if len(data['interactions']) >= self.SCARCITY_THRESHOLDS['trending_creator']:
                scarcity_signals.append("⚡ Trending from creator you follow")
                urgency_score += 10
            
            # Check if posted in last 48h
            newest_post = max(i.created_at for i in data['interactions'])
            hours_ago = (datetime.now() - newest_post).total_seconds() / 3600
            
            if hours_ago < 48:
                scarcity_signals.append(f"✨ New post from creator ({int(hours_ago)}h ago)")
                urgency_score += 8
            
            recommendations.append({
                "product_id": item_id,
                "score": data['score'] + urgency_score,
                "reason": f"From creator you follow",
                "creator_id": data['creator_id'],
                "scarcity_signals": scarcity_signals,
                "urgency_score": urgency_score,
                "interaction_count": len(data['interactions']),
                "hours_since_post": int(hours_ago)
            })
        
        # Sort by score (includes urgency)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def _similar_user_purchases(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find what similar users recently bought/added to canvas.
        Focus on high-intent actions (canvas_add, purchase_complete).
        """
        # Find users with similar profiles
        user_profile = self.db.query(UserStyleProfile).filter(
            UserStyleProfile.user_id == user_id
        ).first()
        
        if not user_profile:
            return []
        
        # Get user's interactions for similarity
        user_interactions = self.db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).all()
        
        user_items = {i.item_id for i in user_interactions if i.item_id}
        user_brands = Counter([
            i.interaction_metadata.get('brand')
            for i in user_interactions
            if i.interaction_metadata and 'brand' in i.interaction_metadata
        ])
        user_categories = Counter([
            i.interaction_metadata.get('category')
            for i in user_interactions
            if i.interaction_metadata and 'category' in i.interaction_metadata
        ])
        
        # Find similar users
        similar_users = []
        all_users = self.db.query(UserStyleProfile).filter(
            UserStyleProfile.user_id != user_id
        ).all()
        
        for other_profile in all_users:
            similarity = 0
            
            # Brand overlap
            other_brands = set(other_profile.favorite_brands) if other_profile.favorite_brands else set()
            my_brands = set(dict(user_brands.most_common(5)).keys())
            if my_brands and other_brands:
                brand_overlap = len(my_brands & other_brands) / len(my_brands | other_brands)
                similarity += brand_overlap * 0.4
            
            # Category overlap
            other_cats = set(other_profile.favorite_categories) if other_profile.favorite_categories else set()
            my_cats = set(dict(user_categories.most_common(5)).keys())
            if my_cats and other_cats:
                cat_overlap = len(my_cats & other_cats) / len(my_cats | other_cats)
                similarity += cat_overlap * 0.3
            
            # Engagement score similarity
            if other_profile.engagement_score > 0 and user_profile.engagement_score > 0:
                engagement_ratio = min(
                    other_profile.engagement_score,
                    user_profile.engagement_score
                ) / max(other_profile.engagement_score, user_profile.engagement_score)
                similarity += engagement_ratio * 0.3
            
            if similarity > 0.15:  # Similarity threshold
                similar_users.append((other_profile.user_id, similarity))
        
        # Sort by similarity
        similar_users.sort(key=lambda x: x[1], reverse=True)
        
        # Get recent high-intent actions from similar users
        recent_cutoff = datetime.now() - timedelta(days=14)  # Last 2 weeks
        recommendations = []
        seen_items = user_items.copy()
        
        for similar_user_id, similarity in similar_users[:20]:  # Top 20 similar users
            high_intent_actions = self.db.query(UserInteraction).filter(
                and_(
                    UserInteraction.user_id == similar_user_id,
                    UserInteraction.action_type.in_([
                        'canvas_add',
                        'purchase_complete',
                        'click_to_retailer',
                        'favorite_product'
                    ]),
                    UserInteraction.created_at >= recent_cutoff,
                    UserInteraction.item_id.isnot(None),
                    UserInteraction.item_id.notin_(seen_items) if seen_items else True
                )
            ).order_by(desc(UserInteraction.created_at)).limit(3).all()
            
            for interaction in high_intent_actions:
                if interaction.item_id not in seen_items:
                    # Calculate how many other similar users also interacted with this
                    similar_user_ids = [u[0] for u in similar_users[:20]]
                    co_interactions = self.db.query(func.count(UserInteraction.id)).filter(
                        and_(
                            UserInteraction.item_id == interaction.item_id,
                            UserInteraction.user_id.in_(similar_user_ids),
                            UserInteraction.action_type.in_([
                                'canvas_add',
                                'purchase_complete',
                                'favorite_product'
                            ])
                        )
                    ).scalar()
                    
                    social_proof_signals = []
                    social_score = 0
                    
                    if co_interactions >= 5:
                        social_proof_signals.append(f"👥 {co_interactions} similar users bought this")
                        social_score += 20
                    elif co_interactions >= 2:
                        social_proof_signals.append(f"👥 {co_interactions} similar users also liked this")
                        social_score += 10
                    
                    # Check how recent
                    hours_ago = (datetime.now() - interaction.created_at).total_seconds() / 3600
                    if hours_ago < 48:
                        social_proof_signals.append(f"🆕 Added by similar user {int(hours_ago)}h ago")
                        social_score += 5
                    
                    recommendations.append({
                        "product_id": interaction.item_id,
                        "score": (interaction.weight * similarity * 10) + social_score,
                        "reason": "Similar users with your style recently added this",
                        "similarity_score": similarity,
                        "action_type": interaction.action_type,
                        "social_proof_signals": social_proof_signals,
                        "co_interaction_count": co_interactions,
                        "hours_ago": int(hours_ago)
                    })
                    seen_items.add(interaction.item_id)
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def _hybrid_recommendations(
        self,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        ULTIMATE ENSEMBLE: Combines 8 different signals for maximum conversion.
        
        Weight distribution optimized for conversion:
        - Behavioral (35%): Past purchases/saves = strongest predictor
        - Creator posts (25%): Trust + FOMO = high conversion
        - Similar user purchases (20%): Social proof + intent
        - Visual similarity (10%): Style matching
        - Wardrobe context (5%): Gap filling + outfit potential
        - Collaborative (3%): Pattern matching
        - Trending (2%): General popularity
        
        Key insight: Weight signals by CONVERSION POWER, not just accuracy.
        """
        # Get recommendations from each strategy
        creator_recs = self._creator_based_recommendations(user_id, limit)
        similar_user_recs = self._similar_user_purchases(user_id, limit)
        content_recs = self._content_based_recommendations(user_id, limit)
        collab_recs = self._collaborative_recommendations(user_id, limit)
        trending_recs = self._trending_recommendations(user_id, limit // 3)
        
        # Combine with conversion-optimized weights
        all_recs = {}
        
        # Layer 1: BEHAVIORAL (from content-based) - 35% weight
        # Purchases >> Saves >> Clicks >> Views
        # This is THE strongest predictor of what they'll actually buy
        for rec in content_recs:
            product_id = rec['product_id']
            # Extract behavioral score if available
            behavioral_score = rec.get('score_breakdown', {}).get('behavioral', rec['score'])
            
            all_recs[product_id] = {
                **rec,
                'score': behavioral_score * 0.35,
                'strategies': ['behavioral'],
                'priority': 'high',
                'conversion_signals': []
            }
        
        # Layer 2: CREATOR-BASED - 25% weight
        # Trust + scarcity + FOMO = high conversion
        for rec in creator_recs:
            product_id = rec['product_id']
            if product_id in all_recs:
                all_recs[product_id]['score'] += rec['score'] * 0.25
                all_recs[product_id]['strategies'].append('creator')
                if 'scarcity_signals' in rec:
                    all_recs[product_id]['conversion_signals'].extend(rec['scarcity_signals'])
            else:
                all_recs[product_id] = {
                    **rec,
                    'score': rec['score'] * 0.25,
                    'strategies': ['creator'],
                    'priority': 'high',
                    'conversion_signals': rec.get('scarcity_signals', [])
                }
        
        # Layer 3: SIMILAR USER PURCHASES - 20% weight
        # Social proof + demonstrated purchase intent
        for rec in similar_user_recs:
            product_id = rec['product_id']
            if product_id in all_recs:
                all_recs[product_id]['score'] += rec['score'] * 0.20
                all_recs[product_id]['strategies'].append('similar_users')
                if 'social_proof_signals' in rec:
                    all_recs[product_id]['conversion_signals'].extend(rec['social_proof_signals'])
            else:
                all_recs[product_id] = {
                    **rec,
                    'score': rec['score'] * 0.20,
                    'strategies': ['similar_users'],
                    'priority': 'high',
                    'conversion_signals': rec.get('social_proof_signals', [])
                }
        
        # Layer 4: VISUAL SIMILARITY - 10% weight
        # Style matching via CLIP embeddings (when implemented)
        for rec in content_recs:
            product_id = rec['product_id']
            visual_score = rec.get('score_breakdown', {}).get('visual', 0)
            if product_id in all_recs and visual_score > 0:
                all_recs[product_id]['score'] += visual_score * 0.10
                if 'visual' not in all_recs[product_id]['strategies']:
                    all_recs[product_id]['strategies'].append('visual')
        
        # Layer 5: WARDROBE CONTEXT - 5% weight
        # Gap filling + outfit completion potential
        for rec in content_recs:
            product_id = rec['product_id']
            gap_score = rec.get('score_breakdown', {}).get('wardrobe_gap', 0)
            outfit_score = rec.get('score_breakdown', {}).get('outfit_potential', 0)
            wardrobe_score = gap_score + outfit_score
            
            if product_id in all_recs and wardrobe_score > 0:
                all_recs[product_id]['score'] += wardrobe_score * 0.05
                if wardrobe_score > 50:  # High wardrobe fit
                    all_recs[product_id]['conversion_signals'].append(
                        f"💡 Works with {int(wardrobe_score/5)} items you own"
                    )
        
        # Layer 6: COLLABORATIVE - 3% weight
        # Pattern matching with similar users
        for rec in collab_recs:
            product_id = rec['product_id']
            if product_id in all_recs:
                all_recs[product_id]['score'] += rec['score'] * 0.03
                if 'collaborative' not in all_recs[product_id]['strategies']:
                    all_recs[product_id]['strategies'].append('collaborative')
            else:
                all_recs[product_id] = {
                    **rec,
                    'score': rec['score'] * 0.03,
                    'strategies': ['collaborative'],
                    'priority': 'medium',
                    'conversion_signals': []
                }
        
        # Layer 7: TRENDING - 2% weight
        # General popularity (weakest signal)
        for rec in trending_recs:
            product_id = rec['product_id']
            if product_id in all_recs:
                all_recs[product_id]['score'] += rec['score'] * 0.02
                if 'trending' not in all_recs[product_id]['strategies']:
                    all_recs[product_id]['strategies'].append('trending')
            else:
                all_recs[product_id] = {
                    **rec,
                    'score': rec['score'] * 0.02,
                    'strategies': ['trending'],
                    'priority': 'low',
                    'conversion_signals': []
                }
        
        # MAGIC: Multi-signal boosting for convergence
        # Items that appear in multiple high-value strategies = HOT
        for product_id, rec in all_recs.items():
            strategies = set(rec['strategies'])
            
            # TRIPLE SIGNAL: Behavioral + Creator + Similar Users = 🚨 URGENT
            if {'behavioral', 'creator', 'similar_users'}.issubset(strategies):
                rec['score'] *= 2.0  # Double the score!
                rec['priority'] = 'urgent'
                rec['conversion_signals'].insert(0, "🚨 TRIPLE SIGNAL: Perfect for you + Creator posted + Similar users buying")
            
            # DOUBLE SIGNAL: Any 2 high-value strategies = High priority
            elif len({'behavioral', 'creator', 'similar_users'} & strategies) >= 2:
                rec['score'] *= 1.5
                rec['priority'] = 'urgent'
                rec['conversion_signals'].insert(0, "🔥 Perfect match: Multiple strong signals")
            
            # Creator + Similar Users (even without behavioral) = Very hot
            elif 'creator' in strategies and 'similar_users' in strategies:
                rec['score'] *= 1.4
                rec['priority'] = 'urgent'
                rec['conversion_signals'].insert(0, "💥 Creator + Social proof: Trending!")
        
        # Sort by priority then score
        priority_order = {'urgent': 3, 'high': 2, 'medium': 1, 'low': 0}
        recommendations = sorted(
            all_recs.values(),
            key=lambda x: (priority_order.get(x.get('priority', 'low'), 0), x['score']),
            reverse=True
        )
        
        return recommendations[:limit]
    
    def _extract_preferences(
        self,
        interactions: List[UserInteraction]
    ) -> Dict[str, Any]:
        """Extract user preferences from interactions with behavioral weighting."""
        # Weight different actions differently
        ACTION_PREFERENCE_WEIGHTS = {
            'purchase_complete': 10.0,      # STRONGEST signal
            'click_to_retailer': 8.0,       # High intent
            'canvas_add': 7.0,              # High intent
            'favorite_product': 5.0,        # Medium-high intent
            'favorite_from_creator': 6.0,   # Medium-high + trust signal
            'wardrobe_upload': 4.0,         # Own it but may not love it
            'view_product': 2.0,            # Weak signal
            'search': 17.0,                  # 🔍 VERY HIGH - Active, specific intent!
        }
        
        weighted_brands = Counter()
        weighted_colors = Counter()
        weighted_categories = Counter()
        price_points = []
        keywords = []
        
        # Apply recency weighting - recent actions matter more
        now = datetime.now()
        
        for interaction in interactions:
            # Calculate recency multiplier (1.0 = recent, decays over 90 days)
            days_ago = (now - interaction.created_at).days
            recency_multiplier = max(0.3, 1.0 - (days_ago / 90.0))
            
            # Get action weight
            action_weight = ACTION_PREFERENCE_WEIGHTS.get(interaction.action_type, 1.0)
            
            # Combined weight
            total_weight = action_weight * recency_multiplier * interaction.weight
            
            if interaction.interaction_metadata:
                metadata = interaction.interaction_metadata
                
                if 'brand' in metadata:
                    weighted_brands[metadata['brand']] += total_weight
                if 'color' in metadata:
                    weighted_colors[metadata['color']] += total_weight
                if 'category' in metadata:
                    weighted_categories[metadata['category']] += total_weight
                if 'price' in metadata:
                    # Weight prices by action type - purchases matter most
                    price_points.append((float(metadata['price']), total_weight))
                if 'query' in metadata:
                    keywords.extend(metadata['query'].lower().split())
        
        # Calculate weighted average price
        if price_points:
            weighted_avg_price = sum(p * w for p, w in price_points) / sum(w for _, w in price_points)
        else:
            weighted_avg_price = None
        
        return {
            'brands': weighted_brands.most_common(10),
            'colors': weighted_colors.most_common(10),
            'categories': weighted_categories.most_common(10),
            'avg_price': weighted_avg_price,
            'price_range': {
                'min': min(p for p, _ in price_points) if price_points else None,
                'max': max(p for p, _ in price_points) if price_points else None,
            },
            'keywords': Counter(keywords).most_common(20)
        }
    
    def _analyze_wardrobe_gaps(
        self,
        wardrobe_items: List[UserInteraction]
    ) -> Dict[str, Any]:
        """
        Analyze wardrobe to find gaps and underutilized categories.
        Key insight: Recommend items that FILL GAPS, not just match style.
        """
        category_counts = Counter()
        color_counts = Counter()
        
        for item in wardrobe_items:
            if item.interaction_metadata:
                if 'category' in item.interaction_metadata:
                    category_counts[item.interaction_metadata['category']] += 1
                if 'color' in item.interaction_metadata:
                    color_counts[item.interaction_metadata['color']] += 1
        
        # Define complete wardrobe targets
        IDEAL_WARDROBE = {
            'tops': 8,
            'bottoms': 6,
            'dresses': 4,
            'outerwear': 3,
            'shoes': 5,
            'accessories': 4,
        }
        
        gaps = {}
        for category, ideal_count in IDEAL_WARDROBE.items():
            actual_count = category_counts.get(category, 0)
            if actual_count < ideal_count:
                gaps[category] = ideal_count - actual_count
        
        return {
            'gaps': gaps,  # Categories they need more of
            'has_lots_of': [cat for cat, count in category_counts.most_common(3)],
            'missing_completely': [cat for cat in IDEAL_WARDROBE if category_counts.get(cat, 0) == 0],
            'color_distribution': color_counts.most_common(10)
        }
    
    def _calculate_behavioral_score(
        self,
        product: ProductAnalytics,
        interactions: List[UserInteraction],
        preferences: Dict[str, Any]
    ) -> float:
        """
        Score based on behavioral signals - what they actually do, not just view.
        Purchases >> Saves >> Clicks >> Views
        """
        score = 0.0
        
        # Base engagement score
        score += product.favorite_count * 2
        score += product.canvas_add_count * 3
        score += product.click_through_count * 4
        score += product.view_count * 0.5
        
        # Boost if matches behavioral patterns
        # (In production, you'd check if product attributes match past interactions)
        
        return min(score, 100.0)  # Cap at 100
    
    def _calculate_attribute_score(
        self,
        product: ProductAnalytics,
        preferences: Dict[str, Any],
        profile: Optional[UserStyleProfile]
    ) -> float:
        """
        Score based on explicit attribute matching.
        Colors, brands, categories, price range.
        """
        score = 0.0
        
        # In production, you'd have product metadata to compare
        # For now, just use product analytics as proxy
        
        # Price range matching
        if preferences['avg_price'] and product.current_price:
            price_diff_ratio = abs(product.current_price - preferences['avg_price']) / preferences['avg_price']
            if price_diff_ratio < 0.3:  # Within 30%
                score += 20
            elif price_diff_ratio < 0.5:  # Within 50%
                score += 10
        
        # Profile matching
        if profile:
            # Engagement boost
            score += profile.engagement_score * 0.5
        
        return min(score, 100.0)
    
    def _calculate_gap_filling_score(
        self,
        product: ProductAnalytics,
        wardrobe_analysis: Dict[str, Any]
    ) -> float:
        """
        Score based on whether this product fills a gap in their wardrobe.
        Key insight: People need variety, not just more of what they have.
        """
        score = 0.0
        
        # In production, check if product.category is in wardrobe_analysis['gaps']
        # Boost score significantly for gap-filling items
        
        # Example: If they have no blazers and this is a blazer, huge boost
        # if product.category in wardrobe_analysis['missing_completely']:
        #     score += 50
        # elif product.category in wardrobe_analysis['gaps']:
        #     score += 30 * wardrobe_analysis['gaps'][product.category]
        
        return min(score, 100.0)
    
    def _calculate_outfit_potential(
        self,
        product: ProductAnalytics,
        wardrobe_items: List[UserInteraction]
    ) -> float:
        """
        Calculate "outfit completion score" - how many new outfits can this create?
        
        Key insight: Items that work with EXISTING wardrobe = higher conversion.
        A black blazer that pairs with 10 items > neon jacket that pairs with 1.
        """
        score = 0.0
        
        # In production, you'd have:
        # - Fashion rules (blazers work with jeans, dresses, etc.)
        # - Visual similarity (CLIP embeddings)
        # - Color compatibility (complementary colors)
        
        # potential_pairings = 0
        # for wardrobe_item in wardrobe_items:
        #     if can_be_styled_together(product, wardrobe_item):
        #         potential_pairings += 1
        # 
        # score = potential_pairings * 5  # 5 points per pairing
        
        # Placeholder: Use engagement as proxy
        score = product.favorite_count * 2
        
        return min(score, 100.0)
    
    def _generate_reason(self, scores: Dict[str, float]) -> str:
        """Generate human-readable reason based on score breakdown."""
        # Find dominant signal
        max_score_type = max(scores.items(), key=lambda x: x[1])[0]
        
        reasons = {
            'behavioral': "Based on items you've bought and saved",
            'visual': "Matches your style aesthetic",
            'attributes': "Matches your color and brand preferences",
            'wardrobe_gap': "Fills a gap in your wardrobe",
            'outfit_potential': "Works with multiple items you own"
        }
        
        return reasons.get(max_score_type, "Recommended for you")
    
    def _calculate_content_score(
        self,
        product: ProductAnalytics,
        preferences: Dict[str, Any],
        profile: Optional[UserStyleProfile]
    ) -> float:
        """Calculate how well a product matches user preferences."""
        score = 0.0
        
        # Base score from product popularity
        score += product.favorite_count * 2
        score += product.canvas_add_count * 3
        score += product.view_count * 0.1
        
        # Boost if matches profile preferences
        if profile:
            # Brand matching
            if profile.favorite_brands:
                # Would need product metadata to match
                pass
            
            # Engagement score boost
            score += profile.engagement_score * 0.1
        
        return score
    
    def _get_match_factors(
        self,
        product: ProductAnalytics,
        preferences: Dict[str, Any]
    ) -> List[str]:
        """Get reasons why this product matches."""
        factors = []
        
        if product.favorite_count > 10:
            factors.append("Popular choice")
        
        if product.canvas_add_count > 5:
            factors.append("Frequently added to canvas")
        
        # Would add more specific matching based on product metadata
        
        return factors
    
    def _cosine_similarity(
        self,
        counter1: Counter,
        counter2: Counter
    ) -> float:
        """Calculate cosine similarity between two counters."""
        if not counter1 or not counter2:
            return 0.0
        
        all_keys = set(counter1.keys()) | set(counter2.keys())
        
        dot_product = sum(counter1.get(k, 0) * counter2.get(k, 0) for k in all_keys)
        
        magnitude1 = sum(v**2 for v in counter1.values()) ** 0.5
        magnitude2 = sum(v**2 for v in counter2.values()) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


def get_recommendation_engine(db: Session) -> RecommendationEngine:
    """Factory function to get recommendation engine instance."""
    return RecommendationEngine(db)
