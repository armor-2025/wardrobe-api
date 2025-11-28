"""
VTO (Virtual Try-On) API Endpoints - V2
Proven 3-step workflow matching TypeScript implementation

STEP 1: Generate base model (one-time)
STEP 2: Apply garments (per outfit)
STEP 3: Generate poses (optional)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json

from database import get_db, User
from vto_system import VTOService, POSE_OPTIONS

router = APIRouter(prefix="/vto", tags=["vto"])


# ==================== SCHEMAS ====================

class BaseModelResponse(BaseModel):
    success: bool
    base_model_image: str  # data URL
    message: str


class VTOApplyRequest(BaseModel):
    base_model_image: str  # data URL from step 1
    garment_urls: List[str]  # URLs of garment images


class VTOResponse(BaseModel):
    success: bool
    vto_image: str  # data URL
    cost: float
    remaining_quota: int


class PoseVariationsRequest(BaseModel):
    try_on_image: str  # data URL from step 2
    poses: List[str]  # Pose instructions


class PoseVariationsResponse(BaseModel):
    success: bool
    pose_variations: List[str]  # List of data URLs


# ==================== HELPER ====================

def get_user_from_token(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate user from Bearer token"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    
    from auth_service import get_current_user
    user = get_current_user(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user


def check_premium_subscription(user: User) -> bool:
    """Check if user has active premium subscription"""
    # TODO: Implement actual subscription check
    return getattr(user, 'is_premium', False) or True  # Remove "or True" in production


def get_vto_quota(user: User, db: Session) -> int:
    """Get remaining VTO quota for user this month"""
    # TODO: Implement quota tracking
    return 50  # Placeholder


# ==================== ENDPOINTS ====================

@router.post("/generate-base-model", response_model=BaseModelResponse)
async def generate_base_model(
    file: UploadFile = File(...),
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    STEP 1: Generate base model from user photo
    
    User uploads a full-body photo
    AI transforms them into a professional model on neutral background
    Face, hair, identity preserved perfectly
    
    This is done ONCE (or when user wants to update their model)
    Store the result for all future try-ons
    
    Returns: Base model image as data URL
    """
    
    # Check premium (optional - could offer 1 free try)
    if not check_premium_subscription(current_user):
        raise HTTPException(
            status_code=403,
            detail="Virtual Try-On requires Premium ($4.99/month). First try-on free!"
        )
    
    # Validate file
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read image
    image_data = await file.read()
    
    if len(image_data) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    # Generate base model
    service = VTOService(db)
    
    try:
        result = await service.setup_user_model(current_user.id, image_data)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message'))
        
        # TODO: Store base_model_image in database for user
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate base model: {str(e)}")


@router.post("/apply-garments", response_model=VTOResponse)
async def apply_garments(
    base_model_image: str = Form(...),  # data URL
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db),
    garment_files: List[UploadFile] = File(...)
):
    """
    STEP 2: Apply garments to base model
    
    Takes:
    - Base model image (from step 1)
    - Garment images (from user's wardrobe)
    
    Returns: Model wearing all garments (pixel-perfect)
    
    Can apply multiple garments in sequence
    Each garment = 1 API call = ~$0.05
    """
    
    # Check premium
    if not check_premium_subscription(current_user):
        raise HTTPException(status_code=403, detail="VTO requires Premium")
    
    # Check quota
    remaining_quota = get_vto_quota(current_user, db)
    if remaining_quota <= 0:
        raise HTTPException(
            status_code=429,
            detail="Monthly VTO quota exceeded"
        )
    
    # Read garment images
    garment_images_bytes = []
    for garment_file in garment_files:
        if not garment_file.content_type.startswith('image/'):
            continue
        garment_images_bytes.append(await garment_file.read())
    
    if not garment_images_bytes:
        raise HTTPException(status_code=400, detail="No valid garment images provided")
    
    # Apply garments
    service = VTOService(db)
    
    try:
        result = await service.generate_outfit_tryon(
            user_id=current_user.id,
            base_model_data_url=base_model_image,
            garment_images=garment_images_bytes
        )
        
        # TODO: Track usage in database
        
        return {
            'success': result['success'],
            'vto_image': result['vto_image'],
            'cost': result['cost'],
            'remaining_quota': remaining_quota - 1
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VTO generation failed: {str(e)}")


@router.post("/generate-poses", response_model=PoseVariationsResponse)
async def generate_pose_variations(
    try_on_image: str = Form(...),  # data URL from step 2
    poses: str = Form(...),  # JSON array of pose instructions
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    STEP 3: Generate pose variations (OPTIONAL)
    
    Takes try-on result and generates different angles/poses
    Person, clothing, background style remain identical
    
    Available poses:
    - "Slightly turned, 3/4 view"
    - "Side profile view"
    - "Walking towards camera"
    - "Leaning against a wall"
    
    Each pose = 1 API call = ~$0.05
    """
    
    # Check premium
    if not check_premium_subscription(current_user):
        raise HTTPException(status_code=403, detail="VTO requires Premium")
    
    # Parse poses
    try:
        pose_list = json.loads(poses)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid poses format")
    
    if not isinstance(pose_list, list) or len(pose_list) == 0:
        raise HTTPException(status_code=400, detail="Poses must be a non-empty array")
    
    # Generate variations
    service = VTOService(db)
    
    try:
        result = await service.generate_pose_variations(
            try_on_data_url=try_on_image,
            poses=pose_list
        )
        
        return {
            'success': True,
            'pose_variations': result['pose_variations']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pose generation failed: {str(e)}")


@router.get("/quota")
def get_user_quota(
    current_user: User = Depends(get_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get user's VTO quota info
    """
    
    if not check_premium_subscription(current_user):
        return {
            'is_premium': False,
            'monthly_limit': 0,
            'used': 0,
            'remaining': 0,
            'message': 'Upgrade to Premium for 50 VTO per month'
        }
    
    # TODO: Query actual usage from database
    monthly_limit = 50
    used = 5  # Placeholder
    remaining = monthly_limit - used
    
    return {
        'is_premium': True,
        'monthly_limit': monthly_limit,
        'used': used,
        'remaining': remaining,
        'reset_date': '2024-12-01'
    }


@router.get("/poses")
def get_available_poses():
    """
    Get list of available pose options
    """
    return {
        'poses': POSE_OPTIONS,
        'description': 'Available pose variations for Step 3'
    }


@router.get("/pricing")
def get_vto_pricing():
    """
    Get VTO pricing info
    """
    return {
        'plans': {
            'free': {
                'price': 0,
                'vto_quota': 0,
                'trial': '1 free try-on'
            },
            'premium': {
                'price': 4.99,
                'billing': 'monthly',
                'vto_quota': 50,
                'features': [
                    'Generate base model',
                    '50 outfit try-ons per month',
                    'Unlimited pose variations',
                    'Professional results',
                    'Your actual face preserved'
                ]
            }
        },
        'workflow': {
            'step_1': 'Generate base model (one-time)',
            'step_2': 'Apply garments (per outfit)',
            'step_3': 'Generate poses (optional)',
            'cost_per_step': '$0.05 per API call'
        }
    }
