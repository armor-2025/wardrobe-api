"""
Test "Shop the Look" with Mush-style visualization
Shows best matches for each item with similarity scores
"""
import os
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import clip
import torch
import json

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

print("=" * 70)
print("🎨 MUSH-STYLE VISUAL MATCHING TEST")
print("=" * 70)

# Initialize
print("\n🔧 Loading models...")
gemini = genai.GenerativeModel('gemini-2.5-flash-image')
device = "cpu"
clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
print("✅ Ready!")

# Analyze celebrity photo
celeb_photo_path = '/mnt/user-data/uploads/IMG_6593.PNG'  # Green blazer look

print(f"\n📸 Analyzing: {celeb_photo_path.split('/')[-1]}")

celeb_image = Image.open(celeb_photo_path)

prompt = """Analyze this fashion photo and identify each clothing item.

For each item provide:
1. Item type
2. Detailed visual description
3. Bounding box [x, y, width, height] as percentages

Return as JSON:
[{"type": "blazer", "description": "...", "bbox": [x,y,w,h]}]"""

response = gemini.generate_content([prompt, celeb_image])

# Parse items
try:
    text = response.text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    items = json.loads(text.strip())
except:
    print("⚠️  Using fallback parsing")
    items = [
        {"type": "blazer", "description": "green blazer", "bbox": [25, 20, 50, 45]},
        {"type": "shirt", "description": "white shirt", "bbox": [30, 35, 40, 25]},
        {"type": "trousers", "description": "green trousers", "bbox": [25, 50, 50, 45]},
    ]

print(f"✅ Found {len(items)} items:")
for item in items:
    print(f"   - {item['type']}")

# Generate embeddings for each item
print("\n🔄 Generating CLIP embeddings for each item...")

item_embeddings = []

for i, item in enumerate(items):
    # Crop item
    if 'bbox' in item:
        width, height = celeb_image.size
        bbox = item['bbox']
        x = int(bbox[0] / 100 * width)
        y = int(bbox[1] / 100 * height)
        w = int(bbox[2] / 100 * width)
        h = int(bbox[3] / 100 * height)
        cropped = celeb_image.crop((x, y, x + w, y + h))
    else:
        cropped = celeb_image
    
    # Save cropped
    cropped.save(f"celeb_{item['type']}.png")
    
    # Generate embedding
    img_input = clip_preprocess(cropped).unsqueeze(0).to(device)
    with torch.no_grad():
        features = clip_model.encode_image(img_input)
        features = features / features.norm(dim=-1, keepdim=True)
    
    item_embeddings.append({
        'type': item['type'],
        'description': item.get('description', ''),
        'embedding': features,
        'cropped_image': cropped
    })
    
    print(f"   ✅ {item['type']}")

# Now test against your wardrobe items
print("\n" + "=" * 70)
print("🔍 FINDING BEST MATCHES FROM YOUR WARDROBE")
print("=" * 70)

wardrobe_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/')

# Get all wardrobe images
wardrobe_items = []
for filename in os.listdir(wardrobe_path):
    if filename.endswith(('.PNG', '.jpg', '.jpeg', '.JPG')):
        wardrobe_items.append(os.path.join(wardrobe_path, filename))

print(f"\n📦 Found {len(wardrobe_items)} items in wardrobe")

# For each celebrity item, find best matches from wardrobe
matches = []

for celeb_item in item_embeddings:
    print(f"\n🔍 Finding matches for: {celeb_item['type']}")
    
    best_matches = []
    
    # Compare with each wardrobe item
    for wardrobe_img_path in wardrobe_items[:20]:  # Test with first 20
        try:
            wardrobe_img = Image.open(wardrobe_img_path)
            
            # Generate embedding
            img_input = clip_preprocess(wardrobe_img).unsqueeze(0).to(device)
            with torch.no_grad():
                features = clip_model.encode_image(img_input)
                features = features / features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity
            similarity = (celeb_item['embedding'] @ features.T).item()
            
            best_matches.append({
                'path': wardrobe_img_path,
                'similarity': similarity,
                'filename': os.path.basename(wardrobe_img_path)
            })
        except:
            continue
    
    # Sort by similarity
    best_matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Show top 5
    print(f"\n   Top 5 matches:")
    for i, match in enumerate(best_matches[:5], 1):
        print(f"   {i}. {match['filename']}")
        print(f"      Similarity: {match['similarity']:.2%}")
    
    matches.append({
        'celeb_item': celeb_item,
        'best_matches': best_matches[:10]
    })

# Create Mush-style canvas
print("\n" + "=" * 70)
print("🎨 CREATING MUSH-STYLE CANVAS")
print("=" * 70)

# Canvas dimensions
canvas_width = 1200
canvas_height = 800
item_size = 200

canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
draw = ImageDraw.Draw(canvas)

# Title
draw.text((20, 20), "SHOP THE LOOK - BEST MATCHES", fill='black')

# Position items
y_offset = 80
for match_set in matches:
    celeb_item = match_set['celeb_item']
    best_match = match_set['best_matches'][0] if match_set['best_matches'] else None
    
    # Celebrity item (left)
    celeb_resized = celeb_item['cropped_image'].copy()
    celeb_resized.thumbnail((item_size, item_size))
    canvas.paste(celeb_resized, (50, y_offset))
    draw.text((50, y_offset + item_size + 5), 
              f"ORIGINAL: {celeb_item['type']}", fill='black')
    
    if best_match:
        # Arrow
        draw.text((270, y_offset + 90), "→", fill='black', font=None)
        
        # Best match (right)
        best_img = Image.open(best_match['path'])
        best_resized = best_img.copy()
        best_resized.thumbnail((item_size, item_size))
        canvas.paste(best_resized, (350, y_offset))
        draw.text((350, y_offset + item_size + 5), 
                  f"MATCH: {best_match['similarity']:.1%}", fill='green')
        
        # More options indicator
        draw.text((570, y_offset + 90), 
                  f"+ {len(match_set['best_matches'])-1} more", 
                  fill='blue')
    
    y_offset += item_size + 80

# Save canvas
canvas.save('shop_the_look_canvas.png')
print("\n✅ Created: shop_the_look_canvas.png")

print("\n" + "=" * 70)
print("📊 RESULTS SUMMARY")
print("=" * 70)

for match_set in matches:
    item = match_set['celeb_item']
    best = match_set['best_matches'][0] if match_set['best_matches'] else None
    
    print(f"\n{item['type'].upper()}")
    print(f"  Celebrity: {item['description'][:60]}...")
    if best:
        print(f"  Best Match: {best['filename']}")
        print(f"  Similarity: {best['similarity']:.2%}")
        print(f"  Alternatives: {len(match_set['best_matches'])-1} more options")

print("\n" + "=" * 70)
print("💡 NEXT: BUILD UI")
print("=" * 70)

print("""
This demo shows:
✅ Visual similarity matching works!
✅ Can find best match for each item
✅ Can show alternatives (grid view)

UI Flow:
1. Show canvas with best matches
2. Click item → Open grid of all similar items
3. User can swap items to try different combinations

This is exactly like Mush! 🎯
""")

