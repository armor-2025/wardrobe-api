"""
Try Gemini in EDIT mode instead of GENERATE mode
Tell it to edit the existing photo, not create a new one
"""
import os
from PIL import Image
import io
import base64
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎯 Gemini EDIT Mode Test")
print("=" * 70)

# Load images
with open('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg', 'rb') as f:
    user_photo = Image.open(io.BytesIO(f.read()))

with open('/Users/gavinwalker/Downloads/files (4)/IMG_5937.PNG', 'rb') as f:
    shirt = Image.open(io.BytesIO(f.read()))

# Key difference: Frame this as EDITING, not generating
prompt = """You are a photo editor. Edit this photo by ONLY changing the person's shirt.

STRICT INSTRUCTIONS:
- This is photo EDITING, not photo generation
- DO NOT change the person's face
- DO NOT change the person's hair
- DO NOT change the person's body
- DO NOT change the background
- DO NOT change anything except the clothing

ONLY EDIT:
- Replace the current shirt with the new shirt shown
- Keep everything else pixel-perfect identical

Think of this like Photoshop: you're cutting out the old shirt and pasting in the new one.
The person must be 100% recognizable as the exact same person.

Return the edited photo."""

print("\n🎨 Running in EDIT mode...")

response = model.generate_content(
    [prompt, user_photo, shirt],
    generation_config=genai.types.GenerationConfig(
        temperature=0.05,  # VERY low - we want precision editing
        top_p=0.3,
        top_k=5,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    result = part.inline_data.data
                    with open('vto_edit_mode.png', 'wb') as f:
                        f.write(result)
                    print("✅ Saved: vto_edit_mode.png")
                    print("\n💡 Framing as 'editing' instead of 'generating' might help!")

print("=" * 70)
