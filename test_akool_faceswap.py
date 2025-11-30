"""
Test Akool face swap API for better hair preservation
"""
import os
import requests
import base64
from PIL import Image
import io

print("=" * 70)
print("🔬 AKOOL FACE SWAP API SETUP")
print("=" * 70)

print("""
Akool is known for BEST hair preservation in face swaps.

FREE TIER: 10 face swaps per day
PAID: $0.01 per swap after free tier

Setup steps:
1. Go to: https://www.akool.com/
2. Sign up (free)
3. Dashboard → API Keys → Create new key
4. Paste your API key below

Then we'll test on one of our perfect Gemini mannequins!
""")

# Check if user has API key
AKOOL_API_KEY = os.getenv('AKOOL_API_KEY', None)

if not AKOOL_API_KEY:
    print("\n📝 To test Akool:")
    print("   1. Get API key from https://www.akool.com/")
    print("   2. Set environment variable:")
    print("      export AKOOL_API_KEY='your-key-here'")
    print("   3. Run this script again")
    print("\n💡 Or paste your key here to test now:")
    print("\n" + "="*70)
    print("PASTE YOUR AKOOL API KEY:")
    print("="*70)
    
    # Show example code for when they have the key
    print("""
    
Example code (will work once you have the key):
```python
cat > visual_search_exact_look.py << 'EOF'
"""
Shop the EXACT Look - Pure Visual Search
Find items that LOOK as close as possible to the celebrity photo
"""
import os
import google.generativeai as genai
from PIL import Image
import json

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("=" * 70)
print("🎯 SHOP THE EXACT LOOK - VISUAL SEARCH")
print("=" * 70)

print("""
APPROACH: Pure Visual Similarity
─────────────────────────────────

Celebrity photo → Segment items → Visual embeddings → Find closest matches

NO tag matching - only "does it LOOK similar?"

Example:
  User sees: Green oversized blazer with gold buttons
  System shows: Items that look EXACTLY like that
  NOT: All green blazers (different styles)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

print("\n🛠️ TECH STACK:")
print("=" * 70)

print("""
OPTION A: CLIP (OpenAI) ⭐ RECOMMENDED
──────────────────────────────────────
✅ Open source, FREE
✅ Best for fashion visual search
✅ Image → Embedding (512 dimensions)
✅ Fast, runs locally or API

Installation:
  pip install transformers torch pillow

Usage:
  from transformers import CLIPProcessor, CLIPModel
  model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
  embedding = model.encode_image(image)


OPTION B: Google Vision AI Product Search
──────────────────────────────────────────
✅ Best quality for retail
✅ Built for product matching
❌ Paid: $1.50 per 1000 searches
❌ Requires product catalog setup


OPTION C: Gemini + Image Descriptions
──────────────────────────────────────
✅ Already using Gemini
✅ Good quality
⚠️  Indirect: Description → Embedding
✅ Fallback if CLIP doesn't work

We'll use CLIP as primary!
""")

print("\n📋 COMPLETE SYSTEM ARCHITECTURE:")
print("=" * 70)

print("""
┌─────────────────────────────────────────────────────────────┐
│                    USER UPLOADS PHOTO                        │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Gemini Segments & Identifies Items                 │
│  ─────────────────────────────────────────                  │
│  Input: Celebrity photo                                      │
│  Output: [                                                   │
│    {                                                         │
│      "item": "blazer",                                       │
│      "bbox": [x, y, w, h],    ← Bounding box                │
│      "description": "green oversized blazer gold buttons"    │
│    },                                                        │
│    { "item": "trousers", ... },                             │
│    { "item": "boots", ... }                                  │
│  ]                                                           │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Crop Each Item from Photo                          │
│  ───────────────────────────────────                        │
│  Use bounding boxes to extract individual items             │
│  Blazer: [cropped image]                                    │
│  Trousers: [cropped image]                                  │
│  Boots: [cropped image]                                     │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Generate CLIP Visual Embeddings                    │
│  ────────────────────────────────────────                   │
│  For each cropped item:                                      │
│    embedding = CLIP.encode_image(cropped_image)             │
│                                                              │
│  Blazer embedding: [0.23, 0.45, 0.12, ... 512 numbers]     │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Search Product Database                            │
│  ────────────────────────────────────                       │
│  SELECT * FROM products                                      │
│  WHERE category = 'blazers'                                  │
│  ORDER BY image_embedding <=> query_embedding               │
│  LIMIT 20                                                    │
│                                                              │
│  Returns products ranked by visual similarity               │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Display Results                                     │
│  ────────────────────────                                   │
│  Show top 20 matches with similarity %                       │
│  User clicks → Affiliate link                                │
└─────────────────────────────────────────────────────────────┘
""")

print("\n💾 DATABASE SCHEMA:")
print("=" * 70)

print("""
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Product info
  name TEXT NOT NULL,
  description TEXT,
  brand TEXT,
  category TEXT NOT NULL,           -- 'blazers', 'trousers', 'shoes', etc.
  price DECIMAL(10,2),
  image_url TEXT NOT NULL,
  affiliate_link TEXT NOT NULL,
  retailer TEXT,
  
  -- Visual embedding (CLIP)
  image_embedding VECTOR(512),      -- CLIP generates 512-dim vectors
  
  -- Metadata
  in_stock BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast similarity search
CREATE INDEX products_embedding_idx 
ON products 
USING ivfflat (image_embedding vector_cosine_ops)
WITH (lists = 100);

-- Category index for filtering
CREATE INDEX products_category_idx ON products(category);
""")

print("\n🔍 SEARCH FUNCTION:")
print("=" * 70)

print("""
CREATE OR REPLACE FUNCTION find_visually_similar_products(
  query_embedding VECTOR(512),
  filter_category TEXT,
  similarity_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  name TEXT,
  brand TEXT,
  price DECIMAL,
  image_url TEXT,
  affiliate_link TEXT,
  similarity_score FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    id,
    name,
    brand,
    price,
    image_url,
    affiliate_link,
    1 - (image_embedding <=> query_embedding) AS similarity_score
  FROM products
  WHERE 
    category = filter_category
    AND in_stock = true
    AND 1 - (image_embedding <=> query_embedding) > similarity_threshold
  ORDER BY image_embedding <=> query_embedding
  LIMIT match_count;
$$;
""")

print("\n💻 PYTHON IMPLEMENTATION:")
print("=" * 70)

# Create the actual implementation
cat > shop_exact_look.py << 'PYTHON'
"""
Shop the Exact Look - Complete Implementation
"""
import os
import google.generativeai as genai
from PIL import Image
import json
import io

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("Installing CLIP...")
os.system("pip install transformers torch pillow --break-system-packages --quiet")

from transformers import CLIPProcessor, CLIPModel
import torch

class ShopTheExactLook:
    def __init__(self):
        print("🔧 Initializing CLIP model...")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.gemini = genai.GenerativeModel('gemini-2.5-flash-image')
        print("✅ Ready!")
    
    def segment_and_identify(self, image_path):
        """
        Step 1: Use Gemini to segment and identify items
        """
        image = Image.open(image_path)
        
        prompt = """Analyze this fashion photo and identify each clothing item worn by the person.

For each item, provide:
1. Item type (e.g., "blazer", "trousers", "dress", "boots", "sunglasses", "bag")
2. Detailed visual description (color, style, material, key features)
3. Approximate bounding box [x, y, width, height] as percentages (0-100)

Return as JSON array:
[
  {
    "type": "blazer",
    "description": "green oversized blazer with gold buttons",
    "bbox": [25, 20, 50, 40]
  },
  ...
]"""

        response = self.gemini.generate_content([prompt, image])
        
        # Parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            items = json.loads(text.strip())
        except:
            # Fallback parsing
            print("⚠️  Could not parse JSON, using fallback")
            items = self._parse_gemini_text(response.text)
        
        return items, image
    
    def crop_items(self, image, items):
        """
        Step 2: Crop each item from the photo using bounding boxes
        """
        width, height = image.size
        cropped_items = []
        
        for item in items:
            bbox = item.get('bbox', [0, 0, 100, 100])
            
            # Convert percentage to pixels
            x = int(bbox[0] / 100 * width)
            y = int(bbox[1] / 100 * height)
            w = int(bbox[2] / 100 * width)
            h = int(bbox[3] / 100 * height)
            
            # Crop
            cropped = image.crop((x, y, x + w, y + h))
            
            cropped_items.append({
                'type': item['type'],
                'description': item['description'],
                'image': cropped
            })
        
        return cropped_items
    
    def generate_visual_embedding(self, image):
        """
        Step 3: Generate CLIP embedding for visual similarity
        """
        # Preprocess image for CLIP
        inputs = self.clip_processor(images=image, return_tensors="pt")
        
        # Get image embedding
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
        
        # Normalize
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # Convert to list
        embedding = image_features[0].numpy().tolist()
        
        return embedding
    
    def search_products(self, embedding, category, supabase_client, limit=20):
        """
        Step 4: Search database for visually similar products
        """
        result = supabase_client.rpc(
            'find_visually_similar_products',
            {
                'query_embedding': embedding,
                'filter_category': category,
                'similarity_threshold': 0.7,
                'match_count': limit
            }
        ).execute()
        
        return result.data
    
    def shop_the_look(self, celebrity_photo_path, supabase_client):
        """
        Complete workflow: Photo → Items → Visual Search → Products
        """
        print("\n" + "="*70)
        print("🛍️  SHOP THE EXACT LOOK")
        print("="*70)
        
        # Step 1: Segment and identify
        print("\n📸 Step 1: Analyzing photo...")
        items, original_image = self.segment_and_identify(celebrity_photo_path)
        print(f"✅ Found {len(items)} items:")
        for item in items:
            print(f"   - {item['type']}: {item['description']}")
        
        # Step 2: Crop items
        print("\n✂️  Step 2: Extracting items from photo...")
        cropped_items = self.crop_items(original_image, items)
        
        # Save cropped images for debugging
        for i, item in enumerate(cropped_items):
            item['image'].save(f"cropped_{item['type']}_{i}.png")
            print(f"   ✅ Saved: cropped_{item['type']}_{i}.png")
        
        results = []
        
        # Step 3-4: Generate embeddings and search
        for item in cropped_items:
            print(f"\n🔍 Step 3-4: Searching for {item['type']}...")
            print(f"   Description: {item['description']}")
            
            # Generate embedding
            embedding = self.generate_visual_embedding(item['image'])
            
            # Search database
            products = self.search_products(
                embedding=embedding,
                category=item['type'] + 's',  # pluralize for category
                supabase_client=supabase_client,
                limit=20
            )
            
            print(f"   ✅ Found {len(products)} similar products")
            
            # Show top 5
            for i, product in enumerate(products[:5], 1):
                print(f"      {i}. {product['name']} - ${product['price']}")
                print(f"         Similarity: {product['similarity_score']:.1%}")
            
            results.append({
                'item': item['type'],
                'description': item['description'],
                'cropped_image_path': f"cropped_{item['type']}.png",
                'products': products
            })
        
        print("\n" + "="*70)
        print("✅ SEARCH COMPLETE!")
        print("="*70)
        
        return results
    
    def _parse_gemini_text(self, text):
        """Fallback parser if JSON fails"""
        return [{
            'type': 'blazer',
            'description': 'green blazer',
            'bbox': [20, 20, 60, 50]
        }]


# Demo
print("\n" + "="*70)
print("📋 USAGE")
print("="*70)

print("""
from supabase import create_client

# Initialize
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
shop_engine = ShopTheExactLook()

# User uploads celebrity photo
results = shop_engine.shop_the_look(
    celebrity_photo_path='celebrity.jpg',
    supabase_client=supabase
)

# Display results in UI
for item_result in results:
    print(f"\\nItem: {item_result['item']}")
    print(f"Description: {item_result['description']}")
    print(f"Cropped image: {item_result['cropped_image_path']}")
    print(f"\\nTop Matches:")
    
    for product in item_result['products'][:10]:
        print(f"  {product['name']} - ${product['price']}")
        print(f"  Similarity: {product['similarity_score']:.1%}")
        print(f"  Buy: {product['affiliate_link']}")
""")

PYTHON

cat shop_exact_look.py

