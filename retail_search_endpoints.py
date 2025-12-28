"""
Vertex AI Search for Retail - API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Header, File, UploadFile, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import base64

from database import get_db
from auth_service import get_current_user
from vertex_retail_search import get_retail_search

router = APIRouter(prefix="/shop", tags=["Shop the Look"])


# ==================== REQUEST/RESPONSE MODELS ====================

class ProductCreate(BaseModel):
    product_id: str
    title: str
    categories: List[str]
    price: float
    currency: str = "GBP"
    image_urls: Optional[List[str]] = None
    brand: Optional[str] = None
    colors: Optional[List[str]] = None
    sizes: Optional[List[str]] = None
    description: Optional[str] = None
    retailer: Optional[str] = None
    affiliate_url: Optional[str] = None


class SearchFilters(BaseModel):
    brand: Optional[str] = None
    color: Optional[str] = None
    retailer: Optional[str] = None
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


# ==================== SEARCH ENDPOINTS ====================

@router.get("/search")
async def text_search(
    query: str = Query(..., description="Search query (e.g., 'black leather jacket')"),
    page_size: int = Query(20, ge=1, le=100),
    brand: Optional[str] = None,
    color: Optional[str] = None,
    retailer: Optional[str] = None,
    category: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Text-based product search with Google-quality semantic understanding
    
    Examples:
    - "black midi dress for date night"
    - "oversized wool coat"
    - "chunky white sneakers"
    """
    # Get user ID for personalization (optional)
    visitor_id = "anonymous"
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if user:
            visitor_id = str(user.id)
    
    # Build filters
    filters = {}
    if brand: filters["brand"] = brand
    if color: filters["color"] = color
    if retailer: filters["retailer"] = retailer
    if category: filters["category"] = category
    if price_min: filters["price_min"] = price_min
    if price_max: filters["price_max"] = price_max
    
    try:
        search = get_retail_search()
        results = search.text_search(
            query=query,
            visitor_id=visitor_id,
            page_size=page_size,
            filters=filters if filters else None
        )
        
        return {
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/visual-search")
async def visual_search(
    file: UploadFile = File(..., description="Image file to search"),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Visual search - upload an outfit image to find matching products
    
    This is the core "Shop the Look" feature:
    1. User uploads outfit photo
    2. AI finds visually similar products from retailer catalogs
    3. Returns matching products with affiliate links
    """
    visitor_id = "anonymous"
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if user:
            visitor_id = str(user.id)
    
    try:
        # Read and encode image
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode()
        
        # Build filters
        filters = {}
        if category: filters["category"] = category
        
        search = get_retail_search()
        results = search.visual_search(
            image_base64=image_base64,
            visitor_id=visitor_id,
            page_size=page_size,
            filters=filters if filters else None
        )
        
        return {
            "type": "visual_search",
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual search failed: {str(e)}")


@router.post("/visual-search-base64")
async def visual_search_base64(
    image_base64: str,
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Visual search with base64 image (for FlutterFlow)
    """
    visitor_id = "anonymous"
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if user:
            visitor_id = str(user.id)
    
    try:
        filters = {}
        if category: filters["category"] = category
        
        search = get_retail_search()
        results = search.visual_search(
            image_base64=image_base64,
            visitor_id=visitor_id,
            page_size=page_size,
            filters=filters if filters else None
        )
        
        return {
            "type": "visual_search",
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual search failed: {str(e)}")


# ==================== RECOMMENDATIONS ====================

@router.get("/recommendations")
async def get_recommendations(
    recommendation_type: str = Query("recommended-for-you", regex="^(recommended-for-you|others-you-may-like|frequently-bought-together|similar-items)$"),
    page_size: int = Query(20, ge=1, le=100),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Get personalized product recommendations
    
    Types:
    - recommended-for-you: Personalized based on history
    - others-you-may-like: Similar to recently viewed
    - frequently-bought-together: Complementary items
    - similar-items: Visually similar products
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        search = get_retail_search()
        results = search.get_recommendations(
            user_id=str(user.id),
            recommendation_type=recommendation_type,
            page_size=page_size
        )
        
        return {
            "user_id": user.id,
            "type": recommendation_type,
            "count": len(results),
            "recommendations": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


@router.get("/similar/{product_id}")
async def get_similar_products(
    product_id: str,
    page_size: int = Query(10, ge=1, le=50),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get products similar to a specific product
    """
    try:
        search = get_retail_search()
        results = search.get_similar_products(
            product_id=product_id,
            page_size=page_size
        )
        
        return {
            "product_id": product_id,
            "count": len(results),
            "similar_products": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar products failed: {str(e)}")


# ==================== PRODUCT MANAGEMENT ====================

@router.post("/products")
async def create_product(
    product: ProductCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Add a product to the catalog (admin/retailer use)
    """
    # TODO: Add admin auth check
    
    try:
        search = get_retail_search()
        created = search.create_product(**product.dict())
        
        return {
            "success": True,
            "product_id": product.product_id,
            "message": "Product created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product creation failed: {str(e)}")


@router.post("/products/bulk")
async def bulk_import_products(
    products: List[ProductCreate],
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Bulk import products from retailer API
    """
    # TODO: Add admin auth check
    
    try:
        search = get_retail_search()
        results = search.bulk_import_products([p.dict() for p in products])
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Delete a product from the catalog
    """
    # TODO: Add admin auth check
    
    try:
        search = get_retail_search()
        success = search.delete_product(product_id)
        
        return {
            "success": success,
            "product_id": product_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ==================== EVENT TRACKING ====================

@router.post("/track")
async def track_event(
    event_type: str = Query(..., regex="^(detail-page-view|add-to-cart|purchase-complete|search|home-page-view)$"),
    product_id: Optional[str] = None,
    search_query: Optional[str] = None,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Track user events for recommendation training
    
    Event types:
    - detail-page-view: Viewed a product
    - add-to-cart: Added to cart/wishlist
    - purchase-complete: Completed purchase
    - search: Performed search
    - home-page-view: Viewed home page
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        search = get_retail_search()
        search.track_event(
            user_id=str(user.id),
            event_type=event_type,
            product_id=product_id,
            search_query=search_query
        )
        
        return {"success": True, "event_type": event_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tracking failed: {str(e)}")


# ==================== SHOP THE LOOK ====================

from shop_the_look_endpoint import get_shop_the_look

@router.post("/shop-the-look")
async def shop_the_look(
    file: UploadFile = File(..., description="Outfit image to analyze"),
    matches_per_item: int = Query(10, ge=1, le=50),
    return_crops: bool = Query(False, description="Include cropped item images in response"),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    🛍️ SHOP THE LOOK - Complete Visual Search Pipeline
    
    Upload an outfit photo and get matching products for every item.
    
    Flow:
    1. Gemini AI detects all clothing items with bounding boxes
    2. Each item is cropped from the original image
    3. Vertex AI visual search finds matching products
    4. Returns grouped results with affiliate links
    
    Returns:
    {
        "items_found": 5,
        "total_matches": 47,
        "results": [
            {
                "item": {"category": "jacket", "description": "Black leather jacket", "color": "black"},
                "matches": [
                    {"product_id": "...", "title": "...", "price": 79.99, "affiliate_url": "..."}
                ]
            }
        ]
    }
    """
    visitor_id = "anonymous"
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if user:
            visitor_id = str(user.id)
    
    try:
        image_bytes = await file.read()
        
        stl = get_shop_the_look()
        results = stl.shop_the_look(
            image_bytes=image_bytes,
            visitor_id=visitor_id,
            matches_per_item=matches_per_item,
            return_crops=return_crops
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shop the Look failed: {str(e)}")


@router.post("/shop-the-look-base64")
async def shop_the_look_base64(
    image_base64: str,
    matches_per_item: int = Query(10, ge=1, le=50),
    return_crops: bool = Query(False),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Shop the Look with base64 image input (for FlutterFlow)
    """
    visitor_id = "anonymous"
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if user:
            visitor_id = str(user.id)
    
    try:
        image_bytes = base64.b64decode(image_base64)
        
        stl = get_shop_the_look()
        results = stl.shop_the_look(
            image_bytes=image_bytes,
            visitor_id=visitor_id,
            matches_per_item=matches_per_item,
            return_crops=return_crops
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shop the Look failed: {str(e)}")
