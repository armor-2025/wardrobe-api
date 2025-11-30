"""Production VTO API - Simple Version"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import cv2
import uuid
from datetime import datetime

# Import everything from vto_complete_system
import sys
sys.path.insert(0, os.path.dirname(__file__))
from vto_complete_system import VTOSystem, GarmentAnalyzer, UserProfile

app = FastAPI(title="VTO API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "vto_outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROFILES = {}
GARMENTS = {}

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

class GenerateVTORequest(BaseModel):
    user_id: str
    garment_ids: List[str]

@app.get("/")
async def root():
    return {
        "service": "VTO API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.post("/api/profiles/create")
async def create_profile(
    user_id: str,
    body_type: str,
    height: str,
    photo: UploadFile = File(...)
):
    photo_filename = f"{user_id}_{uuid.uuid4()}.jpg"
    photo_path = os.path.join(UPLOAD_DIR, photo_filename)
    
    contents = await photo.read()
    with open(photo_path, "wb") as f:
        f.write(contents)
    
    profile_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "body_type": body_type,
        "height": height,
        "photo_url": photo_path,
        "created_at": datetime.now().isoformat()
    }
    
    PROFILES[user_id] = profile_data
    return profile_data

@app.post("/api/garments/upload")
async def upload_garment(
    user_id: str,
    photo: UploadFile = File(...)
):
    garment_id = str(uuid.uuid4())
    filename = f"{garment_id}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    contents = await photo.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    
    analyzer = get_garment_analyzer()
    analysis = analyzer.analyze_garment(filepath)
    
    garment_data = {
        "id": garment_id,
        "user_id": user_id,
        "source": "user_upload",
        "name": f"My {analysis['category']}",
        "category": analysis['category'],
        "image_url": filepath,
        "description": analysis['description'],
        "created_at": datetime.now().isoformat()
    }
    
    GARMENTS[garment_id] = garment_data
    return garment_data

@app.post("/api/vto/generate")
async def generate_vto(request: GenerateVTORequest):
    if request.user_id not in PROFILES:
        raise HTTPException(404, "Profile not found")
    
    profile_data = PROFILES[request.user_id]
    garments = [GARMENTS[gid] for gid in request.garment_ids if gid in GARMENTS]
    
    if not garments:
        raise HTTPException(404, "No garments found")
    
    descriptions = []
    garment_images = []
    
    for g in garments:
        desc = g.get('description') or g['name']
        category = g['category']
        
        if category == 'dress':
            descriptions.append(f"- Dress: {desc}")
        elif category == 'top':
            descriptions.append(f"- Top: {desc}")
        elif category == 'bottom':
            descriptions.append(f"- Bottoms: {desc}")
        elif category == 'outerwear':
            descriptions.append(f"- Outer layer: {desc}")
        elif category == 'shoes':
            descriptions.append(f"- Footwear: {desc}")
        elif category == 'accessory':
            descriptions.append(f"- Accessory: {desc}")
        
        garment_images.append(g['image_url'])
    
    outfit_description = "\n".join(descriptions)
    
    profile = UserProfile(profile_data['photo_url'], profile_data['body_type'], profile_data['height'])
    
    vto = get_vto_system()
    result = vto.generate_vto_with_retry(profile, garment_images, outfit_description, max_attempts=3)
    
    if result.success:
        result_id = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_DIR, f"{result_id}.png")
        cv2.imwrite(output_path, result.image)
        
        return {"success": True, "image_url": output_path, "attempts": result.attempts}
    else:
        return {"success": False, "attempts": result.attempts, "error": result.get_user_message()}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("Starting VTO API on http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
