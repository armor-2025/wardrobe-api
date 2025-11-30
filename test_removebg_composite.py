"""
Approach: Background removal + composite
"""
import os
from PIL import Image
import io
import requests

print("=" * 70)
print("🧪 Test 1: Remove.bg + Composite Approach")
print("=" * 70)

# Option A: Use remove.bg API (needs key)
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY', 'YOUR_KEY_HERE')

# Option B: Use local rembg (no API key needed!)
print("\n📦 Using local rembg (no API key needed)...")

try:
    from rembg import remove
    
    # Remove background from original photo
    print("🔄 Removing background from your photo...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        input_image = f.read()
    
    output_image = remove(input_image)
    
    with open('person_extracted.png', 'wb') as f:
        f.write(output_image)
    
    print("✅ Person extracted with transparent background!")
    print("   Saved: person_extracted.png")
    
    # Now we have perfect person extraction
    # Next: composite onto Gemini's clothes
    print("\n💡 Next step: Generate clothes with Gemini, then composite")
    print("   This gives us: Perfect person + Perfect clothes = $0.10!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Install rembg: pip install rembg")

