import os

file_path = 'app/engine/web_scraper.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace timeout=12 with timeout=8
content = content.replace('timeout=12)', 'timeout=8)')
content = content.replace('timeout=12\n', 'timeout=8\n')
content = content.replace('timeout=12,', 'timeout=8,')

# Replace timeout=25 with timeout=20
content = content.replace('timeout=25)', 'timeout=20)')
content = content.replace('timeout=25\n', 'timeout=20\n')
content = content.replace('timeout=25,', 'timeout=20,')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
