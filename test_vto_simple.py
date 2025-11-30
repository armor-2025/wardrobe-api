"""
VTO Test Script
Usage: python3 test_vto_simple.py <base_photo.jpg> <garment.png>
"""
import asyncio
import sys
from vto_system import VTOGenerator
from dotenv import load_dotenv

async def test(base_photo_path, garment_path):
    load_dotenv()
    
    print("🎭 VTO TEST")
    print("=" * 50)
    
    gen = VTOGenerator()
    
    # Step 1: Generate base model
    print(f"\n📸 Reading base photo: {base_photo_path}")
    with open(base_photo_path, 'rb') as f:
        photo = f.read()
    
    print(f"Size: {len(photo)} bytes")
    print("⏳ Generating base model...")
    
    base_model = await gen.generate_base_model(photo)
    print("✅ Base model generated!")
    
    # Step 2: Apply garment
    print(f"\n👕 Reading garment: {garment_path}")
    with open(garment_path, 'rb') as f:
        garment = f.read()
    
    print("⏳ Applying garment...")
    result = await gen.apply_garment_to_model(base_model, garment)
    print("✅ VTO complete!")
    
    # Save results
    with open('vto_base_model.html', 'w') as f:
        f.write(f'<img src="{base_model}" style="max-width:400px">')
    
    with open('vto_result.html', 'w') as f:
        f.write(f'<img src="{result}" style="max-width:400px">')
    
    print("\n🎉 DONE!")
    print("Open these files in browser:")
    print("  - vto_base_model.html (step 1)")
    print("  - vto_result.html (final result)")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 test_vto_simple.py <your_photo.jpg> <garment.png>")
        sys.exit(1)
    
    asyncio.run(test(sys.argv[1], sys.argv[2]))
