# 🎨 Styling / "Dress Me" - UI Implementation Guide

Based on Whering app's styling tab - carousel interface for quick outfit building.

---

## 🎯 The Concept

### User Flow:
cat > STYLING_UI_GUIDE.md << 'EOF'
# 🎨 Styling / "Dress Me" - UI Implementation Guide

Based on Whering app's styling tab - carousel interface for quick outfit building.

---

## 🎯 The Concept

### User Flow:
```
1. User has a new top they want to style
2. Open "Dress Me" interface
3. See new top at the top (featured)
4. Carousel rows below for each category:
   - Bottom carousel (swipe through pants/skirts)
   - Shoes carousel (swipe through footwear)
   - Jacket carousel (optional, swipe through outerwear)
5. User swipes through each row to find perfect match
6. Tap "Save Outfit" → Creates canvas with all selected items
7. Canvas shows clean layout (not random mess!)
```

---

## 📱 UI Layout (Mobile)
```
┌─────────────────────────────────────┐
│  Styling                        [×] │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐  │
│  │  Featured: New Item         │  │
│  │                              │  │
│  │  [    Product Image    ]     │  │
│  │                              │  │
│  │  $45 - Brand Name            │  │
│  └─────────────────────────────┘  │
│                                     │
│  Style with your wardrobe ↓         │
│                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                     │
│  Bottom                             │
│  ◀ [img] [img] [IMG] [img] [img] ▶ │
│     Jeans  Pants  Khakis Skirt      │
│           (selected)                 │
│                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                     │
│  Shoes                              │
│  ◀ [img] [IMG] [img] [img] [img] ▶ │
│     Nike  Vans  Boots  Heels        │
│          (selected)                  │
│                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                     │
│  Jacket (Optional)                  │
│  ◀ [img] [img] [IMG] [img]      ▶ │
│     Denim Blazer Puffer            │
│            (selected)               │
│                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                     │
│  [ Preview Outfit ]                 │
│  [   Save to Canvas   ]             │
│                                     │
└─────────────────────────────────────┘
```

---

## 🔌 API Integration

### Get "Dress Me" Data

**Endpoint:** `GET /styling/dress-me`

**Query Params:**
- `new_item_id`: (optional) ID of item to feature
- `new_item_category`: (optional) Category of featured item

**Response:**
```json
{
  "slots": [
    {
      "category": "bottom",
      "label": "Pants / Skirt",
      "position": {"x": 0.5, "y": 0.6},
      "optional": false,
      "items": [
        {
          "product_id": "jeans-123",
          "image_url": "https://...",
          "name": "Slim Fit Jeans",
          "brand": "Levi's",
          "price": 89.99,
          "in_wardrobe": true,
          "in_wishlist": false
        }
      ],
      "item_count": 12
    },
    {
      "category": "shoes",
      "label": "Footwear",
      "position": {"x": 0.5, "y": 0.85},
      "optional": false,
      "items": [ /* ... */ ],
      "item_count": 8
    }
  ],
  "featured_item": {
    "product_id": "top-456",
    "category": "top"
  }
}
```

---

## 🎨 FlutterFlow Components

### Main Page Structure
```dart
Scaffold(
  appBar: AppBar(
    title: Text("Styling"),
    actions: [
      IconButton(
        icon: Icon(Icons.close),
        onPressed: () => Navigator.pop(context)
      )
    ]
  ),
  body: Column(
    children: [
      // Featured Item Section (if exists)
      if (featuredItem != null)
        FeaturedItemCard(item: featuredItem),
      
      Divider(),
      
      // Carousel Rows for Each Category
      Expanded(
        child: ListView.builder(
          itemCount: slots.length,
          itemBuilder: (context, index) {
            return CategoryCarousel(
              slot: slots[index],
              onItemSelected: (itemId) {
                setState(() {
                  selectedItems[slot.category] = itemId;
                });
              }
            );
          }
        )
      ),
      
      // Bottom Actions
      Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            ElevatedButton(
              onPressed: () => previewOutfit(),
              child: Text("Preview Outfit")
            ),
            SizedBox(height: 8),
            ElevatedButton(
              onPressed: () => saveToCanvas(),
              child: Text("Save to Canvas"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.black
              )
            )
          ]
        )
      )
    ]
  )
)
```

---

