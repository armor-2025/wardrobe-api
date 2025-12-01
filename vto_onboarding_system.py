"""
Complete VTO Onboarding System with Body Type Selection
========================================================

This implements the full user onboarding flow:
1. Photo upload
2. Body type selection (4 options like MUSH app)
3. Generate base model for verification
4. VTO generation with consistent results

Usage:
    python vto_onboarding_system.py
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
os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')


class BodyTypeOption:
    """Body type options for user selection"""
    
    SLIM = {
        "id": "slim",
        "label": "Slim/Petite",
        "description": "UK 4-8, US 0-4, EU 32-36",
        "prompt": "slim/petite build, lean frame"
    }
    
    AVERAGE = {
        "id": "average",
        "label": "Average/Athletic",
        "description": "UK 10-14, US 6-10, EU 38-42",
        "prompt": "average athletic build, medium frame"
    }
    
    CURVY = {
        "id": "curvy",
        "label": "Curvy/Plus",
        "description": "UK 16-20, US 12-16, EU 44-48",
        "prompt": "curvy plus build, fuller frame"
    }
    
    PLUS = {
        "id": "plus",
        "label": "Plus Size",
        "description": "UK 22+, US 18+, EU 50+",
        "prompt": "plus size build, larger frame"
    }
    
    @classmethod
    def get_all(cls):
        return [cls.SLIM, cls.AVERAGE, cls.CURVY, cls.PLUS]
    
    @classmethod
    def get_by_id(cls, body_type_id):
        for option in cls.get_all():
            if option["id"] == body_type_id:
                return option
        return cls.AVERAGE  # Default


class UserProfile:
    """User profile with photo and preferences"""
    
    def __init__(self, photo_path, body_type_id):
        self.photo_path = photo_path
        self.body_type = BodyTypeOption.get_by_id(body_type_id)
        self.created_at = datetime.now().isoformat()
        
        # Load photo
        self.photo_pil = Image.open(photo_path)
        self.photo_cv = cv2.imread(photo_path)
        
        # Auto-detect features
        self.has_glasses = self._detect_glasses()
        self.hair_description = "from reference photo"
        self.skin_tone = "match reference exactly"
    
    def _detect_glasses(self):
        """Simple heuristic - you could use ML model for this"""
        # For now, return True if we detect certain patterns
        # In production, use a proper glasses detection model
        return True  # Placeholder
    
    def to_dict(self):
        return {
            "photo_path": self.photo_path,
            "body_type": self.body_type["id"],
            "body_type_label": self.body_type["label"],
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
    
    def generate_base_model(self, user_profile, outfit_description="casual outfit"):
        """
        Generate base model photo for user verification
        This is shown during onboarding: "Does this look like you?"
        """
        
        prompt = f"""Create professional fashion photograph of a person.

CRITICAL - Match reference person exactly:
- Skin tone: {user_profile.skin_tone}
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: {"YES - match reference glasses" if user_profile.has_glasses else "NO glasses"}
- Facial features: Match reference ethnicity and features exactly
- Build: {user_profile.body_type['prompt']}
- Age: Match reference age

Clothing: {outfit_description}

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that authentically represents the reference person with their exact appearance and {user_profile.body_type['label']} body type."""
        
        response = gemini_model.generate_content(
            [prompt, user_profile.photo_pil],
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        return self._extract_image(response)
    
    def generate_vto(self, user_profile, garment_images, garment_description):
        """
        Generate VTO with outfit
        Returns final image with user's face on matched body wearing outfit
        """
        
        # Step 1: Generate mannequin with matched appearance
        print(f"📍 Step 1: Generating model matching {user_profile.body_type['label']} body type...")
        
        garment_pil_images = [Image.open(g) if isinstance(g, str) else g for g in garment_images]
        
        prompt = f"""Create professional fashion photograph of a person.

CRITICAL - Match reference person exactly:
- Skin tone: {user_profile.skin_tone}
- Hair: Match reference exactly (color, texture, length, style)
- Glasses: {"YES - match reference glasses" if user_profile.has_glasses else "NO glasses"}
- Facial features: Match reference ethnicity and features exactly
- Build: {user_profile.body_type['prompt']}
- Age: Match reference age

