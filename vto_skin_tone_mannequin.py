"""
Skin-Toned Mannequin VTO
Mannequin colored to match user's skin tone
"""
import os
from PIL import Image
import io
import google.generativeai as genai
import cv2
import numpy as np

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'


def extract_skin_tone(image_bytes: bytes) -> str:
    """
    Extract dominant skin tone from user photo
    Returns as hex color
    """
    # Load image
    img_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    
    # Convert to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Get center region (likely to be skin)
    h, w = img_rgb.shape[:2]
    center_region = img_rgb[h//3:2*h//3, w//3:2*w//3]
    
    # Get average color
    avg_color = center_region.mean(axis=0).mean(axis=0)
    
    # Convert to hex
    r, g, b = int(avg_color[0]), int(avg_color[1]), int(avg_color[2])
    hex_color = f"#{r:02x}{g:02x}{b:02x}"
    
    return hex_color, (r, g, b)


async def generate_skin_tone_mannequin(garment_images: list, skin_tone_hex: str, skin_rgb: tuple):
    """
    Generate mannequin with user's skin tone
    """
    
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    garments = [Image.open(io.BytesIO(g)) for g in garment_images]
    
    r, g, b = skin_rgb
    
    prompt = f"""Create a professional fashion display showing these {len(garments)} clothing items on a retail mannequin.

CRITICAL MANNEQUIN SPECIFICATIONS:

1. SKIN TONE:
   - The mannequin must be colored to match this EXACT skin tone: RGB({r}, {g}, {b}) or {skin_tone_hex}
   - Smooth, matte finish (not glossy)
   - Realistic human skin tone, not white plastic
   - Even coloring across entire mannequin

2. MANNEQUIN FEATURES:
   - Featureless head (smooth, no facial features)
   - Full body with arms and legs
   - Professional retail display style
   - Standing straight, arms slightly away from body
   - Elegant, high-end fashion display

3. CLOTHING:
   - All {len(garments)} garments fitted naturally
   - Professional product photography styling
   - Natural draping and fit

4. SETTING:
   - Clean light gray studio background
   - Soft, even studio lighting
   - High-quality fashion photography
   - Centered composition, full body shot

The mannequin should look like a premium retail display with realistic skin tone matching {skin_tone_hex}.

Return ONLY the final image."""

    response = model.generate_content(
        [prompt] + garments,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
    )
    
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return part.inline_data.data
    
    raise ValueError("No image generated")


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 70)
        print("🎨 Skin-Toned Mannequin VTO")
        print("=" * 70)
        
        # Load user photo to extract skin tone
        print("\n📸 Loading user photo to extract skin tone...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
            user_photo = f.read()
        
        skin_hex, skin_rgb = extract_skin_tone(user_photo)
        print(f"✅ Extracted skin tone: {skin_hex} RGB{skin_rgb}")
        
        # Load garments
        print("\n📦 Loading garments...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
            shirt = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
            boots = f.read()
        
        # Generate mannequin with user's skin tone
        print(f"\n🎨 Generating mannequin with skin tone {skin_hex}...")
        result = await generate_skin_tone_mannequin([shirt, shorts, boots], skin_hex, skin_rgb)
        
        with open('vto_skin_tone_mannequin.png', 'wb') as f:
            f.write(result)
        
        print("✅ Saved: vto_skin_tone_mannequin.png")
        print("\n💡 This mannequin should match the user's skin tone!")
        print("   Professional display + personalized skin = Best of both worlds!")
        print("\n" + "=" * 70)
    
    asyncio.run(test())
