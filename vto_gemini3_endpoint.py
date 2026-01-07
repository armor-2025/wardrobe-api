"""
Gemini 3 Pro Image Virtual Try-On Endpoint - V2 IMPROVED
Model: gemini-3-pro-image-preview
With styling notes, better prompts, fafafa background
Now with optional face closeup for better identity preservation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import base64
import os
from google import genai
from google.genai.types import Part
from PIL import Image
import io

router = APIRouter(prefix="/vto", tags=["Virtual Try-On"])

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = "/tmp/gcp_credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

client = genai.Client()


class GarmentItem(BaseModel):
    image_base64: str
    category: str
    description: str


class VTORequest(BaseModel):
    model_image_base64: str
    face_image_base64: Optional[str] = None  # NEW: Optional face closeup for better identity
    garments: List[GarmentItem]
    body_type: Optional[str] = "average"
    styling_notes: Optional[str] = None


class VTOResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None
    items_count: int = 0
    cost_estimate: float = 0.13


def convert_to_png(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output.getvalue()


def base64_to_part(b64_string: str) -> Part:
    image_bytes = base64.b64decode(b64_string)
    return Part.from_bytes(data=image_bytes, mime_type="image/png")


def categorize_garments(garments: List[GarmentItem], start_index: int = 2) -> dict:
    """Categorize garments with configurable start index for image numbering"""
    layers = {
        "base": [], "bottom": [], "dress": [], "outer": [], "footwear": [], "accessories": []
    }
    for i, g in enumerate(garments, start=start_index):
        cat = g.category.lower()
        item = {"index": i, "description": g.description, "category": g.category}
        if cat in ["top", "tops", "shirt", "blouse", "t-shirt", "tshirt", "sweater", "jumper", "hoodie", "bodysuit"]:
            layers["base"].append(item)
        elif cat in ["bottom", "bottoms", "trousers", "pants", "skirt", "shorts", "jeans"]:
            layers["bottom"].append(item)
        elif cat in ["dress", "jumpsuit", "romper"]:
            layers["dress"].append(item)
        elif cat in ["jacket", "coat", "outerwear", "blazer", "cardigan"]:
            layers["outer"].append(item)
        elif cat in ["shoes", "boots", "trainers", "sneakers", "loafers", "heels", "sandals", "footwear"]:
            layers["footwear"].append(item)
        else:
            layers["accessories"].append(item)
    return layers


def build_prompt(garments: List[GarmentItem], styling_notes: Optional[str] = None, has_face_closeup: bool = False) -> str:
    # Adjust start index based on whether face closeup is provided
    # With face closeup: Image 1 = body, Image 2 = face, Images 3+ = garments
    # Without face closeup: Image 1 = body, Images 2+ = garments
    garment_start_index = 3 if has_face_closeup else 2
    
    layers = categorize_garments(garments, start_index=garment_start_index)
    num_items = len(garments)
    garment_specs = []
    layer_num = 1
    
    # Calculate end index for garments
    garment_end_index = garment_start_index + num_items - 1
    
    # Check if there's outerwear but no top
    has_outerwear = len(layers["outer"]) > 0
    has_top = len(layers["base"]) > 0
    
    for item in layers["base"]:
        if styling_notes and "crop" in styling_notes.lower() and "top" in item["description"].lower():
            action = " - Crop hem to show midriff."
        else:
            action = " - Maintain exact design and fit."
        garment_specs.append(f"{layer_num}. **Base Layer:** [Image {item['index']}: {item['description']}]{action}")
        layer_num += 1
    
    for item in layers["dress"]:
        garment_specs.append(f"{layer_num}. **Full Body:** [Image {item['index']}: {item['description']}] - Action: Maintain exact length, silhouette, and sleeve length from source.")
        layer_num += 1
    
    for item in layers["bottom"]:
        garment_specs.append(f"{layer_num}. **Bottom Layer:** [Image {item['index']}: {item['description']}] - Action: Maintain exact length, silhouette (wide-leg/slim/straight), and texture from source.")
        layer_num += 1
    
    for item in layers["outer"]:
        if has_top:
            action = " - Action: Worn open over base layer, maintain exact sleeve length and silhouette from source."
        else:
            action = " - Action: Worn CLOSED/ZIPPED/BUTTONED (no top underneath), maintain exact sleeve length and silhouette from source."
        if styling_notes:
            styling_lower = styling_notes.lower()
            if "button" in styling_lower or "zip" in styling_lower or "closed" in styling_lower:
                action = " - Action: Worn fully BUTTONED/ZIPPED CLOSED (even if top underneath - top may be partially hidden), maintain exact sleeve length and silhouette from source."
            elif "roll" in styling_lower and "sleeve" in styling_lower:
                action = " - Action: Roll sleeves up to elbows, worn open over base layer."
            elif "drape" in styling_lower or "over the shoulders" in styling_lower:
                action = " - Action: Draped over shoulders, not worn with arms in sleeves."
        garment_specs.append(f"{layer_num}. **Outer Layer:** [Image {item['index']}: {item['description']}]{action}")
        layer_num += 1
    
    for item in layers["footwear"]:
        garment_specs.append(f"{layer_num}. **Footwear:** [Image {item['index']}: {item['description']}] - Action: Replace any existing shoes, show full shoe.")
        layer_num += 1
    
    if layers["accessories"]:
        acc_list = ", ".join([f"[Image {item['index']}: {item['description']}]" for item in layers["accessories"]])
        bag_action = ""
        if styling_notes and "bag" in styling_notes.lower() and "hand" in styling_notes.lower():
            bag_action = " Bag held in hand."
        garment_specs.append(f"{layer_num}. **Accessories:** {acc_list} - Action: Natural placement on body. Maintain EXACT shape, frame thickness, and style from source image. Do NOT add any accessories not provided in source images.{bag_action}")
    
    garment_section = "\n".join(garment_specs)
    
    styling_section = ""
    if styling_notes and styling_notes.strip():
        styling_section = f"""

