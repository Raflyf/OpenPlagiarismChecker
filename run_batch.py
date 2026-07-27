import os
import requests
import time
import json
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(BASE_DIR, "app", "before_turnitin")
URL_UPLOAD = "http://127.0.0.1:5001/upload"
URL_STATUS = "http://127.0.0.1:5001/status/"

files = os.listdir(FOLDER)
results = []

for idx, filename in enumerate(files):
    if not filename.endswith(('.pdf', '.docx', '.doc')):
        continue
        
    filepath = os.path.join(FOLDER, filename)
    print(f"\n[{idx+1}/{len(files)}] Memproses {filename} ...")
    
    session = requests.Session()
    with open(filepath, 'rb') as f:
        # Ganti force_scrape menjadi 'false' agar otomatis menggunakan frozen corpus jika ada!
        resp = session.post(URL_UPLOAD, files={'file': f}, data={'force_scrape': 'false', 'use_semantic': 'true'})
        
    if resp.status_code != 200:
        print(f"Error upload: {resp.text}")
        results.append({'file': filename, 'score': 'ERROR', 'time': 0})
        continue
        
    file_id = resp.json()['file_id']
    
    start_t = time.time()
    score = None
    fooled_score = None
    
    while True:
        status_resp = session.get(URL_STATUS + file_id)
        if status_resp.status_code != 200:
            print("Status Error:", status_resp.text)
            break
        data = status_resp.json()
        if data['status'] == 'completed':
            score = data['data']['total_similarity']
            fooled_score = data['data'].get('fooled_similarity')
            break
        elif data['status'] == 'error':
            print("Error dari server:", data.get('message'))
            break
            
        # Print progress bar
        print(f"\rProgress: {data.get('progress', 0)}% - {data.get('message', '')}", end="")
        time.sleep(2)
        
    t_elapsed = time.time() - start_t
    print("\nSelesai!")
    
    if score is not None:
        if fooled_score is not None:
            score_str = f"{score}% (Curang: {fooled_score}%)"
        else:
            score_str = f"{score}%"
        print(f"Skor akhir: {score_str}")
        results.append({'file': filename, 'score': score_str, 'time': round(t_elapsed, 1)})
    else:
        results.append({'file': filename, 'score': 'ERROR', 'time': round(t_elapsed, 1)})

# Print Table
print("\n" + "="*80)
print(f"{'Nama File':<60} | {'Skor Hasil':<15}")
print("="*80)
for r in results:
    print(f"{r['file'][:58]:<60} | {r['score']:<15}")
print("="*80)
