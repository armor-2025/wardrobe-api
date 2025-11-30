import re

class SmartDescriptionSystem:
    def is_description_detailed_enough(self, product_name: str, category: str) -> bool:
        """Check if product name is detailed enough for VTO"""
        
        name_lower = product_name.lower()
        word_count = len(product_name.split())
        
        if word_count < 3:
            return False
        
        # Check for color
        color_words = ['black', 'white', 'blue', 'red', 'green', 'yellow', 'pink', 'purple',
                      'navy', 'burgundy', 'khaki', 'olive', 'beige', 'cream', 'grey', 'gray',
                      'brown', 'tan', 'camel', 'indigo', 'emerald']
        has_color = any(color in name_lower for color in color_words)
        
        # Check for style descriptors
        style_descriptors = {
            'dress': ['mini', 'midi', 'maxi', 'knee-length', 'cocktail', 'shift', 'wrap', 'bodycon'],
            'top': ['crop', 'oversized', 'fitted', 'loose', 'button-up', 'crew neck', 'v-neck'],
            'bottom': ['wide-leg', 'straight', 'skinny', 'bootcut', 'high-waisted', 'low-rise'],
            'outerwear': ['bomber', 'trench', 'puffer', 'blazer', 'cardigan', 'hoodie'],
            'shoes': ['ankle', 'knee-high', 'platform', 'heeled', 'flat', 'chunky']
        }
        
        has_style = False
        if category in style_descriptors:
            has_style = any(desc in name_lower for desc in style_descriptors[category])
        
        # Check for material
        material_words = ['cotton', 'denim', 'leather', 'suede', 'wool', 'knit', 'silk',
                         'velvet', 'satin', 'linen', 'jersey', 'ribbed', 'textured']
        has_material = any(material in name_lower for material in material_words)
        
        if word_count >= 5:
            return True
        
        if (has_color or has_material) and has_style:
            return True
        
        return False

system = SmartDescriptionSystem()

print("\n" + "=" * 80)
print("🧪 TESTING REAL PRODUCT NAMES")
print("=" * 80)

test_products = [
    {"name": "ASOS DESIGN textured mini dress in burgundy", "category": "dress", "retailer": "ASOS"},
    {"name": "Topshop wide leg jeans in mid wash blue", "category": "bottom", "retailer": "ASOS/Topshop"},
    {"name": "TEXTURED KNIT DRESS", "category": "dress", "retailer": "Zara"},
    {"name": "WIDE LEG JEANS", "category": "bottom", "retailer": "Zara"},
    {"name": "LEATHER BOOTS", "category": "shoes", "retailer": "Zara"},
    {"name": "Ribbed turtleneck dress", "category": "dress", "retailer": "H&M"},
    {"name": "Jeans", "category": "bottom", "retailer": "H&M"},
    {"name": "UO Sophie Scoop Neck Midi Dress", "category": "dress", "retailer": "Urban Outfitters"}
]

for product in test_products:
    print(f"\n{product['retailer']}: \"{product['name']}\"")
    
    is_detailed = system.is_description_detailed_enough(product['name'], product['category'])
    
    if is_detailed:
        print(f"   ✅ DETAILED ENOUGH - Use as-is")
    else:
        print(f"   ⚠️  TOO VAGUE - Needs AI enhancement")

print("\n" + "=" * 80)
print("\n📊 SUMMARY:")
print("=" * 80)
print("\nGood retailers (use product name as-is):")
print("  • ASOS - detailed product names")
print("  • Urban Outfitters - descriptive names")
print("  • Nordstrom - professional descriptions")
print("\nNeeds enhancement (analyze image):")
print("  • Zara - very vague names")
print("  • H&M - hit or miss")
print("  • Mango - minimal descriptions")
print("\n💡 Strategy: Check product name quality, enhance only if needed")
print("=" * 80)
