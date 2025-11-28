"""
ASOS API Service for RapidAPI
Handles all ASOS API calls from the backend
"""
import os
import requests
from typing import Optional, List, Dict, Any
from fastapi import HTTPException


class AsosService:
    """Service class for ASOS RapidAPI integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY", "")
        self.base_url = "https://asos2.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "asos2.p.rapidapi.com"
        }
        
        if not self.api_key or self.api_key == "":
            print("WARNING: RAPIDAPI_KEY not set. ASOS search will not work.")
    
    def search_products(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        country: str = "US",
        currency: str = "USD",
        store: str = "US",
        size_schema: str = "US",
        lang: str = "en-US",
        sort: str = "freshness"
    ) -> Dict[str, Any]:
        """
        Search ASOS products
        
        Args:
            query: Search term (e.g., "red dress")
            limit: Number of results (max 50)
            offset: Pagination offset
            country: Country code (US, GB, etc.)
            currency: Currency code (USD, GBP, etc.)
            store: Store location
            size_schema: Size system (US, UK, etc.)
            lang: Language code
            sort: Sort order (freshness, pricedesc, priceasc, relevance)
        
        Returns:
            Dictionary with search results
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/products/v2/list"
        
        params = {
            "store": store,
            "offset": offset,
            "limit": min(limit, 50),
            "country": country,
            "sort": sort,
            "q": query,
            "currency": currency,
            "sizeSchema": size_schema,
            "lang": lang,
        }
        
        try:
            response = requests.get(url, headers=self.headers, 
params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid RapidAPI key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"ASOS API error: {str(e)}"
                )
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="ASOS API timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASOS API error: {str(e)}")
    
    def get_product_details(
        self,
        product_id: str,
        lang: str = "en-US",
        store: str = "US",
        size_schema: str = "US",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific product
        
        Args:
            product_id: ASOS product ID
            lang: Language code
            store: Store location
            size_schema: Size system
            currency: Currency code
        
        Returns:
            Dictionary with product details
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/products/v3/detail"
        
        params = {
            "id": product_id,
            "lang": lang,
            "store": store,
            "sizeSchema": size_schema,
            "currency": currency,
        }
        
        try:
            response = requests.get(url, headers=self.headers, 
params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Product not found")
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"ASOS API error: {str(e)}"
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASOS API error: {str(e)}")
    def get_categories(
        self,
        country: str = "US",
        lang: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Get available ASOS categories
        
        Args:
            country: Country code
            lang: Language code
        
        Returns:
            Dictionary with category data
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/categories/list"
        
        params = {
            "country": country,
            "lang": lang,
        }
        
        try:
            response = requests.get(url, headers=self.headers, 
params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASOS API error: {str(e)}")
    
    def autocomplete(
        self,
        query: str,
        lang: str = "en-US",
        country: str = "US",
        currency: str = "USD",
        size_schema: str = "US"
    ) -> Dict[str, Any]:
        """
        Get autocomplete suggestions
        
        Args:
            query: Partial search term
            lang: Language code
            country: Country code
            currency: Currency code
            size_schema: Size system
        
        Returns:
            Dictionary with suggestions
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="RAPIDAPI_KEY not configured on server"
            )
        
        url = f"{self.base_url}/auto-complete"
        
        params = {
            "q": query,
            "lang": lang,
            "country": country,
            "currency": currency,
            "sizeSchema": size_schema,
        }
        
        try:
            response = requests.get(url, headers=self.headers, 
params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASOS API error: {str(e)}")


_asos_service = None

def get_asos_service() -> AsosService:
    """Get or create the ASOS service singleton"""
    global _asos_service
    if _asos_service is None:
        _asos_service = AsosService()
    return _asos_service
