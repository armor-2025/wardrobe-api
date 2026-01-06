"""
AI Stylist Service - Generates outfit combinations using GPT-4o-mini
Uses wardrobe items with styling metadata to create smart outfit suggestions
"""
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

STYLIST_SYSTEM_PROMPT = """You are a modern personal stylist.

Your tone is:
- Friendly
- Confident
- Natural
- Concise

You do NOT:
- Use overly formal language
- Sound like customer support
- Over-explain
- Repeat the user's name after the greeting

You DO:
- Speak like a knowledgeable friend with great taste
- Keep responses to 1–3 short sentences
- Offer to show or change something instead of lecturing
- Use simple, modern language"""

OUTFIT_GENERATION_PROMPT = """You are an expert fashion stylist. Given a user's wardrobe items with their styling metadata, create {num_outfits} complete outfit combinations for the occasion: "{occasion}".

USER'S WARDROBE ITEMS:
{wardrobe_items}

RULES:
1. Each outfit MUST include: one top, one bottom, one pair of shoes
2. Outerwear and accessories are optional but encouraged when appropriate
3. Consider formality_level matching - items should be similar formality
4. Consider color harmony - use complementary or coordinated colors
5. Consider material appropriateness for the occasion
6. Only use item IDs from the provided wardrobe - never invent items

Return ONLY valid JSON in this exact format:
{{
  "occasion_title": "Clean title for display",
  "outfits": [
    {{
      "items": {{
        "top": <item_id>,
        "bottom": <item_id>,
        "shoes": <item_id>,
        "outerwear": <item_id or null>,
        "accessory": <item_id or null>
      }},
      "explanation": "1-2 sentence explanation of why this works"
    }}
  ]
}}"""

ADVICE_PROMPT = """You are an expert fashion stylist giving quick advice.

User question: "{question}"

Give a helpful, concise response (1-3 sentences max). If relevant, offer to show outfit examples.
End with a simple suggestion if appropriate."""


