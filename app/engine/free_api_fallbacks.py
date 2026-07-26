"""
Free API Fallbacks - Pencarian Web dengan DuckDuckGo + Google CSE (opsional).
Default: DuckDuckGo (tanpa konfigurasi apapun, langsung jalan).
Jika GOOGLE_API_KEYS + GOOGLE_CX_ID diisi di .env, Google CSE dipakai lebih dulu;
DuckDuckGo menjadi fallback jika Google gagal. Kode CSE sengaja dipertahankan
agar siapapun yang memiliki key bisa langsung mengaktifkannya.
"""

import requests
import time
import hashlib
import json
import os
from pathlib import Path

import sqlite3
import threading

_CACHE_DB_PATH = Path(__file__).parent / '.search_cache.db'
_cache_lock = threading.Lock()

def _get_cache_conn():
    conn = sqlite3.connect(_CACHE_DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS cache (query_hash TEXT PRIMARY KEY, data TEXT, timestamp REAL)")
    return conn

def get_cache_key(query):
    """Generate cache key dari query"""
    return hashlib.md5(query.encode('utf-8')).hexdigest()

def get_cached_results(query, max_age_hours=24):
    """Ambil hasil dari SQLite3 cache jika masih fresh (<24 jam)"""
    try:
        q_hash = get_cache_key(query)
        cutoff = time.time() - (max_age_hours * 3600)
        with _cache_lock:
            conn = _get_cache_conn()
            cur = conn.cursor()
            cur.execute("SELECT data FROM cache WHERE query_hash = ? AND timestamp > ?", (q_hash, cutoff))
            row = cur.fetchone()
            conn.close()
            if row:
                data = json.loads(row[0])
                return data.get('urls', []), data.get('texts', [])
    except Exception:
        pass
    return None, None

def save_to_cache(query, urls, texts):
    """Simpan hasil ke SQLite3 cache (atomik, thread-safe, single-file)"""
    try:
        q_hash = get_cache_key(query)
        data_str = json.dumps({'urls': urls, 'texts': texts}, ensure_ascii=False)
        with _cache_lock:
            conn = _get_cache_conn()
            conn.execute("INSERT OR REPLACE INTO cache (query_hash, data, timestamp) VALUES (?, ?, ?)",
                         (q_hash, data_str, time.time()))
            conn.commit()
            conn.close()
    except Exception:
        pass

def search_google_custom(query, api_key, cx_id, max_results=10):
    """
    Mencari menggunakan Google Custom Search JSON API
    
    Google Custom Search API:
    - 10,000 queries/day GRATIS
    - Reliable dan fast
    - Official Google API
    - Mendukung site: operator dan advanced search
    
    Setup:
    1. Buat project di https://console.cloud.google.com/
    2. Enable Custom Search API
    3. Buat API key
    4. Buat Custom Search Engine di https://programmablesearchengine.google.com/
    5. Set "Search the entire web" = ON
    """
    urls_found = []
    texts_found = []
    
    try:
        # Google Custom Search JSON API endpoint
        base_url = "https://www.googleapis.com/customsearch/v1"
        
        # Lakukan multiple search dengan variasi query untuk coverage maksimal
        queries = [
            query,  # Original query
            f'{query} site:ac.id',  # Prioritas kampus Indonesia
            f'{query} (repository OR jurnal OR skripsi)',  # Prioritas akademik
        ]
        
        all_urls = set()
        
        for q in queries[:2]:  # Limit 2 query variations untuk menghemat quota
            # Google Custom Search bisa 10 results per call
            for start_index in range(1, min(max_results, 11), 10):
                params = {
                    'key': api_key,
                    'cx': cx_id,
                    'q': q,
                    'num': min(10, max_results - len(all_urls)),
                    'start': start_index
                }
                
                try:
                    response = requests.get(base_url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'items' in data:
                            for item in data['items']:
                                url = item.get('link', '')
                                title = item.get('title', '')
                                snippet = item.get('snippet', '')
                                
                                if url and url not in all_urls:
                                    all_urls.add(url)
                                    urls_found.append(url)
                                    
                                    # Gabungkan title + snippet sebagai text preview
                                    text = f"{title}. {snippet}"
                                    texts_found.append(text)
                                    
                                    if len(all_urls) >= max_results:
                                        break
                    
                    elif response.status_code == 429:
                        # Rate limit reached
                        print(f"[Google API] Rate limit reached, stopping...")
                        break
                    
                    elif response.status_code in [400, 403]:
                        # Sembunyikan JSON error panjang dari Google karena ini memang diblokir dari pusat (Google Policy)
                        print(f"[Google API] Akses ditolak (HTTP {response.status_code}) - Menggunakan fallback...")
                        break
                        
                    else:
                        print(f"[Google API] Error HTTP {response.status_code}")
                        break
                    
                    # Hindari rate limiting dengan delay kecil antar request
                    time.sleep(0.5)
                    
                except requests.exceptions.Timeout:
                    break
                except Exception as e:
                    print(f"[Google API] Error: {e}")
                    break
                
                if len(all_urls) >= max_results:
                    break
            
            if len(all_urls) >= max_results:
                break
        
        if urls_found:
            print(f"[Google Custom Search] Found {len(urls_found)} results")
        
    except Exception as e:
        pass  # Sembunyikan error global agar tidak panik
    
    return urls_found, texts_found

def search_duckduckgo_html(query, max_results=10):
    """
    Menggunakan library duckduckgo_search (DDGS) yang jauh lebih handal
    dalam mengatasi rate limiting dibandingkan scraping HTML manual.
    """
    urls_found = []
    texts_found = []
    
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        import time
        
        # Ambil 8 kata saja, JANGAN gunakan quotes "" karena spasi/newline dari ekstraksi PDF bisa menggagalkan exact match!
        search_query = " ".join(query.split()[:8])
        
        # Delay singkat acak untuk menghindari rate limit agresif
        time.sleep(0.5)
        
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=max_results))
            
            for res in results:
                url = res.get('href', '')
                title = res.get('title', '')
                body = res.get('body', '')
                
                if url:
                    urls_found.append(url)
                    texts_found.append(f"{title}. {body}")
                    
        # (log per-probe dibuang; total dilaporkan sekali di akhir get_candidate_urls)
            
    except Exception as e:
        # Timeout/rate-limit DDG lumrah & terjadi per-probe -> cetak sekali saja per proses.
        if not getattr(search_duckduckgo_html, "_warned", False):
            print(f"[!] DuckDuckGo API error (ditampilkan sekali): {e}")
            search_duckduckgo_html._warned = True

    return urls_found, texts_found

