"""
Complete VTO System with Smart Eyewear + Swapped Body Types
=============================================================
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

os.environ['GEMINI_API_KEY'] = 'AIzaSyD1xXl-VJPuMVAs8KWEEpRt0q0dV_BAt78'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])


class GarmentAnalyzer:
    """Analyzes ALL garments in ONE Gemini call for efficiency"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def analyze_outfit(self, garment_images):
        """Analyze all garments in a SINGLE API call"""
        print("\n🔍 Step 2: Analyzing ALL Garments (1 API call)")
        print("-" * 80)
        
        # Load all images
        images = [Image.open(img) if isinstance(img, str) else img for img in garment_images]
        
        prompt = f"""Analyze these {len(images)} clothing items. For EACH item, provide:
- Category (one of: dress, top, bottom, outerwear, shoes, accessory)
- Professional fashion description with color, style, material, features

Return in this EXACT format (one item per line):
ITEM 1: [category] - [description]
ITEM 2: [category] - [description]
...

Example:
ITEM 1: outerwear - Classic indigo denim trucker jacket with button front closure
ITEM 2: top - White cotton graphic t-shirt with blue and red print
ITEM 3: bottom - Black wide-leg drawstring trousers in fluid fabric
ITEM 4: shoes - Burgundy suede Adidas sneakers with gum sole"""
        
        response = self.model.generate_content([prompt] + images)
        text = response.text.strip()
        print(f"   Raw response: {text[:200]}...")
        
        # Parse response
        garments = []
        outfit_parts = []
        
        for line in text.split("\n"):
            if line.strip().startswith("ITEM"):
                try:
                    # Parse "ITEM N: category - description"
                    parts = line.split(":", 1)[1].strip()  # Get after "ITEM N:"
                    cat_desc = parts.split(" - ", 1)
                    category = cat_desc[0].strip().lower()
                    description = cat_desc[1].strip() if len(cat_desc) > 1 else parts
                    
                    garments.append({"category": category, "description": description})
                    
                    # Format for outfit description
                    if category == 'outerwear': outfit_parts.append(f"- Outer layer: {description}")
                    elif category == 'top': outfit_parts.append(f"- Top: {description}")
                    elif category == 'dress': outfit_parts.append(f"- Dress: {description}")
                    elif category == 'bottom': outfit_parts.append(f"- Bottoms: {description}")
                    elif category == 'shoes': outfit_parts.append(f"- Footwear: {description}")
                    elif category == 'accessory': outfit_parts.append(f"- Accessory: {description}")
                    else: outfit_parts.append(f"- {category.title()}: {description}")
                    
                    print(f"   ✅ {category}: {description}")
                except:
                    pass
        
        outfit_description = "\n".join(outfit_parts)
        print(f"\n📝 Complete outfit description:")
        print(outfit_description)
        
        return {"garments": garments, "outfit_description": outfit_description}


class FailureReason(Enum):
    CONTENT_POLICY = "content_policy"
    FACE_DETECTION = "face_detection"
    GENERATION_FAILED = "generation_failed"
    UNKNOWN = "unknown"


class VTOResult:
    def __init__(self, success, image=None, failure_reason=None, attempts=1):
        self.success = success
        self.image = image
        self.failure_reason = failure_reason
        self.attempts = attempts
        self.timestamp = datetime.now().isoformat()
    
    def get_user_message(self):
        if self.success:
            return None
        
        messages = {
            FailureReason.CONTENT_POLICY: {
                "title": "Unable to generate this combination",
                "message": "Our AI system couldn't process this particular clothing combination due to content safety guidelines.",
                "action": "Try a different item"
            },
            FailureReason.FACE_DETECTION: {
                "title": "Couldn't detect face clearly",
                "message": "We had trouble detecting your face in the photo. Try uploading a clearer photo.",
                "action": "Upload a different photo"
            },
            FailureReason.GENERATION_FAILED: {
                "title": "Generation didn't complete",
                "message": "We couldn't complete the generation. Please try again.",
                "action": "Try again"
            },
            FailureReason.UNKNOWN: {
                "title": "Something went wrong",
                "message": "We encountered an unexpected issue. Please try again.",
                "action": "Try again"
            }
        }
        
        return messages.get(self.failure_reason, messages[FailureReason.UNKNOWN])


