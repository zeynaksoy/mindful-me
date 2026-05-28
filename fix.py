import os
path = r'c:\Users\ASUS\Desktop\mindful-me\app\templates\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count('\xa0')
if count > 0:
    content = content.replace('\xa0', ' ')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print(f"Fixed {count} non-breaking spaces.")
