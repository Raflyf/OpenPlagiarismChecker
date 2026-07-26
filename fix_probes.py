import os
import glob

def update_probes(file_path):
    if not os.path.exists(file_path): return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'max(200, min(250' in content:
        content = content.replace('max(200, min(250', 'max(180, min(230')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")

for f in ['app/server.py', 'test_deltas.py', 'run_test_groundtruth.py']:
    update_probes(f)

for f in glob.glob('scratch/*.py'):
    update_probes(f)
