"""
Gemini Prettify - PRODUCTION VERSION
Converts segmented garments to professional flat-lay product images
"""
import google.generativeai as genai
from PIL import Image
import os
from io import BytesIO

class GeminiPrettify:
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.max_size = 1024
        print("✅ Gemini Prettify loaded")
    
    def prepare_image(self, image):
        """Convert RGBA to RGB with white background, resize if needed"""
        if image.mode == 'RGBA':
            print(f"   🔄 Converting RGBA to RGB...")
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        if max(image.size) > self.max_size:
            ratio = self.max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"   📐 Resized to: {image.size}")
        
        return image
    
    def prettify(self, image_path, description="garment", category="clothing"):
        """
        Convert segmented garment to flat-lay product image
        
        Args:
            image_path: Path to segmented garment
            description: Item description (e.g. "crew neck sweater")
            category: Category (e.g. "tops")
        
        Returns:
            PIL Image: Professional flat-lay PNG, or None if failed
        """
        
        image = Image.open(image_path)
        print(f"   📷 Input: {image.size}, {image.mode}")
        
        image = self.prepare_image(image)
        
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
- PNG transparency is NOT needed - white background only

Output a clean, professional product image."""
        
        print(f"   🎨 Generating flat-lay for: {description}...")
        
        try:
            response = self.model.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    top_p=0.8,
                    top_k=40,
                )
            )
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                if candidate.finish_reason != 1:
                    print(f"   ⚠️  Failed: finish_reason={candidate.finish_reason}")
                    return None
                
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            result = Image.open(BytesIO(part.inline_data.data))
                            # Ensure RGB mode for clean output
                            if result.mode != 'RGB':
                                result = result.convert('RGB')
                            print(f"   ✨ Success! ({result.size[0]}x{result.size[1]})")
                            return result
            
            print(f"   ⚠️  No image generated")
            return None
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return None
