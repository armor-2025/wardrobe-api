"""
Two-Step VTO Onboarding System
================================

Step 1: Body Type Selection (4 options)
Step 2: Height Selection (3 options + skip)

This creates accurate, personalized VTO results by combining
body type with height for realistic clothing visualization.

Usage:
    python vto_onboarding_complete.py <photo_path> <body_type> <height>
    
Example:
    python vto_onboarding_complete.py ~/Desktop/photo.jpg curvy tall
"""

import os
import cv2
import numpy as np
from PIL import Image
import io
import json
from datetime import datetime
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

# Configuration
os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')


class BodyType:
    """Body type definitions"""
    
    SLIM = {
        "id": "slim",
        "label": "Slim",
        "description": "UK 4-10, US 0-6, EU 32-38",
        "prompt": "slim lean build, straight silhouette, minimal curves"
    }
    
    AVERAGE = {
        "id": "average",
        "label": "Average",
        "description": "UK 10-14, US 6-10, EU 38-42",
        "prompt": "average build, balanced proportions, moderate curves"
    }
    
    CURVY = {
        "id": "curvy",
        "label": "Curvy",
        "description": "UK 14-18, US 10-14, EU 42-46",
        "prompt": "curvy build, defined waist and fuller hips, hourglass shape"
    }
    
    PLUS = {
        "id": "plus",
        "label": "Plus",
        "description": "UK 18+, US 14+, EU 46+",
        "prompt": "plus size build, fuller figure, soft curves"
    }
    
    @classmethod
    def get_all(cls):
        return [cls.SLIM, cls.AVERAGE, cls.CURVY, cls.PLUS]
    
    @classmethod
    def get_by_id(cls, body_type_id):
        for option in cls.get_all():
            if option["id"] == body_type_id:
                return option
        return cls.AVERAGE


class Height:
    """Height definitions"""
    
    PETITE = {
        "id": "petite",
        "label": "Petite",
        "description": "Under 5'4\" (163cm)",
        "prompt": "petite height under 5'4\", shorter proportions, compact frame"
    }
    
    AVERAGE = {
        "id": "average",
        "label": "Average",
        "description": "5'4\" - 5'8\" (163-173cm)",
        "prompt": "average height 5'4\"-5'8\", standard proportions, balanced frame"
    }
    
    TALL = {
        "id": "tall",
        "label": "Tall",
        "description": "Over 5'8\" (173cm)",
        "prompt": "tall height over 5'8\", longer proportions, elongated limbs"
    }
    
    NONE = {
        "id": "none",
        "label": "Not specified",
        "description": "Skip for now",
        "prompt": ""
    }
    
    @classmethod
    def get_all(cls):
        return [cls.PETITE, cls.AVERAGE, cls.TALL]
    
    @classmethod
    def get_all_with_skip(cls):
        return [cls.PETITE, cls.AVERAGE, cls.TALL, cls.NONE]
    
    @classmethod
    def get_by_id(cls, height_id):
        for option in cls.get_all_with_skip():
            if option["id"] == height_id:
                return option
        return cls.NONE


