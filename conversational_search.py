"""
Conversational Search Service
Uses GPT-4o-mini with Structured Outputs for reliable JSON extraction
Escalates to GPT-4.1-mini for complex queries
"""
import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from fastapi import HTTPException


# JSON Schema for Structured Outputs
SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "search_query": {
            "type": "string",
            "description": "Main keywords for text search"
        },
        "category": {
            "type": "string",
            "enum": ["dress", "top", "shirt", "blouse", "jeans", "trousers", "shorts", "skirt", "jacket", "coat", "shoes", "boots", "bag", "accessories"],
            "description": "Type of clothing"
        },
        "color": {
            "type": "string",
            "description": "Color mentioned"
        },
        "occasion": {
            "type": "string",
            "enum": ["wedding", "party", "casual", "work", "formal", "date", "vacation", "everyday"],
            "description": "Event type"
        },
        "style": {
            "type": "string",
            "description": "Style descriptors (formal, casual, vintage, minimalist, etc.)"
        },
        "min_price": {
            "type": "number",
            "description": "Minimum price"
        },
        "max_price": {
            "type": "number",
            "description": "Maximum price"
        },
        "size": {
            "type": "string",
            "description": "Size mentioned"
        },
        "brand": {
            "type": "string",
            "description": "Specific brand mentioned"
        },
        "length": {
            "type": "string",
            "enum": ["mini", "midi", "maxi", "cropped", "full-length"],
            "description": "For dresses/skirts/trousers"
        },
        "material": {
            "type": "string",
            "description": "Fabric type"
        },
        "season": {
            "type": "string",
            "enum": ["spring", "summer", "autumn", "winter"],
            "description": "Season/weather suitability"
        }
    },
    "required": ["search_query"],
    "additionalProperties": False
}


class ConversationalSearchService:
    """AI-powered natural language search query parser with Structured Outputs"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            print("⚠️  WARNING: OPENAI_API_KEY not set. Conversational search will not work.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
        
        # Simple cache for repeated queries
        self._cache = {}
    
    def parse_query(self, user_query: str, use_advanced: bool = False) -> Dict[str, Any]:
        if not self.client:
            raise HTTPException(status_code=500, detail="OpenAI API not configured")
        
        # Check cache first
        cache_key = user_query.lower().strip()
        if cache_key in self._cache:
            print(f"✅ Cache hit for: {user_query}")
            return self._cache[cache_key]
        
        model = "gpt-4.1-mini" if use_advanced else "gpt-4o-mini"
        
        system_prompt = """You are a fashion search assistant. Parse user queries into structured search parameters.

Extract ONLY fields that are explicitly mentioned or strongly implied.
For prices, extract numbers only (e.g., "under £100" → max_price: 100).
Always include a search_query with relevant keywords."""

        user_prompt = f'Parse this fashion search: "{user_query}"'

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "fashion_search",
                        "strict": True,
                        "schema": SEARCH_SCHEMA
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            result["_model_used"] = model
            result["_original_query"] = user_query
            
            # Escalate if search_query is empty or too generic
            if not use_advanced and (not result.get("search_query") or len(result.get("search_query", "")) < 3):
                print(f"⚠️  Weak extraction with {model}, escalating to gpt-4.1-mini...")
                return self.parse_query(user_query, use_advanced=True)
            
            # Cache successful result
            self._cache[cache_key] = result
            
            return result
            
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {e}")
        except Exception as e:
            # If structured output fails, escalate
            if not use_advanced:
                print(f"⚠️  Error with {model}, escalating: {e}")
                return self.parse_query(user_query, use_advanced=True)
            raise HTTPException(status_code=500, detail=f"AI query parsing error: {e}")
    
    def query_to_search_params(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "q": parsed.get("search_query", ""),
            "limit": 20
        }
        
        if "max_price" in parsed:
            params["max_price"] = parsed["max_price"]
        if "min_price" in parsed:
            params["min_price"] = parsed["min_price"]
        if "category" in parsed:
            params["q"] += f" {parsed['category']}"
        if "color" in parsed:
            params["q"] += f" {parsed['color']}"
        if "occasion" in parsed:
            params["q"] += f" {parsed['occasion']}"
        if "style" in parsed:
            params["q"] += f" {parsed['style']}"
        if "length" in parsed:
            params["q"] += f" {parsed['length']}"
        if "material" in parsed:
            params["q"] += f" {parsed['material']}"
        
        return params


_conversational_service = None

def get_conversational_service() -> ConversationalSearchService:
    global _conversational_service
    if _conversational_service is None:
        _conversational_service = ConversationalSearchService()
    return _conversational_service
