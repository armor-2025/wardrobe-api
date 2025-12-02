"""
VTO (Virtual Try-On) API Endpoints
Uses the working FINAL_WITH_MENSWEAR_NOV7 system
"""
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from typing import List, Optional
import httpx
import base64
import tempfile
import os
from io import BytesIO
from PIL import Image

from vto_system import VTOSystem, GarmentAnalyzer, UserProfile

router = APIRouter(prefix="/vto", tags=["vto"])

# Initialize once
vto_system = None
garment_analyzer = None

def get_vto_system():
    global vto_system
    if vto_system is None:
        vto_system = VTOSystem()
    return vto_system

def get_garment_analyzer():
    global garment_analyzer
    if garment_analyzer is None:
        garment_analyzer = GarmentAnalyzer()
    return garment_analyzer


@router.post("/generate")
async def generate_vto(
    base_model_url: str = Form(...),
    garment_urls: str = Form(...),  # JSON array of URLs
    body_type: str = Form("average"),  # slim, average, curvy, plus
    height: str = Form("average"),  # petite, average, tall, none
    gender: str = Form("womenswear"),  # menswear, womenswear
    authorization: str = Header(None)
):
    """
    Generate VTO from URLs
    
    - base_model_url: User's full body photo URL
    - garment_urls: JSON array of garment image URLs (max 4)
    - body_type: slim, average, curvy, plus
    - height: petite, average, tall, none
    - gender: menswear or womenswear
    """
    import json
    
    # Parse garment URLs
    try:
        garment_url_list = json.loads(garment_urls)
    except:
        raise HTTPException(status_code=400, detail="garment_urls must be valid JSON array")
    
    if not garment_url_list:
        raise HTTPException(status_code=400, detail="At least one garment required")
    
    if len(garment_url_list) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 garments allowed (upgrade to Pro for more)")
    
    try:
        # Download all images
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Download base model
            base_resp = await client.get(base_model_url)
            base_image_bytes = base_resp.content
            
            # Download garments
            garment_bytes_list = []
            for url in garment_url_list:
                resp = await client.get(url)
                garment_bytes_list.append(resp.content)
        
        # Save base model to temp file (UserProfile needs path)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(base_image_bytes)
            base_model_path = f.name
        
        # Save garments to temp files
        garment_paths = []
        for i, gb in enumerate(garment_bytes_list):
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(gb)
                garment_paths.append(f.name)
        
        try:
            # Create user profile
            profile = UserProfile(
                photo_path=base_model_path,
                body_type_id=body_type,
                height_id=height,
                gender_presentation=gender
            )
            
            # Analyze garments
            analyzer = get_garment_analyzer()
            outfit_analysis = analyzer.analyze_outfit(garment_paths)
            outfit_description = outfit_analysis['outfit_description']
            
            # Generate VTO
            system = get_vto_system()
            result = system.generate_vto_with_retry(
                user_profile=profile,
                garment_images=garment_paths,
                garment_description=outfit_description
            )
            
            if result.success:
                # Convert CV2 image to base64
                import cv2
                _, buffer = cv2.imencode('.png', result.image)
                result_b64 = base64.b64encode(buffer).decode()
                
                return {
                    "success": True,
                    "vto_image_base64": result_b64,
                    "attempts": result.attempts
                }
            else:
                error_msg = result.get_user_message()
                raise HTTPException(
                    status_code=500, 
                    detail=error_msg.get('message', 'VTO generation failed')
                )
        
        finally:
            # Cleanup temp files
            os.unlink(base_model_path)
            for p in garment_paths:
                os.unlink(p)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"VTO error: {str(e)}")


@router.get("/pricing")
def get_vto_pricing():
    """Get VTO pricing info"""
    return {
        "cost_per_generation": "$0.10",
        "free_tier": "None",
        "pro_tier": {
            "price": "$4.99/month",
            "includes": "50 VTO generations per month"
        },
        "max_garments_free": 4,
        "max_garments_pro": 8
    }