class UserProfile:
    """User profile with photo, body type, and height"""
    
    def __init__(self, photo_path, body_type_id, height_id="none"):
        self.photo_path = photo_path
        self.body_type = BodyType.get_by_id(body_type_id)
        self.height = Height.get_by_id(height_id)
        self.created_at = datetime.now().isoformat()
        
        # Load photo
        self.photo_pil = Image.open(photo_path)
        self.photo_cv = cv2.imread(photo_path)
        
        # Auto-detect features
        self.has_glasses = self._detect_glasses()
    
    def _detect_glasses(self):
        """Detect if person wears glasses - placeholder for now"""
        # TODO: Implement proper glasses detection
        return True
    
    def get_body_prompt(self):
        """Generate complete body description prompt"""
        prompt = self.body_type["prompt"]
        
        if self.height["id"] != "none":
            prompt += f", {self.height['prompt']}"
        
        return prompt
    
    def get_display_name(self):
        """Get human-readable profile description"""
        if self.height["id"] != "none":
            return f"{self.height['label']} {self.body_type['label']}"
        return self.body_type['label']
    
    def to_dict(self):
        return {
            "photo_path": self.photo_path,
            "body_type": self.body_type["id"],
            "body_type_label": self.body_type["label"],
            "height": self.height["id"],
            "height_label": self.height["label"],
            "display_name": self.get_display_name(),
            "has_glasses": self.has_glasses,
            "created_at": self.created_at
        }
    
    def save(self, output_path):
        """Save profile to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class VTOEngine:
    """VTO generation engine with InsightFace"""
    
    def __init__(self):
        print("🔧 Initializing VTO Engine...")
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ VTO Engine ready\n")
    
    def generate_vto(self, user_profile, garment_images, garment_description, include_shoes=True):
        """
        Generate VTO with full-body shot including shoes
        
        Args:
            user_profile: UserProfile object
            garment_images: List of garment image paths or PIL Images
            garment_description: Text description of complete outfit
            include_shoes: Whether to ensure shoes are visible
        """
        
        print(f"📍 Step 1: Generating {user_profile.get_display_name()} model...")
        
        # Load garment images
        garment_pil_images = []
        for g in garment_images:
            if isinstance(g, str):
                garment_pil_images.append(Image.open(g))
            else:
                garment_pil_images.append(g)
        
        # Build complete prompt
        body_prompt = user_profile.get_body_prompt()
        
        composition = "FULL-LENGTH professional fashion photograph from HEAD TO FEET" if include_shoes else "Professional fashion photograph"
        
        prompt = f"""{composition}

CRITICAL - Match reference person exactly:
- Skin tone: Match reference photo exactly
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: {"YES - match reference glasses exactly" if user_profile.has_glasses else "NO glasses"}
- Facial features: Match reference ethnicity and features exactly
- Body type and height: {body_prompt}
- Age: Match reference age

Clothing (COMPLETE outfit from top to bottom):
{garment_description}"""

        if include_shoes:
            prompt += """

