import sys

# Read the file
with open('test_enhanced_vto.py', 'r') as f:
    content = f.read()

# Add API key after imports
if 'GEMINI_API_KEY' not in content:
    lines = content.split('\n')
    # Find where to insert (after imports, before async def)
    for i, line in enumerate(lines):
        if 'async def test_enhanced_vto' in line:
            lines.insert(i, "os.environ['GEMINI_API_KEY'] = 'AIzaSyAgMKoVUg3IBhLKefBbxYPMf3VypicNzlU'")
            lines.insert(i, '')
            break
    
    # Write back
    with open('test_enhanced_vto.py', 'w') as f:
        f.write('\n'.join(lines))
    
    print("✅ API key added!")
else:
    print("✅ API key already present")
