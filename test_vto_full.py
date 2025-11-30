import asyncio
from vto_system import VTOGenerator
from dotenv import load_dotenv

async def test():
    load_dotenv()
    
    print("🎭 FULL VTO TEST")
    print("=" * 50)
    
    gen = VTOGenerator()
    
    # Step 1: Generate base model
    print("\n📸 STEP 1: Generate Base Model")
    with open('test_base_model.jpg', 'rb') as f:
        photo = f.read()
    
    print(f"Photo size: {len(photo)} bytes")
    print("⏳ Generating base model (5-10 seconds)...")
    
    base_model = await gen.generate_base_model(photo)
    print(f"✅ Base model generated!")
    
    with open('base_model.txt', 'w') as f:
        f.write(base_model)
    print("💾 Saved to base_model.txt")
    
    # Step 2: Apply garment
    print("\n👕 STEP 2: Apply Garment")
    with open('test_garment_shirt.png', 'rb') as f:
        shirt = f.read()
    
    print("⏳ Applying garment (5-10 seconds)...")
    result = await gen.apply_garment_to_model(base_model, shirt)
    print(f"✅ VTO complete!")
    
    with open('vto_result.txt', 'w') as f:
        f.write(result)
    print("💾 Saved to vto_result.txt")
    
    print("\n🎉 DONE! Check .txt files for results")

asyncio.run(test())