class AIStylistService:
    """
    AI Stylist that generates outfit combinations from user's wardrobe
    """
    
    def __init__(self):
        self.model = "gpt-4o-mini"
    
    def _format_wardrobe_for_prompt(self, items: List[Dict]) -> str:
        """Format wardrobe items for the GPT prompt"""
        formatted = []
        for item in items:
            item_str = f"""ID: {item['id']}
  Category: {item.get('category', 'unknown')}
  Color: {item.get('color', 'unknown')}
  Description: {item.get('description', item.get('fabric', 'unknown'))}
  Formality: {item.get('formality_level', 'casual')}
  Silhouette: {item.get('silhouette', 'regular')}
  Material: {item.get('material', 'unknown')}
  Subcategory: {item.get('subcategory', 'unknown')}"""
            formatted.append(item_str)
        return "\n\n".join(formatted)
    
    def _categorize_items(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by category for validation"""
        categorized = {
            "tops": [],
            "bottoms": [],
            "shoes": [],
            "outerwear": [],
            "accessories": []
        }
        
        for item in items:
            cat = item.get('category', '').lower()
            if cat in ['tops', 'top']:
                categorized["tops"].append(item)
            elif cat in ['bottoms', 'bottom', 'pants', 'skirts']:
                categorized["bottoms"].append(item)
            elif cat in ['footwear', 'shoes']:
                categorized["shoes"].append(item)
            elif cat in ['outerwear', 'jackets', 'coats']:
                categorized["outerwear"].append(item)
            elif cat in ['accessories', 'bags', 'jewelry']:
                categorized["accessories"].append(item)
        
        return categorized
    
    def _validate_wardrobe_coverage(self, items: List[Dict]) -> tuple:
        """Check if wardrobe has enough items for outfit generation"""
        categorized = self._categorize_items(items)
        
        missing = []
        if len(categorized["tops"]) == 0:
            missing.append("tops")
        if len(categorized["bottoms"]) == 0:
            missing.append("bottoms")
        if len(categorized["shoes"]) == 0:
            missing.append("shoes")
        
        if missing:
            return False, f"Add some {', '.join(missing)} to get outfit ideas"
        
        return True, ""
    
    async def generate_outfits(
        self, 
        wardrobe_items: List[Dict], 
        occasion: str,
        tagged_item_id: int = None,
        num_outfits: int = 3
    ) -> Dict[str, Any]:
        """
        Generate outfit combinations for a given occasion
        """
        # Validate wardrobe coverage
        has_coverage, error_msg = self._validate_wardrobe_coverage(wardrobe_items)
        if not has_coverage:
            return {"error": error_msg, "type": "insufficient_wardrobe"}
        
        # Format wardrobe for prompt
        wardrobe_text = self._format_wardrobe_for_prompt(wardrobe_items)
        
        # Build the prompt
        # Handle tagged item if provided
        tagged_prefix = ""
        if tagged_item_id:
            tagged_item = next((item for item in wardrobe_items if item["id"] == tagged_item_id), None)
            if tagged_item:
                tagged_prefix = TAGGED_ITEM_PREFIX.format(
                    item_id=tagged_item["id"],
                    category=tagged_item.get("category", "unknown"),
                    color=tagged_item.get("color", "unknown"),
                    description=tagged_item.get("description", "unknown"),
                    formality=tagged_item.get("formality_level", "casual")
                ) + "\n\n"
        
        prompt = tagged_prefix + OUTFIT_GENERATION_PROMPT.format(
            num_outfits=num_outfits,
            occasion=occasion,
            wardrobe_items=wardrobe_text
        )
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": STYLIST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Handle markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # Validate that all item IDs exist in wardrobe
            valid_ids = {item['id'] for item in wardrobe_items}
            for outfit in result.get('outfits', []):
                items = outfit.get('items', {})
                for slot, item_id in items.items():
                    if item_id is not None and item_id not in valid_ids:
                        return {"error": "Generation error - please try again", "type": "invalid_items"}
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw content: {content}")
            return {"error": "Couldn't generate outfits right now. Try again.", "type": "parse_error"}
        except Exception as e:
            print(f"Outfit generation error: {e}")
            return {"error": "Couldn't generate outfits right now. Try again.", "type": "api_error"}
    
    async def get_styling_advice(self, question: str) -> Dict[str, Any]:
        """Get general styling advice for a question"""
        prompt = ADVICE_PROMPT.format(question=question)
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": STYLIST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            advice = response.choices[0].message.content.strip()
            
            # Generate suggested actions based on the question
            suggestions = []
            question_lower = question.lower()
            
            if any(word in question_lower for word in ['work', 'office', 'professional', 'meeting']):
                suggestions.append({"label": "Show work outfits", "occasion": "work"})
            if any(word in question_lower for word in ['casual', 'weekend', 'relaxed']):
                suggestions.append({"label": "Show casual looks", "occasion": "casual weekend"})
            if any(word in question_lower for word in ['date', 'dinner', 'evening']):
                suggestions.append({"label": "Show date night looks", "occasion": "dinner date"})
            if any(word in question_lower for word in ['expensive', 'polished', 'chic']):
                suggestions.append({"label": "Show polished outfits", "occasion": "polished everyday"})
            
            if not suggestions:
                suggestions = [{"label": "Show outfit ideas", "occasion": "everyday casual"}]
            
            return {
                "response": advice,
                "suggestions": suggestions[:2]
            }
            
        except Exception as e:
            print(f"Styling advice error: {e}")
            return {
                "response": "Let me help — what are you dressing for today?",
                "suggestions": [{"label": "Show outfit ideas", "occasion": "everyday casual"}]
            }
    
    def detect_message_type(self, message: str) -> str:
        """Detect if message is an occasion request or general advice question"""
        message_lower = message.lower().strip()
        
        occasion_patterns = [
            'date', 'meeting', 'interview', 'wedding', 'party', 'dinner',
            'brunch', 'lunch', 'coffee', 'drinks', 'work', 'office',
            'casual', 'formal', 'smart', 'pub', 'bar', 'restaurant',
            'birthday', 'event', 'occasion', 'going to', 'attending',
            'dressing for', 'outfit for', 'what to wear to', 'wear to'
        ]
        
        advice_patterns = [
            'how do i', 'how can i', 'what makes', 'why does', 'should i',
            'is it okay', 'can i wear', 'does this', 'help me understand',
            'tips for', 'advice on', 'how to make', 'what\'s the best way'
        ]
        
        for pattern in advice_patterns:
            if pattern in message_lower:
                return "advice"
        
        for pattern in occasion_patterns:
            if pattern in message_lower:
                return "occasion"
        
        if len(message.split()) <= 5:
            return "occasion"
        
        return "advice"


_stylist_service = None

def get_stylist_service() -> AIStylistService:
    global _stylist_service
    if _stylist_service is None:
        _stylist_service = AIStylistService()
    return _stylist_service


TAGGED_ITEM_PREFIX = """IMPORTANT: The user has selected this specific item to build outfits around. 
This item is FIXED and MUST be included in EVERY outfit:
- Item ID: {item_id}
- Category: {category}
- Color: {color}
- Description: {description}
- Formality: {formality}

Build all outfits around this piece. Do not remove or substitute it."""
