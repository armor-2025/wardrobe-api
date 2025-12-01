"""
Try combining shorts + boots in one step to save cost
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("💰 Testing Cost Reduction: Combine Shorts + Boots")
print("=" * 70)

# Load original
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    original = Image.open(io.BytesIO(f.read()))

# Load garments
with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5939.PNG', 'rb') as f:
    shorts = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

# Step 1: Apply shirt only
print("\n👕 Step 1: Applying shirt...")
prompt1 = """Inpaint: Replace ONLY the shirt.
Keep face, hair, body, background IDENTICAL.
Replace shirt with new one shown."""

response = model.generate_content(
    [prompt1, original, shirt],
    generation_config=genai.types.GenerationConfig(temperature=0.05, top_p=0.5, top_k=10)
)

result1 = None
if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    result1 = part.inline_data.data
                    with open('cost_test_step1_shirt.png', 'wb') as f:
                        f.write(result1)
                    print("✅ Saved: cost_test_step1_shirt.png")

if result1:
    # Step 2: Apply BOTH shorts and boots together
    print("\n👖👢 Step 2: Applying shorts AND boots together...")
    
    step1_img = Image.open(io.BytesIO(result1))
    
    prompt2 = """Inpaint: Replace the lower body clothing (pants/shorts AND shoes/boots).

Keep face, hair, upper body, background IDENTICAL.
Replace current lower body garments with:
- These shorts
- These boots

Apply both lower body items together."""

    response = model.generate_content(
        [prompt2, step1_img, shorts, boots],
        generation_config=genai.types.GenerationConfig(temperature=0.05, top_p=0.5, top_k=10)
    )
    
    result2 = None
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        result2 = part.inline_data.data
                        with open('cost_test_step2_lower_body.png', 'wb') as f:
                            f.write(result2)
                        print("✅ Saved: cost_test_step2_lower_body.png")
    
    if result2:
        # Step 3: Studio background
        print("\n🎨 Step 3: Adding studio background...")
        
        step2_img = Image.open(io.BytesIO(result2))
        
        prompt3 = """Place person in clean photo studio.
Preserve person exactly, add professional background and lighting."""
        
        response = model.generate_content(
            [prompt3, step2_img],
            generation_config=genai.types.GenerationConfig(temperature=0.3, top_p=0.7, top_k=20)
        )
        
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            with open('cost_test_final_3steps.png', 'wb') as f:
                                f.write(part.inline_data.data)
                            print("✅ Saved: cost_test_final_3steps.png")

print("\n" + "="*70)
print("💰 Cost Comparison:")
print("   4 steps (current): $0.40")
print("   3 steps (this test): $0.30 (25% savings!)")
print("\n📊 Check if quality is still good!")
print("="*70)
