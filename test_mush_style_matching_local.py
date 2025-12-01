"""
Test "Shop the Look" with Mush-style visualization
Shows best matches for each item with similarity scores
"""
import os
import sys
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

# Use a local image
if len(sys.argv) > 1:
    celeb_photo_path = sys.argv[1]
else:
    # Use one of your existing photos as the "celebrity look"
    celeb_photo_path = os.path.expanduser('~/Desktop/AI OUTFIT PICS/IMG_6561.PNG')

print(f"\n📸 Analyzing: {celeb_photo_path.split('/')[-1]}")

if not os.path.exists(celeb_photo_path):
    print(f"❌ File not found: {celeb_photo_path}")
    print("\nUsage: python test_mush_style_matching_local.py <path_to_celebrity_photo>")
    exit()

celeb_image = Image.open(celeb_photo_path)

prompt = """Analyze this fashion photo and identify each clothing item.

For each item provide:
1. Item type (dress, blazer, shirt, trousers, shoes, bag, sunglasses, etc.)
2. Detailed visual description
3. Bounding box [x, y, width, height] as percentages

Return as JSON:
[{"type": "dress", "description": "...", "bbox": [25, 20, 50, 70]}]"""

response = gemini.generate_content([prompt, celeb_image])

print("\n✅ Gemini Analysis:")
print(response.text[:300] + "...")

# Parse items
try:
    text = response.text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    items = json.loads(text.strip())
except Exception as e:
    print(f"\n⚠️  Could not parse JSON: {e}")
    print("Using manual parsing...")
    items = []

print(f"\n✅ Found {len(items)} items:")
for item in items:
    print(f"   - {item['type']}: {item.get('description', '')[:50]}...")

# Generate embeddings for each item
print("\n🔄 Generating CLIP embeddings for each item...")

item_embeddings = []

for i, item in enumerate(items):
    # Crop item
    if 'bbox' in item and item['bbox']:
        width, height = celeb_image.size
        bbox = item['bbox']
        x = int(bbox[0] / 100 * width)
        y = int(bbox[1] / 100 * height)
        w = int(bbox[2] / 100 * width)
        h = int(bbox[3] / 100 * height)
        cropped = celeb_image.crop((x, y, x + w, y + h))
    else:
        # Use full image if no bbox
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
    if filename.endswith(('.PNG', '.jpg', '.jpeg', '.JPG')) and filename != os.path.basename(celeb_photo_path):
        wardrobe_items.append(os.path.join(wardrobe_path, filename))

print(f"\n📦 Comparing against {len(wardrobe_items)} wardrobe items")

# For each celebrity item, find best matches from wardrobe
matches = []

for celeb_item in item_embeddings:
    print(f"\n🔍 Finding matches for: {celeb_item['type']}")
    
    best_matches = []
    
    # Compare with each wardrobe item
    for wardrobe_img_path in wardrobe_items[:30]:  # Test with first 30
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
        except Exception as e:
            continue
    
    # Sort by similarity
    best_matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Show top 5
    print(f"\n   📊 Top 5 matches:")
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
canvas_width = 1400
canvas_height = max(600, len(matches) * 280)
item_size = 200

canvas = Image.new('RGB', (canvas_width, canvas_height), '#F5F5F5')
draw = ImageDraw.Draw(canvas)

# Title
draw.rectangle([(0, 0), (canvas_width, 60)], fill='#2C3E50')
draw.text((20, 18), "SHOP THE LOOK", fill='white')

# Position items
y_offset = 80
for idx, match_set in enumerate(matches):
    celeb_item = match_set['celeb_item']
    best_match = match_set['best_matches'][0] if match_set['best_matches'] else None
    
    # Background for this row
    draw.rectangle([(10, y_offset - 10), (canvas_width - 10, y_offset + item_size + 50)], 
                   outline='#DDD', width=2)
    
    # Celebrity item (left)
    celeb_resized = celeb_item['cropped_image'].copy()
    celeb_resized.thumbnail((item_size, item_size))
    canvas.paste(celeb_resized, (30, y_offset))
    draw.text((30, y_offset + item_size + 5), 
              f"TARGET: {celeb_item['type'].upper()}", fill='#2C3E50')
    
    if best_match:
        # Arrow
        draw.text((250, y_offset + 90), "→", fill='#3498DB')
        
        # Best match (middle)
        best_img = Image.open(best_match['path'])
        best_resized = best_img.copy()
        best_resized.thumbnail((item_size, item_size))
        canvas.paste(best_resized, (300, y_offset))
        
        # Similarity badge
        draw.rectangle([(300, y_offset), (400, y_offset + 30)], fill='#27AE60')
        draw.text((310, y_offset + 5), 
                  f"{best_match['similarity']:.1%} MATCH", fill='white')
        
        draw.text((300, y_offset + item_size + 5), 
                  f"{best_match['filename'][:25]}", fill='#2C3E50')
        
        # Show top 3 alternatives
        for alt_idx in range(1, min(4, len(match_set['best_matches']))):
            alt = match_set['best_matches'][alt_idx]
            alt_img = Image.open(alt['path'])
            alt_resized = alt_img.copy()
            alt_resized.thumbnail((80, 80))
            
            x_pos = 540 + (alt_idx - 1) * 100
            canvas.paste(alt_resized, (x_pos, y_offset + 60))
            draw.text((x_pos, y_offset + 145), 
                      f"{alt['similarity']:.0%}", fill='#7F8C8D')
        
        # "View All" button
        draw.rectangle([(900, y_offset + 80), (1050, y_offset + 120)], 
                       fill='#3498DB', outline='#2980B9', width=2)
        draw.text((920, y_offset + 90), 
                  f"VIEW ALL ({len(match_set['best_matches'])})", fill='white')
    
    y_offset += 280

# Save canvas
canvas.save('shop_the_look_canvas.png')
print("\n✅ Created: shop_the_look_canvas.png")
print("   Open it to see the Mush-style layout!")

print("\n" + "=" * 70)
print("📊 RESULTS SUMMARY")
print("=" * 70)

for match_set in matches:
    item = match_set['celeb_item']
    best = match_set['best_matches'][0] if match_set['best_matches'] else None
    
    print(f"\n{item['type'].upper()}")
    print(f"  Target: {item['description'][:60]}...")
    if best:
        print(f"  ✅ Best Match: {best['filename']}")
        print(f"  📊 Similarity: {best['similarity']:.2%}")
        print(f"  🔍 Alternatives: {len(match_set['best_matches'])-1} more options")
        
        # Show if it's a good match
        if best['similarity'] > 0.80:
            print(f"  🎯 Excellent match!")
        elif best['similarity'] > 0.70:
            print(f"  ✅ Good match")
        else:
            print(f"  ⚠️  Moderate match - may need more inventory")

print("\n" + "=" * 70)
print("💡 HOW THIS WOULD WORK IN PRODUCTION")
print("=" * 70)

print("""
User Journey:
1. Upload celebrity photo
2. See canvas with best matches (like shop_the_look_canvas.png)
3. Click any item → Grid view of all similar items
4. Swap items to create custom combinations
5. Click "Buy Look" → Checkout with affiliate links

Exactly like Mush! 🎯

Cost: $0.10 per celebrity photo analysis
""")

