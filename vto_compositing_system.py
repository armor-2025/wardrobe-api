"""
Image Compositing VTO System
============================
Pass 1: Generate perfect 4-item outfit
Pass 2: Face swap accessories using OpenCV (overlay images)
Pass 3: Composite accessories
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


class AccessoryCompositor:
    """Composites accessories onto outfit images using OpenCV"""
    
    def __init__(self):
        print("🔧 Initializing Accessory Compositor...")
    
    def composite_bag(self, base_image, bag_image_path):
        """Add bag to the side of the model"""
        print("   Adding bag...")
        
        # Load bag
        bag = cv2.imread(bag_image_path, cv2.IMREAD_UNCHANGED)
        if bag is None:
            print("   ⚠️ Could not load bag image")
            return base_image
        
        # Resize bag to reasonable size (20% of image height)
        height, width = base_image.shape[:2]
        bag_height = int(height * 0.2)
        aspect = bag.shape[1] / bag.shape[0]
        bag_width = int(bag_height * aspect)
        bag = cv2.resize(bag, (bag_width, bag_height))
        
        # Position: bottom right, slightly offset from edge
        x_pos = int(width * 0.7)  # 70% across
        y_pos = int(height * 0.65)  # 65% down (roughly at hip level)
        
        # Composite with alpha blending if available
        result = base_image.copy()
        
        if bag.shape[2] == 4:  # Has alpha channel
            # Extract alpha mask
            alpha = bag[:, :, 3] / 255.0
            
            # Composite
            for c in range(3):
                y_end = min(y_pos + bag_height, height)
                x_end = min(x_pos + bag_width, width)
                
                bag_h = y_end - y_pos
                bag_w = x_end - x_pos
                
                if bag_h > 0 and bag_w > 0:
                    result[y_pos:y_end, x_pos:x_end, c] = (
                        alpha[:bag_h, :bag_w] * bag[:bag_h, :bag_w, c] +
                        (1 - alpha[:bag_h, :bag_w]) * result[y_pos:y_end, x_pos:x_end, c]
                    )
        else:
            # No alpha, just overlay
            y_end = min(y_pos + bag_height, height)
            x_end = min(x_pos + bag_width, width)
            bag_h = y_end - y_pos
            bag_w = x_end - x_pos
            
            if bag_h > 0 and bag_w > 0:
                result[y_pos:y_end, x_pos:x_end] = bag[:bag_h, :bag_w, :3]
        
        print("   ✅ Bag added")
        return result
    
    def composite_scarf(self, base_image, scarf_image_path):
        """Add scarf around neck area"""
        print("   Adding scarf...")
        
        # Load scarf
        scarf = cv2.imread(scarf_image_path, cv2.IMREAD_UNCHANGED)
        if scarf is None:
            print("   ⚠️ Could not load scarf image")
            return base_image
        
        # Resize scarf (15% of image width)
        height, width = base_image.shape[:2]
        scarf_width = int(width * 0.25)
        aspect = scarf.shape[0] / scarf.shape[1]
        scarf_height = int(scarf_width * aspect)
        scarf = cv2.resize(scarf, (scarf_width, scarf_height))
        
        # Position: centered, at neck level (20% down from top)
        x_pos = int((width - scarf_width) / 2)
        y_pos = int(height * 0.2)
        
        # Composite
        result = base_image.copy()
        
        if scarf.shape[2] == 4:  # Has alpha
            alpha = scarf[:, :, 3] / 255.0
            
            for c in range(3):
                y_end = min(y_pos + scarf_height, height)
                x_end = min(x_pos + scarf_width, width)
                
                scarf_h = y_end - y_pos
                scarf_w = x_end - x_pos
                
                if scarf_h > 0 and scarf_w > 0:
                    result[y_pos:y_end, x_pos:x_end, c] = (
                        alpha[:scarf_h, :scarf_w] * scarf[:scarf_h, :scarf_w, c] +
                        (1 - alpha[:scarf_h, :scarf_w]) * result[y_pos:y_end, x_pos:x_end, c]
                    )
        else:
            y_end = min(y_pos + scarf_height, height)
            x_end = min(x_pos + scarf_width, width)
            scarf_h = y_end - y_pos
            scarf_w = x_end - x_pos
            
            if scarf_h > 0 and scarf_w > 0:
                result[y_pos:y_end, x_pos:x_end] = scarf[:scarf_h, :scarf_w, :3]
        
        print("   ✅ Scarf added")
        return result
    
    def composite_accessories(self, base_image, accessory_paths, accessory_analyses):
        """Composite all accessories onto the base image"""
        print("\n🎨 Compositing accessories...")
        
        result = base_image.copy()
        
        for i, (path, analysis) in enumerate(zip(accessory_paths, accessory_analyses)):
            category = analysis['category'].lower()
            description = analysis['description'].lower()
            
            # Determine accessory type and composite
            if 'bag' in category or 'bag' in description:
                result = self.composite_bag(result, path)
            elif 'scarf' in category or 'scarf' in description:
                result = self.composite_scarf(result, path)
            elif 'hat' in category or 'hat' in description or 'cap' in description:
                # TODO: Add hat compositing
                print(f"   ⚠️ Hat compositing not yet implemented")
            else:
                print(f"   ⚠️ Unknown accessory type: {category}")
        
        return result


class CompositingVTO:
    def __init__(self):
        print("🔧 Initializing Compositing VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.compositor = AccessoryCompositor()
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ Compositing VTO ready\n")
    
    def generate_compositing_vto(self, user_profile, clothing_items, accessory_items,
                                 clothing_description, accessory_analyses):
        """
        Generate VTO with composited accessories
        """
        
        print(f"\n✨ COMPOSITING VTO")
        print(f"{'='*80}")
        print(f"Pass 1: Generate {len(clothing_items)} clothing items")
        print(f"Pass 2: Face swap {len(accessory_items)} accessories")
        print(f"Pass 3: Composite accessories")
        print(f"{'='*80}\n")
        
        # PASS 1: Generate base outfit
        print("🎨 PASS 1: Generating base outfit...")
        
        mannequin_prompt = f"""FULL-LENGTH professional fashion photograph from HEAD TO FEET

