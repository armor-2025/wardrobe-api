import asyncio
import sys
from vto_system import VTOGenerator
from dotenv import load_dotenv

async def test():
    load_dotenv()
    
    print("SINGLE-STEP VTO TEST")
    print("=" * 50)
    
    gen = VTOGenerator()
    
    # Base model
    print("\nGenerating base model...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
        photo = f.read()
    
    base = await gen.generate_base_model(photo)
    print("Base ready!")
    
    with open('single_base.html', 'w') as f:
        f.write('<img src="' + base + '" style="max-width:600px">')
    
    # All garments
    print("\nApplying all garments at once...")
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
        shirt = f.read()
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
        shorts = f.read()
    with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
        boots = f.read()
    
    final = await gen.apply_complete_outfit(base, [shirt, shorts, boots])
    print("DONE!")
    
    with open('single_final.html', 'w') as f:
        f.write('<img src="' + final + '" style="max-width:600px">')
    
    print("\nOpen: single_base.html and single_final.html")

asyncio.run(test())
