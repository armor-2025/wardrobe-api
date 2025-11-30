import sys
sys.path.insert(0, '.')

from vto_enhanced_with_hair import HairAndFaceSwapper

print("=" * 70)
print("Testing Hair + Face Preservation")
print("=" * 70)

swapper = HairAndFaceSwapper()
swapper.initialize()

print("\n📸 Loading images...")

# Load test images
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    original = f.read()
print("✅ Original photo loaded")

# Use one of the VTO results as target
with open('vto_standard_NO_SWAP.png', 'rb') as f:
    vto_result = f.read()
print("✅ VTO result loaded")

print("\n🔄 Swapping face + hair region...")
result = swapper.swap_face_with_hair(original, vto_result)

if result:
    with open('test_with_hair_swap.png', 'wb') as f:
        f.write(result)
    print("✅ Saved: test_with_hair_swap.png")
    print("\n💡 Compare these files:")
    print("   - Regular face swap: vto_standard_WITH_SWAP.png")
    print("   - With hair swap: test_with_hair_swap.png")
    print("\n🎨 Open both and see which preserves hair better!")
else:
    print("❌ Failed to swap")
