"""
Avatar Generation Endpoint - V2 with Fly.io FaceSwap Worker
Uses Gemini for generation, then calls Fly worker for face swap
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
import base64
import os
import io
import json
import httpx
from PIL import Image, ImageOps
from rembg import remove
from google import genai
from google.genai.types import Part
import firebase_admin
from firebase_admin import credentials, storage
from sqlalchemy.orm import Session
from database import get_db, User
from app import get_current_user
from datetime import datetime

router = APIRouter(prefix="/avatar", tags=["Avatar"])

# Fly.io FaceSwap Worker URL
FACESWAP_WORKER_URL = "https://yow-faceswap.fly.dev"

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

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


def fix_image_rotation(image_bytes: bytes) -> bytes:
    """Fix EXIF rotation issues from phone photos"""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    return buffer.getvalue()


async def call_faceswap_worker(source_b64: str, target_b64: str) -> str:
    """Call Fly.io worker for face swap"""
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(
            f"{FACESWAP_WORKER_URL}/swap",
            json={
                "source_image_base64": source_b64,
                "target_image_base64": target_b64
            }
        )
        result = response.json()
        print(f"🔄 Fly worker response: success={result.get('success')}, error={result.get('error')}")
        if result.get("success"):
            return result.get("result_image_base64")
        else:
            raise Exception(result.get("error", "Face swap failed"))


@router.post("/generate")
async def generate_avatar(
    photo: UploadFile = File(..., description="Full body photo"),
    face_photo: UploadFile = File(..., description="Face closeup photo"),
    body_type: str = Form(default="average"),
    height: str = Form(default="average"),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:
        # Auth check
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        user = get_current_user(db, token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = str(user.id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Read and fix rotation on both photos
        body_bytes = await photo.read()
        print(f"📷 Body photo size: {len(body_bytes)} bytes")
        body_bytes = fix_image_rotation(body_bytes)
        
        face_bytes = await face_photo.read()
        print(f"📷 Face photo size: {len(face_bytes)} bytes")
        face_bytes = fix_image_rotation(face_bytes)
        
        body_b64 = base64.b64encode(body_bytes).decode('utf-8')
        face_b64 = base64.b64encode(face_bytes).decode('utf-8')
        
        body_part = Part.from_bytes(data=body_bytes, mime_type="image/jpeg")
        face_part = Part.from_bytes(data=face_bytes, mime_type="image/jpeg")
        
        # Build prompt with identity anchoring
        prompt = f"""### IDENTITY REFERENCE (MANDATORY)
- **Image 1 (Full Body):** Use as the source for body proportions, pose, and skin tone.
- **Image 2 (Face Close-up):** Use as the PRIMARY source for all facial features, eye color, skin texture, and fine details.
- **Instruction:** Synthesize the high-detail facial features from Image 2 onto the head of the subject.

TASK: Generate a virtual try-on base image.

BODY SPECIFICATIONS:
{body_type} build, {height} height

OUTFIT:
- Fitted sports bra / crop top in grey-mauve color (hex #8B8589)
- High-waisted leggings (ankle length) in matching grey-mauve color
- BARE FEET (no shoes)

BACKGROUND:
- Light grey studio backdrop (#fafafa)
- Professional fashion photography style

POSE:
- Simple, natural front-facing standing pose
- Arms relaxed at sides

COMPOSITION:
- Full body from head to bare feet
- Subject fills 95% of vertical frame
- Portrait orientation (9:16)

STRICT EXCLUSIONS:
- NO jewelry, NO hair accessories, NO logos, NO patterns on clothing

Generate now."""

        # Step 1: Generate with Gemini
        print("📸 Generating avatar with Gemini...")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, body_part, face_part],
            config={"response_modalities": ["image", "text"]}
        )
        
        generated_bytes = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                generated_bytes = part.inline_data.data
                break
        
        if not generated_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate image")
        
        print(f"✅ Gemini generated {len(generated_bytes)} bytes")
        
        # DEBUG: Save Gemini output
        gemini_url = upload_to_firebase(generated_bytes, f"users/{user_id}/debug_1_gemini_{timestamp}.png", 'image/png')
        print(f"🔍 DEBUG Gemini output: {gemini_url}")
        
        generated_b64 = base64.b64encode(generated_bytes).decode('utf-8')
        
        # Step 2: Face swap via Fly worker
        print("🔄 Swapping face via Fly worker...")
        try:
            swapped_b64 = await call_faceswap_worker(face_b64, generated_b64)
            final_bytes = base64.b64decode(swapped_b64)
            print(f"✅ Face swap returned {len(final_bytes)} bytes")
            
            # DEBUG: Save face swap output
            swap_url = upload_to_firebase(final_bytes, f"users/{user_id}/debug_2_faceswap_{timestamp}.png", 'image/png')
            print(f"🔍 DEBUG Face swap output: {swap_url}")
            
        except Exception as e:
            print(f"⚠️ Face swap failed: {e}, using Gemini output")
            final_bytes = generated_bytes
        
        # Step 3: Remove background
        print("🎨 Removing background...")
        avatar_nobg = remove(
            final_bytes,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10
        )
        print(f"✅ Background removed, {len(avatar_nobg)} bytes")
        
        # DEBUG: Save rembg output
        rembg_url = upload_to_firebase(avatar_nobg, f"users/{user_id}/debug_3_rembg_{timestamp}.png", 'image/png')
        print(f"🔍 DEBUG rembg output: {rembg_url}")
        
        # Step 4: Crop and pad
        img = Image.open(io.BytesIO(avatar_nobg))
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        padding_v = int(img.height * 0.03)
        new_height = img.height + (padding_v * 2)
        padded = Image.new('RGBA', (img.width, new_height), (0, 0, 0, 0))
        padded.paste(img, (0, padding_v))
        
        # Step 5: Save as PNG
        output = io.BytesIO()
        padded.save(output, format='PNG', optimize=True)
        final_png = output.getvalue()
        
        # Step 6: Upload to Firebase
        avatar_path = f"users/{user_id}/avatar_{timestamp}.png"
        avatar_url = upload_to_firebase(final_png, avatar_path, content_type='image/png')
        
        # Also save original photo
        original_path = f"users/{user_id}/original_photo_{timestamp}.jpg"
        original_url = upload_to_firebase(body_bytes, original_path, content_type='image/jpeg')
        
        # Save face photo too
        face_path = f"users/{user_id}/face_photo_{timestamp}.jpg"
        face_url = upload_to_firebase(face_bytes, face_path, content_type='image/jpeg')
        
        # Update user record
        user.avatar_url = avatar_url
        user.face_photo_url = face_url
        user.original_photo_url = original_url
        db.commit()
        
        print(f"✅ Avatar generated: {avatar_url}")
        
        return {
            "success": True,
            "avatar_url": avatar_url,
            "original_photo_url": original_url,
            "face_photo_url": face_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "healthy", "version": "v2-fly-worker-debug"}