### STYLING
Apply: "{styling_notes.strip()}" """
    
    # NEW: Identity anchoring section for face closeup
    identity_anchor = ""
    face_instruction = ""
    if has_face_closeup:
        identity_anchor = """<subject_identity>
Images 1 and 2 show THE SAME PERSON. Generate this exact person wearing the garments.
</subject_identity>

<identity_reference>
Image 1 (Face Close-up): Use strictly for facial features, skin texture, eye color, and expression. This is the IDENTITY ANCHOR.
</identity_reference>

<pose_reference>
Image 2 (Full Body): Same person as Image 1. Use for body shape, size, and proportions. The face in Image 1 shows more detail - use that for facial features.
</pose_reference>

<garment_instructions>
Images 3+: Render these garments with 100% texture fidelity. Do not simplify fabric patterns.
</garment_instructions>

**IDENTITY LOCK:** Face MUST match Image 1 exactly. Use standard editorial pose: standing straight, arms relaxed at sides. Body PROPORTIONS (not pose) from Image 2.

"""
        face_instruction = " The face MUST match Image 1 (face closeup) exactly."
    
    prompt = f"""{identity_anchor}### VISUAL AUDIT (MANDATORY FIRST STEP)
Before generating, analyze each garment image:
1. Identify the specific fabric texture, pattern, and color of each garment in Images {garment_start_index}-{garment_end_index}.
2. Note any logos, buttons, zippers, or unique details that must be preserved.
3. Plan how each garment layer will be rendered with 100% texture fidelity.
Only after completing this audit, proceed to generation.

### SYSTEM TASK
Perform a high-fidelity virtual try-on. Use Image 1 as the immutable identity reference. Synthesize the garments from Images {garment_start_index}-{garment_end_index} onto the subject in Image 1.

