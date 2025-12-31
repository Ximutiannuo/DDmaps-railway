
import re

source_file = 'js/app-main.js'
target_file = 'js/ui-manager.js'

# 要提取的函数名列表
functions_to_extract = [
    'showToast',
    'setButtonLoading',
    'enhanceButton',
    'validateForm',
    'updateMapUploadMessage',
    'resetMapFileInput',
    'showError',
    'handleError',
    'showSuccess',
    'formatDistance',
    'formatSpeed',
    'formatDateTime',
    'escapeHtml'
]

with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

extracted_lines = []
remaining_lines = []

current_function = None
brace_count = 0
in_function = False

i = 0
while i < len(lines):
    line = lines[i]
    
    # 检查函数开始
    if not in_function:
        match = False
        for func_name in functions_to_extract:
            # 匹配 function funcName( 或 async function funcName(
            if re.search(f'function\s+{func_name}\s*\(', line):
                current_function = func_name
                in_function = True
                brace_count = line.count('{') - line.count('}')
                extracted_lines.append(line)
                match = True
                break
        
        if not match:
            remaining_lines.append(line)
            
    else:
        # 在函数内部
        extracted_lines.append(line)
        brace_count += line.count('{') - line.count('}')
        
        if brace_count == 0:
            in_function = False
            current_function = None
            # 添加空行分隔
            extracted_lines.append('\n')
    
    i += 1

# 写入新文件
with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(["// UI 管理和工具函数\n\n"] + extracted_lines)

# 更新原文件
with open(source_file, 'w', encoding='utf-8') as f:
    f.writelines(remaining_lines)

print(f"Extracted {len(functions_to_extract)} functions to {target_file}")