### Featured Item Card
```dart
Container(
  padding: EdgeInsets.all(16),
  child: Column(
    children: [
      Text(
        "Featured: New Item",
        style: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.bold
        )
      ),
      SizedBox(height: 16),
      Container(
        height: 200,
        width: 200,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey[300]),
          borderRadius: BorderRadius.circular(12)
        ),
        child: Image.network(featuredItem.imageUrl)
      ),
      SizedBox(height: 8),
      Text("\$${featuredItem.price}"),
      Text(featuredItem.brand, style: TextStyle(color: Colors.grey))
    ]
  )
)
```

---

### Category Carousel Row
```dart
Container(
  padding: EdgeInsets.symmetric(vertical: 16),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      // Category Header
      Padding(
        padding: EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              slot.label,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600
              )
            ),
            if (slot.optional)
              Text(
                "Optional",
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey
                )
              )
          ]
        )
      ),
      
      SizedBox(height: 12),
      
      // Horizontal Carousel
      Container(
        height: 150,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: EdgeInsets.symmetric(horizontal: 12),
          itemCount: slot.items.length,
          itemBuilder: (context, index) {
            final item = slot.items[index];
            final isSelected = selectedItems[slot.category] == item.productId;
            
            return GestureDetector(
              onTap: () {
                setState(() {
                  selectedItems[slot.category] = item.productId;
                });
                HapticFeedback.lightImpact();
              },
              child: Container(
                width: 120,
                margin: EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: isSelected ? Colors.black : Colors.grey[300],
                    width: isSelected ? 3 : 1
                  ),
                  borderRadius: BorderRadius.circular(8)
                ),
                child: Column(
                  children: [
                    // Product Image
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(8)
                        ),
                        child: Image.network(
                          item.imageUrl,
                          fit: BoxFit.cover
                        )
                      )
                    ),
                    
                    // Product Info
                    Container(
                      padding: EdgeInsets.all(8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.brand,
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.grey
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis
                          ),
                          if (item.inWardrobe)
                            Row(
                              children: [
                                Icon(Icons.checkroom, size: 12),
                                Text(" In Wardrobe", style: TextStyle(fontSize: 9))
                              ]
                            )
                        ]
                      )
                    )
                  ]
                )
              )
            );
          }
        )
      )
    ]
  )
)
```

---

### Preview Outfit Modal
```dart
showModalBottomSheet(
  context: context,
  builder: (context) {
    return Container(
      height: 500,
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          Text(
            "Outfit Preview",
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold
            )
          ),
          
          SizedBox(height: 16),
          
          // Canvas-style preview with dotted guides
          Expanded(
            child: Stack(
              children: [
                // Background with dotted lines
                CustomPaint(
                  painter: DottedGuidesPainter(),
                  child: Container()
                ),
                
                // Items positioned
                ...selectedItems.entries.map((entry) {
                  final position = getPositionForCategory(entry.key);
                  return Positioned(
                    left: screenWidth * position['x'],
                    top: screenHeight * position['y'],
                    child: ProductImage(productId: entry.value)
                  );
                })
              ]
            )
          ),
          
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              saveToCanvas();
            },
            child: Text("Save This Outfit")
          )
        ]
      )
    );
  }
);
```

---

## 🎯 Key Interactions

### 1. Swipe Through Carousel
- Horizontal scroll with momentum
- Haptic feedback on selection
- Bold border on selected item
- Center selected item in view

### 2. Select Item
```dart
onTap: () {
  // Update selected items
  setState(() {
    selectedItems[category] = productId;
  });
  
  // Haptic feedback
  HapticFeedback.lightImpact();
  
  // Optional: Show brief "Selected" indicator
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text("Selected"),
      duration: Duration(milliseconds: 500)
    )
  );
}
```

### 3. Save to Canvas
```dart
Future<void> saveToCanvas() async {
  // Create canvas with selected items
  final items = selectedItems.values.toList();
  
  final response = await http.post(
    Uri.parse('$baseUrl/canvas/'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json'
    },
    body: jsonEncode({
      'name': 'Outfit ${DateTime.now().toString().substring(0, 10)}',
      'items': items,
      'item_positions': _generatePositions(selectedItems),
      'occasion': selectedOccasion,
      'is_public': false
    })
  );
  
  if (response.statusCode == 200) {
    // Show success
    Navigator.pop(context);
    Navigator.pushNamed(context, '/canvas/${canvasId}');
  }
}

Map<String, Map<String, double>> _generatePositions(
  Map<String, String> selectedItems
) {
  // Use template positions for clean layout
  final positions = <String, Map<String, double>>{};
  
  selectedItems.forEach((category, productId) {
    final position = getPositionForCategory(category);
    positions[productId] = position;
  });
  
  return positions;
}
```