Generic fashion model wearing:
{clothing_description}

Model details:
- Body: {user_profile.get_body_prompt()}
- Face: Generic neutral face
- Pose: Standing straight, arms naturally at sides
- Age: Adult

COMPOSITION:
- FULL BODY: Head to feet visible
- Pose: Standing straight, front-facing
- Background: Pure white (#FFFFFF)
- Lighting: Soft, even lighting

Create a complete outfit."""
        
        garment_pils = [Image.open(g) if isinstance(g, str) else g for g in clothing_items]
        
        response = self.gemini_model.generate_content(
            [mannequin_prompt, user_profile.photo_pil] + garment_pils,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        if hasattr(response, 'prompt_feedback') and getattr(response.prompt_feedback, 'block_reason', None):
            return False, None, FailureReason.CONTENT_POLICY
        
        base_bytes = self._extract_image(response)
        if not base_bytes:
            return False, None, FailureReason.GENERATION_FAILED
        
        base_image = cv2.imdecode(np.frombuffer(base_bytes, np.uint8), cv2.IMREAD_COLOR)
        print("✅ Pass 1 complete\n")
        
        os.makedirs('vto_compositing_test', exist_ok=True)
        cv2.imwrite('vto_compositing_test/pass1_base_outfit.png', base_image)
        
        # PASS 2: Face swap FIRST (before accessories)
        print("🎨 PASS 2: Face swapping...")
        
        source_faces = self.app.get(user_profile.photo_cv)
        if not source_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        target_faces = self.app.get(base_image)
        if not target_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        face_swapped = self.swapper.get(base_image, target_faces[0], source_faces[0], paste_back=True)
        print("✅ Pass 2 complete\n")
        
        cv2.imwrite('vto_compositing_test/pass2_face_swapped.png', face_swapped)
        
        # PASS 3: Composite accessories LAST
        if accessory_items:
            print("🎨 PASS 3: Compositing accessories...")
            result = self.compositor.composite_accessories(
                face_swapped, accessory_items, accessory_analyses
            )
            print("✅ Pass 3 complete\n")
            cv2.imwrite('vto_compositing_test/pass3_with_accessories.png', result)
        else:
            result = face_swapped
            print("⏭️ No accessories to composite\n")
        
        return True, result, None
    
    def _extract_image(self, response):
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def test_compositing_vto(photo_path, body_type, height, clothing_paths, accessory_paths):
    print("\n" + "=" * 80)
    print("🎯 COMPOSITING VTO TEST")
    print("=" * 80)
    
    profile = UserProfile(photo_path, body_type, height)
    analyzer = GarmentAnalyzer()
    
    # Analyze items
    print("\n📦 Analyzing clothing...")
    clothing_analyses = [analyzer.analyze_garment(p) for p in clothing_paths]
    clothing_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in clothing_analyses])
    
    print("\n📦 Analyzing accessories...")
    accessory_analyses = [analyzer.analyze_garment(p) for p in accessory_paths]
    
    vto = CompositingVTO()
    
    success, image, reason = vto.generate_compositing_vto(
        profile, clothing_paths, accessory_paths, clothing_desc, accessory_analyses
    )
    
    if success:
        output_path = "vto_compositing_test/compositing_final_result.png"
        cv2.imwrite(output_path, image)
        print(f"\n✅ SUCCESS! Saved to: {output_path}\n")
        return True
    else:
        print(f"\n❌ FAILED: {reason.value}\n")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("\nUsage: python vto_compositing_system.py <photo> <body> <height> <item1> ... -- <acc1> <acc2>\n")
        sys.exit(1)
    
    try:
        sep_idx = sys.argv.index('--')
        clothing = sys.argv[4:sep_idx]
        accessories = sys.argv[sep_idx+1:]
    except ValueError:
        clothing = sys.argv[4:]
        accessories = []
    
    test_compositing_vto(sys.argv[1], sys.argv[2], sys.argv[3], clothing, accessories)
