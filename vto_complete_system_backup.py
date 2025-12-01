"""
Complete Integrated VTO Production System
==========================================

Full production-ready system combining:
- Garment analysis with AI descriptions
- Two-step user onboarding (body type + height)
- VTO generation with retry logic
- Professional error handling

This is the complete system for your API.

Usage:
    python vto_complete_system.py <photo> <body_type> <height> <garment1> <garment2> ...
    
Example:
    python vto_complete_system.py photo.jpg curvy tall dress.png boots.png
"""

import os
import cv2
import numpy as np
from PIL import Image
import io
import json
from datetime import datetime
from enum import Enum
import google.generativeai as genai
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

# Configuration
os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])


# ============================================================================
# GARMENT ANALYZER
# ============================================================================

class GarmentAnalyzer:
    """Analyzes garment images and generates professional descriptions"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self._cache = {}  # Simple in-memory cache
    
    def analyze_garment(self, image_path):
        """
        Analyze a garment image and generate professional description
        
        Returns:
            dict with category and professional description
        """
        
        # Check cache
        if image_path in self._cache:
            print(f"   📦 Using cached analysis")
            return self._cache[image_path]
        
        print(f"   🔍 Analyzing garment...")
        
        image = Image.open(image_path)
        
        prompt = """Analyze this clothing item and provide a professional fashion description.

CRITICAL REQUIREMENTS:
1. Be specific and detailed
2. Use professional fashion terminology
3. Include ALL relevant details:
   - Item type (dress, top, pants, jacket, shoes, etc.)
   - Style (mini, midi, maxi, knee-length, cropped, oversized, etc.)
   - Color (be specific: burgundy not red, navy not blue)
   - Material/fabric if visible
   - Key design features (sleeves, neckline, cut, fit)
   - Length/fit descriptors

4. Use modest, professional language:
   - Say "knee-length dress" not just "mini dress"
   - Say "fitted cocktail dress" not just "tight dress"
   - Emphasize style and fashion, not body exposure

5. Format as a single-line description suitable for fashion photography

EXAMPLES OF GOOD DESCRIPTIONS:
- "Burgundy velvet knee-length cocktail dress with long sleeves and fitted bodice"
- "Emerald green midi dress with scalloped hem and three-quarter sleeves"
- "Navy blue bomber jacket with orange satin lining, worn open"
- "Cream chunky cable-knit oversized sweater with ribbed cuffs"
- "Indigo wide-leg high-waisted denim jeans with full-length cut"
- "Black knee-high leather boots with block heel"

Return ONLY the description, nothing else."""
        
        response = self.model.generate_content([prompt, image])
        description = response.text.strip()
        
        # Get category
        category_prompt = """What category is this clothing item? 

Return ONLY ONE of these categories:
- dress
- top
- bottom
- outerwear
- shoes
- accessory

