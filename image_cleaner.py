"""Clean garment images - remove UI elements"""
from PIL import Image
import io


def smart_garment_crop(image_bytes: bytes) -> bytes:
    """Crop to center, remove UI edges"""
    
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    
    # Remove 10% from each edge to eliminate UI
    crop_percent = 0.10
    
    left = int(width * crop_percent)
    top = int(height * crop_percent)
    right = int(width * (1 - crop_percent))
    bottom = int(height * (1 - crop_percent))
    
    cropped = img.crop((left, top, right, bottom))
    
    # Resize if too large
    max_size = 1024
    if max(cropped.size) > max_size:
        ratio = max_size / max(cropped.size)
        new_size = (int(cropped.width * ratio), int(cropped.height * ratio))
        cropped = cropped.resize(new_size, Image.Resampling.LANCZOS)
    
    output = io.BytesIO()
    cropped.save(output, format='PNG', quality=95)
    return output.getvalue()
