"""
Gemini Prettify - PRODUCTION VERSION (Vertex AI)
Converts segmented garments to professional flat-lay product images
Uses same auth as VTO - no separate API key needed
"""
from google import genai
from google.genai.types import Part
from PIL import Image
import os
import io

# Initialize Vertex AI (same as VTO)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# Handle Render deployment credentials
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = "/tmp/gcp_credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path


class GeminiPrettify:
    
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-2.5-flash-image"
        self.max_size = 1024
        print("✅ Gemini Prettify loaded (Vertex AI)")
    
    def prepare_image(self, image):
        """Convert RGBA to RGB with white background, resize if needed"""
        if isinstance(image, str):
            image = Image.open(image)
        
        if image.mode == 'RGBA':
            print(f"   🔄 Converting RGBA to RGB...")
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if needed
        if max(image.size) > self.max_size:
            ratio = self.max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"   📐 Resized to {new_size}")
        
        return image
    
    def image_to_part(self, image):
        """Convert PIL Image to Gemini Part"""
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        return Part.from_bytes(data=buffer.read(), mime_type="image/jpeg")
    
    def prettify(self, image_path_or_pil, description="garment", category="clothing"):
        """
        Transform segmented garment into professional flat-lay product image
        
        Args:
            image_path_or_pil: Path string or PIL Image
            description: What the item is (e.g., "wool beret", "silk blouse")
        
        Returns:
            PIL Image or None if failed
        """
        try:
            # Load and prepare image
            if isinstance(image_path_or_pil, str):
                image = Image.open(image_path_or_pil)
            else:
                image = image_path_or_pil
            
            print(f"   📷 Input: {image.size}, {image.mode}")
            image = self.prepare_image(image)
            image_part = self.image_to_part(image)
            
            print(f"   🎨 Generating flat-lay for: {description}...")
            
            prompt = f"""This is a segmented cutout of a {description}. 
The image has gaps and rough edges from the segmentation process - these need to be filled in and smoothed.

Create a professional flat-lay product photo of this EXACT {description}:
- Fill in any gaps or holes from segmentation
- Smooth rough edges
- PURE WHITE background (#FFFFFF)
- NO shadows whatsoever
- Flat lay position (laid flat, viewed from above)
- Maintain the EXACT colors and design from the original image
- Clean, professional e-commerce style
- If this is a jacket, coat, cardigan or any outerwear - show it BUTTONED UP / ZIPPED CLOSED
- PNG transparency is NOT needed - white background only

Output a clean, professional product image."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image_part],
                config={"response_modalities": ["image", "text"]}
            )
            
            # Extract generated image
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    result = Image.open(io.BytesIO(part.inline_data.data))
                    print(f"   ✅ Prettified! Output: {result.size}")
                    return result
            
            print("   ❌ No image in response")
            return None
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = GeminiPrettify()
        result = p.prettify(sys.argv[1], "test garment")
        if result:
            result.save("prettified_test.png")
            print("Saved to prettified_test.png")
