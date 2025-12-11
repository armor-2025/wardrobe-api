"""
Avatar Generation Endpoint
Uses Gemini 2.5 Flash for avatar generation (cheaper at $0.04/image)
Accepts multipart file upload (proper approach)
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from pydantic import BaseModel
from typing import Optional
import base64
import os
import json
import io
from google import genai
from google.genai.types import Part
from PIL import Image
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


def init_firebase():
    """Initialize Firebase if not already done"""
    if not firebase_admin._apps:
        # Check for credentials in environment
        firebase_creds = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if firebase_creds:
            creds_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(creds_dict)
        else:
            # Use default credentials (for local dev)
            cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'your-online-wardrobe-jm85cl.firebasestorage.app')
        })


def upload_to_firebase(image_bytes: bytes, path: str) -> str:
    """Upload image to Firebase Storage and return public URL"""
    init_firebase()
    bucket = storage.bucket()
    blob = bucket.blob(path)
    blob.upload_from_string(image_bytes, content_type='image/png')
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


class AvatarResponse(BaseModel):
    success: bool
    original_photo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    error: Optional[str] = None
    cost_estimate: float = 0.04


@router.post("/generate", response_model=AvatarResponse)
async def generate_avatar(photo: UploadFile = File(...)):
    """
    Generate activewear avatar from uploaded photo.
    Accepts multipart file upload.
    """
    
    try:
        # Read the uploaded file
        photo_bytes = await photo.read()
        
        # Convert to PNG for consistency
        png_bytes = convert_to_png(photo_bytes)
        
        # Generate unique user ID for this upload (in production, use actual user ID)
        user_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Upload original photo to Firebase
        original_path = f"users/{user_id}/original_photo_{timestamp}.png"
        original_url = upload_to_firebase(png_bytes, original_path)
        
        # Create Part for Gemini
        photo_part = Part.from_bytes(data=png_bytes, mime_type="image/png")
        
        # Generate activewear avatar using Gemini 2.5 Flash (cheaper)
        prompt = """Transform this person into a clean avatar photo for a fashion app.

REQUIREMENTS:
1. Keep the EXACT same face - same features, skin tone, expression
2. Keep the EXACT same body shape and proportions
3. Dress them in simple black activewear (fitted black t-shirt and black leggings)
4. Clean, neutral light grey studio background
5. Professional photography quality
6. Full body shot, head to toe
7. Simple, confident standing pose

Generate the avatar image."""

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=[prompt, photo_part],
            config={"response_modalities": ["image", "text"]}
        )
        
        # Extract generated image
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # Convert to PNG
                avatar_png = convert_to_png(part.inline_data.data)
                
                # Upload avatar to Firebase
                avatar_path = f"users/{user_id}/avatar_{timestamp}.png"
                avatar_url = upload_to_firebase(avatar_png, avatar_path)
                
                return AvatarResponse(
                    success=True,
                    original_photo_url=original_url,
                    avatar_url=avatar_url,
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


@router.post("/generate-base64", response_model=AvatarResponse)
async def generate_avatar_base64(photo_base64: str):
    """
    Alternative endpoint that accepts base64 (for testing/backwards compatibility)
    """
    try:
        photo_bytes = base64.b64decode(photo_base64)
        
        # Reuse the main logic
        png_bytes = convert_to_png(photo_bytes)
        user_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        original_path = f"users/{user_id}/original_photo_{timestamp}.png"
        original_url = upload_to_firebase(png_bytes, original_path)
        
        photo_part = Part.from_bytes(data=png_bytes, mime_type="image/png")
        
        prompt = """Transform this person into a clean avatar photo for a fashion app.

REQUIREMENTS:
1. Keep the EXACT same face - same features, skin tone, expression
2. Keep the EXACT same body shape and proportions
3. Dress them in simple black activewear (fitted black t-shirt and black leggings)
4. Clean, neutral light grey studio background
5. Professional photography quality
6. Full body shot, head to toe
7. Simple, confident standing pose

Generate the avatar image."""

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=[prompt, photo_part],
            config={"response_modalities": ["image", "text"]}
        )
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                avatar_png = convert_to_png(part.inline_data.data)
                avatar_path = f"users/{user_id}/avatar_{timestamp}.png"
                avatar_url = upload_to_firebase(avatar_png, avatar_path)
                
                return AvatarResponse(
                    success=True,
                    original_photo_url=original_url,
                    avatar_url=avatar_url,
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
        "model": "gemini-2.5-flash-preview-05-20",
        "cost_per_avatar": 0.04,
        "upload_type": "multipart/form-data"
    }
