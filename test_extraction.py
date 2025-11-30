"""
Test item extraction with real image
"""
import requests
import base64
import json

# Configuration
BASE_URL = "http://localhost:8012"
TOKEN = None  # We'll get this from login

def login():
    """Get auth token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "fan@example.com",
            "password": "pass123"
        }
    )
    return response.json()["token"]

def test_extraction(image_path: str, token: str):
    """Upload image and get extraction results"""
    
    # Open image file
    with open(image_path, 'rb') as f:
        files = {'file': ('outfit.png', f, 'image/png')}
        headers = {'Authorization': f'Bearer {token}'}
        
        print(f"📤 Uploading {image_path}...")
        
        # Add upload_type as form data
        data = {'upload_type': 'full_outfit'}
        
        response = requests.post(
            f"{BASE_URL}/extract/outfit-photo",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Detected {result['items_detected']} items")
            print("\nExtracted Items:")
            print("=" * 50)
            
            for idx, item in enumerate(result['items'], 1):
                print(f"\nItem {idx}:")
                print(f"  Category: {item['category']}")
                print(f"  Confidence: {item['confidence']*100:.1f}%")
                print(f"  Attributes: {item['detected_attributes']}")
                
                # Save segmented image
                if 'segmented_image' in item:
                    img_data = base64.b64decode(item['segmented_image'])
                    output_path = f"test_images/extracted_item_{idx}.png"
                    with open(output_path, 'wb') as out:
                        out.write(img_data)
                    print(f"  💾 Saved to: {output_path}")
            
            return result
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None

def test_confirmation(items: list, token: str):
    """Test confirming extracted items"""
    
    # Confirm all items
    confirmations = [
        {
            "item_id": item["item_id"],
            "confirmed": True,
            "name": f"Item {item['category']}",
            "brand": "Test Brand",
            "category": item["category"]
        }
        for item in items
    ]
    
    print("\n📝 Confirming items...")
    
    response = requests.post(
        f"{BASE_URL}/extract/confirm-items",
        json=confirmations,
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['confirmed_count']} items added to wardrobe!")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def main():
    print("🎯 Testing Item Extraction System\n")
    
    # Step 1: Login
    print("1. Logging in...")
    token = login()
    print(f"✅ Got token: {token[:20]}...\n")
    
    # Step 2: Extract items from outfit photo
    print("2. Extracting items from outfit photo...")
    result = test_extraction("test_images/outfit.png", token)
    
    if result:
        # Step 3: Confirm items
        print("\n3. Confirming extracted items...")
        confirmation = test_confirmation(result['items'], token)
        
        # Step 4: Check stats
        print("\n4. Checking extraction stats...")
        stats_response = requests.get(
            f"{BASE_URL}/extract/extraction-stats",
            headers={'Authorization': f'Bearer {token}'}
        )
        stats = stats_response.json()
        print(f"📊 Stats:")
        print(f"  Photos uploaded: {stats['outfit_photos_uploaded']}")
        print(f"  Items extracted: {stats['items_extracted_and_added']}")
        print(f"  Avg per photo: {stats['avg_items_per_photo']}")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    main()