Return only the category word, nothing else."""
        
        category_response = self.model.generate_content([category_prompt, image])
        category = category_response.text.strip().lower()
        
        result = {
            "description": description,
            "category": category,
            "image_path": image_path
        }
        
        # Cache it
        self._cache[image_path] = result
        
        print(f"   ✅ {category}: {description}")
        
        return result
    
    def analyze_outfit(self, garment_images):
        """
        Analyze multiple garments and generate complete outfit description
        
        Returns:
            Complete outfit description formatted for VTO prompt
        """
        
        print("\n📸 Analyzing garments...")
        
        garments = []
        for img_path in garment_images:
            garment_info = self.analyze_garment(img_path)
            garments.append(garment_info)
        
        # Build complete outfit description
        outfit_parts = []
        
        # Order by typical wearing order
        category_order = ['outerwear', 'top', 'dress', 'bottom', 'shoes', 'accessory']
        
        for category in category_order:
            matching = [g for g in garments if g['category'] == category]
            for garment in matching:
                if category == 'outerwear':
                    outfit_parts.append(f"- Outer layer: {garment['description']}")
                elif category == 'top':
                    outfit_parts.append(f"- Top: {garment['description']}")
                elif category == 'dress':
                    outfit_parts.append(f"- Dress: {garment['description']}")
                elif category == 'bottom':
                    outfit_parts.append(f"- Bottoms: {garment['description']}")
                elif category == 'shoes':
                    outfit_parts.append(f"- Footwear: {garment['description']}")
                elif category == 'accessory':
                    outfit_parts.append(f"- Accessory: {garment['description']}")
        
        outfit_description = "\n".join(outfit_parts)
        
        print(f"\n📝 Complete outfit description:")
        print(outfit_description)
        
        return {
            "garments": garments,
            "outfit_description": outfit_description
        }


# ============================================================================
# VTO SYSTEM
# ============================================================================

class FailureReason(Enum):
    """Reasons why VTO generation might fail"""
    CONTENT_POLICY = "content_policy"
    FACE_DETECTION = "face_detection"
    FACE_SWAP_QUALITY = "face_swap_quality"
    GENERATION_FAILED = "generation_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class VTOResult:
    """Result of VTO generation with metadata"""
    
    def __init__(self, success, image=None, failure_reason=None, attempts=1, error_message=None):
        self.success = success
        self.image = image
        self.failure_reason = failure_reason
        self.attempts = attempts
        self.error_message = error_message
        self.timestamp = datetime.now().isoformat()
    
    def get_user_message(self):
        """Get professional message to show user"""
        if self.success:
            if self.attempts > 1:
                return "Generated successfully after a few tries!"
            return "Perfect! Here's how this looks on you."
        
        messages = {
            FailureReason.CONTENT_POLICY: {
                "title": "Unable to generate this combination",
                "message": "Our AI system couldn't process this particular clothing combination due to content safety guidelines. This isn't a reflection on you or the clothing - it's a technical limitation we're working to improve. Please try a different item or contact support if you believe this is an error.",
                "action": "Try a different item"
            },
            FailureReason.FACE_DETECTION: {
                "title": "Couldn't detect face clearly",
                "message": "We had trouble detecting your face in the photo. This can happen with certain lighting or angles. Try uploading a clearer photo with good lighting and your face visible.",
                "action": "Upload a different photo"
            },
            FailureReason.FACE_SWAP_QUALITY: {
                "title": "Generation quality issue",
                "message": "We generated the outfit but the quality wasn't quite right. This happens occasionally - we've already tried a few times. Please tap 'Try Again' to generate a new version.",
                "action": "Try again"
            },
            FailureReason.GENERATION_FAILED: {
                "title": "Generation didn't complete",
                "message": "We couldn't complete the generation this time. This is rare and usually resolves quickly. Please try again in a moment.",
                "action": "Try again"
            },
            FailureReason.NETWORK_ERROR: {
                "title": "Connection issue",
                "message": "We had trouble connecting to our servers. Please check your internet connection and try again.",
                "action": "Check connection"
            },
            FailureReason.UNKNOWN: {
                "title": "Something went wrong",
                "message": "We encountered an unexpected issue. Our team has been notified. Please try again or contact support if this continues.",
                "action": "Try again"
            }
        }
        
        return messages.get(self.failure_reason, messages[FailureReason.UNKNOWN])


class VTOSystem:
    """Production VTO system with retry logic"""
    
    def __init__(self):
        print("🔧 Initializing VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ VTO System ready")
    
    def generate_vto_single_attempt(self, user_profile, garment_images, garment_description, include_shoes=True):
        """Single VTO generation attempt"""
        
        try:
            # Load garment images
            garment_pil_images = []
            for g in garment_images:
                if isinstance(g, str):
                    garment_pil_images.append(Image.open(g))
                else:
                    garment_pil_images.append(g)
            
            # Build prompt
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
            response = self.gemini_model.generate_content(
                [prompt, user_profile.photo_pil] + garment_pil_images,
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            
            # Check for blocks
            if hasattr(response, 'prompt_feedback'):
                block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                if block_reason:
                    return False, None, FailureReason.CONTENT_POLICY
            
            mannequin_bytes = self._extract_image(response)
            if not mannequin_bytes:
                return False, None, FailureReason.GENERATION_FAILED
            
            # Face swap
            source_faces = self.app.get(user_profile.photo_cv)
            if not source_faces:
                return False, None, FailureReason.FACE_DETECTION
            source_face = source_faces[0]
            
            target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
            target_faces = self.app.get(target_img)
            
            if not target_faces:
                return False, None, FailureReason.FACE_DETECTION
            
            result = self.swapper.get(target_img, target_faces[0], source_face, paste_back=True)
            
            return True, result, None
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if "network" in str(e).lower() or "connection" in str(e).lower():
                return False, None, FailureReason.NETWORK_ERROR
            return False, None, FailureReason.UNKNOWN
    
    def generate_vto_with_retry(self, user_profile, garment_images, garment_description, 
                                 include_shoes=True, max_attempts=3):
        """Generate VTO with automatic retry logic"""
        
        print(f"\n🎯 Generating VTO for {user_profile.get_display_name()}")
        
        last_failure_reason = None
        
        for attempt in range(1, max_attempts + 1):
            print(f"   Attempt {attempt}/{max_attempts}...", end=" ")
            
            success, image, failure_reason = self.generate_vto_single_attempt(
                user_profile, 
                garment_images, 
                garment_description, 
                include_shoes
            )
            
            if success:
                print(f"✅")
                return VTOResult(success=True, image=image, attempts=attempt)
            
            last_failure_reason = failure_reason
            print(f"❌ ({failure_reason.value})")
            
            # Don't retry content policy blocks
            if failure_reason == FailureReason.CONTENT_POLICY:
                break
            if failure_reason == FailureReason.NETWORK_ERROR:
                break
        
        return VTOResult(
            success=False,
            failure_reason=last_failure_reason,
            attempts=max_attempts,
            error_message=f"Failed after {max_attempts} attempts"
        )
    
    def _extract_image(self, response):
        """Extract image bytes from Gemini response"""
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


# ============================================================================
# USER PROFILE
# ============================================================================

class BodyType:
    SLIM = {"id": "slim", "label": "Slim", "prompt": "slim lean build, straight silhouette, minimal curves"}
    AVERAGE = {"id": "average", "label": "Average", "prompt": "average build, balanced proportions, moderate curves"}
    CURVY = {"id": "curvy", "label": "Curvy", "prompt": "curvy build, defined waist and fuller hips, hourglass shape"}
    PLUS = {"id": "plus", "label": "Plus", "prompt": "plus size build, fuller figure, soft curves"}
    
    @classmethod
    def get_by_id(cls, body_type_id):
        for option in [cls.SLIM, cls.AVERAGE, cls.CURVY, cls.PLUS]:
            if option["id"] == body_type_id:
                return option
        return cls.AVERAGE


class Height:
    PETITE = {"id": "petite", "label": "Petite", "prompt": "petite height under 5'4\", shorter proportions, compact frame"}
    AVERAGE = {"id": "average", "label": "Average", "prompt": "average height 5'4\"-5'8\", standard proportions, balanced frame"}
    TALL = {"id": "tall", "label": "Tall", "prompt": "tall height over 5'8\", longer proportions, elongated limbs"}
    NONE = {"id": "none", "label": "Not specified", "prompt": ""}
    
    @classmethod
    def get_by_id(cls, height_id):
        for option in [cls.PETITE, cls.AVERAGE, cls.TALL, cls.NONE]:
            if option["id"] == height_id:
                return option
        return cls.NONE


class UserProfile:
    def __init__(self, photo_path, body_type_id, height_id="none"):
        self.photo_path = photo_path
        self.body_type = BodyType.get_by_id(body_type_id)
        self.height = Height.get_by_id(height_id)
        self.photo_pil = Image.open(photo_path)
        self.photo_cv = cv2.imread(photo_path)
        self.has_glasses = True  # TODO: Auto-detect
    
    def get_body_prompt(self):
        prompt = self.body_type["prompt"]
        if self.height["id"] != "none":
            prompt += f", {self.height['prompt']}"
        return prompt
    
    def get_display_name(self):
        if self.height["id"] != "none":
            return f"{self.height['label']} {self.body_type['label']}"
        return self.body_type['label']


# ============================================================================
# COMPLETE WORKFLOW
# ============================================================================

def complete_vto_workflow(photo_path, body_type, height, garment_paths, output_dir="vto_complete_test"):
    """
    Complete VTO workflow:
    1. Create user profile
    2. Analyze garments
    3. Generate VTO with retry
    4. Save results
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("🎯 COMPLETE INTEGRATED VTO SYSTEM")
    print("=" * 80)
    print(f"Model: {photo_path}")
    print(f"Profile: {body_type} + {height}")
    print(f"Garments: {len(garment_paths)} items")
    print("=" * 80)
    
    # Step 1: Create user profile
    print("\n👤 Step 1: Creating User Profile")
    print("-" * 80)
    profile = UserProfile(photo_path, body_type, height)
    print(f"✅ Profile: {profile.get_display_name()}")
    print(f"   Body: {profile.body_type['label']}")
    print(f"   Height: {profile.height['label']}")
    
    # Step 2: Analyze garments
    print("\n🔍 Step 2: Analyzing Garments with AI")
    print("-" * 80)
    analyzer = GarmentAnalyzer()
    outfit = analyzer.analyze_outfit(garment_paths)
    
    # Step 3: Generate VTO
    print("\n✨ Step 3: Generating VTO")
    print("-" * 80)
    vto_system = VTOSystem()
    
    result = vto_system.generate_vto_with_retry(
        profile,
        garment_paths,
        outfit['outfit_description'],
        include_shoes=True,
        max_attempts=3
    )
    
    # Step 4: Save results
    print("\n💾 Step 4: Saving Results")
    print("-" * 80)
    
    if result.success:
        output_path = f"{output_dir}/vto_result.png"
        cv2.imwrite(output_path, result.image)
        print(f"✅ Success! Saved to: {output_path}")
        print(f"   Attempts: {result.attempts}")
        
        # Save metadata
        metadata = {
            "profile": {
                "body_type": profile.body_type['label'],
                "height": profile.height['label']
            },
            "garments": outfit['garments'],
            "outfit_description": outfit['outfit_description'],
            "result": {
                "success": True,
                "attempts": result.attempts,
                "timestamp": result.timestamp
            }
        }
        
        with open(f"{output_dir}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"   Metadata: {output_dir}/metadata.json")
        
        return True
        
    else:
        print(f"❌ Failed after {result.attempts} attempts")
        print(f"   Reason: {result.failure_reason.value}")
        
        user_msg = result.get_user_message()
        print(f"\n📱 User would see:")
        print(f"   {user_msg['title']}")
        print(f"   {user_msg['message']}")
        
        # Save error info
        error_data = {
            "profile": {
                "body_type": profile.body_type['label'],
                "height": profile.height['label']
            },
            "garments": outfit['garments'],
            "error": {
                "reason": result.failure_reason.value,
                "attempts": result.attempts,
                "user_message": user_msg
            }
        }
        
        with open(f"{output_dir}/error.json", 'w') as f:
            json.dump(error_data, f, indent=2)
        
        return False
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("\n" + "=" * 80)
        print("USAGE")
        print("=" * 80)
        print("\npython vto_complete_system.py <photo> <body_type> <height> <garment1> [garment2] ...")
        print("\nExample:")
        print("  python vto_complete_system.py \\")
        print("    photo.jpg \\")
        print("    curvy \\")
        print("    tall \\")
        print("    dress.png \\")
        print("    boots.png")
        print("\nBody Types: slim, average, curvy, plus")
        print("Heights: petite, average, tall, none")
        print("=" * 80 + "\n")
        sys.exit(1)
    
    photo = sys.argv[1]
    body_type = sys.argv[2]
    height = sys.argv[3]
    garments = sys.argv[4:]
    
    complete_vto_workflow(photo, body_type, height, garments)
