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

STYLING_KNOWLEDGE = """
## COLOR RULES
- Use color wheel theory: complementary (opposites), analogous (adjacent), or monochromatic (shades of one)
- Neutrals (black, white, grey, navy, beige) pair with anything
- 60-30-10 rule: 60% dominant color, 30% secondary, 10% accent
- Keep tone consistency: warm tones together, cool tones together

## PROPORTION RULES
- Oversized top → fitted bottom (and vice versa)
- Avoid oversized + oversized unless intentional
- Rule of thirds: 1/3 top + 2/3 bottom is universally flattering

## FORMALITY MATCHING
- Items should be within 1-2 formality levels of each other
- Shoes often set the overall formality tone
"""

ACTIVITY_CONSTRAINTS = {
    "walking": {
        "triggers": ["walk", "sightseeing", "exploring", "errands", "shopping", "market", "museum", "city", "stroll", "tour", "travel day", "day trip", "city break"],
        "rules": """
ACTIVITY CONSTRAINTS (ENFORCED - DO NOT MENTION IN EXPLANATION):
- Footwear MUST be walkable: flats, trainers, low boots, block heels only
- NO stilettos, thin heels, or unstable footwear
- NO restrictive silhouettes that limit movement
- Outfit must be wearable for half a day minimum
"""
    },
    "cold_weather": {
        "triggers": ["winter", "cold", "freezing", "snow", "december", "january", "february", "autumn", "fall"],
        "rules": """
WEATHER CONSTRAINTS (ENFORCED - DO NOT MENTION IN EXPLANATION):
- Outerwear is REQUIRED
- NO sheer-only layers without warm base layers
- NO bare legs without tights/thick socks
- Footwear must be weather-appropriate
"""
    },
    "hot_weather": {
        "triggers": ["summer", "hot", "beach", "july", "august", "vacation", "holiday sun"],
        "rules": """
WEATHER CONSTRAINTS (ENFORCED - DO NOT MENTION IN EXPLANATION):
- Breathable fabrics required
- NO heavy layering
- Footwear must be heat-appropriate
"""
    },
    "rain": {
        "triggers": ["rain", "rainy", "wet", "drizzle"],
        "rules": """
WEATHER CONSTRAINTS (ENFORCED - DO NOT MENTION IN EXPLANATION):
- Weather-appropriate outerwear required
- NO suede or delicate shoes
- NO long hems that drag
"""
    },
    "active": {
        "triggers": ["gym", "workout", "run", "cycling", "sport", "hiking", "active"],
        "rules": """
ACTIVITY CONSTRAINTS (ENFORCED - DO NOT MENTION IN EXPLANATION):
- Activity-appropriate footwear only
- NO restrictive or delicate fabrics
- Prioritise movement and comfort
"""
    },
    "formal": {
        "triggers": ["wedding", "gala", "black tie", "formal event", "ceremony"],
        "rules": """
FORMALITY CONSTRAINTS (ENFORCED):
- Formal dress code required
- Elevated footwear and accessories expected
- Smart tailoring prioritised
"""
    }
}

EXPLANATION_RULES = """
## EXPLANATION GUIDELINES (STRICT)

Explanations must TEACH STYLE, not state the obvious.

✅ FOCUS ON:
- Color harmony (complementary, analogous, monochromatic)
- Proportion balance (volume distribution, rule of thirds)
- Texture contrast (soft vs structured, matte vs shine)
- Tonal cohesion (warm/cool consistency)
- Why pieces elevate each other

❌ NEVER MENTION:
- "Keeps you warm" / "Protects from cold"
- "Comfortable for walking" / "Practical"
- "Weather-appropriate" / "Good for rain"
- Any obvious functionality

Practicality is enforced silently. Explanations educate on taste.

GOOD: "The longer coat balances the fluid skirt, while the neutral palette keeps it refined."
BAD: "The coat keeps you warm and the boots are practical for walking."
"""


def get_activity_constraints(occasion: str) -> str:
    """Detect activity type and return hard constraints"""
    occasion_lower = occasion.lower()
    constraints = []
    
    for activity, config in ACTIVITY_CONSTRAINTS.items():
        if any(trigger in occasion_lower for trigger in config["triggers"]):
            constraints.append(config["rules"])
    
    return "\n".join(constraints) if constraints else ""


