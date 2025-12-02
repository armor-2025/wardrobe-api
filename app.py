from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
from meilisearch import Client
import os, io, json
import numpy as np
import requests
from PIL import Image
#import torch
#import faiss
#import open_clip

from fastapi import HTTPException  # add this with your other FastAPI imports
from asos_service import get_asos_service
from conversational_search import get_conversational_service

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from database import init_db, get_db, User, WardrobeItem, Favorite, Outfit
from auth_service import signup, login, create_access_token, get_current_user
from vision_service import get_vision_service
from stock_checker import get_stock_checker

from fastapi import File, UploadFile
import shutil
import uuid
from pathlib import Path

from datetime import datetime

def prepare_canvas_image(favorite_id: int):
    """Background job to remove background when item is added to canvas"""
    import requests
    from pathlib import Path
    import uuid
    from database import SessionLocal, Favorite
    
    # Create new DB session for this thread
    db = SessionLocal()
    
    try:
        # Get the favorite
        favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()
        if not favorite:
            return
        
        # Update status
        favorite.canvas_processing_status = "processing"
        db.commit()
        
        # Download the original image
        response = requests.get(favorite.image_url, timeout=10)
        if response.status_code != 200:
            favorite.canvas_processing_status = "failed"
            db.commit()
            return
        
        # Save temporarily
        upload_dir = Path("uploads/canvas")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        unique_filename = f"{uuid.uuid4()}.png"
        temp_path = upload_dir / f"temp_{unique_filename}"
        final_path = upload_dir / unique_filename
        
        with temp_path.open("wb") as f:
            f.write(response.content)
        
        # Remove background
        from rembg import remove, new_session
        from PIL import Image
        import numpy as np
        from scipy import ndimage
        
        input_image = Image.open(temp_path)
        session = new_session(model_name='isnet-general-use')
        
        output_image = remove(
            input_image,
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=270,
            alpha_matting_background_threshold=20,
            alpha_matting_erode_size=15
        )
        
        # Post-process to remove artifacts
        if output_image.mode != 'RGBA':
            output_image = output_image.convert('RGBA')
        
        alpha_array = np.array(output_image.split()[3])
        binary = alpha_array > 30
        labeled, num_features = ndimage.label(binary)
        
        if num_features > 1:
            sizes = ndimage.sum(binary, labeled, range(num_features + 1))
            max_label = np.argmax(sizes)
            mask = labeled == max_label
            new_alpha = np.where(mask, alpha_array, 0).astype(np.uint8)
            output_image.putalpha(Image.fromarray(new_alpha))
        
        bbox = output_image.getbbox()
        if bbox:
            output_image = output_image.crop(bbox)
        
        # Save as PNG
        output_image.save(final_path, format='PNG', optimize=True)
        temp_path.unlink()
        
        # Update favorite with canvas image URL
        canvas_url = f"http://127.0.0.1:8012/uploads/canvas/{unique_filename}"
        favorite.canvas_image_url = canvas_url
        favorite.canvas_processing_status = "complete"
        db.commit()
        
        print(f"✅ Canvas image prepared for favorite #{favorite_id}")
        
    except Exception as e:
        print(f"❌ Failed to prepare canvas image #{favorite_id}: {e}")
        try:
            favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()
            if favorite:
                favorite.canvas_processing_status = "failed"
                db.commit()
        except:
            pass
    finally:
        db.close()

app = FastAPI()
from fastapi.staticfiles import StaticFiles

