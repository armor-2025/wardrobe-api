"""
Conversational Search Service
Uses GPT-4o-mini for initial query parsing, escalates to GPT-4o if needed
"""
import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from fastapi import HTTPException


class ConversationalSearchService:
    """AI-powered natural language search query parser"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            print("⚠️  WARNING: OPENAI_API_KEY not set. Conversational search will not work.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
    
    def parse_query(self, user_query: str, use_advanced: bool = False) -> Dict[str, Any]:
        if not self.client:
            raise HTTPException(status_code=500, detail="OpenAI API not configured")
        
        model = "gpt-4o" if use_advanced else "gpt-4o-mini"
        
        system_prompt = """You are a fashion search assistant. Parse user queries into structured search parameters.

Extract these fields when relevant:
- search_query: Main keywords for text search (always include this)
- category: Type of clothing (dress, top, jeans, jacket, shoes, etc.)
- color: Color mentioned (red, blue, black, etc.)
- occasion: Event type (wedding, party, casual, work, etc.)
- style: Style descriptors (formal, casual, vintage, minimalist, etc.)
- min_price: Minimum price (number)
- max_price: Maximum price (number)
- size: Size mentioned (S, M, L, XL, 8, 10, etc.)
- brand: Specific brand mentioned
- length: For dresses/skirts (mini, midi, maxi)
- material: Fabric type (cotton, silk, denim, etc.)

IMPORTANT:
- Always include search_query with relevant keywords
- Only include fields that are explicitly mentioned or strongly implied
- For prices, extract numbers only (e.g., "under £100" → max_price: 100)
- If uncertain, return confidence: "low" so we can escalate

Return ONLY valid JSON, no other text."""

        user_prompt = f"""Parse this fashion search query into structured parameters:

Query: "{user_query}"

Return JSON only."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["_model_used"] = model
            result["_original_query"] = user_query
            
            confidence = result.get("confidence", "high")
            if confidence == "low" and not use_advanced:
                print(f"⚠️  Low confidence with {model}, escalating to GPT-4o...")
                return self.parse_query(user_query, use_advanced=True)
            
            return result
            
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {e}")
        except Exception as e:
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
