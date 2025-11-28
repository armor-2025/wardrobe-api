# recommendation_endpoints.py
# API endpoints for the recommendation system

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from auth_service import get_current_user
from recommendation_engine import get_recommendation_engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    product_id: str
    score: float
    reason: str
    strategies: Optional[List[str]] = None
    match_factors: Optional[List[str]] = None


@router.get("/for-me")
def get_recommendations_for_me(
    limit: int = Query(20, ge=1, le=100),
    strategy: str = Query("hybrid", regex="^(hybrid|content|collaborative|trending)$"),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations for the current user.
    
    **Strategies:**
    - `hybrid`: Combines all strategies (default, best results)
    - `content`: Based on your preferences and history
    - `collaborative`: Based on users with similar taste
    - `trending`: Currently popular items
    
    **Returns:**
    - List of recommended product IDs with scores and reasons
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get recommendation engine
    engine = get_recommendation_engine(db)
    
    # Get recommendations
    recommendations = engine.get_recommendations(
        user_id=user.id,
        limit=limit,
        strategy=strategy
    )
    
    return {
        "user_id": user.id,
        "strategy": strategy,
        "count": len(recommendations),
        "recommendations": recommendations
    }


@router.get("/similar-to/{product_id}")
def get_similar_products(
    product_id: str,
    limit: int = Query(10, ge=1, le=50),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get products similar to a specific product.
    Based on users who interacted with this product.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get users who interacted with this product
    from interaction_models import UserInteraction
    
    product_interactions = db.query(UserInteraction).filter(
        UserInteraction.item_id == product_id
    ).all()
    
    if not product_interactions:
        return {
            "product_id": product_id,
            "recommendations": [],
            "message": "No interaction data for this product yet"
        }
    
    # Get other items these users interacted with
    user_ids = [i.user_id for i in product_interactions]
    
    similar_items = db.query(
        UserInteraction.item_id,
        func.count(UserInteraction.id).label('interaction_count'),
        func.sum(UserInteraction.weight).label('total_weight')
    ).filter(
        UserInteraction.user_id.in_(user_ids),
        UserInteraction.item_id != product_id,
        UserInteraction.item_id.isnot(None)
    ).group_by(
        UserInteraction.item_id
    ).order_by(
        desc('total_weight')
    ).limit(limit).all()
    
    recommendations = [
        {
            "product_id": item_id,
            "score": float(total_weight),
            "interaction_count": interaction_count,
            "reason": f"Users who liked this also liked these"
        }
        for item_id, interaction_count, total_weight in similar_items
    ]
    
    return {
        "product_id": product_id,
        "count": len(recommendations),
        "recommendations": recommendations
    }


@router.get("/trending")
def get_trending_products(
    limit: int = Query(20, ge=1, le=100),
    timeframe: str = Query("week", regex="^(day|week|month|all)$"),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get trending products based on recent activity.
    
    **Timeframes:**
    - `day`: Last 24 hours
    - `week`: Last 7 days (default)
    - `month`: Last 30 days
    - `all`: All time
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from datetime import datetime, timedelta
    from interaction_models import UserInteraction
    
    # Calculate timeframe
    if timeframe == "day":
        since = datetime.now() - timedelta(days=1)
    elif timeframe == "week":
        since = datetime.now() - timedelta(days=7)
    elif timeframe == "month":
        since = datetime.now() - timedelta(days=30)
    else:
        since = None
    
    # Query trending items
    query = db.query(
        UserInteraction.item_id,
        func.count(UserInteraction.id).label('interaction_count'),
        func.sum(UserInteraction.weight).label('total_weight'),
        func.count(func.distinct(UserInteraction.user_id)).label('unique_users')
    ).filter(
        UserInteraction.item_id.isnot(None)
    )
    
    if since:
        query = query.filter(UserInteraction.created_at >= since)
    
    trending = query.group_by(
        UserInteraction.item_id
    ).order_by(
        desc('total_weight')
    ).limit(limit).all()
    
    recommendations = [
        {
            "product_id": item_id,
            "score": float(total_weight),
            "interaction_count": interaction_count,
            "unique_users": unique_users,
            "reason": f"Trending in the last {timeframe}"
        }
        for item_id, interaction_count, total_weight, unique_users in trending
    ]
    
    return {
        "timeframe": timeframe,
        "count": len(recommendations),
        "recommendations": recommendations
    }


@router.post("/feedback")
def provide_recommendation_feedback(
    product_id: str,
    liked: bool,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Provide feedback on a recommendation (like/dislike).
    This helps improve future recommendations.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Track this as an interaction
    from interaction_models import UserInteraction
    
    action_type = "favorite_product" if liked else "dislike_product"
    
    interaction = UserInteraction(
        user_id=user.id,
        action_type=action_type,
        item_id=product_id,
        item_type="product",
        interaction_metadata={"source": "recommendation_feedback"},
        weight=7.0 if liked else -2.0,  # Negative weight for dislikes
        source="recommendation_system"
    )
    
    db.add(interaction)
    db.commit()
    
    return {
        "success": True,
        "message": f"Feedback recorded: {'liked' if liked else 'disliked'}",
        "product_id": product_id
    }


@router.get("/from-creators")
def get_creator_recommendations(
    limit: int = Query(20, ge=1, le=50),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get recommendations from creators you follow.
    Shows new posts and trending items with scarcity signals.
    
    **Scarcity signals:**
    - 🔥 High activity in last 24h
    - ⚡ Trending from creator
    - ✨ New post (within 48h)
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    engine = get_recommendation_engine(db)
    recommendations = engine._creator_based_recommendations(user.id, limit)
    
    return {
        "user_id": user.id,
        "count": len(recommendations),
        "recommendations": recommendations,
        "message": "Items from creators you follow" if recommendations else "Follow some creators to get recommendations!"
    }


@router.get("/similar-users-bought")
def get_similar_user_recommendations(
    limit: int = Query(20, ge=1, le=50),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    See what users with similar style recently bought or added to canvas.
    
    **Social proof signals:**
    - 👥 Multiple similar users bought this
    - 🆕 Recently added by similar user
    - High-intent actions (canvas adds, purchases)
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    engine = get_recommendation_engine(db)
    recommendations = engine._similar_user_purchases(user.id, limit)
    
    return {
        "user_id": user.id,
        "count": len(recommendations),
        "recommendations": recommendations,
        "message": "Based on users with similar style to you"
    }


@router.get("/hot-items")
def get_hot_items(
    limit: int = Query(10, ge=1, le=30),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get "hot" items - products that are:
    - From creators you follow AND
    - Being bought by similar users
    
    These are your highest-conversion recommendations!
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    engine = get_recommendation_engine(db)
    
    # Get both types
    creator_recs = engine._creator_based_recommendations(user.id, limit * 2)
    similar_recs = engine._similar_user_purchases(user.id, limit * 2)
    
    # Find overlap - items in both lists
    creator_items = {r['product_id']: r for r in creator_recs}
    similar_items = {r['product_id']: r for r in similar_recs}
    
    hot_items = []
    for product_id in creator_items:
        if product_id in similar_items:
            # Combine the data
            combined = {
                "product_id": product_id,
                "score": creator_items[product_id]['score'] + similar_items[product_id]['score'],
                "reason": "🚨 HOT: From your creator + bought by similar users",
                "creator_data": creator_items[product_id],
                "similar_user_data": similar_items[product_id],
                "urgency": "high"
            }
            
            # Combine all signals
            signals = []
            if 'scarcity_signals' in creator_items[product_id]:
                signals.extend(creator_items[product_id]['scarcity_signals'])
            if 'social_proof_signals' in similar_items[product_id]:
                signals.extend(similar_items[product_id]['social_proof_signals'])
            
            combined['all_signals'] = signals
            hot_items.append(combined)
    
    # Sort by combined score
    hot_items.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        "user_id": user.id,
        "count": len(hot_items),
        "hot_items": hot_items[:limit],
        "message": "Your highest-conversion opportunities!" if hot_items else "Keep engaging to discover hot items!"
    }
