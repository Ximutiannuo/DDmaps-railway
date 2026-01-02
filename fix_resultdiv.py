with open('driver.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert the resultDiv declaration after the comment line
insert_line = "                const resultDiv = document.getElementById('route-result');\n"

# Find the exact line with the comment
for i, line in enumerate(lines):
    if '// 2.' in line and '隐藏路线结果区域' in line:
        # Insert after this line (before the if statement)
        lines.insert(i+1, insert_line)
        print(f'Inserted resultDiv declaration after line {i+1}')
        break

with open('driver.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('File updated successfully!')
