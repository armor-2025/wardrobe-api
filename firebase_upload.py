import firebase_admin
from firebase_admin import credentials, storage
import os
import uuid
from io import BytesIO

# Initialize Firebase if not already done
def get_firebase_bucket():
    if not firebase_admin._apps:
        # Use default credentials or service account
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'your-online-wardrobe-jm85cl.firebasestorage.app'
            })
        else:
            # Try default credentials
            firebase_admin.initialize_app(options={
                'storageBucket': 'your-online-wardrobe-jm85cl.firebasestorage.app'
            })
    return storage.bucket()

def upload_image_to_firebase(image_bytes: bytes, folder: str = "prettified") -> str:
    """Upload image bytes to Firebase Storage and return the public URL"""
    bucket = get_firebase_bucket()
    
    filename = f"{folder}/{uuid.uuid4()}.png"
    blob = bucket.blob(filename)
    
    blob.upload_from_string(image_bytes, content_type='image/png')
    blob.make_public()
    
    return blob.public_url
