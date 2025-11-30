"""
Product Indexer - Build FAISS index from ASOS products for visual search

This script:
1. Fetches products from ASOS API across multiple categories
2. Downloads product images
3. Creates CLIP embeddings for visual similarity
4. Saves to FAISS index for fast visual search

Run: python build_product_index.py
"""
import os
import json
import requests
from io import BytesIO
from PIL import Image
import numpy as np
import faiss
import torch
import open_clip
from tqdm import tqdm
from asos_service import AsosService


# Configuration
CATEGORIES = [
    "dresses", "tops", "jeans", "jackets", "shoes", 
    "bags", "skirts", "trousers", "coats", "jumpers"
]
PRODUCTS_PER_CATEGORY = 50  # Total: ~500 products
OUTPUT_INDEX = "faiss.index"
OUTPUT_META = "faiss_meta.json"


def load_clip_model():
    """Load CLIP model for image encoding"""
    print("Loading CLIP model...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    model.eval()
    device = "cpu"  # Use "cuda" if you have GPU
    model.to(device)
    return model, preprocess, device


def fetch_asos_products(category, limit=50):
    """Fetch products from ASOS for a given category"""
    print(f"\nFetching {limit} products for category: {category}")
    
    asos = AsosService()
    try:
        result = asos.search_products(
            query=category,
            limit=limit,
            country="GB",  # UK for GBP prices
            currency="GBP"
        )
        
        products = []
        for item in result.get("products", []):
            price_data = item.get("price", {}).get("current", {})
            products.append({
                "id": str(item.get("id", "")),
                "title": item.get("name", ""),
                "image": item.get("imageUrl", ""),
                "brand": item.get("brandName", ""),
                "retailer": "ASOS",
                "price": price_data.get("value", 0.0),
                "category": category
            })
        
        print(f"✓ Fetched {len(products)} products")
        return products
    
    except Exception as e:
        print(f"✗ Error fetching {category}: {e}")
        return []


def load_image_from_url(url, timeout=10):
    """Download and load image from URL"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        return img
    except Exception as e:
        print(f"  ✗ Failed to load image: {e}")
        return None


def encode_image(img, model, preprocess, device):
    """Create CLIP embedding for image"""
    try:
        img_tensor = preprocess(img).unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = model.encode_image(img_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding.cpu().numpy().astype("float32")[0]
    except Exception as e:
        print(f"  ✗ Failed to encode image: {e}")
        return None


def build_index():
    """Main function to build FAISS index"""
    
    # Load CLIP model
    model, preprocess, device = load_clip_model()
    
    # Collect products from all categories
    all_products = []
    for category in CATEGORIES:
        products = fetch_asos_products(category, limit=PRODUCTS_PER_CATEGORY)
        all_products.extend(products)
        
        # Be nice to the API - don't hammer it
        import time
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"Total products collected: {len(all_products)}")
    print(f"{'='*60}\n")
    
    # Create embeddings
    embeddings = []
    metadata = []
    
    print("Creating image embeddings...")
    for i, product in enumerate(tqdm(all_products)):
        # Download image
        img = load_image_from_url(product["image"])
        if img is None:
            continue
        
        # Create embedding
        embedding = encode_image(img, model, preprocess, device)
        if embedding is None:
            continue
        
        embeddings.append(embedding)
        metadata.append({
            "id": product["id"],
            "title": product["title"],
            "image": product["image"],
            "brand": product["brand"],
            "retailer": product["retailer"],
            "price": product["price"],
            "category": product["category"]
        })
        
        # Progress update every 50 items
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(all_products)} products")
    
    print(f"\n✓ Successfully encoded {len(embeddings)} products")
    
    # Build FAISS index
    print("\nBuilding FAISS index...")
    embeddings_array = np.array(embeddings).astype('float32')
    
    # Normalize vectors for cosine similarity
    faiss.normalize_L2(embeddings_array)
    
    # Create index
    dimension = embeddings_array.shape[1]  # Should be 512 for CLIP ViT-B-32
    index = faiss.IndexFlatIP(dimension)  # Inner product = cosine similarity for normalized vectors
    index.add(embeddings_array)
    
    print(f"✓ FAISS index created with {index.ntotal} vectors")
    
    # Save index and metadata
    print(f"\nSaving to disk...")
    faiss.write_index(index, OUTPUT_INDEX)
    with open(OUTPUT_META, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Saved index to: {OUTPUT_INDEX}")
    print(f"✓ Saved metadata to: {OUTPUT_META}")
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"INDEX STATISTICS")
    print(f"{'='*60}")
    print(f"Total products indexed: {len(metadata)}")
    print(f"Vector dimensions: {dimension}")
    print(f"Index size: {os.path.getsize(OUTPUT_INDEX) / 1024 / 1024:.2f} MB")
    print(f"Metadata size: {os.path.getsize(OUTPUT_META) / 1024:.2f} KB")
    
    # Category breakdown
    from collections import Counter
    category_counts = Counter(m["category"] for m in metadata)
    print(f"\nProducts per category:")
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count}")
    
    print(f"\n{'='*60}")
    print(f"✓ Index build complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("="*60)
    print("ASOS PRODUCT INDEXER")
    print("="*60)
    print("\nThis will fetch ~500 products from ASOS and build a visual search index.")
    print("This may take 10-15 minutes depending on your internet connection.\n")
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        exit()
    
    build_index()
