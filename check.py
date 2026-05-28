import os
path = r'c:\Users\ASUS\Desktop\mindful-me\app\templates\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
count = 0
for i, line in enumerate(lines):
    if '\\' in line:
        print(f"Line {i+1}: {line.strip()}")
        count += 1
print(f"Total lines with backslash: {count}")

# Check for non-breaking spaces too just in case
print(f"Total non-breaking spaces: {content.count(chr(160))}")
