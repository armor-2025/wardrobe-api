"""
Gemini 3 Pro Image Virtual Try-On Endpoint
Production-ready VTO using gemini-3-pro-image-preview
"""

import os
import json
import tempfile
import base64
import asyncio
from io import BytesIO
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from google import genai
from google.genai.types import Part
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_gcp_credentials():
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            json.loads(creds_json)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(creds_json)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
                logger.info(f"GCP credentials loaded from env var to {f.name}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

setup_gcp_credentials()

router = APIRouter(prefix="/vto", tags=["Virtual Try-On"])

def get_gemini_client():
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    return genai.Client()

class GarmentItem(BaseModel):
    image_base64: str
    category: str
    description: Optional[str] = None

class VTORequest(BaseModel):
    model_image_base64: str
    garments: List[GarmentItem]
    body_type: Optional[str] = "average"

class VTOResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None
    items_count: int = 0
    cost_estimate: float = 0.0

def base64_to_part(base64_string: str) -> Part:
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    image_data = base64.b64decode(base64_string)
    mime_type = "image/png" if image_data[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    return Part.from_bytes(data=image_data, mime_type=mime_type)

def image_to_base64(image_data: bytes) -> str:
    return base64.b64encode(image_data).decode('utf-8')

def build_vto_prompt(garments: List[GarmentItem], body_type: str = "average") -> str:
    garment_descriptions = []
    for i, garment in enumerate(garments, 1):
        desc = garment.description or garment.category
        garment_descriptions.append(f"{i}. {garment.category.upper()}: {desc}")
    garments_text = "\n".join(garment_descriptions)
    
    body_instruction = ""
    if body_type == "plus":
        body_instruction = "CRITICAL: The model has a plus-size body type. You MUST preserve their exact body shape and proportions - do NOT slim them down."
    elif body_type == "curvy":
        body_instruction = "CRITICAL: The model has a curvy body type. You MUST preserve their exact curves and proportions."
    elif body_type == "slim":
        body_instruction = "The model has a slim body type. Preserve their exact proportions."
    
    prompt = f"""Generate a photorealistic image of the person wearing ALL of these items:

{garments_text}

CRITICAL REQUIREMENTS:
1. FACE: Keep the EXACT same face - same features, expression, skin tone.
2. BODY: Keep the EXACT same body shape and proportions. {body_instruction}
3. ALL ITEMS: Every single garment listed above MUST be visible in the final image.
4. LAYERING: If there's a coat/jacket, show it worn OPEN over inner layers.
5. FULL BODY: Show complete full-body shot from head to toe, including feet with shoes.
6. BACKGROUND: Clean, neutral grey studio background.
7. QUALITY: Professional fashion photography quality.

The person in Image 1 is your model. Images 2-{len(garments) + 1} are the garments.
Generate ONE final image showing the model wearing ALL items together."""
    return prompt

async def generate_vto(model_image_base64: str, garments: List[GarmentItem], body_type: str = "average") -> dict:
    try:
        client = get_gemini_client()
        prompt = build_vto_prompt(garments, body_type)
        content = [prompt]
        content.append(base64_to_part(model_image_base64))
        for garment in garments:
            content.append(base64_to_part(garment.image_base64))
        
        logger.info(f"Generating VTO with {len(garments)} items using Gemini 3 Pro Image")
        
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=content,
            config={"response_modalities": ["image", "text"], "temperature": 0.4}
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    return {"success": True, "image_base64": image_to_base64(image_data), "error": None, "items_count": len(garments), "cost_estimate": 0.13}
        
        return {"success": False, "image_base64": None, "error": "No image generated", "items_count": len(garments), "cost_estimate": 0.13}
    except Exception as e:
        logger.error(f"VTO generation failed: {str(e)}")
        return {"success": False, "image_base64": None, "error": str(e), "items_count": len(garments), "cost_estimate": 0.0}

@router.post("/generate", response_model=VTOResponse)
async def vto_generate(request: VTORequest):
    if not request.garments:
        raise HTTPException(status_code=400, detail="At least one garment required")
    if len(request.garments) > 12:
        raise HTTPException(status_code=400, detail="Maximum 12 items supported")
    result = await generate_vto(request.model_image_base64, request.garments, request.body_type)
    return VTOResponse(**result)

@router.get("/health")
async def vto_health():
    try:
        client = get_gemini_client()
        return {"status": "healthy", "model": "gemini-3-pro-image-preview", "location": "global", "max_items": 12, "cost_per_generation": "$0.13"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    app = FastAPI(title="Gemini 3 Pro VTO API")
    app.include_router(router)
    uvicorn.run(app, host="0.0.0.0", port=8000)
