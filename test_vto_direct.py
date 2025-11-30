import asyncio
import sys
from vto_system import VTOGenerator

async def test():
    # Read image
    with open(sys.argv[1], 'rb') as f:
        image_data = f.read()
    
    print("🎭 Testing VTO System...")
    print(f"📸 Image size: {len(image_data)} bytes")
    
    # Generate base model
    print("\n⏳ Step 1: Generating base model...")
    gen = VTOGenerator()
    result = await gen.generate_base_model(image_data)
    
    print(f"✅ Generated! Length: {len(result)}")
    print(f"📊 Preview: {result[:100]}...")
    
    # Save result
    with open('base_model_result.txt', 'w') as f:
        f.write(result)
    
    print("\n✅ Saved to base_model_result.txt")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_vto_direct.py <image_file>")
        sys.exit(1)
    
    asyncio.run(test())
