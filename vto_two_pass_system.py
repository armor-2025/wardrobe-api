"""
Two-Pass VTO System: Clothing First, Then Accessories + Face
=============================================================

Pass 1: Generate mannequin with 4 clothing items (no face)
Pass 2: Add accessories to the mannequin image
Pass 3: Face swap user's face onto final result
"""

import os
import cv2
import numpy as np
from PIL import Image
import json
from datetime import datetime
from enum import Enum
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# Import the existing classes from vto_complete_system
from vto_complete_system import (
    GarmentAnalyzer, BodyType, Height, UserProfile, 
    FailureReason, VTOResult
)

class TwoPassVTOSystem:
    def __init__(self):
        print("🔧 Initializing Two-Pass VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ Two-Pass VTO System ready\n")
    
    def generate_two_pass_vto(self, user_profile, clothing_items, accessory_items, 
                              clothing_description, accessory_description):
        """
        Two-pass VTO generation
        
        Pass 1: Generate mannequin with clothing (4 items max)
        Pass 2: Add accessories to mannequin
        Pass 3: Face swap
        """
        
        print(f"\n✨ TWO-PASS VTO GENERATION")
        print(f"{'='*80}")
        print(f"Pass 1: {len(clothing_items)} clothing items")
        print(f"Pass 2: {len(accessory_items)} accessories")
        print(f"{'='*80}\n")
        
        # PASS 1: Generate mannequin with clothing
        print("🎨 PASS 1: Generating base outfit on mannequin...")
        
        mannequin_prompt = f"""FULL-LENGTH professional fashion photograph from HEAD TO FEET

Generic fashion model wearing:
{clothing_description}

Model details:
- Body: {user_profile.get_body_prompt()}
- Face: Generic neutral face (will be replaced)
- Eyes: Open, looking forward, no eyewear
- Age: Adult

COMPOSITION:
- FULL BODY: Head to feet, complete legs and shoes visible
- Pose: Standing straight, front-facing, arms at sides
- Background: Pure white (#FFFFFF), clean product photography style, no shadows
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
        print("✅ Pass 1 complete: Base outfit generated\n")
        
        # Save Pass 1 result for debugging
        os.makedirs('vto_two_pass_test', exist_ok=True)
        cv2.imwrite('vto_two_pass_test/pass1_mannequin.png', mannequin_image)
        
        # PASS 2: Add accessories to mannequin
        if accessory_items:
            print(f"🎨 PASS 2: Adding {len(accessory_items)} accessories to outfit...")
            
            mannequin_pil = Image.fromarray(cv2.cvtColor(mannequin_image, cv2.COLOR_BGR2RGB))
            accessory_pils = [Image.open(a) if isinstance(a, str) else a for a in accessory_items]
            
            accessory_prompt = f"""Take this fashion photograph and add these accessories:
{accessory_description}

CRITICAL INSTRUCTIONS:
- Keep the EXACT same clothing, pose, body position, and lighting
- Only add the accessories mentioned above
- Maintain pure white background
- Do NOT change the outfit or model's pose
- Accessories should look natural (bag in hand or on shoulder, scarf around neck)

Add accessories while preserving everything else exactly."""
            
            response2 = self.gemini_model.generate_content(
                [accessory_prompt, mannequin_pil] + accessory_pils,
                generation_config=genai.types.GenerationConfig(temperature=0.2)
            )
            
            if hasattr(response2, 'prompt_feedback') and getattr(response2.prompt_feedback, 'block_reason', None):
                print("⚠️ Pass 2 blocked, using Pass 1 result")
                final_image = mannequin_image
            else:
                final_bytes = self._extract_image(response2)
                if final_bytes:
                    final_image = cv2.imdecode(np.frombuffer(final_bytes, np.uint8), cv2.IMREAD_COLOR)
                    print("✅ Pass 2 complete: Accessories added\n")
                    
                    # Save Pass 2 result for debugging
                    cv2.imwrite('vto_two_pass_test/pass2_with_accessories.png', final_image)
                else:
                    print("⚠️ Pass 2 failed, using Pass 1 result")
                    final_image = mannequin_image
        else:
            final_image = mannequin_image
            print("⏭️ Skipping Pass 2: No accessories\n")
        
        # PASS 3: Face swap
        print("🎨 PASS 3: Swapping user's face onto final result...")
        
        source_faces = self.app.get(user_profile.photo_cv)
        if not source_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        target_faces = self.app.get(final_image)
        if not target_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        result = self.swapper.get(final_image, target_faces[0], source_faces[0], paste_back=True)
        print("✅ Pass 3 complete: Face swapped\n")
        
        return True, result, None
    
    def _extract_image(self, response):
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def test_two_pass_vto(photo_path, body_type, height, clothing_paths, accessory_paths, output_dir="vto_two_pass_test"):
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("🎯 TWO-PASS VTO TEST")
    print("=" * 80)
    print(f"Model: {os.path.basename(photo_path)}")
    print(f"Profile: {body_type} + {height}")
    print(f"Clothing: {len(clothing_paths)} items")
    print(f"Accessories: {len(accessory_paths)} items")
    print("=" * 80)
    
    profile = UserProfile(photo_path, body_type, height)
    
    analyzer = GarmentAnalyzer()
    
    # Analyze clothing
    print("\n📦 Analyzing clothing items...")
    clothing_analyses = [analyzer.analyze_garment(p) for p in clothing_paths]
    clothing_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in clothing_analyses])
    
    # Analyze accessories
    print("\n📦 Analyzing accessories...")
    accessory_analyses = [analyzer.analyze_garment(p) for p in accessory_paths]
    accessory_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in accessory_analyses])
    
    vto_system = TwoPassVTOSystem()
    
    success, image, reason = vto_system.generate_two_pass_vto(
        profile,
        clothing_paths,
        accessory_paths,
        clothing_desc,
        accessory_desc
    )
    
    if success:
        output_path = f"{output_dir}/two_pass_result.png"
        cv2.imwrite(output_path, image)
        print(f"\n✅ SUCCESS! Saved to: {output_path}\n")
        return True
    else:
        print(f"\n❌ FAILED: {reason.value}\n")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("\nUsage: python vto_two_pass_system.py <photo> <body_type> <height> <clothing1> <clothing2> ... -- <accessory1> <accessory2>")
        print("\nExample: python vto_two_pass_system.py me.jpg average none pants.jpg top.jpg jacket.jpg shoes.jpg -- bag.jpg\n")
        sys.exit(1)
    
    # Find the separator
    try:
        separator_idx = sys.argv.index('--')
        clothing = sys.argv[4:separator_idx]
        accessories = sys.argv[separator_idx+1:]
    except ValueError:
        # No separator, treat all as clothing
        clothing = sys.argv[4:]
        accessories = []
    
    test_two_pass_vto(sys.argv[1], sys.argv[2], sys.argv[3], clothing, accessories)
