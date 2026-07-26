import os
files = ['app/server.py', 'test_deltas.py', 'app/engine/web_scraper.py']
for f in files:
    if os.path.exists(f):
        with open(f, 'rb') as file:
            content = file.read()
        if content.startswith(b'\xff\xfe'):
            text = content.decode('utf-16le')
            with open(f, 'w', encoding='utf-8') as file:
                file.write(text)
            print(f'Converted UTF-16 to UTF-8 for {f}')
