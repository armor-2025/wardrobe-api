# 📸 Item Extraction - Frontend Implementation Guide

## Overview
Like ALTA app - upload one outfit photo, get multiple wardrobe items automatically extracted.

**User Flow:**
1. Upload photo of outfit they're wearing
2. AI detects & segments each item (top, bottom, shoes, etc.)
3. User reviews extracted items
4. Confirm → Items added to wardrobe as clean PNGs

---

## 🎯 API Endpoints

### 1. Extract Items from Outfit Photo

**Endpoint:** `POST /extract/outfit-photo`

**Headers:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Body:**
```
file: [image file]
```

**Response:**
```json
{
  "original_photo": "base64_encoded_image",
  "items_detected": 4,
  "items": [
    {
      "item_id": "temp-001",
      "category": "top",
      "confidence": 0.95,
      "bounding_box": [100, 50, 300, 200],
      "segmented_image": "base64_png_with_transparent_bg",
      "detected_attributes": {
        "color": "black",
        "style": "casual",
        "pattern": "solid",
        "fit": "regular"
      }
    },
    {
      "item_id": "temp-002",
      "category": "bottom",
      "confidence": 0.93,
      "segmented_image": "base64_png",
      "detected_attributes": {
        "color": "blue",
        "style": "denim",
        "pattern": "solid"
      }
    }
    // ... more items
  ]
}
```

---

### 2. Confirm Extracted Items

**Endpoint:** `POST /extract/confirm-items`

**Body:**
```json
{
  "items": [
    {
      "item_id": "temp-001",
      "confirmed": true,
      "name": "Black T-Shirt",
      "brand": "Uniqlo",
      "category": "top"
    },
    {
      "item_id": "temp-002",
      "confirmed": true,
      "name": "Blue Jeans",
      "brand": "Levi's",
      "category": "bottom"
    },
    {
      "item_id": "temp-003",
      "confirmed": false  // User rejected this detection
    }
  ]
}
```

**Response:**
```json
{
  "confirmed_count": 2,
  "items": [
    {
      "item_id": "temp-001",
      "name": "Black T-Shirt",
      "brand": "Uniqlo",
      "category": "top",
      "status": "added_to_wardrobe"
    },
    {
      "item_id": "temp-002",
      "name": "Blue Jeans",
      "brand": "Levi's",
      "category": "bottom",
      "status": "added_to_wardrobe"
    }
  ],
  "message": "Added 2 items to your wardrobe"
}
```

---

### 3. Batch Upload Multiple Photos

**Endpoint:** `POST /extract/batch-upload`

**Body:**
```
files[]: [multiple image files]
```

**Response:**
```json
{
  "photos_processed": 3,
  "total_items_detected": 12,
  "results": [
    {
      "filename": "outfit1.jpg",
      "items_detected": 4,
      "items": [...]
    },
    {
      "filename": "outfit2.jpg",
      "items_detected": 5,
      "items": [...]
    }
  ]
}
```

---

## 📱 FlutterFlow Implementation

