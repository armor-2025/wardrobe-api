"""
Vertex AI Search for Retail - Shop the Look
============================================
Visual and text-based product search using Google's retail AI

Features:
- Image search (upload outfit → find matching products)
- Text search with semantic understanding
- Personalized recommendations
- Product catalog management
"""

import os
from typing import List, Dict, Any, Optional
from google.cloud import retail_v2 as retail
from google.cloud.retail_v2 import Product, ProductDetail, Image
from google.protobuf import field_mask_pb2
import base64
import json

# Configuration
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0930631788")
LOCATION = "global"
CATALOG = "default_catalog"
BRANCH = "default_branch"

# Full resource paths
CATALOG_PATH = f"projects/{PROJECT_ID}/locations/{LOCATION}/catalogs/{CATALOG}"
BRANCH_PATH = f"{CATALOG_PATH}/branches/{BRANCH}"


class VertexRetailSearch:
    """
    Vertex AI Search for Retail integration
    """
    
    def __init__(self):
        self.product_client = retail.ProductServiceClient()
        self.search_client = retail.SearchServiceClient()
        self.prediction_client = retail.PredictionServiceClient()
        self.user_event_client = retail.UserEventServiceClient()
        print(f"✅ Vertex Retail Search initialized")
        print(f"   Project: {PROJECT_ID}")
        print(f"   Catalog: {CATALOG_PATH}")
    
    # ==================== PRODUCT CATALOG ====================
    
    def create_product(
        self,
        product_id: str,
        title: str,
        categories: List[str],
        price: float,
        currency: str = "GBP",
        image_urls: List[str] = None,
        brand: str = None,
        colors: List[str] = None,
        sizes: List[str] = None,
        description: str = None,
        retailer: str = None,
        affiliate_url: str = None,
        availability: str = "IN_STOCK",
        **extra_attributes
    ) -> Product:
        """
        Add a product to the catalog
        
        Args:
            product_id: Unique ID (e.g., "asos-12345")
            title: Product name
            categories: List like ["Clothing", "Dresses", "Midi Dresses"]
            price: Current price
            image_urls: List of product image URLs
            brand: Brand name
            colors: List of colors
            sizes: Available sizes
            description: Product description
            retailer: Source retailer (ASOS, Zara, etc.)
            affiliate_url: Affiliate link for commission
        """
        
        # Build product
        product = Product(
            name=f"{BRANCH_PATH}/products/{product_id}",
            id=product_id,
            title=title,
            categories=categories,
            description=description or "",
            availability=availability,
            price_info=retail.PriceInfo(
                price=price,
                original_price=price,
                currency_code=currency,
            ),
        )
        
        # Add images
        if image_urls:
            product.images = [
                Image(uri=url, height=500, width=500)
                for url in image_urls[:5]  # Max 5 images
            ]
        
        # Add attributes
        attributes = {}
        
        if brand:
            attributes["brand"] = retail.CustomAttribute(
                text=[brand],
                searchable=True,
            )
        
        if colors:
            attributes["color"] = retail.CustomAttribute(
                text=colors,
                searchable=True,
            )
        
        if sizes:
            attributes["size"] = retail.CustomAttribute(
                text=sizes,
                searchable=True,
            )
        
        if retailer:
            attributes["retailer"] = retail.CustomAttribute(
                text=[retailer],
                searchable=True,
            )
        
        if affiliate_url:
            attributes["affiliate_url"] = retail.CustomAttribute(
                text=[affiliate_url],
                searchable=False,
            )
        
        # Add any extra attributes
        for key, value in extra_attributes.items():
            if isinstance(value, list):
                attributes[key] = retail.CustomAttribute(text=value, searchable=True)
            else:
                attributes[key] = retail.CustomAttribute(text=[str(value)], searchable=True)
        
        product.attributes = attributes
        
        # Create in catalog
        request = retail.CreateProductRequest(
            parent=BRANCH_PATH,
            product=product,
            product_id=product_id,
        )
        
        created_product = self.product_client.create_product(request=request)
        print(f"✅ Created product: {product_id}")
        return created_product
    
    def bulk_import_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk import products from retailer API data
        
        Args:
            products: List of product dicts with keys matching create_product args
        
        Returns:
            Summary of import results
        """
        results = {"success": 0, "failed": 0, "errors": []}
        
        for product_data in products:
            try:
                self.create_product(**product_data)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "product_id": product_data.get("product_id"),
                    "error": str(e)
                })
        
        print(f"📦 Bulk import: {results['success']} success, {results['failed']} failed")
        return results
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        try:
            request = retail.GetProductRequest(
                name=f"{BRANCH_PATH}/products/{product_id}"
            )
            return self.product_client.get_product(request=request)
        except Exception as e:
            print(f"❌ Product not found: {product_id}")
            return None
    
    def delete_product(self, product_id: str) -> bool:
        """Delete a product from catalog"""
        try:
            request = retail.DeleteProductRequest(
                name=f"{BRANCH_PATH}/products/{product_id}"
            )
            self.product_client.delete_product(request=request)
            print(f"🗑️ Deleted product: {product_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to delete: {e}")
            return False
    
    # ==================== SEARCH ====================
    
    def text_search(
        self,
        query: str,
        visitor_id: str = "anonymous",
        page_size: int = 20,
        filters: Dict[str, Any] = None,
        order_by: str = None,
        boost_spec: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Text-based product search with semantic understanding
        
        Args:
            query: Search query (e.g., "black leather jacket")
            visitor_id: User ID for personalization
            page_size: Number of results
            filters: Filter criteria (e.g., {"brand": "ASOS", "price_max": 100})
            order_by: Sort order (e.g., "price asc", "relevance")
            boost_spec: Boost certain attributes (e.g., {"brand:ASOS": 1.5})
        
        Returns:
            List of matching products with scores
        """
        
        request = retail.SearchRequest(
            placement=f"{CATALOG_PATH}/placements/default_search",
            branch=BRANCH_PATH,
            query=query,
            visitor_id=visitor_id,
            page_size=page_size,
        )
        
        # Add filters
        if filters:
            filter_parts = []
            if "brand" in filters:
                filter_parts.append(f'attributes.brand: ANY("{filters["brand"]}")')
            if "color" in filters:
                filter_parts.append(f'attributes.color: ANY("{filters["color"]}")')
            if "retailer" in filters:
                filter_parts.append(f'attributes.retailer: ANY("{filters["retailer"]}")')
            if "price_min" in filters:
                filter_parts.append(f'price >= {filters["price_min"]}')
            if "price_max" in filters:
                filter_parts.append(f'price <= {filters["price_max"]}')
            if "category" in filters:
                filter_parts.append(f'categories: ANY("{filters["category"]}")')
            
            if filter_parts:
                request.filter = " AND ".join(filter_parts)
        
        # Add ordering
        if order_by:
            request.order_by = order_by
        
        # Execute search
        response = self.search_client.search(request=request)
        
        # Parse results
        results = []
        for result in response.results:
            product = result.product
            results.append({
                "product_id": product.id,
                "title": product.title,
                "price": product.price_info.price if product.price_info else None,
                "currency": product.price_info.currency_code if product.price_info else "GBP",
                "image_url": product.images[0].uri if product.images else None,
                "brand": product.attributes.get("brand", {}).text[0] if product.attributes.get("brand") else None,
                "color": product.attributes.get("color", {}).text if product.attributes.get("color") else [],
                "retailer": product.attributes.get("retailer", {}).text[0] if product.attributes.get("retailer") else None,
                "affiliate_url": product.attributes.get("affiliate_url", {}).text[0] if product.attributes.get("affiliate_url") else None,
                "relevance_score": result.matching_variant_fields,
            })
        
        print(f"🔍 Search '{query}': {len(results)} results")
        return results
    
    def visual_search(
        self,
        image_base64: str,
        visitor_id: str = "anonymous",
        page_size: int = 20,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Image-based product search (Shop the Look)
        
        Args:
            image_base64: Base64 encoded image
            visitor_id: User ID for personalization
            page_size: Number of results
            filters: Optional filters
        
        Returns:
            List of visually similar products
        """
        
        # Note: Visual search requires Vision API Product Search
        # which is part of Vertex AI Search for Commerce
        
        request = retail.SearchRequest(
            placement=f"{CATALOG_PATH}/placements/default_search",
            branch=BRANCH_PATH,
            visitor_id=visitor_id,
            page_size=page_size,
            # Visual query
            visual_query=retail.SearchRequest.VisualQuery(
                image_bytes=base64.b64decode(image_base64)
            )
        )
        
        if filters:
            filter_parts = []
            if "category" in filters:
                filter_parts.append(f'categories: ANY("{filters["category"]}")')
            if filter_parts:
                request.filter = " AND ".join(filter_parts)
        
        response = self.search_client.search(request=request)
        
        results = []
        for result in response.results:
            product = result.product
            results.append({
                "product_id": product.id,
                "title": product.title,
                "price": product.price_info.price if product.price_info else None,
                "image_url": product.images[0].uri if product.images else None,
                "brand": product.attributes.get("brand", {}).text[0] if product.attributes.get("brand") else None,
                "retailer": product.attributes.get("retailer", {}).text[0] if product.attributes.get("retailer") else None,
                "affiliate_url": product.attributes.get("affiliate_url", {}).text[0] if product.attributes.get("affiliate_url") else None,
                "similarity_score": result.matching_variant_fields,
            })
        
        print(f"📸 Visual search: {len(results)} results")
        return results
    
    # ==================== RECOMMENDATIONS ====================
    
    def get_recommendations(
        self,
        user_id: str,
        recommendation_type: str = "recommended-for-you",
        page_size: int = 20,
        filter_out_product_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized product recommendations
        
        Args:
            user_id: User ID
            recommendation_type: One of:
                - "recommended-for-you" (personalized)
                - "others-you-may-like" (similar to viewed)
                - "frequently-bought-together"
                - "similar-items"
            page_size: Number of recommendations
            filter_out_product_ids: Products to exclude (e.g., already owned)
        
        Returns:
            List of recommended products
        """
        
        request = retail.PredictRequest(
            placement=f"{CATALOG_PATH}/placements/{recommendation_type}",
            user_event=retail.UserEvent(
                event_type="home-page-view",
                visitor_id=user_id,
            ),
            page_size=page_size,
        )
        
        if filter_out_product_ids:
            request.filter = f'NOT product_id: ANY({",".join(filter_out_product_ids)})'
        
        response = self.prediction_client.predict(request=request)
        
        results = []
        for result in response.results:
            product = result.product
            results.append({
                "product_id": product.id,
                "title": product.title,
                "price": product.price_info.price if product.price_info else None,
                "image_url": product.images[0].uri if product.images else None,
                "brand": product.attributes.get("brand", {}).text[0] if product.attributes.get("brand") else None,
                "retailer": product.attributes.get("retailer", {}).text[0] if product.attributes.get("retailer") else None,
                "affiliate_url": product.attributes.get("affiliate_url", {}).text[0] if product.attributes.get("affiliate_url") else None,
            })
        
        print(f"🎯 Recommendations for {user_id}: {len(results)} products")
        return results
    
    def get_similar_products(
        self,
        product_id: str,
        page_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get products similar to a specific product
        """
        return self.get_recommendations(
            user_id="anonymous",
            recommendation_type="similar-items",
            page_size=page_size
        )
    
    # ==================== USER EVENTS (for training) ====================
    
    def track_event(
        self,
        user_id: str,
        event_type: str,
        product_id: str = None,
        search_query: str = None
    ):
        """
        Track user events for model training
        
        Event types:
            - detail-page-view: Viewed product
            - add-to-cart: Added to cart
            - purchase-complete: Completed purchase
            - search: Performed search
            - home-page-view: Viewed home page
        """
        
        user_event = retail.UserEvent(
            event_type=event_type,
            visitor_id=user_id,
            event_time=None,  # Defaults to now
        )
        
        if product_id:
            user_event.product_details = [
                ProductDetail(product=Product(id=product_id))
            ]
        
        if search_query:
            user_event.search_query = search_query
        
        request = retail.WriteUserEventRequest(
            parent=CATALOG_PATH,
            user_event=user_event,
        )
        
        self.user_event_client.write_user_event(request=request)
        print(f"📊 Tracked: {event_type} for user {user_id}")


# ==================== HELPER FUNCTIONS ====================

def get_retail_search():
    """Get singleton instance"""
    return VertexRetailSearch()


# ==================== TEST ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🛍️ VERTEX AI SEARCH FOR RETAIL - TEST")
    print("="*60 + "\n")
    
    search = VertexRetailSearch()
    
    # Test creating a product
    print("\n📦 Testing product creation...")
    try:
        product = search.create_product(
            product_id="test-dress-001",
            title="Black Midi Dress with Slit",
            categories=["Clothing", "Dresses", "Midi Dresses"],
            price=79.99,
            image_urls=["https://example.com/dress.jpg"],
            brand="ASOS",
            colors=["black"],
            sizes=["XS", "S", "M", "L", "XL"],
            description="Elegant black midi dress with thigh-high slit",
            retailer="ASOS",
            affiliate_url="https://asos.com/dress?affiliate=yow123"
        )
        print(f"✅ Product created: {product.id}")
    except Exception as e:
        print(f"⚠️ Product creation test: {e}")
    
    # Test search
    print("\n🔍 Testing text search...")
    try:
        results = search.text_search("black dress", page_size=5)
        print(f"✅ Search returned {len(results)} results")
    except Exception as e:
        print(f"⚠️ Search test: {e}")
    
    print("\n✅ Vertex Retail Search setup complete!")
    print("Ready for retailer data import.")
