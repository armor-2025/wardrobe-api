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
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.max_size = 1024
        print("✅ Gemini Prettify loaded")
    
    def prepare_image(self, image):
        """Convert RGBA to RGB with white background, resize if needed"""
        # Convert RGBA to RGB with white background
        if image.mode == 'RGBA':
            print(f"   🔄 Converting RGBA to RGB...")
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])  # Use alpha as mask
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large
        if max(image.size) > self.max_size:
            ratio = self.max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"   📐 Resized to: {image.size}")
        
        return image
    
    def prettify(self, image_path):
        """
        Convert segmented garment to flat-lay product image
        
        Args:
            image_path: Path to segmented garment (can be RGBA or RGB)
        
        Returns:
            PIL Image: Professional flat-lay version, or None if failed
        """
        
        # Load image
        image = Image.open(image_path)
        print(f"   📷 Input: {image.size}, {image.mode}")
        
        # Prepare (convert RGBA->RGB, resize)
        image = self.prepare_image(image)
        
        prompt = "show this exact jacket as a professional flat lay product photo"
        
        print(f"   🎨 Generating flat-lay...")
        
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.4,
                top_p=0.8,
                top_k=40,
            )
            
            response = self.model.generate_content(
                [prompt, image],
                generation_config=generation_config
            )
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Check finish reason (1 = success)
                if candidate.finish_reason != 1:
                    print(f"   ⚠️  Failed: finish_reason={candidate.finish_reason}")
                    return None
                
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            result = Image.open(BytesIO(part.inline_data.data))
                            print(f"   ✨ Success! ({result.size[0]}x{result.size[1]})")
                            return result
            
            print(f"   ⚠️  No image generated")
            return None
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return None