### Step 1: Upload Photo Screen
```dart
class UploadOutfitScreen extends StatefulWidget {
  @override
  _UploadOutfitScreenState createState() => _UploadOutfitScreenState();
}

class _UploadOutfitScreenState extends State<UploadOutfitScreen> {
  File? _selectedImage;
  bool _isUploading = false;
  
  Future<void> _pickImage(ImageSource source) async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(
      source: source,
      maxWidth: 1920,
      maxHeight: 1920,
      imageQuality: 85
    );
    
    if (image != null) {
      setState(() {
        _selectedImage = File(image.path);
      });
    }
  }
  
  Future<void> _uploadAndExtract() async {
    if (_selectedImage == null) return;
    
    setState(() => _isUploading = true);
    
    try {
      // Create multipart request
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/extract/outfit-photo')
      );
      
      // Add headers
      request.headers['Authorization'] = 'Bearer $token';
      
      // Add file
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          _selectedImage!.path
        )
      );
      
      // Send request
      var response = await request.send();
      var responseData = await response.stream.bytesToString();
      var jsonResponse = jsonDecode(responseData);
      
      // Navigate to review screen
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => ReviewExtractedItemsScreen(
            extractionResult: jsonResponse
          )
        )
      );
      
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Upload failed: $e'))
      );
    } finally {
      setState(() => _isUploading = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Add Items from Photo')),
      body: Column(
        children: [
          // Instructions
          Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Upload a photo of your outfit. AI will detect each item!',
              style: TextStyle(fontSize: 16),
              textAlign: TextAlign.center
            )
          ),
          
          // Image preview
          if (_selectedImage != null)
            Expanded(
              child: Image.file(_selectedImage!),
            )
          else
            Expanded(
              child: Center(
                child: Icon(Icons.photo_camera, size: 100, color: Colors.grey)
              )
            ),
          
          // Action buttons
          Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                // Take photo
                ElevatedButton.icon(
                  onPressed: () => _pickImage(ImageSource.camera),
                  icon: Icon(Icons.camera_alt),
                  label: Text('Take Photo'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: Size(double.infinity, 50)
                  )
                ),
                
                SizedBox(height: 12),
                
                // Choose from gallery
                OutlinedButton.icon(
                  onPressed: () => _pickImage(ImageSource.gallery),
                  icon: Icon(Icons.photo_library),
                  label: Text('Choose from Gallery'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: Size(double.infinity, 50)
                  )
                ),
                
                SizedBox(height: 24),
                
                // Upload button
                if (_selectedImage != null)
                  ElevatedButton(
                    onPressed: _isUploading ? null : _uploadAndExtract,
                    child: _isUploading
                      ? CircularProgressIndicator(color: Colors.white)
                      : Text('Extract Items'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: Size(double.infinity, 50),
                      backgroundColor: Colors.black
                    )
                  )
              ]
            )
          )
        ]
      )
    );
  }
}
```

---

### Step 2: Review Extracted Items Screen
```dart
class ReviewExtractedItemsScreen extends StatefulWidget {
  final Map<String, dynamic> extractionResult;
  
  ReviewExtractedItemsScreen({required this.extractionResult});
  
  @override
  _ReviewExtractedItemsScreenState createState() => 
    _ReviewExtractedItemsScreenState();
}

class _ReviewExtractedItemsScreenState 
    extends State<ReviewExtractedItemsScreen> {
  
  List<ExtractedItem> items = [];
  bool _isSaving = false;
  
  @override
  void initState() {
    super.initState();
    _parseItems();
  }
  
  void _parseItems() {
    setState(() {
      items = (widget.extractionResult['items'] as List)
        .map((item) => ExtractedItem.fromJson(item))
        .toList();
    });
  }
  
  Future<void> _confirmItems() async {
    setState(() => _isSaving = true);
    
    // Only send confirmed items
    final confirmedItems = items
      .where((item) => item.confirmed)
      .map((item) => {
        'item_id': item.itemId,
        'confirmed': true,
        'name': item.name,
        'brand': item.brand,
        'category': item.category
      })
      .toList();
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/extract/confirm-items'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode({'items': confirmedItems})
      );
      
      if (response.statusCode == 200) {
        // Success!
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${confirmedItems.length} items added to wardrobe!'),
            backgroundColor: Colors.green
          )
        );
        
        // Go back to wardrobe
        Navigator.popUntil(context, (route) => route.isFirst);
      }
      
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Save failed: $e'))
      );
    } finally {
      setState(() => _isSaving = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final confirmedCount = items.where((i) => i.confirmed).length;
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Review Items (${items.length} detected)'),
        actions: [
          TextButton(
            onPressed: _isSaving ? null : _confirmItems,
            child: Text(
              'Save ($confirmedCount)',
              style: TextStyle(color: Colors.white)
            )
          )
        ]
      ),
      body: ListView.builder(
        itemCount: items.length,
        padding: EdgeInsets.all(16),
        itemBuilder: (context, index) {
          final item = items[index];
          return ExtractedItemCard(
            item: item,
            onToggle: () {
              setState(() {
                item.confirmed = !item.confirmed;
              });
            },
            onEdit: () => _showEditDialog(item)
          );
        }
      )
    );
  }
  
  void _showEditDialog(ExtractedItem item) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edit Item'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              decoration: InputDecoration(labelText: 'Name'),
              controller: TextEditingController(text: item.name),
              onChanged: (value) => item.name = value
            ),
            SizedBox(height: 12),
            TextField(
              decoration: InputDecoration(labelText: 'Brand'),
              controller: TextEditingController(text: item.brand),
              onChanged: (value) => item.brand = value
            )
          ]
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel')
          ),
          TextButton(
            onPressed: () {
              setState(() {});
              Navigator.pop(context);
            },
            child: Text('Save')
          )
        ]
      )
    );
  }
}
```

