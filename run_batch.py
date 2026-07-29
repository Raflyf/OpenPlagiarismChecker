"""
Batch Uploader for Plagiarism Checker
Mengirim banyak file PDF/DOCX ke server lokal untuk diproses berurutan.
"""
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
        resp = session.post(URL_UPLOAD, files={'file': f}, data={
            'force_scrape': 'false',
            'use_semantic': 'true',
            'exclude_quotes': 'true',
            'exclude_biblio': 'true'
        })

    if resp.status_code != 200:
        print(f"    [!] Gagal upload: {resp.status_code} {resp.text[:100]}")
        continue

    data = resp.json()
    file_id = data.get('file_id')
    print(f"    [OK] file_id={file_id}")

    # Polling status
    max_retries = 600  # 10 menit (1 detik per poll)
    for attempt in range(max_retries):
        status_resp = session.get(URL_STATUS + file_id)
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress', 0)
            message = status_data.get('message', '')
            if progress is not None and message:
                print(f"    [{progress}%] {message}", end='\r')

            if status == 'completed':
                score = status_data.get('data', {}).get('total_similarity', 'N/A')
                print(f"\n    [SELESAI] Score: {score}%")
                results.append({
                    'file': filename,
                    'score': score,
                    'file_id': file_id
                })
                break
            elif status in ('error', 'cancelled'):
                msg = status_data.get('message', 'Unknown error')
                print(f"\n    [ERROR] {msg}")
                results.append({
                    'file': filename,
                    'score': 'ERROR',
                    'file_id': file_id,
                    'error': msg
                })
                break
        time.sleep(1)

print("\n" + "="*80)
print("HASIL BATCH PROCESSING")
print("="*80)
for r in results:
    print(f"{r['file'][:58]:<60} | {r['score']:<15}")
print("="*80)
