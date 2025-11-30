"""
Test garment application directly
"""
import asyncio
import sys
from vto_system import VTOGenerator
from dotenv import load_dotenv
import base64

async def test(photo_path, garment_path):
    load_dotenv()
    
    print("👕 GARMENT APPLICATION TEST")
    print("=" * 50)
    
    gen = VTOGenerator()
    
    # Read your photo
    print(f"\n📸 Reading: {photo_path}")
    with open(photo_path, 'rb') as f:
        photo = f.read()
    
    # Convert to data URL
    photo_b64 = base64.b64encode(photo).decode('utf-8')
    photo_url = f"data:image/jpeg;base64,{photo_b64}"
    
    # Read garment
    print(f"👔 Reading: {garment_path}")
    with open(garment_path, 'rb') as f:
        garment = f.read()
    
    # Apply garment
    print("⏳ Applying garment (5-10 seconds)...")
    result = await gen.apply_garment_to_model(photo_url, garment)
    
    print("✅ Done!")
    
    # Save
    with open('direct_garment_result.html', 'w') as f:
        f.write(f'<img src="{result}" style="max-width:800px">')
    
    print("\n🎉 Open: direct_garment_result.html")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 test_direct_garment.py <photo.jpg> <garment.png>")
        sys.exit(1)
    asyncio.run(test(sys.argv[1], sys.argv[2]))
