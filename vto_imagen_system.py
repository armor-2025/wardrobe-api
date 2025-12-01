"""
Two-Pass VTO with Imagen for Accessories
==========================================
Pass 1: Gemini generates base outfit (4 items)
Pass 2: Imagen adds accessories to the image
Pass 3: Face swap
"""

import os
import cv2
import numpy as np
from PIL import Image
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

from vto_complete_system import (
    GarmentAnalyzer, BodyType, Height, UserProfile, 
    FailureReason, VTOResult
)

class ImagenTwoPassVTO:
    def __init__(self):
        print("🔧 Initializing Imagen Two-Pass VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.imagen_model = genai.GenerativeModel('imagen-4.0-generate-001')
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ Imagen Two-Pass VTO ready\n")
    
    def generate_imagen_two_pass(self, user_profile, clothing_items, accessory_items, 
                                 clothing_description, accessory_description):
        """
        Two-pass with Imagen for accessories
        """
        
        print(f"\n✨ IMAGEN TWO-PASS VTO")
        print(f"{'='*80}")
        print(f"Pass 1: Gemini - {len(clothing_items)} clothing items")
        print(f"Pass 2: Imagen - {len(accessory_items)} accessories")
        print(f"{'='*80}\n")
        
        # PASS 1: Gemini generates base outfit
        print("🎨 PASS 1: Gemini generating base outfit...")
        
        mannequin_prompt = f"""FULL-LENGTH professional fashion photograph from HEAD TO FEET

Generic fashion model wearing:
{clothing_description}

Model details:
- Body: {user_profile.get_body_prompt()}
- Face: Generic neutral face
- Eyes: Open, looking forward
- Age: Adult

COMPOSITION:
- FULL BODY: Head to feet, complete legs and shoes visible
- Pose: Standing straight, front-facing, arms at sides
- Background: Pure white (#FFFFFF)
- Lighting: Soft, even fashion photography lighting

Create a complete outfit on a generic model."""
        
        garment_pils = [Image.open(g) if isinstance(g, str) else g for g in clothing_items]
        
        response1 = self.gemini_model.generate_content(
            [mannequin_prompt, user_profile.photo_pil] + garment_pils,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        if hasattr(response1, 'prompt_feedback') and getattr(response1.prompt_feedback, 'block_reason', None):
            return False, None, FailureReason.CONTENT_POLICY
        
        mannequin_bytes = self._extract_image(response1)
        if not mannequin_bytes:
            return False, None, FailureReason.GENERATION_FAILED
        
        mannequin_image = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
        print("✅ Pass 1 complete\n")
        
        os.makedirs('vto_imagen_test', exist_ok=True)
        cv2.imwrite('vto_imagen_test/pass1_gemini_base.png', mannequin_image)
        
        # PASS 2: Imagen adds accessories
        if accessory_items:
            print(f"🎨 PASS 2: Imagen adding {len(accessory_items)} accessories...")
            
            # Convert to PIL for Imagen
            mannequin_pil = Image.fromarray(cv2.cvtColor(mannequin_image, cv2.COLOR_BGR2RGB))
            accessory_pils = [Image.open(a) if isinstance(a, str) else a for a in accessory_items]
            
            # Imagen prompt for editing
            imagen_prompt = f"""Add these accessories to this fashion photograph:
{accessory_description}

IMPORTANT:
- Keep the exact same outfit, pose, and model
- Only add the accessories
- Maintain white background
- Make accessories look natural and realistic"""
            
            try:
                # Use Imagen to edit the image
                response2 = self.imagen_model.generate_content(
                    [imagen_prompt, mannequin_pil] + accessory_pils,
                    generation_config=genai.types.GenerationConfig(temperature=0.2)
                )
                
                if hasattr(response2, 'prompt_feedback') and getattr(response2.prompt_feedback, 'block_reason', None):
                    print("⚠️ Imagen blocked, using Pass 1 result")
                    final_image = mannequin_image
                else:
                    final_bytes = self._extract_image(response2)
                    if final_bytes:
                        final_image = cv2.imdecode(np.frombuffer(final_bytes, np.uint8), cv2.IMREAD_COLOR)
                        print("✅ Pass 2 complete\n")
                        cv2.imwrite('vto_imagen_test/pass2_imagen_accessories.png', final_image)
                    else:
                        print("⚠️ Imagen failed, using Pass 1 result")
                        final_image = mannequin_image
            except Exception as e:
                print(f"⚠️ Imagen error: {e}")
                print("Using Pass 1 result")
                final_image = mannequin_image
        else:
            final_image = mannequin_image
            print("⏭️ No accessories\n")
        
        # PASS 3: Face swap
        print("🎨 PASS 3: Face swapping...")
        
        source_faces = self.app.get(user_profile.photo_cv)
        if not source_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        target_faces = self.app.get(final_image)
        if not target_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        result = self.swapper.get(final_image, target_faces[0], source_faces[0], paste_back=True)
        print("✅ Pass 3 complete\n")
        
        return True, result, None
    
    def _extract_image(self, response):
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def test_imagen_vto(photo_path, body_type, height, clothing_paths, accessory_paths):
    print("\n" + "=" * 80)
    print("🎯 IMAGEN TWO-PASS VTO TEST")
    print("=" * 80)
    
    profile = UserProfile(photo_path, body_type, height)
    analyzer = GarmentAnalyzer()
    
    # Analyze items
    print("\n📦 Analyzing clothing...")
    clothing_analyses = [analyzer.analyze_garment(p) for p in clothing_paths]
    clothing_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in clothing_analyses])
    
    print("\n📦 Analyzing accessories...")
    accessory_analyses = [analyzer.analyze_garment(p) for p in accessory_paths]
    accessory_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in accessory_analyses])
    
    vto = ImagenTwoPassVTO()
    
    success, image, reason = vto.generate_imagen_two_pass(
        profile, clothing_paths, accessory_paths, clothing_desc, accessory_desc
    )
    
    if success:
        output_path = "vto_imagen_test/imagen_final_result.png"
        cv2.imwrite(output_path, image)
        print(f"\n✅ SUCCESS! Saved to: {output_path}\n")
        return True
    else:
        print(f"\n❌ FAILED: {reason.value}\n")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("\nUsage: python vto_imagen_system.py <photo> <body> <height> <item1> <item2> ... -- <acc1> <acc2>\n")
        sys.exit(1)
    
    try:
        sep_idx = sys.argv.index('--')
        clothing = sys.argv[4:sep_idx]
        accessories = sys.argv[sep_idx+1:]
    except ValueError:
        clothing = sys.argv[4:]
        accessories = []
    
    test_imagen_vto(sys.argv[1], sys.argv[2], sys.argv[3], clothing, accessories)