class BodyType:
    SLIM = {
        "id": "slim",
        "label": "Slim",
        "prompt": "slim lean build, straight silhouette, minimal curves"
    }
    
    AVERAGE = {
        "id": "average",
        "label": "Average",
        "prompt": "average medium build, UK size 14, noticeably fuller body with soft curves, fuller hips and bust than slim"
    }
    
    CURVY = {
        "id": "curvy",
        "label": "Curvy",
        "prompt": "plus size build, fuller figure, soft curves"
    }
    
    PLUS = {
        "id": "plus",
        "label": "Plus",
        "prompt": "plus size build, UK size 26-28, very large fuller figure, substantially rounder body, noticeably wider frame, fuller rounder face, fuller arms and legs, soft rounded curves throughout"
    }
    
    @classmethod
    def get_by_id(cls, body_type_id):
        for opt in [cls.SLIM, cls.AVERAGE, cls.CURVY, cls.PLUS]:
            if opt["id"] == body_type_id:
                return opt
        return cls.AVERAGE

class Height:
    PETITE = {
        "id": "petite",
        "label": "Petite",
        "prompt": "petite height under 5'4\", shorter proportions"
    }    
    AVERAGE = {
        "id": "average",
        "label": "Average",
        "prompt": "average height 5'4\"-5'8\", standard proportions"
    }
    
    TALL = {
        "id": "tall",
        "label": "Tall",
        "prompt": "tall height over 5'8\", longer proportions"
    }
    
    NONE = {
        "id": "none",
        "label": "Not specified",
        "prompt": ""
    }
    
    @classmethod
    def get_by_id(cls, height_id):
        for opt in [cls.PETITE, cls.AVERAGE, cls.TALL, cls.NONE]:
            if opt["id"] == height_id:
                return opt
        return cls.NONE


class UserProfile:
    def __init__(self, photo_path, body_type_id, height_id="none", gender_presentation="menswear", appearance_description=None):
        self.photo_path = photo_path
        self.body_type = BodyType.get_by_id(body_type_id)
        self.height = Height.get_by_id(height_id)
        self.photo_pil = Image.open(photo_path)
        self.photo_cv = cv2.imread(photo_path)
        self.has_glasses = False
        self.gender_presentation = gender_presentation  # "menswear" or "womenswear"
        
        # Analyze appearance once (like ALTA does)
        if appearance_description is None:
            self.appearance = self._analyze_appearance()
        else:
            self.appearance = appearance_description
        
        # Detect glasses from appearance description
        if self.appearance and ('glasses' in self.appearance.lower() or 'wearing' in self.appearance.lower()):
            self.has_glasses = True
    def _analyze_appearance(self):
        """Analyze photo to get consistent hair & skin description (like ALTA)"""
        try:
            analyzer = genai.GenerativeModel('gemini-2.5-flash-image')
            
            # Check if this is menswear or womenswear to adjust analysis
            is_menswear = self.gender_presentation == "menswear"
            
            if is_menswear:
                prompt = """Analyze this person's hair, facial hair, AND glasses in detail.

CRITICAL - Hair length definitions:
- "very short/buzzcut" = less than 1 inch, military cut
- "short" = 1-3 inches, styled but above ears
- "medium" = 4-6 inches, reaches ears or covers them
- "long" = past ears, toward shoulders or beyond

Format: "[hair description], [facial hair description], [glasses: yes/no]"

Hair: State length (very short/short/medium/long), texture, color, and styling
Facial hair: Be specific - "full thick beard", "short trimmed beard", "light stubble", "goatee", "mustache", or "clean shaven"

Examples:
- "short textured black hair styled upward (2-3 inches), full thick dark beard, wearing black frame glasses"
- "very short buzzcut black hair (under 1 inch), clean shaven, no glasses"
- "medium wavy brown hair covering ears, short trimmed beard, wearing clear frame glasses"

IMPORTANT: If hair is above or at ear level, it's SHORT not medium. Be accurate about measurements."""
            else:
                prompt = """Analyze this person's hairstyle AND glasses in detail.

Provide: length, texture, color, styling details, and whether they wear glasses

Examples:
- "shoulder-length straight blonde hair center-parted, wearing tortoiseshell frame glasses"
- "long curly dark brown hair with volume, no glasses"
- "short textured black hair with bangs, wearing round black glasses"

Be detailed and specific."""
            
            response = analyzer.generate_content([prompt, self.photo_pil])
            description = response.text.strip().replace('"', '').replace("'", "")
            
            print(f"   📸 Appearance: {description}")
            return description
        except Exception as e:
            print(f"   ⚠️  Could not analyze: {e}")
            return "short dark hair"  # Fallback

        
        # Analyze appearance once (like ALTA does)
        if appearance_description is None:
            self.appearance = self._analyze_appearance()
        else:
            self.appearance = appearance_description
        
        # Detect glasses from appearance description
        if self.appearance and ('glasses' in self.appearance.lower() or 'wearing' in self.appearance.lower()):
            self.has_glasses = True
    
    def get_body_prompt(self):
        prompt = self.body_type["prompt"]
        if self.height["id"] != "none":
            prompt += f", {self.height['prompt']}"
        # Add appearance for consistency
        if hasattr(self, 'appearance'):
            prompt += f", {self.appearance}"
        return prompt
    
    def get_display_name(self):
        if self.height["id"] != "none":
            return f"{self.height['label']} {self.body_type['label']}"
        return self.body_type['label']


