"""
Install CLIP and test visual embeddings
"""
import os
import sys

print("=" * 70)
print("🔧 INSTALLING CLIP")
print("=" * 70)

print("\n📦 Installing required packages...")
print("This may take 2-3 minutes for first-time installation...\n")

# Install CLIP dependencies
os.system("pip install transformers torch torchvision pillow --break-system-packages")

print("\n✅ Installation complete!")
print("\n🧪 Testing CLIP...")

from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

print("\n📥 Loading CLIP model (first time downloads ~500MB)...")
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

print("\n" + "=" * 70)
print("🎯 HOW VISUAL SEARCH WORKS")
print("=" * 70)

print("""
SIMILARITY CALCULATION:

Imagine 2 products:

Product A: Green blazer (similar to our image)
  Embedding: [0.23, 0.45, 0.12, ..., 0.89]
  
Product B: Red dress (different)
  Embedding: [0.91, 0.05, 0.88, ..., 0.15]

Our query image:
  Embedding: [0.25, 0.43, 0.14, ..., 0.87]

Similarity Score (cosine similarity):
  Query <-> Product A: 0.95 (95% similar) ✅
  Query <-> Product B: 0.32 (32% similar) ❌

Database returns Product A first because it's most similar!

This works because CLIP "understands" visual features:
- Colors, shapes, textures
- Style, cut, silhouette  
- Materials, patterns
- Overall aesthetic
""")

print("\n" + "=" * 70)
print("💾 DATABASE SETUP")
print("=" * 70)

print("""
Now we need to:

1. Create Supabase account
2. Create products table with vector column
3. Import products with CLIP embeddings
4. Build search API

Ready to continue? Here's what each step involves:

STEP 1: Supabase Setup (5 min)
────────────────────────────────
- Sign up at supabase.com (free)
- Create new project
- Enable pgvector extension
- Create products table

STEP 2: Product Import (variable time)
───────────────────────────────────────
- Connect to Rakuten/affiliate APIs
- For each product:
  * Download image
  * Generate CLIP embedding
  * Store in Supabase
- Could process 1000 products in ~30 min

STEP 3: Search API (2-3 hours)
───────────────────────────────
- Endpoint: POST /api/shop-the-look
- Input: Celebrity photo
- Process: 
  * Gemini segments items
  * CLIP generates embeddings
  * Query Supabase for matches
- Output: Similar products

Want me to help with any of these steps?
""")

print("\n💰 COST SUMMARY:")
print("=" * 70)
print("""
Per "Shop the Look" search:
- Gemini analysis: $0.10
- CLIP embeddings: $0.00 (runs locally)
- Supabase queries: $0.00 (free tier)
────────────────────────────────
TOTAL: $0.10 per search

With affiliate commissions:
- Average order: $200
- Commission: 10% = $20
- Your cost: $0.10
- Profit: $19.90 per conversion! 💰
""")