# Serve uploaded files
# Create uploads directory if it doesn't exist
import os
os.makedirs("uploads/wardrobe", exist_ok=True)
os.makedirs("uploads/canvas", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Initialize database
init_db()

# Security
security = HTTPBearer()

# CORS for the Flutter web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEILI_HOST = os.getenv("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_KEY  = os.getenv("MEILI_KEY",  "master_key")
client     = Client(MEILI_HOST, MEILI_KEY)
# ---- Visual search: CLIP + FAISS ----
VINDEX_PATH = "faiss.index"
VMETA_PATH  = "faiss_meta.json"

# Load CLIP (image encoder only)
_v_model = None
_preprocess = None
_v_device = "cpu"
#_v_model, _, _preprocess = open_clip.create_model_and_transforms(
#    "ViT-B-32", pretrained="openai"
#)
#_v_model.eval()
#_v_device = "cpu"
#_v_model.to(_v_device)
#
## Load FAISS index + metadata (created by vision_index.py)
_v_index = None
_v_meta  = []
if os.path.exists(VINDEX_PATH) and os.path.exists(VMETA_PATH):
#    _v_index = faiss.read_index(VINDEX_PATH)
    with open(VMETA_PATH, "r") as f:
        _v_meta = json.load(f)

def _load_image_from_url(url, timeout=15):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def _encode_image_from_url(url: str) -> np.ndarray:
    img = _preprocess(_load_image_from_url(url)).unsqueeze(0).to(_v_device)
    with torch.no_grad():
        emb = _v_model.encode_image(img)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().astype("float32")

@app.get("/ping")
async def ping():
    return {"ok": True}



@app.get("/vsearch")
def visual_search(image: str, k: int = 10):
    """
    Visual similarity search.
    GET /vsearch?image=<image_url>&k=10
    """
    if _v_index is None or not _v_meta:
        raise HTTPException(status_code=503, detail="Visual index not loaded (run vision_index.py first).")

    try:
        q = _encode_image_from_url(image)  # shape (1, 512)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load/encode image: {e}")

    # Nearest neighbors (cosine on L2-normalized vectors ≈ inner product)
    D, I = _v_index.search(q, min(k, len(_v_meta)))

    hits = []
    for rank, (idx, score) in enumerate(zip(I[0].tolist(), D[0].tolist()), start=1):
        if idx < 0 or idx >= len(_v_meta):
            continue
        m = _v_meta[idx]
        hits.append({
            "rank": rank,
            "score": float(score),
            "id": m.get("id"),
            "title": m.get("title"),
            "image": m.get("image"),
        })
    return {"results": hits}

from fastapi import File, UploadFile   # <-- keep this import near your other FastAPI imports

@app.post("/vsearch_upload")
async def vsearch_upload(file: UploadFile = File(...), k: int = 10):
    """
    Visual search by uploaded image file (multipart/form-data).
    Field name: 'file'
    """
    if _v_index is None or not _v_meta:
        raise HTTPException(
            status_code=503,
            detail="Visual index not loaded (run vision_index.py first)."
        )

    try:
        # 1) Read uploaded bytes -> PIL image (RGB)
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert("RGB")

        # 2) Encode with CLIP
        with torch.no_grad():
            inp = _preprocess(img).unsqueeze(0).to(_v_device)
            emb = _v_model.encode_image(inp)
            emb = emb / emb.norm(dim=-1, keepdim=True)
            q = emb.cpu().numpy().astype("float32")

        # 3) FAISS search
        D, I = _v_index.search(q, min(k, len(_v_meta)))

        # 4) Build hits
        hits = []
        for rank, (idx, score) in enumerate(zip(I[0].tolist(), D[0].tolist()), start=1):
            if idx < 0 or idx >= len(_v_meta):
                continue
            m = _v_meta[idx]
            hits.append({
                "rank": rank,
                "score": float(score),
                "id": m.get("id"),
                "title": m.get("title"),
                "image": m.get("image"),
            })

        return {"results": hits}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not process image: {e}")



@app.get("/asos/search")
def asos_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    country: str = Query("US"),
    currency: str = Query("USD"),
    sort: Optional[str] = Query("freshness"),
):
    asos = get_asos_service()
    print(f"DEBUG: search_params = {search_params}")
    data = asos.search_products(query=q, limit=limit, offset=offset, country=country, currency=currency, sort=sort)
    products = []
    for item in data.get("products", []):
        price_data = item.get("price", {}).get("current", {})
        price_value = price_data.get("value", 0.0)
        
        # Apply price filters if specified
        max_price = search_params.get("max_price")
        min_price = search_params.get("min_price")
        
        if max_price and price_value > max_price:
            continue  # Skip items over max price
        if min_price and price_value < min_price:
            continue  # Skip items under min price
        
        image_url = item.get("imageUrl", "")
        if image_url and not image_url.startswith("http"):
            image_url = f"https://{image_url}"
        products.append({
            "id": str(item.get("id", "")),
            "title": item.get("name", ""),
            "image": image_url,
            "brand": item.get("brandName", ""),
            "retailer": "ASOS",
            "price": price_value,
        })
    return {"results": products, "total": data.get("itemCount", 0)}

@app.get("/asos/product/{product_id}")
def asos_product_detail(product_id: str, country: str = Query("US"), currency: str = Query("USD")):
    asos = get_asos_service()
    return asos.get_product_details(product_id=product_id, store=country, currency=currency)

@app.get("/search/conversational")
def conversational_search(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(20, ge=1, le=50)
):
    conv = get_conversational_service()
    parsed = conv.parse_query(q)
    search_params = conv.query_to_search_params(parsed)
    search_params["limit"] = limit
    asos = get_asos_service()
    print(f"DEBUG conversational: search_params = {search_params}")
    data = asos.search_products(
        query=search_params.get("q", ""), 
        limit=limit, 
        country="US", 
        currency="USD",
        min_price=search_params.get("min_price"),
        max_price=search_params.get("max_price")
    )
    products = []
    for item in data.get("products", []):
        price_data = item.get("price", {}).get("current", {})
        image_url = item.get("imageUrl", "")
        if image_url and not image_url.startswith("http"):
            image_url = f"https://{image_url}"
        products.append({
            "id": str(item.get("id", "")),
            "title": item.get("name", ""),
            "image": image_url,
            "brand": item.get("brandName", ""),
            "retailer": "ASOS",
            "price": price_data.get("value", 0.0),
        })
    return {"results": products, "total": data.get("itemCount", 0), "parsed_query": parsed, "model_used": parsed.get("_model_used")}


from fastapi.responses import StreamingResponse

@app.get("/proxy/image")
async def proxy_image(url: str):
    """
    Proxy images to avoid CORS issues
    GET /proxy/image?url=https://...
    """
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Get content type from the response
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=content_type
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch image: {str(e)}")

# ============= AUTH ENDPOINTS =============

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/signup")
def auth_signup(req: SignupRequest, db: Session = Depends(get_db)):
    user = signup(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    token = create_access_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "email": user.email}}

@app.post("/auth/login")
def auth_login(req: LoginRequest, db: Session = Depends(get_db)):
    user = login(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "email": user.email}}

# ============= WARDROBE ENDPOINTS =============

class WardrobeUploadRequest(BaseModel):
    image_url: str