---

### Step 3: Extracted Item Card Widget
```dart
class ExtractedItemCard extends StatelessWidget {
  final ExtractedItem item;
  final VoidCallback onToggle;
  final VoidCallback onEdit;
  
  ExtractedItemCard({
    required this.item,
    required this.onToggle,
    required this.onEdit
  });
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.only(bottom: 16),
      child: Column(
        children: [
          // Item image with checkmark overlay
          Stack(
            children: [
              // Segmented item image
              Container(
                height: 200,
                width: double.infinity,
                color: Colors.grey[100],
                child: Image.memory(
                  base64Decode(item.segmentedImage),
                  fit: BoxFit.contain
                )
              ),
              
              // Confidence badge
              Positioned(
                top: 8,
                right: 8,
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getConfidenceColor(item.confidence),
                    borderRadius: BorderRadius.circular(12)
                  ),
                  child: Text(
                    '${(item.confidence * 100).round()}%',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold
                    )
                  )
                )
              ),
              
              // Checkmark overlay
              Positioned(
                top: 8,
                left: 8,
                child: GestureDetector(
                  onTap: onToggle,
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: item.confirmed 
                        ? Colors.green 
                        : Colors.grey[300],
                      shape: BoxShape.circle
                    ),
                    child: Icon(
                      item.confirmed 
                        ? Icons.check 
                        : Icons.close,
                      color: Colors.white
                    )
                  )
                )
              )
            ]
          ),
          
          // Item details
          Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Category badge
                Chip(
                  label: Text(item.category.toUpperCase()),
                  backgroundColor: Colors.black,
                  labelStyle: TextStyle(
                    color: Colors.white,
                    fontSize: 10
                  )
                ),
                
                SizedBox(height: 8),
                
                // Name
                Text(
                  item.name ?? 'Unnamed Item',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold
                  )
                ),
                
                // Brand
                if (item.brand != null)
                  Text(
                    item.brand!,
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 14
                    )
                  ),
                
                SizedBox(height: 12),
                
                // Detected attributes
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (item.attributes['color'] != null)
                      _buildAttributeChip(
                        Icons.palette,
                        item.attributes['color']!
                      ),
                    if (item.attributes['style'] != null)
                      _buildAttributeChip(
                        Icons.style,
                        item.attributes['style']!
                      ),
                    if (item.attributes['pattern'] != null)
                      _buildAttributeChip(
                        Icons.texture,
                        item.attributes['pattern']!
                      )
                  ]
                ),
                
                SizedBox(height: 12),
                
                // Edit button
                OutlinedButton.icon(
                  onPressed: onEdit,
                  icon: Icon(Icons.edit),
                  label: Text('Edit Details'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: Size(double.infinity, 40)
                  )
                )
              ]
            )
          )
        ]
      )
    );
  }
  
  Widget _buildAttributeChip(IconData icon, String label) {
    return Chip(
      avatar: Icon(icon, size: 16),
      label: Text(label),
      backgroundColor: Colors.grey[200]
    );
  }
  
  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.9) return Colors.green;
    if (confidence >= 0.7) return Colors.orange;
    return Colors.red;
  }
}
```

