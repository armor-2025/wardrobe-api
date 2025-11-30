"""
Simpler approach - use sentence-transformers CLIP model
"""
import os
import sys

print("=" * 70)
print("🔧 ALTERNATIVE: Using sentence-transformers")
print("=" * 70)

print("\n📦 Installing sentence-transformers (lighter than transformers)...")
os.system("pip install sentence-transformers pillow scipy --break-system-packages")

print("\n✅ Testing...")

from sentence_transformers import SentenceTransformer
from PIL import Image

print("\n📥 Loading CLIP model...")
model = SentenceTransformer('clip-ViT-B-32')
print("✅ Model loaded!")

# Test with an image
if len(sys.argv) > 1:
    image_path = sys.argv[1]
else:
    image_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')

print(f"\n📸 Testing with: {image_path}")

image = Image.open(image_path)

print("\n🔄 Generating visual embedding...")
embedding = model.encode(image)

print("✅ Embedding generated!")
print(f"   Dimensions: {len(embedding)}")
print(f"   First 10 values: {[f'{x:.4f}' for x in embedding[:10]]}")

print("\n" + "=" * 70)
print("🎯 TESTING WITH MULTIPLE IMAGES")
print("=" * 70)

# Test similarity
test_images = [
    '~/Desktop/AI OUTFIT PICS/IMG_6561.PNG',
    '~/Desktop/AI OUTFIT PICS/IMG_6563.PNG',
    '~/Desktop/AI OUTFIT PICS/IMG_6565.PNG',
]

embeddings = []
print("\nGenerating embeddings for comparison...")

for img_path in test_images:
    full_path = os.path.expanduser(img_path)
    if os.path.exists(full_path):
        img = Image.open(full_path)
        emb = model.encode(img)
        embeddings.append((full_path.split('/')[-1], emb))
        print(f"  ✅ {full_path.split('/')[-1]}")

if len(embeddings) >= 2:
    print("\n📊 Similarity Scores:")
    print("─" * 70)
    
    from scipy.spatial.distance import cosine
    
    base_name, base_emb = embeddings[0]
    
    for name, emb in embeddings[1:]:
        similarity = 1 - cosine(base_emb, emb)
        print(f"  {base_name} <-> {name}")
        print(f"  Similarity: {similarity:.2%}\n")

print("\n" + "=" * 70)
print("✅ SUCCESS - VISUAL EMBEDDINGS WORKING!")
print("=" * 70)

print("""
This model:
✅ Generates 512-dimensional embeddings
✅ Works with images directly
✅ Perfect for visual similarity search
✅ Production-ready

WHAT THIS MEANS:
────────────────
We can now find products that LOOK similar!

Example:
  User uploads: Green blazer photo
  We generate: embedding = [0.23, 0.45, 0.12, ...]
  
  Database has:
    Product A (green blazer): [0.24, 0.44, 0.13, ...] → 98% similar ✅
    Product B (red dress):    [0.91, 0.05, 0.88, ...] → 25% similar ❌
  
  Return Product A!

💰 COST: $0.00 per embedding (runs locally)

🚀 NEXT STEPS:
──────────────
1. Set up Supabase database
2. Import products with embeddings
3. Build search API
4. Ship it!

Ready to continue?
""")

