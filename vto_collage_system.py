"""
Collage Compositing VTO System with Smart Accessory Ordering
=============================================================
"""

import os
import cv2
import numpy as np
from rembg import remove
from PIL import Image
import io
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


class CollageCompositor:
    """Creates a collage with smart accessory ordering"""
    
    def __init__(self):
        print("🔧 Initializing Collage Compositor...")
    
    def remove_background(self, image):
        """
        Hybrid background removal:
        - Clean backgrounds → OpenCV (preserves thin straps/chains)
        - Complex backgrounds → rembg AI (handles models/busy scenes)
        """
        # Analyze background complexity
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray)
        light_pixels = np.sum(gray > 180) / gray.size
        
        # Decision: Clean (simple) vs Complex background
        is_clean = (std_dev < 70 and light_pixels > 0.70)
        
        if is_clean:
            print(f"      → OpenCV (clean bg: std={std_dev:.1f}, light={light_pixels:.1%})")
            # CLEAN BACKGROUND → OpenCV (fast, preserves details)
            img_rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
            
            # Mask for light backgrounds
            lower_light = np.array([180, 180, 180, 0])
            upper_light = np.array([255, 255, 255, 255])
            mask = cv2.inRange(img_rgba, lower_light, upper_light)
            
            # Mask for beige/tan
            lower_beige = np.array([170, 190, 200, 0])
            upper_beige = np.array([255, 255, 255, 255])
            mask_beige = cv2.inRange(img_rgba, lower_beige, upper_beige)
            
            # Combine and apply
            mask_combined = cv2.bitwise_or(mask, mask_beige)
            mask_inv = cv2.bitwise_not(mask_combined)
            img_rgba[:, :, 3] = mask_inv
            
            return img_rgba
        else:
            print(f"      → rembg AI (complex bg: std={std_dev:.1f}, light={light_pixels:.1%})")
            # COMPLEX BACKGROUND → rembg AI (accurate extraction)
            
            # Convert 16-bit images to 8-bit first
            if image.dtype != np.uint8:
                if image.max() > 255:
                    image = (image / 256).astype(np.uint8)
                else:
                    image = image.astype(np.uint8)
            
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Remove with rembg
            output_bytes = remove(img_bytes)
            
            # Convert back
            output_img = Image.open(io.BytesIO(output_bytes))
            img_array = np.array(output_img)
            
            # RGBA to BGRA for OpenCV
            if img_array.shape[2] == 4:
                img_bgra = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)
            else:
                img_bgra = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                img_bgra = cv2.cvtColor(img_bgra, cv2.COLOR_BGR2BGRA)
            
            return img_bgra
    
    
    def crop_transparent_padding(self, img_rgba):
        """Remove transparent padding from PNG to get tight crop around visible content"""
        if img_rgba.shape[2] == 4:
            # Get alpha channel
            alpha = img_rgba[:, :, 3]
            
            # Find non-transparent pixels
            rows = np.any(alpha > 10, axis=1)  # At least 10/255 opacity
            cols = np.any(alpha > 10, axis=0)
            
            if rows.any() and cols.any():
                y_min, y_max = np.where(rows)[0][[0, -1]]
                x_min, x_max = np.where(cols)[0][[0, -1]]
                
                # Crop to content
                return img_rgba[y_min:y_max+1, x_min:x_max+1]
        
        return img_rgba
    def standardize_canvas(self, image, has_accessories=False):
        """Crop and resize canvas - keep model, minimize empty space"""
        print("   🔧 Standardizing canvas dimensions...")
        
        h, w = image.shape[:2]
        
        if has_accessories:
            target_w = 3000
            target_h = 6000  # Tall enough for full body with feet
        else:
            target_w = 2400
            target_h = 4000
        
        current_aspect = w / h
        target_aspect = target_w / target_h
        
        if current_aspect > target_aspect:
            new_w = int(h * target_aspect)
            crop_x = 0
            cropped = image[:, crop_x:crop_x+new_w]
        else:
            new_h = int(w / target_aspect)
            crop_y = 0  # Crop from TOP to preserve head/face
            cropped = image[crop_y:crop_y+new_h, :]
        
        resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        
        print(f"   ✅ Canvas: {w}x{h} → {target_w}x{target_h}")
        return resized
    
    def get_accessory_order(self, category):
        """Return sort order based on where accessory sits on body"""
        order_map = {
            'hat': 1, 'cap': 1, 'beanie': 1,
            'sunglasses': 2, 'glasses': 2, 'eyewear': 2,
            'earring': 3,
            'necklace': 4,
            'scarf': 5,
            'bag': 6, 'purse': 6, 'handbag': 6
        }
        
        category_lower = category.lower()
        for key, order in order_map.items():
            if key in category_lower:
                return order
        return 99
    
    def create_collage(self, main_image, accessory_paths, accessory_analyses):
        """Composite accessories with perfect equal spacing"""
        print("\n🎨 Compositing accessories onto seamless background...")
        
        main_h, main_w = main_image.shape[:2]
        result = main_image.copy()
        
        accessories = []
        for path, analysis in zip(accessory_paths, accessory_analyses):
            acc = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if acc is None:
                acc = cv2.imread(path)
            
            if acc is not None:
                if acc.shape[2] == 3:
                    acc_rgba = self.remove_background(acc)
                else:
                    acc_rgba = acc
                
                # Crop transparent padding for tight spacing
                acc_rgba = self.crop_transparent_padding(acc_rgba)
                
                category = analysis['category']
                order = self.get_accessory_order(category)
                
                accessories.append({
                    'image': acc_rgba,
                    'name': os.path.basename(path),
                    'category': category,
                    'order': order
                })
                print(f"   ✅ Loaded {category}: {os.path.basename(path)}")
        
        if not accessories:
            print("   No accessories to display")
            return result
        
        accessories.sort(key=lambda x: x['order'])
        print(f"   📋 Ordered: {' → '.join([a['category'] for a in accessories])}")
        
        margin_top = int(main_h * 0.05)
        margin_bottom = int(main_h * 0.05)
        available_height = main_h - margin_top - margin_bottom
        
        num_accessories = len(accessories)
        max_item_height = int(available_height * 0.18)
        
        resized_accessories = []
        for acc_data in accessories:
            acc_rgba = acc_data['image']
            orig_h, orig_w = acc_rgba.shape[:2]
            aspect = orig_w / orig_h
            
            new_h = max_item_height
            new_w = int(new_h * aspect)
            
            max_width = int(main_w * 0.25)
            if new_w > max_width:
                new_w = max_width
                new_h = int(new_w / aspect)
            
            acc_resized = cv2.resize(acc_rgba, (new_w, new_h))
            resized_accessories.append(acc_resized)
        
        total_acc_height = sum(acc.shape[0] for acc in resized_accessories)
        
        print(f"   📐 Total accessories height: {total_acc_height}px")
        print(f"   📐 Available height: {available_height}px")
        
        if total_acc_height < available_height:
            total_gap_space = available_height - total_acc_height
            num_gaps = num_accessories + 1
            gap_size = total_gap_space / num_gaps
            print(f"   📏 {num_accessories} items with {num_gaps} equal gaps of {gap_size:.1f}px")
            print(f"   📏 Total space: {available_height}px - {total_acc_height}px items = {total_gap_space}px for gaps")
        else:
            gap_size = 20
            print(f"   ⚠️ Items too big, minimal gaps")
        
        max_acc_width = max(acc.shape[1] for acc in resized_accessories)
        
        # Position FAR to the right - in their own space
        x_column = int(main_w * 0.78)  # 78% across - further right
        
        # Ensure they fit with good margin
        if x_column + max_acc_width > main_w - 50:
            x_column = main_w - max_acc_width - 50
        
        y_current = margin_top + gap_size
        
        for i, acc in enumerate(resized_accessories):
            acc_h, acc_w = acc.shape[:2]
            x_pos = x_column + (max_acc_width - acc_w) // 2
            
            if y_current + acc_h > main_h - margin_bottom or x_pos < 0 or x_pos + acc_w > main_w:
                print(f"   ⚠️ Skipping accessory {i+1} - doesn't fit")
                continue
            
            y_start = int(y_current)
            y_end = int(y_current + acc_h)
            
            if acc.shape[2] == 4:
                for c in range(3):
                    alpha = acc[:, :, 3] / 255.0
                    result[y_start:y_end, x_pos:x_pos+acc_w, c] = (
                        alpha * acc[:, :, c] +
                        (1 - alpha) * result[y_start:y_end, x_pos:x_pos+acc_w, c]
                    )
            else:
                result[y_start:y_end, x_pos:x_pos+acc_w] = acc[:, :, :3]
            
            y_current += acc_h + gap_size
        
        print("   ✅ Accessories composited seamlessly")
        return result


