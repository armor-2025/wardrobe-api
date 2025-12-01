"""
Two-Photo VTO System
Like ALTA: Full body + Face close-up for better identity preservation
"""
import os
import cv2
import numpy as np
from PIL import Image
import io
import base64
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'


class TwoPhotoVTO:
    """
    Better approach: Use two photos
    1. Full body photo - for VTO generation
    2. Face close-up - for high-quality face swap
    """
    
    def __init__(self):
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
        
        # Initialize face detection
        from insightface.app import FaceAnalysis
        from insightface.model_zoo import get_model
        
        self.face_app = FaceAnalysis(name='buffalo_l')
        self.face_app.prepare(ctx_id=-1)
        
        self.swapper = get_model('inswapper_128.onnx', 
                                download=True,
                                download_zip=True)
    
    async def generate_vto_from_body_photo(self, full_body_bytes: bytes, garment_images: list) -> bytes:
        """
        Step 1: Generate VTO using full body photo
        Focus on getting clothes perfect, face doesn't matter here
        """
        
        body_img = Image.open(io.BytesIO(full_body_bytes))
        garment_imgs = [Image.open(io.BytesIO(g)) for g in garment_images]
        
        prompt = f"""Transform this photo to show the person wearing these {len(garment_imgs)} new clothing items.

REQUIREMENTS:
- Keep the person's body shape, proportions, and pose
- Replace their current clothes with the new garments shown
- Professional fashion photography quality
- Clean light gray studio background
- Soft, even lighting
- Natural fit and draping of clothes

Focus on making the CLOTHES look perfect on this person's body.

Return ONLY the final image."""

        response = self.model.generate_content(
            [prompt, body_img] + garment_imgs,
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
    
    def swap_face_from_closeup(self, vto_result_bytes: bytes, face_closeup_bytes: bytes) -> bytes:
        """
        Step 2: Swap face using high-quality close-up
        The close-up gives us much better face detail for swapping
        """
        
        # Load images
        vto_img = cv2.imdecode(np.frombuffer(vto_result_bytes, np.uint8), cv2.IMREAD_COLOR)
        face_img = cv2.imdecode(np.frombuffer(face_closeup_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        # Detect faces
        vto_faces = self.face_app.get(vto_img)
        source_faces = self.face_app.get(face_img)
        
        if not vto_faces or not source_faces:
            print("⚠️ Could not detect faces")
            return vto_result_bytes
        
        # Use the close-up face (higher quality)
        source_face = source_faces[0]
        target_face = vto_faces[0]
        
        # Swap face
        result = self.swapper.get(vto_img, target_face, source_face, paste_back=True)
        
        # Encode
        _, buffer = cv2.imencode('.png', result)
        return buffer.tobytes()


# Test it
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 70)
        print("🎯 Two-Photo VTO System Test")
        print("=" * 70)
        
        vto = TwoPhotoVTO()
        
        # Load photos
        print("\n📸 Loading photos...")
        
        # Full body photo
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
            full_body = f.read()
        print("✅ Full body photo loaded")
        
        # For now, we'll use the same photo as close-up
        # In production, user uploads a separate face close-up
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
            face_closeup = f.read()
        print("✅ Face close-up loaded")
        
        # Load garments
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
            shirt = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
            shorts = f.read()
        with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
            boots = f.read()
        
        # Step 1: Generate VTO from body photo
        print("\n🎨 Step 1: Generating VTO from body photo...")
        vto_bytes = await vto.generate_vto_from_body_photo(full_body, [shirt, shorts, boots])
        
        with open('step1_vto_from_body.png', 'wb') as f:
            f.write(vto_bytes)
        print("✅ Saved: step1_vto_from_body.png")
        
        # Step 2: Swap face using close-up
        print("\n🔄 Step 2: Swapping face using close-up...")
        final_bytes = vto.swap_face_from_closeup(vto_bytes, face_closeup)
        
        with open('vto_two_photo_final.png', 'wb') as f:
            f.write(final_bytes)
        print("✅ Saved: vto_two_photo_final.png")
        
        print("\n" + "=" * 70)
        print("💡 Using a separate face close-up should give better results!")
        print("   The higher resolution face photo helps face swap quality.")
        print("\n📊 Compare:")
        print("   - step1_vto_from_body.png (before face swap)")
        print("   - vto_two_photo_final.png (after face swap)")
        print("=" * 70)
    
    asyncio.run(test())
