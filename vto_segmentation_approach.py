"""
Segmentation-Based VTO
1. Extract the person from original photo
2. Generate clothes-only image
3. Composite them together
"""
import os
import cv2
import numpy as np
from PIL import Image
import io
import base64
import google.generativeai as genai


class SegmentationVTO:
    """
    More reliable approach:
    1. Keep user's photo for head/face
    2. Generate ONLY the clothing portion
    3. Composite them intelligently
    """
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    async def generate_clothes_only(self, garment_images: list) -> bytes:
        """
        Generate just the clothing on a mannequin/model
        We'll composite the user's head onto this
        """
        
        garment_imgs = [Image.open(io.BytesIO(g)) for g in garment_images]
        
        prompt = f"""Create a professional fashion photo showing these {len(garment_imgs)} clothing items being worn together as a complete outfit.

REQUIREMENTS:
- Show the clothes on a neutral, generic fashion model
- Professional standing pose, arms at sides
- Clean light gray studio background
- Soft, even lighting
- High-quality product photography style
- The model should be generic and neutral (we will replace the head)

Focus on making the CLOTHES look perfect.

Return ONLY the final image."""

        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.8,
            top_k=40,
        )
        
        content = [prompt] + garment_imgs
        
        response = self.model.generate_content(
            content,
            generation_config=generation_config
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        
        raise ValueError("No image generated")
    
    async def composite_user_head(self, user_photo_bytes: bytes, clothes_image_bytes: bytes) -> bytes:
        """
        Take user's head from original photo and put it on the clothes model
        This uses the head preservation technique we developed earlier
        """
        from insightface.app import FaceAnalysis
        
        # Initialize face detection
        app = FaceAnalysis(name='buffalo_l')
        app.prepare(ctx_id=-1)
        
        # Load images
        user_img = cv2.imdecode(np.frombuffer(user_photo_bytes, np.uint8), cv2.IMREAD_COLOR)
        clothes_img = cv2.imdecode(np.frombuffer(clothes_image_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        # Detect faces
        user_faces = app.get(user_img)
        clothes_faces = app.get(clothes_img)
        
        if not user_faces or not clothes_faces:
            print("⚠️ Could not detect faces, returning clothes image")
            return clothes_image_bytes
        
        user_bbox = user_faces[0].bbox.astype(int)
        clothes_bbox = clothes_faces[0].bbox.astype(int)
        
        # Expand for full head
        def expand_for_head(bbox, img_shape):
            x1, y1, x2, y2 = bbox
            fw = x2 - x1
            fh = y2 - y1
            
            new_x1 = max(0, int(x1 - fw * 0.5))
            new_y1 = max(0, int(y1 - fh * 1.2))  # Way up for hair
            new_x2 = min(img_shape[1], int(x2 + fw * 0.5))
            new_y2 = int(y2 + fh * 0.3)  # Down to neck
            
            return [new_x1, new_y1, new_x2, new_y2]
        
        user_head_bbox = expand_for_head(user_bbox, user_img.shape)
        clothes_head_bbox = expand_for_head(clothes_bbox, clothes_img.shape)
        
        # Extract user's head
        ux1, uy1, ux2, uy2 = user_head_bbox
        user_head = user_img[uy1:uy2, ux1:ux2]
        
        # Prepare clothes image region
        cx1, cy1, cx2, cy2 = clothes_head_bbox
        c_height = cy2 - cy1
        c_width = cx2 - cx1
        
        if c_height <= 0 or c_width <= 0:
            return clothes_image_bytes
        
        # Resize user head to match
        user_head_resized = cv2.resize(user_head, (c_width, c_height))
        
        # Create smooth mask
        mask = np.zeros((c_height, c_width), dtype=np.float32)
        center_x, center_y = c_width // 2, c_height // 2
        cv2.ellipse(mask, (center_x, center_y), (c_width // 2, c_height // 2), 0, 0, 360, 1, -1)
        mask = cv2.GaussianBlur(mask, (99, 99), 0)
        mask = np.stack([mask] * 3, axis=2)
        
        # Blend
        result = clothes_img.copy()
        clothes_region = result[cy1:cy2, cx1:cx2]
        blended = (user_head_resized * mask + clothes_region * (1 - mask)).astype(np.uint8)
        result[cy1:cy2, cx1:cx2] = blended
        
        # Encode
        _, buffer = cv2.imencode('.png', result)
        return buffer.tobytes()


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 70)
        print("🎯 Segmentation-Based VTO Test")
        print("=" * 70)
        
        os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
        
        vto = SegmentationVTO()
        
        # Load garments
        print("\n📦 Loading garments...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
            shirt = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
            boots = f.read()
        
        # Step 1: Generate clothes on generic model
        print("\n🎨 Step 1: Generating clothes on generic model...")
        clothes_bytes = await vto.generate_clothes_only([shirt, shorts, boots])
        
        with open('step1_clothes_only.png', 'wb') as f:
            f.write(clothes_bytes)
        print("✅ Saved: step1_clothes_only.png")
        
        # Step 2: Composite user's head onto it
        print("\n🔄 Step 2: Adding user's head to the clothes...")
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
            user_photo = f.read()
        
        final_bytes = await vto.composite_user_head(user_photo, clothes_bytes)
        
        with open('vto_segmentation_final.png', 'wb') as f:
            f.write(final_bytes)
        print("✅ Saved: vto_segmentation_final.png")
        
        print("\n💡 Check both files:")
        print("   step1_clothes_only.png - Clothes on generic model")
        print("   vto_segmentation_final.png - With your actual head!")
    
    asyncio.run(test())