---

### Step 4: Data Models
```dart
class ExtractedItem {
  String itemId;
  String category;
  double confidence;
  String segmentedImage;  // base64
  Map<String, String> attributes;
  bool confirmed;
  String? name;
  String? brand;
  
  ExtractedItem({
    required this.itemId,
    required this.category,
    required this.confidence,
    required this.segmentedImage,
    required this.attributes,
    this.confirmed = true,  // Default to confirmed
    this.name,
    this.brand
  });
  
  factory ExtractedItem.fromJson(Map<String, dynamic> json) {
    return ExtractedItem(
      itemId: json['item_id'],
      category: json['category'],
      confidence: json['confidence'].toDouble(),
      segmentedImage: json['segmented_image'],
      attributes: Map<String, String>.from(
        json['detected_attributes'] ?? {}
      ),
      name: _generateDefaultName(json),
      brand: 'Unknown Brand'
    );
  }
  
  static String _generateDefaultName(Map<String, dynamic> json) {
    final category = json['category'];
    final color = json['detected_attributes']?['color'] ?? '';
    final style = json['detected_attributes']?['style'] ?? '';
    
    return '$color $style $category'.trim();
  }
}
```

---

## 🎯 User Experience Tips

### 1. Onboarding Flow
```dart
// Show this during first-time setup
OnboardingScreen(
  title: 'Quick Setup',
  description: 'Upload photos of your favorite outfits. AI will extract each item!',
  action: ElevatedButton(
    onPressed: () => Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => UploadOutfitScreen())
    ),
    child: Text('Upload Outfits')
  )
)
```

### 2. Empty Wardrobe State
```dart
if (wardrobeItems.isEmpty) {
  EmptyState(
    icon: Icons.photo_camera,
    title: 'No items yet',
    description: 'Upload outfit photos to get started',
    action: ElevatedButton(
      onPressed: openUploadScreen,
      child: Text('Add from Photo')
    )
  )
}
```

### 3. Progress Indicator
```dart
LinearProgressIndicator(
  value: uploadProgress,  // 0.0 to 1.0
)
Text('Analyzing photo... ${(uploadProgress * 100).round()}%')
```

---

## 🔥 Advanced Features

### 1. Multi-Photo Upload
```dart
Future<void> _pickMultiplePhotos() async {
  final ImagePicker picker = ImagePicker();
  final List<XFile>? images = await picker.pickMultipleImages(
    maxWidth: 1920,
    maxHeight: 1920,
    imageQuality: 85
  );
  
  if (images != null && images.length > 0) {
    // Show progress dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => BatchUploadProgressDialog(images: images)
    );
  }
}
```

### 2. Photo Tips Modal
```dart
showModalBottomSheet(
  context: context,
  builder: (context) => Container(
    padding: EdgeInsets.all(24),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('📸 Photo Tips', style: TextStyle(fontSize: 20)),
        SizedBox(height: 16),
        ListTile(
          leading: Icon(Icons.wb_sunny),
          title: Text('Good lighting'),
          subtitle: Text('Natural light works best')
        ),
        ListTile(
          leading: Icon(Icons.person),
          title: Text('Stand straight'),
          subtitle: Text('Full body, arms at sides')
        ),
        ListTile(
          leading: Icon(Icons.wallpaper),
          title: Text('Plain background'),
          subtitle: Text('Helps AI detect items better')
        )
      ]
    )
  )
);
```

---

## 📊 Success Metrics to Track
```dart
// Track extraction quality
analytics.logEvent('item_extraction', {
  'items_detected': itemsDetected,
  'items_confirmed': itemsConfirmed,
  'avg_confidence': avgConfidence,
  'time_to_review': reviewDuration
});
```

---

Ready to integrate! This will make adding wardrobe items SUPER fast! 🚀