def search_with_fallbacks(query, use_cache=True):
    """
    Search menggunakan Google Custom Search API dengan caching,
    serta otomatis fallback ke DuckDuckGo HTML jika Google belum disetup.
    
    Returns:
        tuple: (list of URLs, list of text snippets)
    """
    
    # Check cache first
    if use_cache:
        cached_urls, cached_texts = get_cached_results(query, max_age_hours=24)
        if cached_urls:
            return cached_urls, cached_texts
    
    # Shorten query jika terlalu panjang (Google CSE limit 2048 chars)
    short_query = ' '.join(query.split()[:20])
    
    # Google Custom Search API credentials
    import os
    google_env = os.environ.get('GOOGLE_API_KEYS', '')
    google_api_keys = google_env.split(',') if google_env else []
    cx_id = os.environ.get('GOOGLE_CX_ID', '')
    
    all_urls = []
    all_texts = []
    
    is_configured = bool(google_api_keys) and bool(cx_id)
    
    if is_configured:
        # Try each API key with load balancing
        for api_key in google_api_keys:
            try:
                urls, texts = search_google_custom(short_query, api_key, cx_id, max_results=15)
                all_urls.extend(urls)
                all_texts.extend(texts)
                
                if len(all_urls) >= 10:
                    break  # Cukup, jangan buang quota
                    
            except Exception as e:
                print(f"[!] Google API key error: {e}")
                continue
    
    # Fallback ke DuckDuckGo jika Google tidak dikonfigurasi atau gagal
    if not all_urls:
            
        try:
            urls, texts = search_duckduckgo_html(short_query, max_results=15)
            all_urls.extend(urls)
            all_texts.extend(texts)
        except Exception as e:
            print(f"[!] Fallback DuckDuckGo error: {e}")
            
    # Cache results
    if use_cache and all_urls:
        save_to_cache(query, all_urls, all_texts)
    
    return all_urls, all_texts