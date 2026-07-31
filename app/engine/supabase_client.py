"""
Supabase Client Utility Module for Plagiarism Checker
Dukungan terpusat REST API Supabase dengan otomatis batching, error handling, & fallback.
"""
import os
import json
import time
import urllib.parse
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATHS = [
    os.path.join(BASE_DIR, "..", "..", ".env"),
    os.path.join(BASE_DIR, "..", ".env")
]

def _load_env():
    env_vars = {}
    for p in ENV_PATHS:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
            except Exception:
                pass
    return env_vars

_env = _load_env()
SUPABASE_URL = os.environ.get("SUPABASE_URL", _env.get("SUPABASE_URL", "https://afrbbvxjywnnxxvqmlma.supabase.co"))
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", _env.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmcmJidnhqeXdubnh4dnFtbG1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU0NjY2NjQsImV4cCI6MjEwMTA0MjY2NH0.EQCemQPpN_BDMKfQi1aVMcwS0uKP1IXFa-WpdxelR2g"))

_session = requests.Session()
_session.headers.update({
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
})

def _clean_str(s):
    if not isinstance(s, str):
        return ""
    # PostgreSQL rejects null bytes (\x00 / \u0000) with error 22P05
    s = s.replace('\x00', '').replace('\u0000', '')
    return s.encode('utf-8', 'ignore').decode('utf-8').strip()

def is_supabase_configured():
    return bool(SUPABASE_URL and SUPABASE_KEY)

# --- 1. Corpus Bank Supabase Functions ---

def get_bank_urls_supabase():
    """Mengambil seluruh daftar URL yang tersimpan di Supabase corpus_bank."""
    if not is_supabase_configured():
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/corpus_bank?select=url"
        resp = _session.get(url, timeout=6.0)
        if resp.status_code == 200:
            rows = resp.json()
            return set(r['url'] for r in rows if 'url' in r)
    except Exception as e:
        print(f"[Supabase] Warning get_bank_urls: {e}")
    return None

def get_bank_texts_supabase(target_urls):
    """Mengambil teks spesifik untuk target_urls dari Supabase (batch 50 URL)."""
    if not is_supabase_configured() or not target_urls:
        return {}
    
    result = {}
    target_list = list(target_urls)
    
    for i in range(0, len(target_list), 50):
        batch = target_list[i:i+50]
        try:
            # Sanitasi URL untuk in-clause PostgREST
            formatted_urls = ",".join(f'"{_clean_str(u)}"' for u in batch)
            url = f"{SUPABASE_URL}/rest/v1/corpus_bank?select=url,text_content&url=in.({formatted_urls})"
            resp = _session.get(url, timeout=8.0)
            if resp.status_code == 200:
                rows = resp.json()
                for r in rows:
                    result[r['url']] = r['text_content']
        except Exception as e:
            print(f"[Supabase] Warning get_bank_texts batch {i}: {e}")
            
    return result

def save_to_corpus_bank_supabase(new_corpus):
    """Menyimpan/meng-upsert dict {url: text} baru ke Supabase corpus_bank (batch 50 items) dengan pembersihan Unicode null-bytes."""
    if not is_supabase_configured() or not new_corpus:
        return False
    
    items = []
    for u, t in new_corpus.items():
        if isinstance(t, str) and len(t) > 150:
            clean_u = _clean_str(u)
            clean_t = _clean_str(t)
            domain = _clean_str(urllib.parse.urlparse(clean_u).netloc)
            if clean_u and clean_t:
                items.append({"url": clean_u, "domain": domain, "text_content": clean_t})
            
    if not items:
        return False
        
    saved_count = 0
    headers = {"Prefer": "resolution=ignore-duplicates"}
    
    for i in range(0, len(items), 50):
        batch = items[i:i+50]
        try:
            url = f"{SUPABASE_URL}/rest/v1/corpus_bank"
            resp = _session.post(url, json=batch, headers=headers, timeout=10.0)
            if resp.status_code in (200, 201, 409):
                saved_count += len(batch)
            else:
                # Fallback: jika batch gagal (400 Bad Request karena 1 item korup), kirim per-item agar item valid tetap masuk
                for single_item in batch:
                    try:
                        r_single = _session.post(url, json=[single_item], headers=headers, timeout=3.0)
                        if r_single.status_code in (200, 201, 409):
                            saved_count += 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Supabase] Warning save_to_corpus_bank batch {i}: {e}")
            
    if saved_count > 0:
        print(f"[Supabase] Berhasil menyimpan {saved_count} sumber baru ke Supabase corpus_bank.")
        return True
    return False

# --- 2. Search Cache Supabase Functions ---

def get_cached_results_supabase(query_hash):
    """Mengambil hasil cache pencarian dari Supabase search_cache."""
    if not is_supabase_configured():
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/search_cache?select=results_json&query_hash=eq.{query_hash}"
        resp = _session.get(url, timeout=4.0)
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                return rows[0].get('results_json')
    except Exception as e:
        print(f"[Supabase] Warning get_cached_results: {e}")
    return None

def save_to_cache_supabase(query_hash, engine, results_dict):
    """Menyimpan cache hasil pencarian ke Supabase search_cache."""
    if not is_supabase_configured():
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/search_cache"
        payload = {
            "query_hash": query_hash,
            "engine": engine,
            "results_json": results_dict
        }
        headers = {"Prefer": "resolution=merge-duplicates"}
        resp = _session.post(url, json=payload, headers=headers, timeout=5.0)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[Supabase] Warning save_to_cache: {e}")
    return False

# --- 3. Analysis Jobs Status Supabase Functions ---

def save_job_status_supabase(file_id, session_id, status, progress=0, message="", result_json=None):
    """Menyimpan atau memperbarui status job analisis di Supabase analysis_jobs."""
    if not is_supabase_configured():
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/analysis_jobs"
        payload = {
            "file_id": file_id,
            "session_id": session_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        if result_json is not None:
            payload["result_json"] = result_json
            
        headers = {"Prefer": "resolution=merge-duplicates"}
        resp = _session.post(url, json=payload, headers=headers, timeout=5.0)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[Supabase] Warning save_job_status: {e}")
    return False

def get_job_status_supabase(file_id):
    """Mengambil status job analisis dari Supabase analysis_jobs."""
    if not is_supabase_configured():
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/analysis_jobs?select=*&file_id=eq.{file_id}"
        resp = _session.get(url, timeout=4.0)
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                return rows[0]
    except Exception as e:
        print(f"[Supabase] Warning get_job_status: {e}")
    return None
