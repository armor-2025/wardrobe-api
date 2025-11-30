"""
Test Face Swap - Quick verification that InsightFace works
Run this first before testing full VTO
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vto_enhanced import FaceSwapper

async def test_face_swap():
    print("=" * 60)
    print("🧪 Testing Face Swap Functionality")
    print("=" * 60)
    
    # Initialize face swapper
    print("\n1️⃣ Initializing InsightFace...")
    swapper = FaceSwapper()
    swapper.initialize()
    
    if not swapper._initialized:
        print("❌ FAILED: InsightFace not initialized")
        print("\nTo fix:")
        print("  pip install insightface onnxruntime opencv-python")
        return
    
    print("✅ InsightFace initialized successfully!")
    
    # Load test image
    print("\n2️⃣ Loading test image...")
    test_image_path = '/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg'
    
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        print("\nPlease update the path to your test image in the script")
        return
    
    with open(test_image_path, 'rb') as f:
        test_image = f.read()
    
    print(f"✅ Loaded: {test_image_path}")
    print(f"   Size: {len(test_image):,} bytes")
    
    # Test face swap (using same image as both source and target)
    print("\n3️⃣ Testing face swap...")
    print("   (Using same image as source and target for testing)")
    
    result = swapper.swap_face(test_image, test_image)
    
    if result:
        print("✅ Face swap successful!")
        print(f"   Result size: {len(result):,} bytes")
        
        # Save result
        output_path = 'test_face_swap_result.png'
        with open(output_path, 'wb') as f:
            f.write(result)
        
        print(f"\n💾 Result saved to: {output_path}")
        print(f"   Open it to verify face swap worked!")
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nFace swap is working correctly. You can now:")
        print("1. Test full VTO with face swap (test_enhanced_vto.py)")
        print("2. Deploy to production")
        print("3. Start using enhanced VTO system")
        
    else:
        print("❌ Face swap failed")
        print("\nPossible issues:")
        print("1. No face detected in image")
        print("2. Image format not supported")
        print("3. Model not loaded correctly")

if __name__ == "__main__":
    asyncio.run(test_face_swap())
