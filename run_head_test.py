import cv2
import numpy as np

print("=" * 70)
print("Testing Full Head Preservation")
print("=" * 70)

from insightface.app import FaceAnalysis

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1)
print("✅ Initialized")

# Load images
print("\n📸 Loading images...")
orig_img = cv2.imread('/Users/gavinwalker/Downloads/files (4)/IMG_6033.jpeg')
vto_img = cv2.imread('vto_standard_NO_SWAP.png')
print("✅ Images loaded")

# Detect faces
print("\n🔍 Detecting faces...")
orig_faces = app.get(orig_img)
vto_faces = app.get(vto_img)

if not orig_faces or not vto_faces:
    print("❌ No faces detected")
    exit()

print(f"✅ Found {len(orig_faces)} face in original")
print(f"✅ Found {len(vto_faces)} face in VTO")

orig_bbox = orig_faces[0].bbox.astype(int)
vto_bbox = vto_faces[0].bbox.astype(int)

print(f"\n📊 Original face bbox: {orig_bbox}")
print(f"📊 VTO face bbox: {vto_bbox}")

# Expand for full head
x1, y1, x2, y2 = orig_bbox
face_width = x2 - x1
face_height = y2 - y1

# Big expansion for hair
expand_up = int(face_height * 1.2)
expand_sides = int(face_width * 0.5)
expand_down = int(face_height * 0.2)

hx1 = max(0, x1 - expand_sides)
hy1 = max(0, y1 - expand_up)
hx2 = min(orig_img.shape[1], x2 + expand_sides)
hy2 = min(orig_img.shape[0], y2 + expand_down)

print(f"\n📊 Expanded head region: ({hx1}, {hy1}) to ({hx2}, {hy2})")

# Extract head
orig_head = orig_img[hy1:hy2, hx1:hx2]

# Do same for VTO
vx1, vy1, vx2, vy2 = vto_bbox
vx1 = max(0, vx1 - expand_sides)
vy1 = max(0, vy1 - expand_up)
vx2 = min(vto_img.shape[1], vx2 + expand_sides)
vy2 = min(vto_img.shape[0], vy2 + expand_down)

# Resize original head to match VTO region
vto_height = vy2 - vy1
vto_width = vx2 - vx1

print(f"\n🔄 Resizing original head to ({vto_width}, {vto_height})")
orig_head_resized = cv2.resize(orig_head, (vto_width, vto_height))

# Create soft mask
mask = np.zeros((vto_height, vto_width), dtype=np.float32)
center_x, center_y = vto_width // 2, vto_height // 2
axes_x, axes_y = vto_width // 2, vto_height // 2
cv2.ellipse(mask, (center_x, center_y), (axes_x, axes_y), 0, 0, 360, 1, -1)
mask = cv2.GaussianBlur(mask, (99, 99), 0)
mask = np.stack([mask] * 3, axis=2)

# Blend
print("\n🎨 Blending head onto VTO...")
result = vto_img.copy()
vto_region = result[vy1:vy2, vx1:vx2]
blended = (orig_head_resized * mask + vto_region * (1 - mask)).astype(np.uint8)
result[vy1:vy2, vx1:vx2] = blended

# Save
cv2.imwrite('test_full_head_preserved.png', result)
print("✅ Saved: test_full_head_preserved.png")
print("\n💡 Open it and check if the hair is preserved!")
