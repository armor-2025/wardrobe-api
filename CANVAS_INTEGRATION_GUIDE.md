# 🎨 Canvas/Outfit Builder - Integration Guide

## Overview
Users build outfits by combining items on a digital canvas. Think Pinterest boards but for outfits you can actually buy.

**Key Feature:** Canvas adds = 20x recommendation weight (highest signal!)

---

## 🎯 Core Features

### 1. Create Canvas
**Endpoint:** `POST /canvas/`
```json
{
  "name": "Work Outfit Monday",
  "items": ["blazer-123", "jeans-456"],
  "occasion": "work",
  "season": "fall",
  "tags": ["professional", "minimalist"],
  "is_public": false
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 4,
  "name": "Work Outfit Monday",
  "items": ["blazer-123", "jeans-456"],
  "item_positions": {},
  "occasion": "work",
  "tags": ["professional", "minimalist"],
  "is_public": false,
  "vto_generated": false,
  "vto_image_url": null,
  "created_at": "2025-11-01T13:37:40.783917"
}
```

---

### 2. Add Item to Canvas
**Endpoint:** `POST /canvas/{canvas_id}/items/{item_id}`

**Body (optional):**
```json
{
  "x": 0.5,
  "y": 0.3
}
```

**Use Cases:**
- User taps "Add to Canvas" on product page
- User drags item onto canvas
- System auto-suggests item to complete outfit

**Important:** This triggers 20x weight in recommendation algorithm!

---

### 3. Get My Canvases
**Endpoint:** `GET /canvas/my-canvases?limit=50`

Returns all user's canvases, sorted by most recent.

---

### 4. Update Canvas
**Endpoint:** `PUT /canvas/{canvas_id}`
```json
{
  "name": "Updated Name",
  "items": ["item-1", "item-2", "item-3"],
  "is_public": true
}
```

---

### 5. Get Outfit Suggestions
**Endpoint:** `GET /canvas/{canvas_id}/suggestions`

**Response:**
```json
{
  "canvas_id": 1,
  "items_count": 2,
  "suggestions": [
    {
      "category": "shoes",
      "reason": "Complete your outfit with shoes",
      "suggested_items": [
        {
          "product_id": "shoes-001",
          "match_score": 0.85
        }
      ]
    }
  ]
}
```

**Smart AI:** Analyzes what's on canvas and suggests what's missing.

---

### 6. Discover Public Canvases
**Endpoint:** `GET /canvas/discover/public?occasion=work&limit=20`

Browse other users' outfit inspiration.

---

### 7. Like Canvas
**Endpoint:** `POST /canvas/{canvas_id}/like`

Social feature - users can like each other's outfits.

---

## 📱 UI Components (FlutterFlow)

### Canvas Grid View (My Canvases)
```
GridView
├─ Canvas Card
    ├─ Thumbnail (composite of items)
    ├─ Canvas Name
    ├─ Item Count Badge (3 items)
    ├─ Like Count
    └─ Tap → Open Canvas Detail
```

### Canvas Detail/Editor
```
Stack
├─ Canvas Background (white/beige)
├─ Positioned Items (drag & drop)
│   └─ Product Image
│       ├─ Drag Handle
│       └─ Remove Button (X)
├─ Bottom Sheet
    ├─ Canvas Name (editable)
    ├─ Tags (chips)
    ├─ Action Buttons
        ├─ Add Item (+)
        ├─ Share
        ├─ Generate VTO (Premium) ⭐
        └─ Save/Done
```

### Add Item to Canvas Flow
```
Product Page
└─ "Add to Canvas" Button
    ├─ If user has canvases:
    │   └─ Show bottom sheet
    │       ├─ "Add to existing canvas"
    │       │   └─ List of canvases
    │       └─ "Create new canvas"
    └─ If no canvases:
        └─ Create new canvas modal
```

