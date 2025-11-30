"""
Test full outfit - layer multiple garments
"""
import asyncio
from vto_system import VTOGenerator
from dotenv import load_dotenv

async def test():
    load_dotenv()
    
    print("👔 FULL OUTFIT TEST")
    print("=" * 50)
    
    gen = VTOGenerator()
    
    # Step 1: Generate base model
    print("\n📸 Step 1: Generate base model")
    with open('~/Downloads/files (4)/IMG_6033.jpeg'.replace('~', '/Users/gavinwalker'), 'rb') as f:
        photo = f.read()
    
    print("⏳ Generating base model...")
    base_model = await gen.generate_base_model(photo)
    print("✅ Base model done!")
    
    # Save base
    with open('outfit_step1_base.html', 'w') as f:
        f.write(f'<h2>Step 1: Base Model</h2><img src="{base_model}" style="max-width:600px">')
    
    # Step 2: Apply shirt
    print("\n👕 Step 2: Apply shirt")
    with open('~/Downloads/files (4)/IMG_5937.PNG'.replace('~', '/Users/gavinwalker'), 'rb') as f:
        shirt = f.read()
    
    print("⏳ Applying shirt...")
    with_shirt = await gen.apply_garment_to_model(base_model, shirt)
    print("✅ Shirt applied!")
    
    with open('outfit_step2_shirt.html', 'w') as f:
        f.write(f'<h2>Step 2: With Shirt</h2><img src="{with_shirt}" style="max-width:600px">')
    
    # Step 3: Apply shorts
    print("\n🩳 Step 3: Apply shorts")
    with open('~/Downloads/files (4)/IMG_5939.PNG'.replace('~', '/Users/gavinwalker'), 'rb') as f:
        shorts = f.read()
    
    print("⏳ Applying shorts...")
    with_shorts = await gen.apply_garment_to_model(with_shirt, shorts)
    print("✅ Shorts applied!")
    
    with open('outfit_step3_shorts.html', 'w') as f:
        f.write(f'<h2>Step 3: With Shorts</h2><img src="{with_shorts}" style="max-width:600px">')
    
    # Step 4: Apply boots
    print("\n👢 Step 4: Apply boots")
    with open('~/Downloads/files (4)/IMG_5938.PNG'.replace('~', '/Users/gavinwalker'), 'rb') as f:
        boots = f.read()
    
    print("⏳ Applying boots...")
    final = await gen.apply_garment_to_model(with_shorts, boots)
    print("✅ Boots applied!")
    
    with open('outfit_step4_final.html', 'w') as f:
        f.write(f'<h2>Step 4: FINAL OUTFIT!</h2><img src="{final}" style="max-width:600px">')
    
    print("\n🎉 OUTFIT COMPLETE!")
    print("\nOpen these files:")
    print("  1. outfit_step1_base.html")
    print("  2. outfit_step2_shirt.html")
    print("  3. outfit_step3_shorts.html")
    print("  4. outfit_step4_final.html")

asyncio.run(test())
