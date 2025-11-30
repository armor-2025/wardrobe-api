"""
Install CLIP and test visual embeddings (with safetensors)
"""
import os
import sys

print("=" * 70)
print("🔧 INSTALLING CLIP (Safe Version)")
print("=" * 70)

print("\n📦 Installing required packages...")

# Install with safetensors support
os.system("pip install transformers torch torchvision pillow safetensors --break-system-packages")

print("\n✅ Installation complete!")
print("\n🧪 Testing CLIP with safetensors...")

from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

print("\n📥 Loading CLIP model with safetensors...")
try:
    # Force use of safetensors
    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32",
        use_safetensors=True
    )
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("✅ CLIP loaded successfully!")
except Exception as e:
    print(f"⚠️  Error: {e}")
    print("\nTrying alternative approach...")
    
    # Try upgrading torch
    print("Upgrading PyTorch to latest version...")
    os.system("pip install --upgrade torch torchvision --break-system-packages")
    
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("✅ CLIP loaded!")

# Test with an image
if len(sys.argv) > 1:
    image_path = sys.argv[1]
else:
    image_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')

print(f"\n📸 Testing with: {image_path}")

image = Image.open(image_path)

print("\n🔄 Generating visual embedding...")

# Process image
inputs = processor(images=image, return_tensors="pt")

# Generate embedding
with torch.no_grad():
    image_features = model.get_image_features(**inputs)

# Normalize
image_features = image_features / image_features.norm(dim=-1, keepdim=True)

# Convert to list
embedding = image_features[0].numpy().tolist()

print("✅ Embedding generated!")
print(f"   Dimensions: {len(embedding)}")
print(f"   First 10 values: {[f'{x:.4f}' for x in embedding[:10]]}")

# Save embedding to file for inspection
import json
with open('test_embedding.json', 'w') as f:
    json.dump({
        'image': image_path,
        'embedding_dim': len(embedding),
        'embedding': embedding[:50]  # Save first 50 values
    }, f, indent=2)

print("\n💾 Saved test embedding to: test_embedding.json")

print("\n" + "=" * 70)
print("🎯 TESTING SIMILARITY")
print("=" * 70)

# Test with multiple images to show similarity
test_images = [
    ('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG', 'Woman in blouse'),
    ('~/Desktop/AI OUTFIT PICS/IMG_6563.PNG', 'Red dress'),
    ('~/Desktop/AI OUTFIT PICS/IMG_6565.PNG', 'Green dress'),
]

embeddings = []

print("\nGenerating embeddings for comparison...")

for img_path, desc in test_images:
    full_path = os.path.expanduser(img_path)
    if os.path.exists(full_path):
        img = Image.open(full_path)
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        embeddings.append((desc, features))
        print(f"  ✅ {desc}")

if len(embeddings) >= 2:
    print("\n📊 Similarity Scores:")
    print("─" * 70)
    
    # Calculate cosine similarity between images
    from torch.nn.functional import cosine_similarity
    
    base_desc, base_emb = embeddings[0]
    
    for desc, emb in embeddings[1:]:
        similarity = cosine_similarity(base_emb, emb).item()
        print(f"  {base_desc} <-> {desc}")
        print(f"  Similarity: {similarity:.2%}")
        print()

print("\n" + "=" * 70)
print("💡 HOW THIS WORKS IN PRODUCTION")
print("=" * 70)

print("""
When a user uploads a celebrity photo:

1. Gemini segments items → "green blazer", "white shirt", etc.

2. For each item, CLIP generates embedding:
   green_blazer_embedding = [0.23, 0.45, ...]

3. Search database for similar products:
   SELECT *, 
          1 - (image_embedding <=> [0.23, 0.45, ...]) as similarity
   FROM products
   WHERE category = 'blazers'
   ORDER BY similarity DESC
   LIMIT 20

4. Return products with highest similarity scores

Products that LOOK similar will have high similarity scores!
""")

print("\n" + "=" * 70)
print("🚀 READY FOR PRODUCTION")
print("=" * 70)

print("""
✅ CLIP working
✅ Can generate visual embeddings
✅ Can calculate similarity

Next steps:
A) Set up Supabase database
B) Build product import script  
C) Create search API
D) All of the above

Which do you want to tackle first?
""")

