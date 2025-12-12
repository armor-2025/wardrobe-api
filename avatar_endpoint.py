"""
Avatar Generation Endpoint
Uses the EXACT prompt from vto_system_final.py
Accepts multipart file upload with body_type and height parameters
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional
import base64
import os
import json
import io
from google import genai
from google.genai.types import Part
from PIL import Image
from rembg import remove
import firebase_admin
from firebase_admin import credentials, storage
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

# Body type prompts (from vto_system_final.py)
BODY_PROMPTS = {
    "slim": "slim/athletic build",
    "average": "average build",
    "curvy": "curvy build with wider hips",
    "plus": "plus-size build"
}

# Height prompts (from vto_system_final.py)
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


def convert_to_png(image_bytes: bytes) -> bytes:
    """Convert any image format to PNG for consistency"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output.getvalue()


def detect_image_format(image_bytes: bytes) -> tuple:
    """Detect image format and return (extension, mime_type)"""
    img = Image.open(io.BytesIO(image_bytes))
    fmt = img.format.lower() if img.format else 'jpeg'
    if fmt == 'jpg':
        fmt = 'jpeg'
    mime_type = f"image/{fmt}"
    ext = 'jpg' if fmt == 'jpeg' else fmt
    return ext, mime_type


class AvatarResponse(BaseModel):
    success: bool
    original_photo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    cost_estimate: float = 0.04


@router.post("/generate", response_model=AvatarResponse)
async def generate_avatar(
    photo: UploadFile = File(...),
    body_type: str = Form(default="average"),
    height: str = Form(default="average")
):
    """
    Generate activewear avatar from uploaded photo.
    EXACT prompt from vto_system_final.py
    """
    
    try:
        # Read the uploaded file
        photo_bytes = await photo.read()
        
        # Detect original format (keep original as-is)
        ext, mime_type = detect_image_format(photo_bytes)
        
        # Generate unique user ID
        user_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Upload original photo AS-IS (no conversion)
        original_path = f"users/{user_id}/original_photo_{timestamp}.{ext}"
        original_url = upload_to_firebase(photo_bytes, original_path, content_type=mime_type)
        
        # Create Part for Gemini (original format)
        photo_part = Part.from_bytes(data=photo_bytes, mime_type=mime_type)
        
        # Get body and height prompts
        body_prompt = BODY_PROMPTS.get(body_type, BODY_PROMPTS["average"])
        height_prompt = HEIGHT_PROMPTS.get(height, HEIGHT_PROMPTS["average"])
        
        # EXACT PROMPT FROM vto_system_final.py
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
- NOTHING except the activewear described

Full body visible from head to bare feet.
Same face, same hair from the photo.

OUTPUT:
1. Write "DESCRIPTION:" followed by appearance + body type + height details
2. Generate the image

Generate now."""

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, photo_part],
            config={"response_modalities": ["image", "text"]}
        )
        
        description = None
        image_data = None
        
        # Extract description and image
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                text = part.text.strip()
                if 'DESCRIPTION:' in text:
                    description = text.split('DESCRIPTION:')[1].strip()
                else:
                    description = text
            
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
        
        if image_data:
            # Convert generated avatar to PNG
            # Remove background for transparent PNG
            avatar_nobg = remove(image_data)
            
            # Clean grey edge artifact from rembg
            img = Image.open(io.BytesIO(avatar_nobg))
            if img.mode == 'RGBA':
                r, g, b, a = img.split()
                # Make alpha more binary (remove semi-transparent grey edges)
                a = a.point(lambda x: 0 if x < 240 else 255)
                img = Image.merge('RGBA', (r, g, b, a))
            
            # Convert to PNG bytes
            output = io.BytesIO()
            img.save(output, format='PNG', optimize=True)
            output.seek(0)
            avatar_png = output.getvalue()
            
            # Upload avatar as PNG
            avatar_path = f"users/{user_id}/avatar_{timestamp}.png"
            avatar_url = upload_to_firebase(avatar_png, avatar_path, content_type='image/png')
            
            return AvatarResponse(
                success=True,
                original_photo_url=original_url,
                avatar_url=avatar_url,
                description=description,
                cost_estimate=0.04
            )
        
        return AvatarResponse(
            success=False,
            error="No avatar image generated"
        )
        
    except Exception as e:
        return AvatarResponse(
            success=False,
            error=str(e)
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "gemini-2.5-flash-image",
        "cost_per_avatar": 0.04,
        "upload_type": "multipart/form-data",
        "params": ["photo", "body_type", "height"]
    }