class CollageVTO:
    def __init__(self):
        print("🔧 Initializing Collage VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.compositor = CollageCompositor()
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ Collage VTO ready\n")
    
    def generate_collage_vto(self, user_profile, clothing_items, accessory_items, 
                            clothing_description, accessory_analyses):
        
        print(f"\n✨ COLLAGE VTO")
        print(f"{'='*80}")
        print(f"Pass 1: Generate {len(clothing_items)} clothing items")
        print(f"Pass 2: Face swap")
        print(f"Pass 3: Add {len(accessory_items)} accessories")
        print(f"{'='*80}\n")
        
        print("🎨 PASS 1: Generating base outfit...")
        
        has_accessories = len(accessory_items) > 0
        
        if has_accessories:
            canvas_instruction = """- Image Format: WIDE HORIZONTAL LANDSCAPE (not portrait)
- Layout: Fashion magazine spread style with model on LEFT HALF, empty studio space on RIGHT HALF
- Model Position: Full body standing on the LEFT side of frame
- Background: Professional gray studio (#C8C8C8) extending wide to the right
- Pose: Standing straight, arms at sides

CRITICAL: Create a WIDE HORIZONTAL image like a fashion magazine double-page spread. The model should occupy the left portion, with substantial empty gray studio space extending to the right for product display. Think: model on left page, products on right page."""
        else:
            canvas_instruction = """- Canvas: Standard centered composition
- Pose: Standing straight, front-facing, centered"""
        
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
{canvas_instruction}
- Background: Professional gray studio (#C8C8C8) consistent across entire canvas
- Lighting: Soft, even lighting with subtle shadows

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
        
        os.makedirs('vto_collage_test', exist_ok=True)
        cv2.imwrite('vto_collage_test/pass1_base_outfit.png', base_image)
        
        print("🎨 PASS 2: Face swapping...")
        
        source_faces = self.app.get(user_profile.photo_cv)
        if not source_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        target_faces = self.app.get(base_image)
        if not target_faces:
            return False, None, FailureReason.FACE_DETECTION
        
        face_swapped = self.swapper.get(base_image, target_faces[0], source_faces[0], paste_back=True)
        print("✅ Pass 2 complete\n")
        
        cv2.imwrite('vto_collage_test/pass2_face_swapped.png', face_swapped)
        
        face_swapped = self.compositor.standardize_canvas(face_swapped, has_accessories)
        cv2.imwrite('vto_collage_test/pass2_standardized.png', face_swapped)
        
        if accessory_items:
            result = self.compositor.create_collage(face_swapped, accessory_items, accessory_analyses)
            print("✅ Pass 3 complete\n")
        else:
            result = face_swapped
            print("⏭️ No accessories\n")
        
        return True, result, None
    
    def _extract_image(self, response):
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def test_collage_vto(photo_path, body_type, height, clothing_paths, accessory_paths):
    print("\n" + "=" * 80)
    print("🎯 COLLAGE VTO TEST")
    print("=" * 80)
    
    profile = UserProfile(photo_path, body_type, height)
    analyzer = GarmentAnalyzer()
    
    print("\n📦 Analyzing clothing...")
    clothing_analyses = [analyzer.analyze_garment(p) for p in clothing_paths]
    clothing_desc = "\n".join([f"- {a['category'].title()}: {a['description']}" for a in clothing_analyses])
    
    print("\n📦 Analyzing accessories...")
    accessory_analyses = [analyzer.analyze_garment(p) for p in accessory_paths]
    
    vto = CollageVTO()
    
    success, image, reason = vto.generate_collage_vto(
        profile, clothing_paths, accessory_paths, clothing_desc, accessory_analyses
    )
    
    if success:
        output_path = "vto_collage_test/collage_final_result.png"
        cv2.imwrite(output_path, image)
        print(f"\n✅ SUCCESS! Saved to: {output_path}\n")
        return True
    else:
        print(f"\n❌ FAILED: {reason.value}\n")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("\nUsage: python vto_collage_system.py <photo> <body> <height> <item1> ... -- <acc1> <acc2>\n")
        sys.exit(1)
    
    try:
        sep_idx = sys.argv.index('--')
        clothing = sys.argv[4:sep_idx]
        accessories = sys.argv[sep_idx+1:]
    except ValueError:
        clothing = sys.argv[4:]
        accessories = []
    
    test_collage_vto(sys.argv[1], sys.argv[2], sys.argv[3], clothing, accessories)
