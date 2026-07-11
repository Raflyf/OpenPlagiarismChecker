import time
import random
import requests
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from concurrent.futures import ThreadPoolExecutor
from ddgs import DDGS

# Sembunyikan peringatan jika situs web yang di-scrape kebetulan berupa XML/RSS
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def fetch_probe(probe):
    """Mencari satu probe ke DuckDuckGo"""
    urls_found = []
    try:
        ddgs = DDGS()
        short_probe = " ".join(probe.split()[:15])
        results = ddgs.text(f'{short_probe}', max_results=8)
        for res in list(results):
            if 'href' in res and not res['href'].endswith('.pdf'): 
                urls_found.append(res['href'])
        # Jeda lebih singkat karena sudah disebar ke beberapa thread
        time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        pass
    return urls_found

def get_candidate_urls(sentences, max_probes=120, progress_cb=None):
    """Mencari kandidat URL jurnal/referensi menggunakan sampel kalimat"""
    probes = random.sample(sentences, min(len(sentences), max_probes))
    urls = set()
    
    print(f"Mencari kandidat URL dari {len(probes)} sampel kalimat (Multi-Threading Cepat)...")
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_probe, p) for p in probes]
        total = len(futures)
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            urls.update(future.result())
            if progress_cb:
                progress_cb(i + 1, total)
            
    print(f"Berhasil mengumpulkan {len(urls)} kandidat URL.")
    return list(urls)

def scrape_url(url):
    """Mengunduh konten teks dari suatu URL (Mirip crawler bot Turnitin)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Ambil semua teks dari tag paragraf
            paragraphs = soup.find_all(['p', 'div', 'span'])
            text = " ".join([p.get_text() for p in paragraphs])
            # Bersihkan teks
            import re
            text = re.sub(r'\s+', ' ', text).strip()
            return url, text
    except:
        pass
    return url, ""

def scrape_all_candidates(urls, progress_cb=None):
    """Mengeksekusi multi-threading untuk mendownload isi artikel dari web"""
    corpus = {}
    print(f"Mengunduh isi dari {len(urls)} sumber web secara paralel...")
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        futures = [executor.submit(scrape_url, u) for u in urls]
        total = len(futures)
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            url, text = future.result()
            if len(text) > 100: # Hanya simpan web yang memiliki konten valid
                corpus[url] = text
            if progress_cb:
                progress_cb(i + 1, total)
                
    return corpus