@app.post("/wardrobe/upload")
def upload_wardrobe_item(
    req: WardrobeUploadRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # AI analyze the image
    vision = get_vision_service()
    tags = vision.analyze_clothing(req.image_url)
    
    # Save to database
    item = WardrobeItem(
        user_id=user.id,
        image_url=req.image_url,
        category=tags.get('category', 'unknown'),
        color=tags.get('color', 'unknown'),
        fabric=tags.get('description', 'unknown'),
        pattern='',
        style_tags='[]',
        user_edited=False
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "image_url": item.image_url,
        "tags": tags
    }

@app.post("/wardrobe/upload-file")
async def upload_wardrobe_file(
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads/wardrobe")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.png"  # Always save as PNG
    temp_path = upload_dir / f"temp_{unique_filename}"
    final_path = upload_dir / unique_filename
    
    # Save uploaded file temporarily
    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

# Remove background using rembg
    try:
        from rembg import remove, new_session
        from PIL import Image, ImageDraw
        import numpy as np
        
        # Open image
        input_image = Image.open(temp_path)
        
        # Create session with best model
        session = new_session(model_name='isnet-general-use')
        
        # Remove background - rembg is smart enough to focus on main subject
        output_image = remove(
            input_image, 
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=270,
            alpha_matting_background_threshold=20,
            alpha_matting_erode_size=15
        )
        
        # Post-process: remove small artifacts (logos, icons)
        if output_image.mode != 'RGBA':
            output_image = output_image.convert('RGBA')
        
        # Get alpha channel
        pixels = output_image.load()
        width, height = output_image.size
        
        # Find the main clothing object by getting largest connected region
        alpha_array = np.array(output_image.split()[3])
        
        # Remove small isolated regions (logos, icons, text)
        from scipy import ndimage
        
        # Threshold alpha
        binary = alpha_array > 30
        
        # Label connected components
        labeled, num_features = ndimage.label(binary)
        
        # Find largest component (the clothing item)
        if num_features > 1:
            sizes = ndimage.sum(binary, labeled, range(num_features + 1))
            
            # Keep only the largest component
            max_label = np.argmax(sizes)
            mask = labeled == max_label
            
            # Create new alpha channel with only main object
            new_alpha = np.where(mask, alpha_array, 0).astype(np.uint8)
            
            # Apply new alpha
            output_image.putalpha(Image.fromarray(new_alpha))
        
        # Crop to content
        bbox = output_image.getbbox()
        if bbox:
            output_image = output_image.crop(bbox)
        
        # Save as PNG
        output_image.save(final_path, format='PNG', optimize=True)
        temp_path.unlink()
        
    except Exception as e:
        print(f"Background removal failed: {e}")
        shutil.move(temp_path, final_path)
    
    # Create public URL (OUTSIDE the try/except)
    local_url = f"http://127.0.0.1:8012/uploads/wardrobe/{unique_filename}"
    image_url = f"https://yow-api.onrender.com/uploads/wardrobe/{unique_filename}"
    
    # AI analyze the image
    vision = get_vision_service()
    tags = vision.analyze_clothing(local_url)
    
    # Save to database
    item = WardrobeItem(
        user_id=user.id,
        image_url=image_url,
        category=tags.get('category', 'unknown'),
        color=tags.get('color', 'unknown'),
        fabric=tags.get('description', 'unknown'),
        pattern='',
        style_tags='[]',
        user_edited=False
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "image_url": image_url,
        "tags": tags,
        "background_removed": True
    }

@app.put("/wardrobe/items/{item_id}")
def update_wardrobe_item(
    item_id: int,
    category: str = None,
    color: str = None,
    fabric: str = None,
    pattern: str = None,
    style_tags: str = None,  # JSON string array
    brand: str = None,
    size: str = None,
    price: float = None,
    date_purchased: str = None,  # ISO format string
    season: str = None,
    state: str = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Update wardrobe item details after review"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get item and verify ownership
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update fields if provided
    if category is not None:
        item.category = category
    if color is not None:
        item.color = color
    if fabric is not None:
        item.fabric = fabric
    if pattern is not None:
        item.pattern = pattern
    if style_tags is not None:
        item.style_tags = style_tags
    if brand is not None:
        item.brand = brand
    if size is not None:
        item.size = size
    if price is not None:
        item.price = price
    if date_purchased is not None:
        from dateutil import parser
        item.date_purchased = parser.parse(date_purchased)
    if season is not None:
        item.season = season
    if state is not None:
        item.state = state
    
    # Mark as user-edited if they changed AI tags
    if any([category, color, fabric, pattern, style_tags]):
        item.user_edited = True
    
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "image_url": item.image_url,
        "category": item.category,
        "color": item.color,
        "fabric": item.fabric,
        "pattern": item.pattern,
        "style_tags": json.loads(item.style_tags) if item.style_tags else [],
        "brand": item.brand,
        "size": item.size,
        "price": item.price,
        "date_purchased": item.date_purchased.isoformat() if item.date_purchased else None,
        "season": item.season,
        "state": item.state,
        "user_edited": item.user_edited,
        "created_at": item.created_at.isoformat()
    }   

@app.get("/wardrobe/items")
def get_wardrobe_items(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    items = db.query(WardrobeItem).filter(WardrobeItem.user_id == user.id).all()
    
    return {
        "items": [
            {
                "id": item.id,
                "image_url": item.image_url,
                "category": item.category,
                "color": item.color,
                "fabric": item.fabric,
                "pattern": item.pattern,
                "style_tags": json.loads(item.style_tags) if item.style_tags else [],
                "created_at": item.created_at.isoformat()
            }
            for item in items
        ]
    }

# ============= FAVORITES ENDPOINTS =============

class AddFavoriteRequest(BaseModel):
    product_id: str
    title: str
    image_url: str
    brand: Optional[str] = None
    retailer: str
    price: float
    product_url: str
    notify_on_price_drop: Optional[bool] = True
    price_alert_threshold: Optional[float] = None

@app.post("/favorites")
def add_favorite(
    req: AddFavoriteRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Save with original image - NO background removal
    favorite = Favorite(
        user_id=user.id,
        product_id=req.product_id,
        title=req.title,
        price=req.price,
        image_url=req.image_url,  # Keep original
        canvas_image_url=None,  # Will be created when added to canvas
        canvas_processing_status=None,
        product_url=req.product_url,
        retailer=req.retailer,
        brand=req.brand if hasattr(req, 'brand') else None,
        notify_on_price_drop=req.notify_on_price_drop if hasattr(req, 'notify_on_price_drop') else True,
        price_alert_threshold=req.price_alert_threshold if hasattr(req, 'price_alert_threshold') else None,
        original_price=req.price
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return {
        "id": favorite.id,
        "product_id": favorite.product_id,
        "title": favorite.title,
        "price": favorite.price,
        "image_url": favorite.image_url,  # Original product image
        "product_url": favorite.product_url,
        "retailer": favorite.retailer,
        "brand": favorite.brand
    }

@app.get("/favorites")
def get_favorites(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    
    return {
        "favorites": [
            {
                "id": fav.id,
                "product_id": fav.product_id,
                "title": fav.title,
                "image_url": fav.image_url,
                "canvas_image_url": fav.canvas_image_url,
                "canvas_processing_status": fav.canvas_processing_status,
                "brand": fav.brand,
                "retailer": fav.retailer,
                "price": fav.price,
                "product_url": fav.product_url,
                "created_at": fav.created_at.isoformat()
            }
            for fav in favs
        ]
    }

@app.delete("/favorites/{fav_id}")
def delete_favorite(
    fav_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    fav = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == user.id
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(fav)
    db.commit()
    
    return {"message": "Removed from favorites"}

@app.post("/favorites/{favorite_id}/prepare-canvas")
def prepare_favorite_for_canvas(
    favorite_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Prepare a favorited item for canvas by removing background"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get favorite and verify ownership
    favorite = db.query(Favorite).filter(
        Favorite.id == favorite_id,
        Favorite.user_id == user.id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    # If already processed, return existing canvas image
    if favorite.canvas_image_url and favorite.canvas_processing_status == "complete":
        return {
            "id": favorite.id,
            "canvas_image_url": favorite.canvas_image_url,
            "status": "complete",
            "message": "Canvas image already ready"
        }
    
    # If currently processing, return status
    if favorite.canvas_processing_status == "processing":
        return {
            "id": favorite.id,
            "status": "processing",
            "message": "Background removal in progress..."
        }
    
    # Start background processing
    import threading
    favorite.canvas_processing_status = "pending"
    db.commit()
    
    threading.Thread(
        target=prepare_canvas_image,
        args=(favorite.id,),
        daemon=True
    ).start()
    
    return {
        "id": favorite.id,
        "status": "pending",
        "message": "Preparing canvas image..."
    }

# ============= OUTFITS ENDPOINTS =============

class CreateOutfitRequest(BaseModel):
    name: str
    outfit_data: dict  # JSON with items, positions, etc.

class UpdateOutfitRequest(BaseModel):
    name: str
    outfit_data: dict

@app.post("/outfits")
def create_outfit(
    req: CreateOutfitRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    outfit = Outfit(
        user_id=user.id,
        name=req.name,
        outfit_data=json.dumps(req.outfit_data),
        thumbnail_url=None  # TODO: Generate thumbnail later
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    
    return {
        "id": outfit.id,
        "name": outfit.name,
        "outfit_data": json.loads(outfit.outfit_data),
        "created_at": outfit.created_at.isoformat()
    }

@app.get("/outfits")
def get_outfits(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    outfits = db.query(Outfit).filter(Outfit.user_id == user.id).all()
    
    return {
        "outfits": [
            {
                "id": outfit.id,
                "name": outfit.name,
                "outfit_data": json.loads(outfit.outfit_data),
                "thumbnail_url": outfit.thumbnail_url,
                "created_at": outfit.created_at.isoformat()
            }
            for outfit in outfits
        ]
    }

@app.put("/outfits/{outfit_id}")
def update_outfit(
    outfit_id: int,
    req: UpdateOutfitRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    outfit = db.query(Outfit).filter(
        Outfit.id == outfit_id,
        Outfit.user_id == user.id
    ).first()
    
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    outfit.name = req.name
    outfit.outfit_data = json.dumps(req.outfit_data)
    db.commit()
    db.refresh(outfit)
    
    return {
        "id": outfit.id,
        "name": outfit.name,
        "outfit_data": json.loads(outfit.outfit_data),
        "created_at": outfit.created_at.isoformat()
    }

@app.delete("/outfits/{outfit_id}")
def delete_outfit(
    outfit_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    outfit = db.query(Outfit).filter(
        Outfit.id == outfit_id,
        Outfit.user_id == user.id
    ).first()
    
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    db.delete(outfit)
    db.commit()
    
    return {"message": "Outfit deleted"}

# ============= PRICE TRACKING ENDPOINTS =============

@app.get("/favorites/{fav_id}/price-history")
def get_price_history(
    fav_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    fav = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == user.id
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    price_history = json.loads(fav.price_history) if fav.price_history else []
    
    return {
        "product_id": fav.product_id,
        "title": fav.title,
        "current_price": fav.price,
        "original_price": fav.original_price,
        "price_change": fav.price - fav.original_price if fav.original_price else 0,
        "price_history": price_history
    }

class SetPriceAlertRequest(BaseModel):
    threshold: float

@app.post("/favorites/{fav_id}/set-alert")
def set_price_alert(
    fav_id: int,
    req: SetPriceAlertRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    fav = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == user.id
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    fav.price_alert_threshold = req.threshold
    db.commit()
    
    return {"message": f"Alert set: notify when price drops below £{req.threshold}"}

@app.post("/check-prices")
def check_all_prices(db: Session = Depends(get_db)):
    """
    Background job endpoint to check prices for all favorited items
    Should be called by a cron job daily
    """
    favorites = db.query(Favorite).all()
    updated_count = 0
    alerts = []
    
    for fav in favorites:
        # TODO: Call retailer API to get current price
        # For now, this is a placeholder
        # In production, you'd call ASOS/Vinted/etc API here
        
        # Placeholder: Randomly simulate price changes for testing
        import random
        if random.random() < 0.3:  # 30% chance of price change
            old_price = fav.price
            new_price = round(old_price * random.uniform(0.8, 1.2), 2)
            
            # Update price
            fav.price = new_price
            fav.last_price_check = datetime.utcnow()
            
            # Add to price history
            history = json.loads(fav.price_history) if fav.price_history else []
            history.append({
                "date": datetime.utcnow().isoformat(),
                "price": new_price
            })
            fav.price_history = json.dumps(history)
            
            updated_count += 1
            
            # Check if alert threshold met
            if fav.price_alert_threshold and new_price < fav.price_alert_threshold:
                alerts.append({
                    "user_id": fav.user_id,
                    "product": fav.title,
                    "new_price": new_price,
                    "threshold": fav.price_alert_threshold
                })
    
    db.commit()
    
    return {
        "checked": len(favorites),
        "updated": updated_count,
        "alerts": alerts
    }

# ============= SIZE PREFERENCES ENDPOINTS =============

class SizePreferenceRequest(BaseModel):
    enabled: bool = True
    gender_preference: str = "women"  # "women", "men", "both"
    tops: list = []
    bottoms: list = []
    shoes: list = []
    dresses: list = []

@app.post("/size-preferences")
def set_size_preferences(
    req: SizePreferenceRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if preferences already exist
    from database import SizePreference
    pref = db.query(SizePreference).filter(SizePreference.user_id == user.id).first()
    
    if pref:
        # Update existing
        pref.enabled = req.enabled
        pref.gender_preference = req.gender_preference
        pref.tops = json.dumps(req.tops)
        pref.bottoms = json.dumps(req.bottoms)
        pref.shoes = json.dumps(req.shoes)
        pref.dresses = json.dumps(req.dresses)
        pref.updated_at = datetime.utcnow()
    else:
        # Create new
        pref = SizePreference(
            user_id=user.id,
            enabled=req.enabled,
            gender_preference=req.gender_preference,
            tops=json.dumps(req.tops),
            bottoms=json.dumps(req.bottoms),
            shoes=json.dumps(req.shoes),
            dresses=json.dumps(req.dresses)
        )
        db.add(pref)
    
    db.commit()
    db.refresh(pref)
    
    return {
        "message": "Size preferences saved",
        "preferences": {
            "enabled": pref.enabled,
            "gender_preference": pref.gender_preference,
            "tops": json.loads(pref.tops) if pref.tops else [],
            "bottoms": json.loads(pref.bottoms) if pref.bottoms else [],
            "shoes": json.loads(pref.shoes) if pref.shoes else [],
            "dresses": json.loads(pref.dresses) if pref.dresses else []
        }
    }

@app.get("/size-preferences")
def get_size_preferences(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from database import SizePreference
    pref = db.query(SizePreference).filter(SizePreference.user_id == user.id).first()
    
    if not pref:
        return {
            "enabled": False,
            "gender_preference": "women",
            "tops": [],
            "bottoms": [],
            "shoes": [],
            "dresses": []
        }
    
    return {
        "enabled": pref.enabled,
        "gender_preference": pref.gender_preference,
        "tops": json.loads(pref.tops) if pref.tops else [],
        "bottoms": json.loads(pref.bottoms) if pref.bottoms else [],
        "shoes": json.loads(pref.shoes) if pref.shoes else [],
        "dresses": json.loads(pref.dresses) if pref.dresses else []
    }

@app.post("/size-preferences/toggle")
def toggle_size_filter(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from database import SizePreference
    pref = db.query(SizePreference).filter(SizePreference.user_id == user.id).first()
    
    if not pref:
        raise HTTPException(status_code=404, detail="No size preferences set")
    
    pref.enabled = not pref.enabled
    db.commit()
    
    return {"enabled": pref.enabled, "message": f"Size filter {'enabled' if pref.enabled else 'disabled'}"}

# ============= STOCK CHECKING ENDPOINTS =============

@app.post("/check-stock")
def check_all_stock(db: Session = Depends(get_db)):
    """
    Background job to check stock levels for all favorited items
    Should be called by cron job daily/hourly
    """
    from database import Favorite
    
    favorites = db.query(Favorite).all()
    checker = get_stock_checker()
    updated_count = 0
    alerts = []
    
    for fav in favorites:
        if not fav.product_url:
            continue
        
        # Check current stock
        stock_info = checker.check_stock(fav.product_url, fav.product_id, fav.retailer)
        
        old_status = fav.stock_status
        new_status = stock_info['status']
        
        # Update favorite with new stock info
        fav.stock_status = new_status
        fav.stock_level = stock_info.get('level')
        fav.last_stock_check = datetime.utcnow()
        
        updated_count += 1
        
        # Generate alerts for status changes
        if old_status != new_status:
            # Low stock alert
            if new_status == "low_stock" and fav.notify_on_low_stock:
                alerts.append({
                    "type": "low_stock",
                    "user_id": fav.user_id,
                    "product": fav.title,
                    "status": new_status,
                    "level": stock_info.get('level'),
                    "text": stock_info.get('text')
                })
            
            # Out of stock alert
            elif new_status == "out_of_stock":
                alerts.append({
                    "type": "out_of_stock",
                    "user_id": fav.user_id,
                    "product": fav.title,
                    "status": new_status
                })
            
            # Back in stock alert
            elif old_status == "out_of_stock" and new_status in ["in_stock", "low_stock"] and fav.notify_on_back_in_stock:
                alerts.append({
                    "type": "back_in_stock",
                    "user_id": fav.user_id,
                    "product": fav.title,
                    "status": new_status
                })
    
    db.commit()
    
    return {
        "checked": len(favorites),
        "updated": updated_count,
        "alerts": alerts
    }

@app.get("/favorites/{fav_id}/stock")
def get_stock_status(
    fav_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get current stock status for a favorited item"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from database import Favorite
    fav = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == user.id
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    return {
        "product_id": fav.product_id,
        "title": fav.title,
        "stock_status": fav.stock_status or "unknown",
        "stock_level": fav.stock_level,
        "last_checked": fav.last_stock_check.isoformat() if fav.last_stock_check else None
    }

@app.post("/favorites/{fav_id}/check-stock-now")
def check_stock_now(
    fav_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Manually trigger stock check for a specific item"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from database import Favorite
    fav = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == user.id
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    if not fav.product_url:
        raise HTTPException(status_code=400, detail="No product URL available")
    
    # Check stock
    checker = get_stock_checker()
    stock_info = checker.check_stock(fav.product_url, fav.product_id, fav.retailer)
    
    # Update favorite
    fav.stock_status = stock_info['status']
    fav.stock_level = stock_info.get('level')
    fav.last_stock_check = datetime.utcnow()
    db.commit()
    
    return {
        "product": fav.title,
        "stock_status": stock_info['status'],
        "stock_level": stock_info.get('level'),
        "text": stock_info.get('text'),
        "method": stock_info.get('method')
    }

# AI Tracking System
from tracking_endpoints import router as tracking_router
app.include_router(tracking_router)

# Recommendation System
from recommendation_endpoints import router as recommendation_router
app.include_router(recommendation_router)

# Creator System
from creator_endpoints import router as creator_router
from canvas_endpoints import router as canvas_router
from styling_endpoints import router as styling_router
from extraction_endpoints import router as extraction_router
from vto_endpoints import router as vto_router
app.include_router(creator_router)
app.include_router(canvas_router)
app.include_router(styling_router)
app.include_router(extraction_router)
app.include_router(vto_router)

# Custom image serving with CORS headers
from fastapi.responses import FileResponse

@app.get("/images/wardrobe/{filename}")
async def serve_wardrobe_image(filename: str):
    file_path = Path(f"uploads/wardrobe/{filename}")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(
        file_path,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ============ OUTFIT QUEUE SYSTEM ============
from outfit_queue import create_queue, get_queue, delete_queue, QueuedItem, UploadQueue
from sam3_service import get_sam3_service

@app.post("/wardrobe/upload-smart")
async def upload_wardrobe_smart(
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Smart upload - handles both single items and full outfits
    Returns first item + queue info if outfit detected
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file bytes
    file_bytes = await file.read()
    
    # Save original temporarily for Gemini analysis
    upload_dir = Path("uploads/wardrobe")
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_filename = f"temp_analyze_{uuid.uuid4()}.png"
    temp_path = upload_dir / temp_filename
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
    
    # Analyze with Gemini (ONE call - detects type + all items)
    vision = get_vision_service()
    analysis = vision.analyze_upload(str(temp_path))
    
    print(f"Gemini analysis: {analysis}")
    
    image_type = analysis.get("type", "single_item")
    items = analysis.get("items", [])
    
    if not items:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not detect clothing items")
    
    # SINGLE ITEM - process normally
    if image_type == "single_item" or len(items) == 1:
        temp_path.unlink(missing_ok=True)
        
        # Remove background
        processed_bytes = await process_single_item(file_bytes)
        
        # Save to file
        unique_filename = f"{uuid.uuid4()}.png"
        final_path = upload_dir / unique_filename
        with open(final_path, "wb") as f:
            f.write(processed_bytes)
        
        image_url = f"https://yow-api.onrender.com/uploads/wardrobe/{unique_filename}"
        item_info = items[0]
        
        return {
            "type": "single_item",
            "queue_id": None,
            "total_items": 1,
            "current_index": 0,
            "item": {
                "image_url": image_url,
                "category": item_info.get("category", "unknown"),
                "description": item_info.get("description", "unknown"),
                "color": item_info.get("color", "unknown")
            }
        }
    
    # OUTFIT - segment with SAM 3 and create queue
    print(f"Outfit detected with {len(items)} items, segmenting with SAM 3...")
    
    sam3 = get_sam3_service()
    queued_items = []
    
    for item_info in items:
        label = item_info.get("label", "clothing")
        description = item_info.get("description", "unknown item")
        
        # Call SAM 3 to segment this item
        seg_result = await sam3.segment_item(file_bytes, label)
        
        if seg_result["success"]:
            # Extract the segmented image
            extracted_bytes = await extract_mask_from_result(file_bytes, seg_result["result"], category=item_info.get("category", ""))
            
            if extracted_bytes:
                queued_items.append(QueuedItem(
                    image_bytes=extracted_bytes,
                    description=description,
                    category=item_info.get("category", "unknown"),
                    color=item_info.get("color", "unknown")
                ))
                print(f"  ✓ Segmented: {description}")
            else:
                print(f"  ✗ Failed to extract: {description}")
        else:
            print(f"  ✗ SAM 3 failed for: {description}")
    
    temp_path.unlink(missing_ok=True)
    
    if not queued_items:
        raise HTTPException(status_code=400, detail="Could not segment any items from outfit")
    
    # Create queue
    queue = create_queue(user.id, queued_items)
    
    # Save first item to file and return it
    first_item = queue.get_current()
    unique_filename = f"{uuid.uuid4()}.png"
    final_path = upload_dir / unique_filename
    with open(final_path, "wb") as f:
        f.write(first_item.image_bytes)
    
    image_url = f"https://yow-api.onrender.com/uploads/wardrobe/{unique_filename}"
    
    return {
        "type": "outfit",
        "queue_id": queue.queue_id,
        "total_items": queue.total_items,
        "current_index": 0,
        "item": {
            "image_url": image_url,
            "category": first_item.category,
            "description": first_item.description,
            "color": first_item.color
        }
    }


@app.post("/wardrobe/save-and-next")
async def save_and_next_item(
    queue_id: str,
    category: str,
    description: str,
    color: str,
    image_url: str,
    brand: str = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Save current item to wardrobe and get next item from queue"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Save item to database
    item = WardrobeItem(
        user_id=user.id,
        image_url=image_url,
        category=category,
        color=color,
        fabric=description,  # Using fabric field for description
        pattern='',
        style_tags='[]',
        brand=brand or '',
        user_edited=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    # Get queue and advance
    queue = get_queue(queue_id, user.id)
    
    if not queue:
        return {
            "saved_item_id": item.id,
            "has_next": False,
            "next_item": None
        }
    
    # Advance to next item
    next_queued = queue.advance()
    
    if not next_queued:
        delete_queue(queue_id)
        return {
            "saved_item_id": item.id,
            "has_next": False,
            "next_item": None
        }
    
    # Save next item to file
    upload_dir = Path("uploads/wardrobe")
    unique_filename = f"{uuid.uuid4()}.png"
    final_path = upload_dir / unique_filename
    with open(final_path, "wb") as f:
        f.write(next_queued.image_bytes)
    
    next_image_url = f"https://yow-api.onrender.com/uploads/wardrobe/{unique_filename}"
    
    return {
        "saved_item_id": item.id,
        "has_next": True,
        "queue_id": queue_id,
        "total_items": queue.total_items,
        "current_index": queue.current_index,
        "next_item": {
            "image_url": next_image_url,
            "category": next_queued.category,
            "description": next_queued.description,
            "color": next_queued.color
        }
    }


@app.post("/wardrobe/skip-item")
async def skip_item(
    queue_id: str,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Skip current item without saving and get next item"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    queue = get_queue(queue_id, user.id)
    
    if not queue:
        return {"has_next": False, "next_item": None}
    
    # Advance to next item
    next_queued = queue.advance()
    
    if not next_queued:
        delete_queue(queue_id)
        return {"has_next": False, "next_item": None}
    
    # Save next item to file
    upload_dir = Path("uploads/wardrobe")
    unique_filename = f"{uuid.uuid4()}.png"
    final_path = upload_dir / unique_filename
    with open(final_path, "wb") as f:
        f.write(next_queued.image_bytes)
    
    next_image_url = f"https://yow-api.onrender.com/uploads/wardrobe/{unique_filename}"
    
    return {
        "has_next": True,
        "queue_id": queue_id,
        "total_items": queue.total_items,
        "current_index": queue.current_index,
        "next_item": {
            "image_url": next_image_url,
            "category": next_queued.category,
            "description": next_queued.description,
            "color": next_queued.color
        }
    }


# Helper functions
async def process_single_item(file_bytes: bytes) -> bytes:
    """Remove background from single item"""
    try:
        from rembg import remove, new_session
        from PIL import Image
        from io import BytesIO
        
        input_image = Image.open(BytesIO(file_bytes))
        session = new_session(model_name='isnet-general-use')
        
        output_image = remove(
            input_image,
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=270,
            alpha_matting_background_threshold=20,
            alpha_matting_erode_size=15
        )
        
        if output_image.mode != 'RGBA':
            output_image = output_image.convert('RGBA')
        
        # Crop to content
        bbox = output_image.getbbox()
        if bbox:
            output_image = output_image.crop(bbox)
        
        output_buffer = BytesIO()
        output_image.save(output_buffer, format='PNG', optimize=True)
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"Background removal failed: {e}")
        return file_bytes


async def extract_mask_from_result(original_bytes: bytes, sam_result: dict, category: str = "") -> bytes:
    """Extract segmented item from SAM 3 result - combines paired items (shoes, gloves)"""
    from PIL import Image, ImageDraw
    from io import BytesIO
    
    # Categories that come in pairs
    PAIRED_CATEGORIES = ["footwear", "shoes", "gloves"]
    
    try:
        img = Image.open(BytesIO(original_bytes)).convert("RGBA")
        orig_width, orig_height = img.size
        
        if "prompt_results" in sam_result and len(sam_result["prompt_results"]) > 0:
            prompt_result = sam_result["prompt_results"][0]
            predictions = prompt_result.get("predictions", [])
            
            if predictions:
                # Check if this is a paired category
                category_lower = category.lower()
                is_paired = any(paired in category_lower for paired in PAIRED_CATEGORIES)
                
                mask = Image.new("L", (orig_width, orig_height), 0)
                draw = ImageDraw.Draw(mask)
                
                if is_paired:
                    # Combine all high-confidence predictions (for shoes, gloves)
                    print(f"Paired category {category} - combining {len(predictions)} predictions")
                    for pred in predictions:
                        confidence = pred.get("confidence", 0)
                        if confidence > 0.5 and "masks" in pred:
                            for polygon in pred["masks"]:
                                if len(polygon) >= 20:
                                    poly_points = [(p[0], p[1]) for p in polygon]
                                    draw.polygon(poly_points, fill=255)
                else:
                    # Single item - use highest confidence prediction
                    best_pred = max(predictions, key=lambda p: p.get("confidence", 0))
                    confidence = best_pred.get("confidence", 0)
                    print(f"Extracting mask: {orig_width}x{orig_height}, Confidence: {confidence:.2f}")
                    if "masks" in best_pred:
                        for polygon in best_pred["masks"]:
                            if len(polygon) >= 20:
                                poly_points = [(p[0], p[1]) for p in polygon]
                                draw.polygon(poly_points, fill=255)
                
                result = Image.new("RGBA", (orig_width, orig_height), (0, 0, 0, 0))
                result.paste(img, mask=mask)
                
                bbox = result.getbbox()
                if bbox:
                    result = result.crop(bbox)
                
                output = BytesIO()
                result.save(output, format="PNG")
                return output.getvalue()
        
        return None
        
    except Exception as e:
        print(f"Mask extraction error: {e}")
        return None
        return None


@app.post("/wardrobe/prettify")
async def prettify_item(
    image_url: str,
    authorization: str = Header(None)
):
    """Prettify a segmented garment image using Gemini"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    db = next(get_db())
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from gemini_prettify import GeminiPrettify
    import httpx
    
    try:
        # Download the image
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            image_bytes = response.content
        
        # Save temporarily
        temp_path = f"uploads/temp_{uuid.uuid4()}.png"
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        
        # Prettify
        prettifier = GeminiPrettify()
        result = prettifier.prettify(temp_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        if result is None:
            raise HTTPException(status_code=500, detail="Prettify failed")
        
        # Save result
        upload_dir = Path("uploads/prettified")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.png"
        result_path = upload_dir / filename
        result.save(result_path, "PNG")
        
        prettified_url = f"https://yow-api.onrender.com/uploads/prettified/{filename}"
        
        return {
            "success": True,
            "prettified_url": prettified_url,
            "cost": 0.015
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prettify error: {str(e)}")


# Updated prettify endpoint with description/category
@app.post("/wardrobe/prettify-v2")
async def prettify_item_v2(
    image_url: str,
    description: str = "garment",
    category: str = "clothing",
    authorization: str = Header(None)
):
    """Prettify a segmented garment image using Gemini with description context"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    db = next(get_db())
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from gemini_prettify import GeminiPrettify
    import httpx
    
    try:
        # Download the image
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            image_bytes = response.content
        
        # Save temporarily
        temp_path = f"uploads/temp_{uuid.uuid4()}.png"
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        
        # Prettify with description context
        prettifier = GeminiPrettify()
        result = prettifier.prettify(temp_path, description=description, category=category)
        
        # Clean up temp file
        os.remove(temp_path)
        
        if result is None:
            raise HTTPException(status_code=500, detail="Prettify failed")
        
        # Remove white background with rembg for transparent PNG
        from rembg import remove
        from io import BytesIO
        
        img_buffer = BytesIO()
        result.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        transparent_bytes = remove(img_buffer.read())
        result = Image.open(BytesIO(transparent_bytes))
        
        # Save result as PNG
        upload_dir = Path("uploads/prettified")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.png"
        result_path = upload_dir / filename
        result.save(result_path, "PNG")
        
        prettified_url = f"https://yow-api.onrender.com/uploads/prettified/{filename}"
        
        return {
            "success": True,
            "prettified_url": prettified_url,
            "cost": 0.015
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prettify error: {str(e)}")


# ==================== ACCESSORY OVERLAY SYSTEM ====================
# Sequential overlay: Add 2 accessories per call, chain results

@app.post("/vto/overlay-accessories")
async def overlay_accessories(
    authorization: str = Header(None)
):
    """
    Add accessories to existing VTO image
    Uses the proven 2+1+1 pattern for up to 4 accessories
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(' ')[1]
    db = next(get_db())
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    import base64
    from io import BytesIO
    
    data = await request.json()
    base_b64 = data.get('base_image_base64')
    accessory_images_b64 = data.get('accessory_images_base64', [])
    
    if not base_b64 or not accessory_images_b64:
        raise HTTPException(status_code=400, detail="Missing base image or accessories")
    
    count = len(accessory_images_b64)
    
    # The proven prompt
    prompt = f"""CRITICAL INSTRUCTION: You are doing an OVERLAY task, NOT generating a new image.

IMAGE 1 is the BASE. You must keep this image's EXACT dimensions, framing, and aspect ratio. The person's FULL BODY from head to feet must remain visible EXACTLY as shown.

DO NOT:
- Crop or cut off the bottom (feet must stay visible)
- Zoom in or reframe
- Change the person's pose, face, hair, or body
- Modify the original clothing
- Alter the background

DO:
- Add the {count} accessory items naturally on top of the existing image
- Match lighting and shadows
- Position accessories realistically (sunglasses on face, bag in hand/shoulder)

This is like placing stickers on a photo - the photo stays identical, you just add items on top."""

    try:
        # Decode images
        base_image = Image.open(BytesIO(base64.b64decode(base_b64)))
        accessory_images = [Image.open(BytesIO(base64.b64decode(acc))) for acc in accessory_images_b64]
        
        # Use Gemini 2.5 Flash Image
        model = genai.GenerativeModel('gemini-2.5-flash-image')
        
        # Build content array
        content_array = [prompt, base_image] + accessory_images
        
        response = model.generate_content(content_array)
        
        # Extract image
        if hasattr(response, 'candidates') and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data.data:
                    result_b64 = base64.b64encode(part.inline_data.data).decode()
                    return {
                        "success": True,
                        "result_image_base64": result_b64,
                        "cost": 0.04
                    }
        
        raise HTTPException(status_code=500, detail="No image generated")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overlay error: {str(e)}")






# ==================== VTO TEST ENDPOINT ====================
import google.generativeai as genai_vto

@app.post("/vto/test-generate")
async def vto_test_generate(req: Request):
    """
    Test VTO endpoint - no auth, accepts URLs
    DELETE THIS BEFORE PRODUCTION
    """
    import httpx
    import base64
    from io import BytesIO
    import os
    
    # Configure Gemini
    genai_vto.configure(api_key=os.getenv('GEMINI_API_KEY'))
    
    data = await req.json()
    base_model_url = data.get('base_model_url')
    garment_urls = data.get('garment_urls', [])
    
    if not base_model_url or not garment_urls:
        raise HTTPException(status_code=400, detail="Missing base_model_url or garment_urls")
    
    try:
        # Download all images with longer timeout
        async with httpx.AsyncClient(timeout=60.0) as client:
            base_resp = await client.get(base_model_url)
            base_image = Image.open(BytesIO(base_resp.content))
            
            garment_images = []
            for url in garment_urls[:4]:
                resp = await client.get(url)
                garment_images.append(Image.open(BytesIO(resp.content)))
        
        # Build prompt
        prompt = f"""You are a virtual try-on system. 
        
IMAGE 1 is a photo of a person (the model).
IMAGES 2-{len(garment_images)+1} are clothing items.

Generate a NEW photo of the SAME person wearing ALL the clothing items.

CRITICAL REQUIREMENTS:
- Keep the person's face, body, and pose EXACTLY the same
- Replace their current clothing with the provided garments
- Make it look photorealistic - natural lighting, proper fit
- Show full body from head to toe
- Maintain the original image dimensions and framing"""

        # Call Gemini
        model = genai_vto.GenerativeModel('gemini-2.5-flash-preview-05-20')
        content_array = [prompt, base_image] + garment_images
        
        response = model.generate_content(content_array)
        
        # Extract result
        if hasattr(response, 'candidates') and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data.data:
                    result_b64 = base64.b64encode(part.inline_data.data).decode()
                    return {
                        "success": True,
                        "result_image_base64": result_b64
                    }
        
        raise HTTPException(status_code=500, detail="No image generated")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"VTO error: {str(e)}")
