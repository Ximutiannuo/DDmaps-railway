import re

# Read file
with open('driver.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with duplicate resultDiv around line 4638
# We need to remove it (line index 4637, 0-indexed)
fixed_lines = []
found_first_resultdiv = False
skip_next_resultdiv = False

for i, line in enumerate(lines):
    # Check if this is the first resultDiv declaration in cancelNavigation function
    if 'const resultDiv = document.getElementById' in line:
        if not found_first_resultdiv:
            found_first_resultdiv = True
            fixed_lines.append(line)
        else:
            # Skip the duplicate declaration
            print(f"Removing duplicate at line {i+1}: {line.strip()[:50]}...")
            continue
    else:
        fixed_lines.append(line)

# Write back
with open('driver.html', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Done! File updated.")
