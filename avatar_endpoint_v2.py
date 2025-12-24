"""
Avatar Generation Endpoint V2
=============================
Dual image input (full body + face closeup) + InsightFace face swap
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Header, Depends
from pydantic import BaseModel
from typing import Optional
import base64
import os
import json
import io
import cv2
import numpy as np
from google import genai
from google.genai.types import Part
from PIL import Image, ImageOps
from rembg import remove
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import firebase_admin
from firebase_admin import credentials, storage
from sqlalchemy.orm import Session
from database import get_db, User
from datetime import datetime
import uuid

router = APIRouter(prefix="/avatar", tags=["Avatar"])

# Initialize Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# Handle Render deployment credentials
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = "/tmp/gcp_credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

client = genai.Client()

# Initialize InsightFace (lazy loading)
_face_app = None
_swapper = None

def get_face_swap():
    global _face_app, _swapper
    if _face_app is None:
        print("Loading InsightFace...")
        _face_app = FaceAnalysis(name='buffalo_l')
        _face_app.prepare(ctx_id=-1, det_size=(640, 640))
        _swapper = get_model('inswapper_128.onnx', download=True, download_zip=True)
        print("✅ InsightFace ready")
    return _face_app, _swapper

# Body type prompts
BODY_PROMPTS = {
    "slim": "slim/athletic build",
    "average": "average build",
    "curvy": "curvy build with wider hips",
    "plus": "plus-size build"
}

HEIGHT_PROMPTS = {
    "petite": "petite height (under 5'4\")",
    "average": "average height (5'4\"-5'7\")",
    "tall": "tall height (over 5'7\")"
}


def init_firebase():
    """Initialize Firebase if not already done"""
    if not firebase_admin._apps:
        firebase_creds = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if firebase_creds:
            creds_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(creds_dict)
        else:
            cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'your-online-wardrobe-jm85cl.firebasestorage.app')
        })


def upload_to_firebase(image_bytes: bytes, path: str, content_type: str = 'image/png') -> str:
    """Upload image to Firebase Storage and return public URL"""
    init_firebase()
    bucket = storage.bucket()
    blob = bucket.blob(path)
    blob.upload_from_string(image_bytes, content_type=content_type)
    blob.make_public()
    return blob.public_url


def fix_exif_rotation(image_bytes: bytes) -> bytes:
    """Fix EXIF rotation from phone photos"""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    return buffer.getvalue()


def pil_to_cv2(pil_img):
    """Convert PIL to CV2"""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_img):
    """Convert CV2 to PIL"""
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))


class AvatarResponse(BaseModel):
    success: bool
    original_photo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    cost_estimate: float = 0.04


@router.post("/generate", response_model=AvatarResponse)
async def generate_avatar(
    photo: UploadFile = File(..., description="Full body photo"),
    face_photo: UploadFile = File(..., description="Face closeup photo (required)"),
    body_type: str = Form(default="average"),
    height: str = Form(default="average"),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Generate activewear avatar from uploaded photos.
    
    - photo: Full body photo (required)
    - face_photo: Face closeup (optional, improves likeness significantly)
    - body_type: slim, average, curvy, plus
    - height: petite, average, tall
    """
    
    try:
        # Auth check
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        from app import get_current_user
        token = authorization.split(' ')[1]
        user = get_current_user(db, token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = str(user.id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Read and fix EXIF rotation
        body_bytes = await photo.read()
        body_bytes = fix_exif_rotation(body_bytes)
        
        # Upload original photo
        original_path = f"users/{user_id}/original_photo_{timestamp}.jpg"
        original_url = upload_to_firebase(body_bytes, original_path, content_type='image/jpeg')
        
        # Prepare body image for Gemini
        body_part = Part.from_bytes(data=body_bytes, mime_type='image/jpeg')
        
        # Check if face closeup provided
        has_face_closeup = True  # Always required
        face_bytes = None
        face_part = None
        
        if has_face_closeup:
            face_bytes = await face_photo.read()
            face_bytes = fix_exif_rotation(face_bytes)
            face_part = Part.from_bytes(data=face_bytes, mime_type='image/jpeg')
            print(f"📸 Using dual image input (body + face closeup)")
        else:
            print(f"📸 Using single image input (body only)")
        
        # Get prompts
        body_prompt = BODY_PROMPTS.get(body_type, BODY_PROMPTS["average"])
        height_prompt = HEIGHT_PROMPTS.get(height, HEIGHT_PROMPTS["average"])
        
        # Build prompt based on input type
        if has_face_closeup:
            prompt = f"""### IDENTITY REFERENCE (MANDATORY)
- **Image 1 (Full Body):** Use as the source for body proportions, pose, and skin tone.
- **Image 2 (Face Close-up):** Use as the PRIMARY source for all facial features, eye color, skin texture, and fine details.
- **Instruction:** Synthesize the high-detail facial features from Image 2 onto the head of the subject.

TASK: Analyze this person AND generate a virtual try-on base image.

STEP 1 - ANALYZE:
Describe this person's physical appearance for virtual try-ons.
Use Image 2 (face close-up) for facial details.
Include: skin tone, distinctive features (freckles, moles), hair color/length/texture, face shape.
Format as ONE detailed sentence.

STEP 2 - GENERATE:
Generate a professional fashion photo of this EXACT person.
The face MUST match Image 2 exactly.

BODY SPECIFICATIONS:
{body_prompt}, {height_prompt}

OUTFIT:
- Fitted sports bra / crop top in grey-mauve color (muted purple-grey/taupe, hex #8B8589)
- High-waisted leggings (ankle length) in matching grey-mauve color
- BARE FEET (no shoes)

BACKGROUND:
- Light grey studio backdrop
- Professional fashion photography style

POSE:
- Simple, natural front-facing standing pose
- Arms relaxed at sides

COMPOSITION:
- Subject must fill 95% of frame height
- Facial resolution must match the clarity of Image 2

STRICT EXCLUSIONS - DO NOT ADD:
- NO jewelry (no necklaces, earrings, bracelets, rings, watches)
- NO hair accessories
- NO logos, NO branding, NO text on clothing
- NOTHING except the activewear described

Full body visible from head to bare feet.
Same face as Image 2, same hair from the photos.

OUTPUT:
1. Write "DESCRIPTION:" followed by appearance + body type + height details
2. Generate the image

Generate now."""
            contents = [prompt, body_part, face_part]
        else:
            # Original single-image prompt
            prompt = f"""TASK: Analyze this person AND generate a virtual try-on base image.

STEP 1 - ANALYZE:
Describe this person's physical appearance for virtual try-ons.
Include: skin tone, distinctive features (freckles, moles), hair color/length/texture, face shape.
Format as ONE detailed sentence.

STEP 2 - GENERATE:
Generate a professional fashion photo of this EXACT person.

BODY SPECIFICATIONS:
{body_prompt}, {height_prompt}

OUTFIT:
- Fitted sports bra / crop top in grey-mauve color (muted purple-grey/taupe, hex #8B8589)
- High-waisted leggings (ankle length) in matching grey-mauve color
- BARE FEET (no shoes)

BACKGROUND:
- Light grey studio backdrop
- Professional fashion photography style

POSE:
- Simple, natural front-facing standing pose
- Arms relaxed at sides

STRICT EXCLUSIONS - DO NOT ADD:
- NO jewelry (no necklaces, earrings, bracelets, rings, watches)
- NO hair accessories
- NO logos, NO branding, NO text on clothing
- NOTHING except the activewear described

Full body visible from head to bare feet.
Same face, same hair from the photo.

OUTPUT:
1. Write "DESCRIPTION:" followed by appearance + body type + height details
2. Generate the image

Generate now."""
            contents = [prompt, body_part]
        
        # Generate with Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents,
            config={"response_modalities": ["image", "text"]}
        )
        
        description = None
        image_data = None
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                text = part.text.strip()
                if 'DESCRIPTION:' in text:
                    description = text.split('DESCRIPTION:')[1].strip()
                else:
                    description = text
            
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
        
        if not image_data:
            return AvatarResponse(
                success=False,
                error="No image generated by Gemini"
            )
        
        # InsightFace swap if face closeup provided
        if has_face_closeup and face_bytes:
            try:
                print("🔄 Applying InsightFace swap...")
                face_app, swapper = get_face_swap()
                
                # Load images as CV2
                face_pil = Image.open(io.BytesIO(face_bytes))
                face_cv2 = pil_to_cv2(face_pil)
                
                gen_pil = Image.open(io.BytesIO(image_data))
                gen_cv2 = pil_to_cv2(gen_pil)
                
                # Detect faces
                source_faces = face_app.get(face_cv2)
                target_faces = face_app.get(gen_cv2)
                
                if source_faces and target_faces:
                    result_cv2 = swapper.get(
                        gen_cv2,
                        target_faces[0],
                        source_faces[0],
                        paste_back=True
                    )
                    
                    # Convert back to bytes
                    result_pil = cv2_to_pil(result_cv2)
                    buffer = io.BytesIO()
                    result_pil.save(buffer, format='PNG')
                    image_data = buffer.getvalue()
                    print("✅ InsightFace swap complete")
                else:
                    print(f"⚠️ Face swap skipped: source={len(source_faces)}, target={len(target_faces)}")
            except Exception as e:
                print(f"⚠️ InsightFace error: {e}")
        
        # Remove background with alpha matting
        avatar_nobg = remove(
            image_data,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10
        )
        
        # Crop to content bounds
        img = Image.open(io.BytesIO(avatar_nobg))
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # Add vertical padding (3% top and bottom)
        padding_v = int(img.height * 0.03)
        new_height = img.height + (padding_v * 2)
        padded = Image.new('RGBA', (img.width, new_height), (0, 0, 0, 0))
        padded.paste(img, (0, padding_v))
        img = padded
        
        # Save final PNG
        final_buffer = io.BytesIO()
        img.save(final_buffer, format='PNG')
        avatar_png = final_buffer.getvalue()
        
        # Upload to Firebase
        avatar_path = f"users/{user_id}/avatar_{timestamp}.png"
        avatar_url = upload_to_firebase(avatar_png, avatar_path, content_type='image/png')
        
        # Save to user profile
        user.avatar_url = avatar_url
        user.original_photo_url = original_url
        db.commit()
        
        return AvatarResponse(
            success=True,
            original_photo_url=original_url,
            avatar_url=avatar_url,
            description=description,
            cost_estimate=0.04
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Avatar generation error: {e}")
        import traceback
        traceback.print_exc()
        return AvatarResponse(
            success=False,
            error=str(e)
        )
