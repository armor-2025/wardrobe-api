"""
ASOS API Service - DataCrawler API (asos10)
==========================================
Updated to use the working DataCrawler API from RapidAPI
"""
import os
import requests
from typing import Optional, List, Dict, Any
from fastapi import HTTPException


class AsosService:
    """Service class for ASOS DataCrawler RapidAPI integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY", "")
        self.base_url = "https://asos10.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "asos10.p.rapidapi.com"
        }
        
        if not self.api_key or self.api_key == "":
            print("⚠️  WARNING: RAPIDAPI_KEY not set. ASOS search will not work.")
    
    def search_products(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        country: str = "US",
        currency: str = "USD",
        store: str = "US",
        size_schema: str = "US",
        lang: str = "en",
        sort: str = "recommended"
    ) -> Dict[str, Any]:
        """
        Search ASOS products using DataCrawler API
        
        Args:
            query: Search term (e.g., "red dress", "black jeans")
            limit: Number of results (max 50)
            offset: Pagination offset
            country: Country code (US, GB, etc.)
            currency: Currency code (USD, GBP, EUR, etc.)
            store: Store location (US, GB, etc.)
            size_schema: Size system (US, UK, EU, etc.)
            lang: Language code (en, etc.)
            sort: Sort order (recommended, freshness, pricedesc, priceasc)
        
        Returns:
            Dictionary with search results
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/api/v1/getProductListBySearchTerm"
        
        params = {
            "searchTerm": query,
            "limit": min(limit, 50),
            "offset": offset,
            "country": country,
            "currency": currency,
            "store": store,
            "sizeSchema": size_schema,
            "languageShort": lang,
            "sort": sort,
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check if response is valid
            if not data.get("status"):
                raise HTTPException(
                    status_code=500,
                    detail=f"ASOS API error: {data.get('message', 'Unknown error')}"
                )
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid ASOS API key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="ASOS API rate limit exceeded")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="ASOS API timeout")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"ASOS API request failed: {str(e)}")
    
    def search_products_simple(
        self,
        query: str,
        limit: int = 20,
        country: str = "US",
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """
        Simplified search that returns a clean list of products
        
        Args:
            query: Search term
            limit: Number of results
            country: Country code
            currency: Currency code
        
        Returns:
            List of product dictionaries with standardized fields
        """
        raw_data = self.search_products(
            query=query,
            limit=limit,
            country=country,
            currency=currency,
            store=country  # Use country as store
        )
        
        products = []
        raw_products = raw_data.get("data", {}).get("products", [])
        
        for item in raw_products:
            product = {
                "id": item.get("id"),
                "name": item.get("name"),
                "brand": item.get("brandName"),
                "color": item.get("colour"),
                "price": item.get("price", {}).get("current", {}).get("value"),
                "price_text": item.get("price", {}).get("current", {}).get("text"),
                "original_price": item.get("price", {}).get("previous", {}).get("value"),
                "original_price_text": item.get("price", {}).get("previous", {}).get("text"),
                "is_on_sale": item.get("price", {}).get("isMarkedDown", False),
                "image_url": f"https://{item.get('imageUrl')}" if item.get("imageUrl") else None,
                "additional_images": [
                    f"https://{img}" for img in item.get("additionalImageUrls", [])
                ],
                "product_url": f"https://www.asos.com/{item.get('url')}" if item.get("url") else None,
                "is_selling_fast": item.get("isSellingFast", False),
            }
            products.append(product)
        
        return products
    
    def get_product_detail(self, product_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific product
        
        Args:
            product_id: ASOS product ID
        
        Returns:
            Product detail dictionary
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/api/v1/getProductById"
        
        params = {
            "productId": product_id,
            "country": "US",
            "currency": "USD",
            "store": "US",
            "languageShort": "en",
            "sizeSchema": "US"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    
    def shop_the_look(
        self,
        items: List[str],
        limit_per_item: int = 10,
        country: str = "US",
        currency: str = "USD"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for similar products for multiple items (shop the whole look)
        
        Args:
            items: List of search terms (e.g., ["black blazer", "white shirt", "navy trousers"])
            limit_per_item: Number of results per item
            country: Country code
            currency: Currency code
        
        Returns:
            Dictionary mapping each search term to its results
        """
        results = {}
        
        for item in items:
            try:
                products = self.search_products_simple(
                    query=item,
                    limit=limit_per_item,
                    country=country,
                    currency=currency
                )
                results[item] = products
            except Exception as e:
                print(f"Error searching for '{item}': {e}")
                results[item] = []
        
        return results


# Create a default instance for easy importing
_default_service = None

def get_asos_service() -> AsosService:
    """Get or create the default ASOS service instance"""
    global _default_service
    if _default_service is None:
        _default_service = AsosService()
    return _default_service


# Quick test if run directly
if __name__ == "__main__":
    import json
    
    print("Testing ASOS DataCrawler Service...")
    
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("Set RAPIDAPI_KEY environment variable first!")
        print("export RAPIDAPI_KEY=your_key_here")
        exit(1)
    
    service = AsosService(api_key)
    
    # Test search
    print("\n🔍 Searching for 'black dress'...")
    products = service.search_products_simple("black dress", limit=3)
    
    for i, p in enumerate(products, 1):
        print(f"\n{i}. {p['name']}")
        print(f"   Brand: {p['brand']}")
        print(f"   Price: {p['price_text']}")
        print(f"   Image: {p['image_url']}")
    
    print(f"\n✅ Found {len(products)} products!")