OUTFIT_GENERATION_PROMPT = """You are an expert fashion stylist using color theory and styling principles.

{styling_knowledge}

{activity_constraints}

{explanation_rules}

Create {num_outfits} outfit combinations for: "{occasion}".

USER'S WARDROBE ITEMS:
{wardrobe_items}

RULES:
1. Each outfit MUST include: one top, one bottom, one pair of shoes
2. Bags are ESSENTIAL for women's outfits - include one in almost every outfit:
   - Crossbody/shoulder bag: casual daytime, shopping, errands
   - Tote: work, travel, beach
   - Clutch/mini bag: evening events, dinner dates
   - Only skip bag for: gym, athletic activities, very short outings
3. Sunglasses: REQUIRED for any daytime outdoor occasion (walking, brunch, beach, shopping)
4. Other accessories encouraged (jewelry, scarves, belts, hats)
5. Outerwear REQUIRED if weather/activity demands
6. Apply color wheel theory for color matching
7. Balance proportions (oversized top = fitted bottom)
8. Match formality levels across items
9. Activity and weather constraints are NON-NEGOTIABLE
10. VARIETY IS KEY: Do NOT repeat the same items across outfits. Use DIFFERENT pieces for each outfit unless wardrobe is very limited.
11. Only use item IDs from the provided wardrobe - never invent items

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
        "bag": <item_id or null>,
        "accessory": <item_id or null>
      }},
      "explanation": "1-2 sentences about COLOR HARMONY, PROPORTION, or TEXTURE BALANCE only"
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
        import random
        items = items.copy()  # Don't modify original
        random.shuffle(items)  # Avoid positional bias - GPT favors early items
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
            "bags": [],
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
            elif cat in ['bags']:
                categorized["bags"].append(item)
            elif cat in ['accessories', 'jewelry']:
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
        tagged_item_ids: List[int] = None,
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
        
        # Get activity-based constraints
        activity_constraints = get_activity_constraints(occasion)
        
        # Build the prompt
        # Handle tagged items if provided (supports multiple)
        tagged_prefix = ""
        if tagged_item_ids and len(tagged_item_ids) > 0:
            tagged_items = [item for item in wardrobe_items if item["id"] in tagged_item_ids]
            if tagged_items:
                items_list = []
                for item in tagged_items:
                    items_list.append(f"- {item.get('category', 'unknown')} (ID: {item['id']}): {item.get('color', 'unknown')} {item.get('description', 'unknown')}")
                items_text = "\n".join(items_list)
                tagged_prefix = f"IMPORTANT: The user has selected these specific items to build outfits around.\nThese items are FIXED and MUST ALL be included in EVERY outfit:\n{items_text}\n\nBuild all outfits around these pieces. Do not remove or substitute them.\n\n"
        
        prompt = tagged_prefix + OUTFIT_GENERATION_PROMPT.format(
            styling_knowledge=STYLING_KNOWLEDGE,
            activity_constraints=activity_constraints,
            explanation_rules=EXPLANATION_RULES,
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
            
            # Enrich outfits with image URLs for frontend display
            item_lookup = {item["id"]: item for item in wardrobe_items}
            for outfit in result.get("outfits", []):
                outfit["item_details"] = []
                for slot, item_id in outfit.get("items", {}).items():
                    if item_id is not None and item_id in item_lookup:
                        item = item_lookup[item_id]
                        outfit["item_details"].append({
                            "id": item_id,
                            "slot": slot,
                            "imageUrl": item.get("image_url", ""),
                            "category": item.get("category", ""),
                            "color": item.get("color", ""),
                            "description": item.get("description", "")
                        })
            
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
            'dressing for', 'outfit for', 'what to wear to', 'wear to', 'holiday', 'vacation', 'trip', 'skiing', 'beach', 'travel'
        ]
        
        advice_patterns = [
            'how do i', 'how can i', 'what makes', 'why does', 'should i',
            'is it okay', 'can i wear', 'does this', 'help me understand',
            'tips for', 'advice on', 'how to make', 'what\'s the best way'
        ]
        
        for pattern in advice_patterns:
            if pattern in message_lower:
                return "occasion"
        
        for pattern in occasion_patterns:
            if pattern in message_lower:
                return "occasion"
        
        if len(message.split()) <= 5:
            return "occasion"
        
        return "occasion"


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