class VTOSystem:
    def __init__(self):
        print("🔧 Initializing VTO System...")
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-image')
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ VTO System ready\n")
    
    def _is_trying_on_eyewear(self, description):
        """Check if outfit includes eyewear to try on"""
        eyewear_keywords = [
            'sunglasses', 'glasses', 'eyeglasses', 'eyewear', 'shades',
            'spectacles', 'frames', 'reading glasses', 'aviators', 'wayfarers'
        ]
        desc_lower = description.lower()
        return any(keyword in desc_lower for keyword in eyewear_keywords)
    
    def generate_vto_with_retry(self, user_profile, garment_images, garment_description, max_attempts=3):
        print(f"\n✨ Step 3: Generating VTO")
        print("-" * 80)
        print(f"🎯 Generating for {user_profile.get_display_name()}")
        
        for attempt in range(1, max_attempts + 1):
            print(f"   Attempt {attempt}/{max_attempts}...", end=" ")
            success, image, reason = self._generate_single(user_profile, garment_images, garment_description)
            
            if success:
                print("✅")
                return VTOResult(True, image, None, attempt)
            
            print(f"❌ ({reason.value})")
            if reason == FailureReason.CONTENT_POLICY:
                break
        
        return VTOResult(False, None, reason, max_attempts)
    
    def _generate_single(self, profile, garment_images, description):
        try:
            garment_pils = [Image.open(g) if isinstance(g, str) else g for g in garment_images]
            
            # Smart eyewear handling
            trying_on_eyewear = self._is_trying_on_eyewear(description)
            
            if trying_on_eyewear:
                eyewear_instruction = "wearing the eyewear/sunglasses from the garment as shown in images"
            elif profile.has_glasses:
                eyewear_instruction = "wearing their own glasses exactly as shown in reference photo"
            else:
                eyewear_instruction = "with NO eyewear on face - clear unobstructed eyes, no glasses of any kind"
            
            # Parse hair description for specific constraints
            hair_desc = profile.appearance if hasattr(profile, 'appearance') else 'short dark hair'
            is_short = 'short' in hair_desc.lower() and 'shoulder' not in hair_desc.lower()
            is_straight = 'straight' in hair_desc.lower()
            
            # Build ultra-specific hair instruction
            hair_constraint = f"Hair: {hair_desc}"
            if is_short:
                hair_constraint += " - CRITICAL: Hair length MUST be above ears, 2-4 inches maximum"
            if is_straight:
                hair_constraint += " - MUST be straight, no curls or waves"
            
            prompt = f"""FULL-LENGTH professional fashion photograph from HEAD TO FEET

CRITICAL - Match reference person EXACTLY:
- Skin tone: Match exactly
- {hair_constraint}
- FORBIDDEN: Long hair, shoulder-length hair, hair below ears, curly hair (unless specified)
- Eyewear: {eyewear_instruction}
- Facial features: Match ethnicity and features exactly
- Body: {profile.get_body_prompt()}
- Age: Match reference

Clothing (complete outfit):
{description}

COMPOSITION REQUIREMENTS:
- FULL BODY: Must show entire person from head to feet
- Include complete legs and footwear in frame
- Not cropped at knees or legs

Pose: Standing straight, front-facing, arms naturally at sides
Background: Professional gray studio (#C8C8C8)
Lighting: Soft, even fashion photography lighting

Create a model that matches the reference person's hair length and skin tone exactly."""

            
            response = self.gemini_model.generate_content(
                [prompt, profile.photo_pil] + garment_pils,
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            
            if hasattr(response, 'prompt_feedback') and getattr(response.prompt_feedback, 'block_reason', None):
                return False, None, FailureReason.CONTENT_POLICY
            
            mannequin_bytes = self._extract_image(response)
            if not mannequin_bytes:
                return False, None, FailureReason.GENERATION_FAILED
            
            source_faces = self.app.get(profile.photo_cv)
            if not source_faces:
                return False, None, FailureReason.FACE_DETECTION
            
            target_img = cv2.imdecode(np.frombuffer(mannequin_bytes, np.uint8), cv2.IMREAD_COLOR)
            target_faces = self.app.get(target_img)
            if not target_faces:
                return False, None, FailureReason.FACE_DETECTION
            
            result = self.swapper.get(target_img, target_faces[0], source_faces[0], paste_back=True)
            return True, result, None
            
        except Exception as e:
            print(f"\nError: {e}")
            return False, None, FailureReason.UNKNOWN
    
    def _extract_image(self, response):
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return part.inline_data.data
        return None


def complete_vto_workflow(photo_path, body_type, height, gender_presentation, garment_paths, output_dir="vto_complete_test"):
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("🎯 COMPLETE INTEGRATED VTO SYSTEM")
    print("=" * 80)
    print(f"Model: {os.path.basename(photo_path)}")
    print(f"Profile: {body_type} + {height}")
    print(f"Garments: {len(garment_paths)} items")
    print("=" * 80)
    
    print("\n👤 Step 1: Creating User Profile")
    print("-" * 80)
    profile = UserProfile(photo_path, body_type, height, gender_presentation)
    print(f"✅ Profile: {profile.get_display_name()}")
    
    analyzer = GarmentAnalyzer()
    outfit = analyzer.analyze_outfit(garment_paths)
    
    vto_system = VTOSystem()
    result = vto_system.generate_vto_with_retry(profile, garment_paths, outfit['outfit_description'], max_attempts=3)
    
    print("\n💾 Step 4: Saving Results")
    print("-" * 80)
    
    if result.success:
        output_path = f"{output_dir}/vto_result.png"
        cv2.imwrite(output_path, result.image)
        print(f"✅ Success! Saved to: {output_path}")
        print(f"   Attempts: {result.attempts}")
        return True
    else:
        print(f"❌ Failed after {result.attempts} attempts")
        print(f"   Reason: {result.failure_reason.value}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("\nUsage: python vto_complete_system.py <photo> <body_type> <height> <gender> <garment1> [garment2] ...")
        print("\nBody Types: slim, average, curvy, plus")
        print("Heights: petite, average, tall, none")
        print("Gender: menswear, womenswear\n")
        sys.exit(1)
    
    complete_vto_workflow(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