### Outfit Suggestions Widget
```
Container (Canvas Detail)
├─ Header: "Complete Your Look"
├─ Horizontal Scroll
    └─ Suggestion Card
        ├─ Category Icon (shoes, bag, etc.)
        ├─ Product Image
        ├─ Match Score Badge (85%)
        ├─ Price
        └─ "Add to Canvas" Button
```

---

## 🎨 Visual Layout System

### Item Positioning
Canvas uses relative coordinates (0.0 to 1.0):
```dart
// Item at center
item_positions: {
  "blazer-123": {"x": 0.5, "y": 0.3},  // Top center
  "jeans-456": {"x": 0.5, "y": 0.6},   // Middle center
  "shoes-789": {"x": 0.5, "y": 0.85}   // Bottom center
}

// In FlutterFlow
Positioned(
  left: screenWidth * position['x'],
  top: screenHeight * position['y'],
  child: ProductImage()
)
```

### Smart Auto-Layout
For items without positions, use smart defaults:
```dart
Map<String, double> getDefaultPosition(String category) {
  switch(category) {
    case 'hat': return {'x': 0.5, 'y': 0.1};
    case 'top': return {'x': 0.5, 'y': 0.3};
    case 'bottom': return {'x': 0.5, 'y': 0.6};
    case 'shoes': return {'x': 0.5, 'y': 0.85};
    case 'bag': return {'x': 0.8, 'y': 0.5};
    default: return {'x': 0.5, 'y': 0.5};
  }
}
```

---

## 🚀 Key User Flows

### Flow 1: Create Outfit from Scratch
```
1. User taps "Create Outfit" (+ button)
2. Modal: "What's this outfit for?"
   - Work, Casual, Date, Formal, etc.
3. Empty canvas appears
4. User taps "Add Item" 
5. Browse products or search
6. Tap item → Added to canvas
7. Repeat until satisfied
8. Name outfit, add tags
9. Save (private) or Share (public)
```

### Flow 2: Add to Canvas from Product Page
```
1. User browsing products
2. Sees item they like
3. Taps "Add to Canvas" button
4. Bottom sheet shows:
   - Existing canvases (with thumbnails)
   - "Create new canvas"
5. User selects canvas
6. Item added with animation
7. Toast: "Added to Work Outfit"
```

### Flow 3: Outfit Completion
```
1. User has canvas with 2 items (top + bottom)
2. Canvas shows: "Complete your look"
3. AI suggests matching shoes
4. User taps suggestion
5. Item preview appears on canvas
6. User confirms → Added
7. Outfit complete!
```

### Flow 4: Browse Inspiration
```
1. User taps "Discover" tab
2. Grid of public canvases
3. Filter by:
   - Occasion (work, casual, etc.)
   - Season (spring, summer, etc.)
4. Tap canvas → View detail
5. Like button
6. "Shop This Look" → Buy all items
7. "Save to My Canvases" → Copy outfit
```

---

## 💰 Monetization: VTO Premium

### Free Features:
- Create unlimited canvases
- Add items
- Get suggestions
- Browse public canvases

### Premium Features (VTO):
- **See outfit ON YOU**
- Upload photo once
- Generate try-on for any canvas
- Realistic lighting & fit
- Save VTO images

### Premium Pricing Ideas:
- $4.99/month - 20 VTO generations
- $9.99/month - Unlimited VTO
- $0.99 per VTO (pay-as-you-go)

---

## 🎯 Recommendation Impact

### Why Canvas Matters:
```
Canvas Add = 20x weight

Example:
- User views blazer: +1 point
- User clicks blazer: +18 points  
- User adds blazer to canvas: +20 points (HIGHEST!)

Canvas shows TRUE INTENT to buy.
```

### Outfit Context:
```
User creates canvas:
- Black blazer
- White jeans
- Black shoes

Recommendation engine learns:
✓ User likes monochrome
✓ User prefers classic style
✓ Suggest: Black belt, white shirt, minimalist bag
```

---

## 🎨 Design Tips