COMPOSITION REQUIREMENTS (CRITICAL):
- FULL BODY SHOT: Must show entire person from head to feet
- Include complete legs and footwear in frame
- Framing: Show full outfit from top of head to bottom of shoes
- Camera angle: Full-length body shot (not cropped at legs or knees)
- Ensure feet and shoes are fully visible"""

        prompt += """

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that authentically represents the reference person with their exact appearance and body type wearing the complete outfit."""
        
        # Generate with Gemini
        response = gemini_model.generate_content(
            [prompt, user_profile.photo_pil] + garment_pil_images,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        mannequin_bytes = self._extract_image(response)
        if not mannequin_bytes:
            print("❌ Gemini generation failed")
            return None
        
        print("✅ Mannequin generated")
        
        # Step 2: Face swap
        print("📍 Step 2: Face swap for perfect identity match...")
        
        # Get source face
        source_faces = self.app.get(user_profile.photo_cv)
        if not source_faces:
            print("❌ No face detected in user photo")
            return None
        source_face = source_faces[0]
        
        # Get target face from mannequin
        target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
        target_faces = self.app.get(target_img)
        
        if not target_faces:
            print("❌ No face detected in mannequin")
            return None
        
        # Perform face swap
        result = self.swapper.get(target_img, target_faces[0], source_face, paste_back=True)
        print("✅ Face swap complete\n")
        
        return result
    
    def _extract_image(self, response):
        """Extract image bytes from Gemini response"""
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def display_onboarding_options():
    """Display available options for user reference"""
    
    print("\n" + "=" * 80)
    print("STEP 1: BODY TYPE OPTIONS")
    print("=" * 80)
    for bt in BodyType.get_all():
        print(f"  {bt['id']:8s} - {bt['label']:10s} ({bt['description']})")
    
    print("\n" + "=" * 80)
    print("STEP 2: HEIGHT OPTIONS (Optional)")
    print("=" * 80)
    for ht in Height.get_all_with_skip():
        print(f"  {ht['id']:8s} - {ht['label']:10s} ({ht['description']})")
    
    print("\n" + "=" * 80)


def test_full_system(photo_path, body_type_id, height_id="none", output_dir="vto_test_results"):
    """
    Complete test of two-step onboarding system
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("🎯 TWO-STEP VTO ONBOARDING TEST")
    print("=" * 80)
    print(f"Photo: {photo_path}")
    print(f"Body Type: {body_type_id}")
    print(f"Height: {height_id}")
    print(f"Output: {output_dir}/")
    print("=" * 80 + "\n")
    
    # Create profile
    print("📋 Creating User Profile")
    print("-" * 80)
    profile = UserProfile(photo_path, body_type_id, height_id)
    print(f"✅ Profile: {profile.get_display_name()}")
    print(f"   Body: {profile.body_type['label']} ({profile.body_type['description']})")
    print(f"   Height: {profile.height['label']} ({profile.height['description']})")
    print(f"   Glasses: {'Yes' if profile.has_glasses else 'No'}")
    print(f"   Body Prompt: {profile.get_body_prompt()}")
    
    profile_path = f"{output_dir}/user_profile.json"
    profile.save(profile_path)
    print(f"💾 Saved: {profile_path}\n")
    
    # Initialize engine
    engine = VTOEngine()
    
    # Test outfits
    ai_pics = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')
    
    test_cases = [
        {
            "name": "01_jumper_jeans_boots",
            "garments": [ai_pics + 'IMG_6567.PNG', ai_pics + 'IMG_6578.PNG', ai_pics + 'IMG_6574.PNG'],
            "description": """- Top: Cream chunky knit oversized sweater
- Bottoms: Indigo wide-leg jeans (full length to ankles)
- Footwear: Sand/beige UGG-style boots"""
        },
        {
            "name": "02_burgundy_dress_boots",
            "garments": [ai_pics + 'IMG_6566.PNG', ai_pics + 'IMG_6573.PNG'],
            "description": """- Dress: Burgundy mini dress
- Footwear: Knee-high leather boots"""
        },
        {
            "name": "03_bomber_jeans",
            "garments": [ai_pics + 'IMG_6555.PNG', ai_pics + 'IMG_6577.PNG'],
            "description": """- Outer: Navy bomber jacket (worn open)
- Top: White t-shirt underneath
- Bottoms: Blue wide-leg jeans
- Footwear: Black ankle boots"""
        },
        {
            "name": "04_coat_outfit",
            "garments": [ai_pics + 'IMG_6569.PNG', ai_pics + 'IMG_6578.PNG'],
            "description": """- Outer: Grey wool overcoat (worn open)
- Top: Black turtleneck
- Bottoms: Indigo wide-leg jeans
- Footwear: Black leather boots"""
        }
    ]
    
    print("🧪 Testing 4 Complete Outfits (with shoes)")
    print("-" * 80 + "\n")
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}/4: {test['name']}")
        
        try:
            result = engine.generate_vto(
                profile,
                test['garments'],
                test['description'],
                include_shoes=True
            )
            
            if result is not None:
                output_path = f"{output_dir}/{test['name']}.png"
                cv2.imwrite(output_path, result)
                print(f"✅ Success: {output_path}\n")
                results.append({"test": test['name'], "success": True})
            else:
                print(f"❌ Failed\n")
                results.append({"test": test['name'], "success": False})
                
        except Exception as e:
            print(f"❌ Error: {e}\n")
            results.append({"test": test['name'], "success": False, "error": str(e)})
    
    # Summary
    print("=" * 80)
    print("📊 TEST RESULTS")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\n✅ Success Rate: {success_count}/4 ({success_count/4*100:.0f}%)")
    print(f"\n📁 Results: {output_dir}/\n")
    
    print("🔍 Check for:")
    print("   1. Full body visible (head to feet)")
    print("   2. Shoes/boots visible")
    print("   3. Body type matches selection")
    print("   4. Height proportions correct")
    print("   5. Face and glasses preserved")
    print("   6. Consistent across all outfits")
    
    print("\n" + "=" * 80)
    
    return results


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("VTO TWO-STEP ONBOARDING SYSTEM")
    print("=" * 80)
    
    if len(sys.argv) < 3:
        print("\nUsage: python vto_onboarding_complete.py <photo> <body_type> [height]")
        display_onboarding_options()
        print("\nExamples:")
        print("  python vto_onboarding_complete.py photo.jpg slim petite")
        print("  python vto_onboarding_complete.py photo.jpg curvy tall")
        print("  python vto_onboarding_complete.py photo.jpg average")
        print("=" * 80 + "\n")
        sys.exit(1)
    
    photo = sys.argv[1]
    body_type = sys.argv[2]
    height = sys.argv[3] if len(sys.argv) > 3 else "none"
    
    if not os.path.exists(photo):
        print(f"❌ Photo not found: {photo}")
        sys.exit(1)
    
    test_full_system(photo, body_type, height)
