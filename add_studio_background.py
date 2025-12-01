"""
Take the sequential VTO result and put it on clean studio background
Like professional product photography
"""
import os
from PIL import Image
import io
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash-image')

print("=" * 70)
print("🎨 Adding Professional Studio Background")
print("=" * 70)

# Load the sequential final result
with open('sequential_final.png', 'rb') as f:
    vto_result = Image.open(io.BytesIO(f.read()))

prompt = """Professional photo editing: Extract this person and place them on a clean studio background.

REQUIREMENTS:
1. PERSON EXTRACTION:
   - Keep the person EXACTLY as they are
   - Precise cutout around their silhouette
   - Preserve all details (face, hair, clothes, pose)
   
2. NEW BACKGROUND:
   - Clean light gray studio background (#E8E8E8)
   - Soft, even studio lighting
   - Subtle drop shadow beneath feet for depth
   - Professional product photography quality
   
3. LIGHTING ADJUSTMENT:
   - Add soft studio lighting that wraps around the person
   - Enhance shadows and highlights naturally
   - Make it look like professional fashion photography

The person should look like they're in a high-end photo studio.

Output: Professional studio portrait."""

print("\n🎨 Applying studio background and lighting...")

response = model.generate_content(
    [prompt, vto_result],
    generation_config=genai.types.GenerationConfig(
        temperature=0.3,
        top_p=0.7,
        top_k=20,
    )
)

if hasattr(response, 'candidates') and response.candidates:
    for candidate in response.candidates:
        if hasattr(candidate, 'content') and candidate.content:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open('vto_with_studio_bg.png', 'wb') as f:
                        f.write(part.inline_data.data)
                    print("✅ Saved: vto_with_studio_bg.png")
                    print("\n💡 This should look like professional product photography!")
                    print("   Clean background, professional lighting, premium quality!")

print("\n" + "=" * 70)