### Canvas Background
- Light beige/cream (warm, Pinterest-style)
- OR white (clean, modern)
- Subtle texture (fabric, paper)

### Item Cards on Canvas
- Product image with transparent background (ideal)
- OR product image with subtle shadow
- Size: Proportional to real-world (shoes smaller than dress)

### Drag & Drop Feel
- Haptic feedback on move
- Shadow follows drag
- Snap to grid (optional)
- Delete zone (drag to trash)

### Empty State
- "Start building your outfit"
- Suggested templates to start from
- Popular items in your style

---

## 📊 Analytics to Track

### Canvas Metrics:
- Canvases created per user
- Average items per canvas
- Completion rate (started → saved)
- Conversion: Canvas → Purchase

### Item Performance:
- Most added to canvas
- Most completed outfits
- Best converting combinations

### Social Metrics:
- Public canvas views
- Likes per canvas
- Saved/copied canvases

---

## 🔥 Advanced Features (Future)

### 1. Outfit Boards
Multiple canvases in one collection
"Summer Vacation" board with 5 outfit canvases

### 2. Canvas Collaboration
Share canvas with friend for feedback
"What do you think of this outfit?"

### 3. Smart Templates
AI generates full outfit from one item
"Build outfits around this jacket"

### 4. Packing Lists
Turn canvas into travel checklist
"Paris Trip Outfits" → Packing list

### 5. Outfit Challenges
Weekly challenges: "Style this item 3 ways"
Community voting on best outfit

---

## 🎬 Animation Ideas

### Adding Item:
- Fade in + scale animation
- Lands with bounce
- Particle effect (sparkles)

### Completing Outfit:
- Checkmark animation
- Confetti 🎉
- "Outfit Complete!" badge

### Generating VTO:
- Shimmer effect on canvas
- Progress bar: "Generating your try-on..."
- Reveal with slide animation

---

## 🐛 Edge Cases

### Empty Canvas
- Show "Add items to get started"
- Suggest popular items
- Show templates

### Too Many Items
- Warn at 10+ items
- "Consider creating multiple outfits"
- Auto-suggest splitting into 2 canvases

### Item No Longer Available
- Show "Out of stock" badge
- Suggest alternative
- Keep in canvas (user might want to remember it)

### Duplicate Items
- Prevent adding same item twice
- OR allow (user might want 2 white shirts)

---

## 🎨 Example Canvas JSON
```json
{
  "id": 1,
  "name": "Work Meeting Outfit",
  "items": [
    "navy-blazer-123",
    "white-shirt-456", 
    "grey-pants-789",
    "brown-shoes-012"
  ],
  "item_positions": {
    "navy-blazer-123": {"x": 0.5, "y": 0.25},
    "white-shirt-456": {"x": 0.5, "y": 0.4},
    "grey-pants-789": {"x": 0.5, "y": 0.6},
    "brown-shoes-012": {"x": 0.5, "y": 0.85}
  },
  "occasion": "work",
  "season": "fall",
  "tags": ["professional", "business-casual"],
  "is_public": true,
  "like_count": 24,
  "vto_generated": true,
  "vto_image_url": "https://cdn.example.com/vto/user4_canvas1.jpg"
}
```

---

## 🚀 Quick Start Checklist

FlutterFlow Implementation:
- [ ] Create Canvas custom data type
- [ ] Build canvas grid page
- [ ] Build canvas detail/editor page
- [ ] Add "Add to Canvas" button on product pages
- [ ] Implement drag & drop
- [ ] Build suggestion widget
- [ ] Add social features (like, share)
- [ ] Test on mobile device

Backend Ready:
- ✅ Canvas CRUD endpoints
- ✅ Add/remove items
- ✅ Outfit suggestions
- ✅ Public discovery
- ✅ Like system
- ✅ 20x recommendation weight

Next Steps:
- VTO integration (next feature!)
- Smart outfit completion AI
- Social feed of canvases
- Canvas templates

---

Canvas is the CORE of your product. It's where the magic happens! 🎨✨