Clothing: {garment_description}

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that authentically represents the reference person with {user_profile.body_type['label']} body type wearing the specified outfit."""
        
        response = gemini_model.generate_content(
            [prompt, user_profile.photo_pil] + garment_pil_images,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        
        mannequin_bytes = self._extract_image(response)
        if not mannequin_bytes:
            return None
        
        print("✅ Mannequin generated")
        
        # Step 2: Face swap
        print("📍 Step 2: Face swap for perfect identity match...")
        
        # Get source face from user photo
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


def test_consistency(user_photo_path, body_type_id, output_dir="vto_consistency_test"):
    """
    Test VTO consistency with multiple outfit generations
    
    Args:
        user_photo_path: Path to user's photo
        body_type_id: One of: slim, average, curvy, plus
        output_dir: Directory to save results
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("🎯 VTO CONSISTENCY TEST")
    print("=" * 80)
    print(f"User Photo: {user_photo_path}")
    print(f"Body Type: {body_type_id}")
    print(f"Output: {output_dir}/")
    print("=" * 80)
    print()
    
    # Step 1: Create user profile
    print("📋 Step 1: Creating User Profile")
    print("-" * 80)
    user_profile = UserProfile(user_photo_path, body_type_id)
    print(f"✅ Profile created")
    print(f"   Body Type: {user_profile.body_type['label']}")
    print(f"   Glasses: {'Yes' if user_profile.has_glasses else 'No'}")
    print()
    
    # Save profile
    profile_path = f"{output_dir}/user_profile.json"
    user_profile.save(profile_path)
    print(f"💾 Profile saved: {profile_path}\n")
    
    # Step 2: Initialize VTO engine
    vto_engine = VTOEngine()
    
    # Step 3: Generate base model for verification
    print("👤 Step 2: Generating Base Model (Onboarding Preview)")
    print("-" * 80)
    base_model = vto_engine.generate_base_model(
        user_profile,
        outfit_description="simple white t-shirt and jeans"
    )
    
    if base_model:
        base_path = f"{output_dir}/00_BASE_MODEL_verification.png"
        with open(base_path, 'wb') as f:
            f.write(base_model)
        print(f"✅ Base model: {base_path}")
        print("   (Show this to user: 'Does this look like you?')\n")
    
    # Step 4: Test outfit consistency
    print("🧪 Step 3: Testing Outfit Consistency")
    print("-" * 80)
    print("Generating 6 different outfits to test consistency...\n")
    
    ai_pics_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')
    
    test_outfits = [
        {
            "name": "outfit1_red_dress",
            "garments": [ai_pics_path + 'IMG_6563.PNG'],
            "description": "Red knee-length dress"
        },
        {
            "name": "outfit2_green_dress", 
            "garments": [ai_pics_path + 'IMG_6565.PNG'],
            "description": "Green mini dress"
        },
        {
            "name": "outfit3_jumper_jeans",
            "garments": [ai_pics_path + 'IMG_6567.PNG', ai_pics_path + 'IMG_6578.PNG'],
            "description": "Cream knit jumper, indigo wide-leg jeans"
        },
        {
            "name": "outfit4_leather_pants",
            "garments": [ai_pics_path + 'IMG_6564.PNG'],
            "description": "Brown leather trousers, black turtleneck"
        },
        {
            "name": "outfit5_bomber_jacket",
            "garments": [ai_pics_path + 'IMG_6555.PNG', ai_pics_path + 'IMG_6577.PNG'],
            "description": "Navy bomber jacket, blue wide-leg jeans"
        },
        {
            "name": "outfit6_burgundy_dress",
            "garments": [ai_pics_path + 'IMG_6566.PNG'],
            "description": "Burgundy mini dress"
        }
    ]
    
    results = []
    
    for i, outfit in enumerate(test_outfits, 1):
        print(f"🧪 Test {i}/6: {outfit['name']}")
        print(f"   Garments: {outfit['description']}")
        
        try:
            result = vto_engine.generate_vto(
                user_profile,
                outfit['garments'],
                outfit['description']
            )
            
            if result is not None:
                output_path = f"{output_dir}/{i:02d}_{outfit['name']}.png"
                cv2.imwrite(output_path, result)
                print(f"   ✅ Success: {output_path}")
                results.append({
                    "outfit": outfit['name'],
                    "success": True,
                    "path": output_path
                })
            else:
                print(f"   ❌ Failed to generate")
                results.append({
                    "outfit": outfit['name'],
                    "success": False
                })
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                "outfit": outfit['name'],
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Summary
    print("=" * 80)
    print("📊 CONSISTENCY TEST RESULTS")
    print("=" * 80)
    
    successful = sum(1 for r in results if r.get('success'))
    print(f"\n✅ Success Rate: {successful}/{len(results)} ({successful/len(results)*100:.0f}%)")
    print(f"\n📁 All results saved to: {output_dir}/\n")
    
    print("🔍 Check for consistency:")
    print("   1. Face - Same person in all photos?")
    print("   2. Glasses - Preserved in all photos?")
    print("   3. Hair - Consistent color/style?")
    print("   4. Skin tone - Same across all?")
    print("   5. Body type - Matches selected type?")
    print("   6. Clothes - Accurate to references?")
    
    print("\n" + "=" * 80)
    
    # Save results summary
    summary_path = f"{output_dir}/test_results.json"
    with open(summary_path, 'w') as f:
        json.dump({
            "user_profile": user_profile.to_dict(),
            "test_date": datetime.now().isoformat(),
            "results": results,
            "success_rate": f"{successful}/{len(results)}"
        }, f, indent=2)
    
    print(f"💾 Results summary: {summary_path}")
    print("=" * 80)
    
    return results


# Command-line interface
if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("VTO ONBOARDING & CONSISTENCY TEST SYSTEM")
    print("=" * 80 + "\n")
    
    # Example usage
    if len(sys.argv) < 3:
        print("Usage: python vto_onboarding_system.py <photo_path> <body_type>")
        print("\nBody Types:")
        for option in BodyTypeOption.get_all():
            print(f"  {option['id']:8s} - {option['label']:20s} {option['description']}")
        print("\nExample:")
        print("  python vto_onboarding_system.py ~/Desktop/AI\\ OUTFIT\\ PICS/IMG_6603.JPG curvy")
        sys.exit(1)
    
    photo_path = sys.argv[1]
    body_type = sys.argv[2]
    
    if not os.path.exists(photo_path):
        print(f"❌ Error: Photo not found: {photo_path}")
        sys.exit(1)
    
    # Run consistency test
    test_consistency(photo_path, body_type)
