# Read the broken file
with open('asos_service.py', 'r') as f:
    lines = f.readlines()

# Fix it line by line
fixed = []
skip_next = False

for i in range(len(lines)):
    if skip_next:
        skip_next = False
        continue
    
    line = lines[i]
    
    # If line has an unclosed string
    if line.rstrip().endswith('"') and line.count('"') % 2 == 1:
        # Check if next line completes it
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # If next line ends with "), it's the continuation
            if next_line.endswith('")') or next_line.endswith('")'):
                # Merge the lines
                combined = line.rstrip()[:-1] + ' ' + next_line
                fixed.append(combined + '\n')
                skip_next = True
                continue
    
    fixed.append(line)

# Write the fixed version
with open('asos_service.py', 'w') as f:
    f.writelines(fixed)

print(f"Fixed! {len(lines)} -> {len(fixed)} lines")
