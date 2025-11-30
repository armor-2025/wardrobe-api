"""
Better: Apply clothes to the extracted person directly
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 VTO on Extracted Person")
print("=" * 70)

# Load extracted person (already has transparent BG)
person_extracted = Image.open('person_extracted.png')

# Load garments
base_path = '/Users/gavinwalker/Downloads/files (4)/'
with open(base_path + 'IMG_5747.jpg', 'rb') as f:
    jumper = Image.open(io.BytesIO(f.read()))
with open(base_path + 'white jeans.png', 'rb') as f:
    jeans = Image.open(io.BytesIO(f.read()))
with open(base_path + 'IMG_5938.PNG', 'rb') as f:
    boots = Image.open(io.BytesIO(f.read()))

prompt = """This person has been extracted from their original photo.
Replace their current clothes with these 3 new garments:
- Black Adidas jumper
- White jeans  
- Tan cowboy boots

CRITICAL: Keep the person's face, hair, and body EXACTLY as shown.
Only change the clothing regions.
Maintain transparent/gray background.

Output: Same person, new clothes."""

print("\n🎨 Applying clothes to extracted person...")

response = model.generate_content(
    [prompt, person_extracted, jumper, jeans, boots],
    generation_config=genai.types.GenerationConfig(temperature=0.01)
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('vto_on_extracted.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: vto_on_extracted.png")
                    print("💰 Cost: $0.10")
                    print("\n💡 This should preserve face since person is pre-extracted!")

