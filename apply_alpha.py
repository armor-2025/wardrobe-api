from rembg import remove

input_path = "/Users/gavinwalker/Desktop/vto_v2_test5_jumper.png"
output_path = "/Users/gavinwalker/Desktop/vto_v2_test5_jumper_alpha.png"

print("Loading image...")
with open(input_path, "rb") as f:
    image_bytes = f.read()

print("Applying alpha matting...")
result = remove(
    image_bytes,
    alpha_matting=True,
    alpha_matting_foreground_threshold=240,
    alpha_matting_background_threshold=10
)

with open(output_path, "wb") as f:
    f.write(result)

print(f"✅ Saved to: {output_path}")