---

## 🎨 Canvas Templates with Dotted Guides

### Template Structure

**Endpoint:** `GET /styling/templates`

**Response:**
```json
{
  "templates": [
    {
      "id": "basic-outfit",
      "name": "Basic Outfit",
      "slots": [
        {
          "category": "top",
          "position": {"x": 0.5, "y": 0.35},
          "size": {"width": 0.6, "height": 0.3}
        }
      ]
    }
  ]
}
```

### Rendering Dotted Guides
```dart
class DottedGuidesPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.grey[300]
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    
    // Draw dotted rectangles for each slot
    for (final slot in template.slots) {
      final rect = Rect.fromCenter(
        center: Offset(
          size.width * slot.position['x'],
          size.height * slot.position['y']
        ),
        width: size.width * slot.size['width'],
        height: size.height * slot.size['height']
      );
      
      // Draw dotted border
      _drawDottedRect(canvas, rect, paint);
      
      // Draw label
      final textPainter = TextPainter(
        text: TextSpan(
          text: slot.label,
          style: TextStyle(color: Colors.grey, fontSize: 12)
        ),
        textDirection: TextDirection.ltr
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(rect.center.dx - textPainter.width / 2, rect.top - 20)
      );
    }
  }
  
  void _drawDottedRect(Canvas canvas, Rect rect, Paint paint) {
    const dashWidth = 5;
    const dashSpace = 3;
    
    // Top line
    double startX = rect.left;
    while (startX < rect.right) {
      canvas.drawLine(
        Offset(startX, rect.top),
        Offset(min(startX + dashWidth, rect.right), rect.top),
        paint
      );
      startX += dashWidth + dashSpace;
    }
    
    // Similar for right, bottom, left lines...
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

---

## 🔥 Advanced Features

### 1. Quick Add from Product Page
```dart
// On product page
FloatingActionButton(
  onPressed: () {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => DressMePage(
          featuredItemId: product.id,
          featuredItemCategory: product.category
        )
      )
    );
  },
  child: Icon(Icons.style),
  label: Text("Style This")
)
```

### 2. Category Filtering
```dart
// Only show categories that make sense
if (featuredItemCategory == 'top') {
  // Hide top carousel
  // Show bottom, shoes, jacket
} else if (featuredItemCategory == 'bottom') {
  // Hide bottom carousel
  // Show top, shoes, jacket
}
```

### 3. Smart Defaults
```dart
// Pre-select items that match well
void preselectMatchingItems() {
  if (featuredItem != null) {
    // Use recommendation engine
    final suggestions = await getSmartSuggestions(
      featuredItemId: featuredItem.id
    );
    
    setState(() {
      suggestions.forEach((category, productId) {
        selectedItems[category] = productId;
      });
    });
  }
}
```

---

## 📊 State Management
```dart
class DressMeState {
  // Featured item (optional)
  String? featuredItemId;
  String? featuredItemCategory;
  
  // Slots data from API
  List<CategorySlot> slots = [];
  
  // User selections
  Map<String, String> selectedItems = {};
  
  // UI state
  bool isLoading = false;
  bool isSaving = false;
  
  // Methods
  void selectItem(String category, String productId) {
    selectedItems[category] = productId;
  }
  
  bool isItemSelected(String category, String productId) {
    return selectedItems[category] == productId;
  }
  
  Future<void> saveOutfit() async {
    isSaving = true;
    // ... save logic
    isSaving = false;
  }
}
```

---

## 🎯 Success Metrics

Track these analytics:
- Time spent in "Dress Me" interface
- Number of carousel swipes per category
- Items selected vs total items available
- Save rate (% of sessions that save outfit)
- Canvas create rate from Dress Me

---

## ✨ Polish Details

### Visual Feedback
- Selected item: **Bold black border** (3px)
- Unselected: Thin grey border (1px)
- Haptic feedback on tap
- Smooth scroll animations

### Empty States
- No items in category: "Add items to your wardrobe"
- No selections made: "Select items to build your outfit"

### Performance
- Lazy load images
- Cache carousel data
- Preload adjacent items

---

This creates the EXACT experience you described - clean, organized, quick outfit building! 🎨✨