### IDENTITY PRESERVATION (CRITICAL)
- **Subject:** Maintain the EXACT face, skin tone, hair texture, hair color, and body proportions of the person in Image 1.
- **Face:** Keep EXACT original face with NO makeup, filters, or skin smoothing added.{face_instruction}
- **Expression:** Match the EXACT expression from the face reference image. If source shows slight smile with few teeth, keep slight smile with few teeth. NO exaggerated smiles or full teeth grins unless shown in source.
- **Anatomy Check:** Ensure exactly TWO hands and TWO feet. No limb duplication or extra appendages.
- **Pose:** Natural standing pose, full body visible from head to toe.

### GARMENT SPECIFICATIONS & LAYERING
Analyze the provided garment images carefully. Apply them in the following order (from closest to body outward):

{garment_section}

### TEXTURE & FIDELITY CONSTRAINTS (CRITICAL)
- **Texture Integrity:** Transfer colors, patterns, and materials EXACTLY as shown in source images.
- **NO Hallucinations:** Do NOT add pinstripes, logos, patterns, embroidery, or any textures not visible in the source garment images.
- **Color Accuracy:** Match exact color values from source garments.
- **Sleeve Preservation:** Preserve EXACT sleeve lengths from source images. If source shows sleeveless/short sleeve, do NOT add or extend sleeves.
- **Length Preservation:** Preserve EXACT garment lengths from source images. Trousers: maintain exact length. Tops: maintain exact length. Dresses: maintain exact length.
- **Silhouette Preservation:** Maintain EXACT fit and silhouette - if oversized keep oversized, if fitted keep fitted, if wide-leg keep wide-leg.
{styling_section}

### COMPOSITION (MANDATORY)
- Single image. Portrait 9:16 aspect ratio.
- Subject fills 95% vertical frame. Head near top edge, shoes near bottom edge.
- 50mm lens, eye-level. No wide-angle distortion.

### OUTPUT REQUIREMENTS
- Background: Pure off-white studio (#fafafa) with professional fashion editorial lighting
- Sharp focus on garment textures (leather grain, fabric weave, stitching)
- All {num_items} garments clearly visible and accurate to source images
- Photorealistic, high-fashion editorial quality result

### EXECUTION
Generate the final composite image showing the subject from Image 1 fully dressed in the specified items."""

    return prompt


@router.post("/generate", response_model=VTOResponse)
async def generate_vto(request: VTORequest):
    try:
        if len(request.garments) > 12:
            raise HTTPException(status_code=400, detail="Maximum 12 garments allowed")
        if len(request.garments) == 0:
            raise HTTPException(status_code=400, detail="At least 1 garment required")
        
        model_part = base64_to_part(request.model_image_base64)
        garment_parts = [base64_to_part(g.image_base64) for g in request.garments]
        
        # Check if face closeup provided
        has_face_closeup = request.face_image_base64 is not None and len(request.face_image_base64) > 0
        face_part = None
        if has_face_closeup:
            face_part = base64_to_part(request.face_image_base64)
            print("📸 Using face closeup for enhanced identity preservation")
        
        prompt = build_prompt(request.garments, request.styling_notes, has_face_closeup)
        
        print("=" * 60)
        print("VTO PROMPT (V2 IMPROVED):")
        print("=" * 60)
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        print("=" * 60)
        
        # Build contents in correct order
        if has_face_closeup:
            contents = [prompt, face_part, model_part] + garment_parts
        else:
            contents = [prompt, model_part] + garment_parts
        
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config={"response_modalities": ["image", "text"]}
        )
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                png_bytes = convert_to_png(part.inline_data.data)
                result_base64 = base64.b64encode(png_bytes).decode('utf-8')
                return VTOResponse(
                    success=True,
                    image_base64=result_base64,
                    items_count=len(request.garments),
                    cost_estimate=0.13
                )
        
        return VTOResponse(success=False, error="No image generated", items_count=len(request.garments))
    except Exception as e:
        return VTOResponse(success=False, error=str(e), items_count=len(request.garments) if request.garments else 0)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "gemini-3-pro-image-preview",
        "version": "v2-improved",
        "max_items": 12,
        "cost_per_image": 0.13,
        "features": ["styling_notes", "hierarchical_layering", "fafafa_background", "face_closeup_support"]
    }
