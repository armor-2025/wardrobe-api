"""
Gemini 3 Pro Image Virtual Try-On Endpoint
Model: gemini-3-pro-image-preview
Cost: ~$0.13/image (real-time), $0.065 (batch)
Max items: 12
NO temperature specified - defaults to 1.0 (Google recommended)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import base64
import os
import json
from google import genai
from google.genai.types import Part
from PIL import Image
import io

router = APIRouter(prefix="/vto", tags=["Virtual Try-On"])

# Initialize Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"  # MUST be global for image generation

# Handle Render deployment credentials
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = "/tmp/gcp_credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

client = genai.Client()


class GarmentItem(BaseModel):
    image_base64: str
    category: str  # top, bottom, dress, coat, shoes, bag, hat, scarf, sunglasses, jewelry
    description: str  # e.g., "navy blue sweater", "black leather boots"


class VTORequest(BaseModel):
    model_image_base64: str
    garments: List[GarmentItem]
    body_type: Optional[str] = "average"  # slim, average, curvy, plus


class VTOResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None
    items_count: int = 0
    cost_estimate: float = 0.13


def convert_to_png(image_bytes: bytes) -> bytes:
    """Convert any image format to PNG for consistency"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output.getvalue()


def base64_to_part(b64_string: str) -> Part:
    """Convert base64 string to Gemini Part"""
    image_bytes = base64.b64decode(b64_string)
    return Part.from_bytes(data=image_bytes, mime_type="image/png")


def build_prompt(garments: List[GarmentItem]) -> str:
    """Build the VTO prompt - EXACT format from working 9-item test"""
    
    # Build garment list with image references
    garment_lines = []
    for i, g in enumerate(garments, start=2):  # Start at 2 because image 1 is the model
        layer_hint = ""
        if g.category.lower() in ["coat", "jacket", "outerwear"]:
            layer_hint = " (OUTERMOST LAYER - worn open)"
        elif g.category.lower() in ["top", "sweater", "shirt", "blouse"]:
            layer_hint = " (TOP - visible under outerwear)"
        elif g.category.lower() in ["bottom", "trousers", "pants", "skirt"]:
            layer_hint = " (BOTTOM)"
        elif g.category.lower() in ["dress"]:
            layer_hint = " (DRESS - visible under outerwear)"
        elif g.category.lower() in ["shoes", "boots", "trainers", "sneakers"]:
            layer_hint = " (SHOES)"
        elif g.category.lower() in ["bag", "handbag", "purse"]:
            layer_hint = " (ACCESSORY - held or on shoulder)"
        elif g.category.lower() in ["scarf"]:
            layer_hint = " (ACCESSORY - around neck)"
        elif g.category.lower() in ["hat", "cap", "beanie"]:
            layer_hint = " (ACCESSORY - worn on head)"
        elif g.category.lower() in ["sunglasses", "glasses"]:
            layer_hint = " (ACCESSORY - worn on face)"
        elif g.category.lower() in ["jewelry", "earrings", "necklace", "bracelet"]:
            layer_hint = " (JEWELRY)"
        
        garment_lines.append(f"- Image {i}: {g.description}{layer_hint}")
    
    garments_text = "\n".join(garment_lines)
    num_items = len(garments)
    
    # Build critical requirements based on items present
    requirements = [
        "1. EXACT same face - preserve all facial features precisely",
        "2. EXACT same body shape and proportions",
        f"3. ALL {num_items} items must be clearly visible and accurate to source images",
    ]
    
    # Add layering requirement if coat/jacket present
    has_outerwear = any(g.category.lower() in ["coat", "jacket", "outerwear"] for g in garments)
    if has_outerwear:
        requirements.append("4. Coat/jacket worn OPEN so inner layers are visible underneath")
    
    # Add accessory-specific requirements
    has_scarf = any(g.category.lower() == "scarf" for g in garments)
    has_sunglasses = any(g.category.lower() in ["sunglasses", "glasses"] for g in garments)
    has_hat = any(g.category.lower() in ["hat", "cap", "beanie"] for g in garments)
    has_bag = any(g.category.lower() in ["bag", "handbag", "purse"] for g in garments)
    has_jewelry = any(g.category.lower() in ["jewelry", "earrings", "necklace", "bracelet"] for g in garments)
    
    req_num = 5 if has_outerwear else 4
    
    if has_scarf:
        requirements.append(f"{req_num}. Scarf worn around neck")
        req_num += 1
    if has_sunglasses:
        requirements.append(f"{req_num}. Sunglasses worn on face")
        req_num += 1
    if has_hat:
        requirements.append(f"{req_num}. Hat worn on head")
        req_num += 1
    if has_bag:
        requirements.append(f"{req_num}. Bag visible and accurate to source")
        req_num += 1
    if has_jewelry:
        requirements.append(f"{req_num}. Jewelry visible on ears/neck/wrist")
        req_num += 1
    
    requirements.append(f"{req_num}. Full body shot showing feet with shoes")
    req_num += 1
    requirements.append(f"{req_num}. Neutral grey studio background")
    
    requirements_text = "\n".join(requirements)
    
    prompt = f"""Virtual try-on task: Dress the person in image 1 wearing ALL of these:
{garments_text}

CRITICAL REQUIREMENTS:
{requirements_text}

Generate the virtual try-on result."""
    
    return prompt


@router.post("/generate", response_model=VTOResponse)
async def generate_vto(request: VTORequest):
    """Generate virtual try-on image using Gemini 3 Pro Image"""
    
    try:
        if len(request.garments) > 12:
            raise HTTPException(status_code=400, detail="Maximum 12 garments allowed")
        
        if len(request.garments) == 0:
            raise HTTPException(status_code=400, detail="At least 1 garment required")
        
        # Prepare model image
        model_part = base64_to_part(request.model_image_base64)
        
        # Prepare garment images
        garment_parts = [base64_to_part(g.image_base64) for g in request.garments]
        
        # Build prompt
        prompt = build_prompt(request.garments)
        
        # Build contents: prompt, model image, then garments
        contents = [prompt, model_part] + garment_parts
        
        # Generate - NO temperature specified (defaults to 1.0 as Google recommends)
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config={"response_modalities": ["image", "text"]}
        )
        
        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # Convert to PNG for consistency
                png_bytes = convert_to_png(part.inline_data.data)
                result_base64 = base64.b64encode(png_bytes).decode('utf-8')
                
                return VTOResponse(
                    success=True,
                    image_base64=result_base64,
                    items_count=len(request.garments),
                    cost_estimate=0.13
                )
        
        return VTOResponse(
            success=False,
            error="No image generated",
            items_count=len(request.garments)
        )
        
    except Exception as e:
        return VTOResponse(
            success=False,
            error=str(e),
            items_count=len(request.garments) if request.garments else 0
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "gemini-3-pro-image-preview",
        "location": "global",
        "max_items": 12,
        "cost_per_image": 0.13,
        "temperature": "default (1.0)"
    }
