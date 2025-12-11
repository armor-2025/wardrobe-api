"""
Avatar Generation Endpoint
Generates activewear avatar from user's signup photo using Gemini 2.5 Flash
All outputs converted to PNG for consistency
"""

import os
import json
import base64
import io
from PIL import Image
import firebase_admin
from firebase_admin import credentials, storage
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai.types import Part
from database import SessionLocal, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/avatar", tags=["Avatar"])

def init_firebase():
    if not firebase_admin._apps:
        firebase_creds = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if firebase_creds:
            creds_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'your-bucket.appspot.com')
            })

class AvatarRequest(BaseModel):
    photo_base64: str
    body_type: Optional[str] = "average"

def get_gemini_client():
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    return genai.Client()

def base64_to_bytes(base64_string: str) -> bytes:
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    return base64.b64decode(base64_string)

def convert_to_png(image_bytes: bytes) -> bytes:
    """Convert any image format to PNG"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()

def upload_to_firebase(image_bytes: bytes, path: str) -> str:
    """Upload PNG image to Firebase Storage and return public URL"""
    init_firebase()
    png_bytes = convert_to_png(image_bytes)
    bucket = storage.bucket()
    blob = bucket.blob(path)
    blob.upload_from_string(png_bytes, content_type='image/png')
    blob.make_public()
    return blob.public_url

async def generate_activewear_avatar(photo_base64: str, body_type: str) -> bytes:
    """Generate activewear version using Gemini 2.5 Flash"""
    
    client = get_gemini_client()
    photo_bytes = base64_to_bytes(photo_base64)
    mime_type = "image/png" if photo_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    photo_part = Part.from_bytes(data=photo_bytes, mime_type=mime_type)
    
    body_instruction = ""
    if body_type == "plus":
        body_instruction = "CRITICAL: Preserve their exact plus-size body shape - do NOT slim them down."
    elif body_type == "curvy":
        body_instruction = "CRITICAL: Preserve their exact curvy proportions."
    
    prompt = f"""Transform this person into a fashion-ready avatar photo.

REQUIREMENTS:
1. KEEP their EXACT face - same features, expression, skin tone
2. KEEP their EXACT body shape and proportions. {body_instruction}
3. DRESS them in neutral activewear: fitted grey tank top and black leggings
4. POSE: Standing naturally, arms relaxed at sides, facing camera
5. FULL BODY: Show complete figure from head to toe
6. BACKGROUND: Clean, neutral light grey studio background
7. LIGHTING: Professional, even studio lighting
8. QUALITY: High-resolution fashion photography style

Generate ONE image of this person ready to be styled with different outfits."""

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=[prompt, photo_part],
        config={"response_modalities": ["image", "text"]}
    )
    
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                return convert_to_png(part.inline_data.data)
    
    raise Exception("No image generated")


@router.post("/generate")
async def generate_avatar(request: AvatarRequest, authorization: str = Header(None)):
    """Generate activewear avatar from user's photo. All images saved as PNG."""
    try:
        # Get user from token
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        token = authorization.replace("Bearer ", "")
        
        db = SessionLocal()
        try:
            # Decode token to get user (simplified - adapt to your auth)
            from auth_service import decode_token
            user_data = decode_token(token)
            user = db.query(User).filter(User.id == user_data["user_id"]).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_id = user.id
            
            # 1. Upload original photo as PNG
            original_bytes = base64_to_bytes(request.photo_base64)
            original_path = f"users/{user_id}/original_photo.png"
            original_url = upload_to_firebase(original_bytes, original_path)
            logger.info(f"Uploaded original photo for user {user_id}")
            
            # 2. Generate activewear avatar (returns PNG)
            avatar_bytes = await generate_activewear_avatar(
                request.photo_base64, 
                request.body_type
            )
            
            # 3. Upload avatar as PNG
            avatar_path = f"users/{user_id}/avatar.png"
            avatar_url = upload_to_firebase(avatar_bytes, avatar_path)
            logger.info(f"Uploaded avatar for user {user_id}")
            
            # 4. Update user profile
            user.original_photo_url = original_url
            user.avatar_url = avatar_url
            user.body_type = request.body_type
            db.commit()
            
            return {
                "success": True,
                "original_photo_url": original_url,
                "avatar_url": avatar_url
            }
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar generation failed: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/me")
async def get_my_avatar(authorization: str = Header(None)):
    """Get current user's avatar info"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    token = authorization.replace("Bearer ", "")
    
    db = SessionLocal()
    try:
        from auth_service import decode_token
        user_data = decode_token(token)
        user = db.query(User).filter(User.id == user_data["user_id"]).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "original_photo_url": user.original_photo_url,
            "avatar_url": user.avatar_url,
            "body_type": user.body_type
        }
    finally:
        db.close()
