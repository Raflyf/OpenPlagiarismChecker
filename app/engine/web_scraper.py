import os
import time
import random
import requests
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Sembunyikan peringatan jika situs web yang di-scrape berupa XML/RSS
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- Bank Korpus Lokal (SQLite3 Database) ---
import sqlite3 as _sqlite3
import json as _json
import threading as _threading
import ipaddress as _ipaddress

_BANK_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "corpus_bank", "bank.json")
_BANK_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "corpus_bank", "bank.db")
_bank_lock = _threading.Lock()  # lindungi mutasi DB dari race antar-thread

def _get_bank_conn():
    """Helper untuk membuka koneksi SQLite3 bank.db dengan PRAGMA WAL & cache teroptimasi."""
    conn = _sqlite3.connect(_BANK_DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")
    return conn

def init_bank_db():
    """Inisialisasi tabel SQLite3 dan lakukan auto-migrasi dari bank.json jika ada."""
    os.makedirs(os.path.dirname(_BANK_DB_PATH), exist_ok=True)
    with _bank_lock:
        conn = _get_bank_conn()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS corpus (url TEXT PRIMARY KEY, text TEXT)")
        conn.commit()
        
        # Migrasi otomatis jika bank.json versi lama ada
        if os.path.exists(_BANK_JSON_PATH):
            try:
                print(f"[Bank] Mengimpor data lama dari bank.json ke SQLite bank.db...")
                with open(_BANK_JSON_PATH, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                items = [(u, t) for u, t in data.items() if len(t) > 150]
                cur.executemany("INSERT OR IGNORE INTO corpus (url, text) VALUES (?, ?)", items)
                conn.commit()
                print(f"[Bank] Berhasil migrasi {len(items)} sumber ke bank.db SQLite.")
                # Rename bank.json agar migrasi hanya berjalan 1x
                os.rename(_BANK_JSON_PATH, _BANK_JSON_PATH + ".bak")
            except Exception as e:
                print(f"[Bank] Warning migrasi: {e}")
        conn.close()

def get_bank_urls():
    """Mengembalikan set URL yang tersimpan di bank.db (hemat RAM, ~1-2MB)."""
    init_bank_db()
    conn = _get_bank_conn()
    cur = conn.cursor()
    cur.execute("SELECT url FROM corpus")
    urls = set(row[0] for row in cur.fetchall())
    conn.close()
    return urls

def get_bank_texts(target_urls):
    """Mengambil teks spesifik HANYA untuk target_urls dari bank.db."""
    if not target_urls:
        return {}
    init_bank_db()
    conn = _get_bank_conn()
    cur = conn.cursor()
    result = {}
    target_list = list(target_urls)
    for i in range(0, len(target_list), 500):
        batch = target_list[i:i+500]
        placeholders = ",".join("?" for _ in batch)
        cur.execute(f"SELECT url, text FROM corpus WHERE url IN ({placeholders})", batch)
        for url, text in cur.fetchall():
            result[url] = text
    conn.close()
    return result

def load_corpus_bank():
    """Load seluruh isi bank.db sebagai dict (untuk backward compatibility Pemanggil)."""
    init_bank_db()
    conn = _get_bank_conn()
    cur = conn.cursor()
    cur.execute("SELECT url, text FROM corpus")
    data = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return data

def save_to_corpus_bank(new_corpus):
    """Simpan sumber baru ke bank.db SQLite (atomik & thread-safe)."""
    if not new_corpus:
        return
    init_bank_db()
    with _bank_lock:
        try:
            conn = _get_bank_conn()
            cur = conn.cursor()
            items = [(u, t) for u, t in new_corpus.items() if isinstance(t, str) and len(t) > 150]
            cur.executemany("INSERT OR IGNORE INTO corpus (url, text) VALUES (?, ?)", items)
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM corpus")
            total = cur.fetchone()[0]
            conn.close()
            print(f"[Bank] Tersimpan ke bank.db (total: {total} sumber)")
        except Exception as e:
            print(f"[Bank] PERINGATAN: gagal menyimpan ke bank.db: {e}")

def is_safe_url(url):
    """Sanitasi URL anti-SSRF: memblokir IP privat/local, loopback, dan metadata endpoint."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ('localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal'):
            return False
        try:
            ip = _ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False

# --- Rotasi API Key (round-robin) untuk backup & mengurangi rate-limit 429 ---
import itertools, threading

def _load_keys(*env_names):
    """Kumpulkan key dari beberapa env var (comma-separated), buang duplikat & kosong."""
    seen, keys = set(), []
    for name in env_names:
        for k in os.environ.get(name, "").split(","):
            k = k.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
    return keys

_s2_lock = threading.Lock()
_s2_cycle = None

def _next_s2_key():
    """Ambil S2 key berikutnya secara round-robin (thread-safe). None bila tak ada key."""
    global _s2_cycle
    with _s2_lock:
        if _s2_cycle is None:
            keys = _load_keys("S2_API_KEYS", "S2_API_KEY")
            _s2_cycle = itertools.cycle(keys) if keys else itertools.cycle([None])
        return next(_s2_cycle)

_cohere_lock = threading.Lock()
_cohere_cycle = None

def _next_cohere_key():
    """Ambil Cohere key berikutnya secara round-robin (thread-safe). None bila tak ada key."""
    global _cohere_cycle
    with _cohere_lock:
        if _cohere_cycle is None:
            keys = _load_keys("COHERE_KEYS", "COHERE_KEY")
            _cohere_cycle = itertools.cycle(keys) if keys else itertools.cycle([None])
        return next(_cohere_cycle)

def cohere_expand_queries(probe, n=3):
    """Pakai Cohere chat (command-a) sebagai query-expander: hasilkan variasi frasa
    pencarian akademik Indonesia untuk 1 probe. Connector web-search Cohere sudah
    dihapus (15 Sep 2025), jadi Cohere TIDAK dipakai mencari URL langsung; variasi
    ini diumpankan ke DuckDuckGo yang masih berfungsi. Return list frasa (bisa kosong)."""
    key = _next_cohere_key()
    if not key:
        return []
    try:
        prompt = (
            "Anda membantu mendeteksi plagiarisme skripsi Bahasa Indonesia. "
            f"Buat {n} variasi frasa pencarian singkat (5-8 kata) untuk menemukan sumber "
            "jurnal/skripsi yang mungkin menjadi asal kalimat berikut. Jawab HANYA daftar "
            "frasa, satu per baris, tanpa nomor atau penjelasan.\n\n"
            f"Kalimat: {probe}"
        )
        res = requests.post(
            "https://api.cohere.ai/v2/chat",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "command-a-03-2025",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3},
            timeout=20,
        )
        if res.status_code != 200:
            return []
        data = res.json()
        # v2 chat: message.content adalah list blok {type:'text', text:...}
        text = ""
        for block in data.get("message", {}).get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        lines = [ln.strip(" -*0123456789.\t") for ln in text.splitlines()]
        return [ln for ln in lines if len(ln.split()) >= 3][:n]
    except Exception:
        return []

# Budget global: jumlah probe yang boleh menyisir repo Indonesia (lambat karena throttling
# server kampus). Di-reset tiap run di get_candidate_urls(). Melindungi dari 75x hit.
# Lock: decrement dijalankan oleh banyak worker paralel -> tanpa lock, read-modify-write
# bisa balapan (jumlah crawl non-deterministik). Lock membuat konsumsi budget deterministik.
_INDO_REPO_BUDGET = 15
_INDO_REPO_LOCK = threading.Lock()

def fetch_semantic_scholar(probe):
    """Mencari paper di Semantic Scholar (Mencakup 200 Juta+ Makalah Akademik)"""
    urls_found = []
    texts_found = []
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        short_probe = " ".join(probe.split()[:15])
        params = {
            "query": short_probe,
            "limit": 5,
            "fields": "title,abstract,url,openAccessPdf"
        }
        s2_key = _next_s2_key()
        s2_headers = {"x-api-key": s2_key} if s2_key else {}
        res = requests.get(url, params=params, headers=s2_headers, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            for paper in data.get('data', []):
                p_url = paper.get('url') or f"https://semanticscholar.org/paper/{paper.get('paperId','')}"
                abstract = paper.get('abstract') or ""
                title = paper.get('title') or ""

                oa_pdf = paper.get('openAccessPdf')
                if oa_pdf and oa_pdf.get('url'):
                    p_url = oa_pdf['url']

                combined_text = f"{title}. {abstract}"
                if len(combined_text) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined_text)
    except Exception:
        pass
    return urls_found, texts_found

def fetch_crossref(probe):
    """Mencari metadata jurnal via Crossref (Repositori Terbesar DOI Jurnal)"""
    urls_found = []
    texts_found = []
    try:
        url = "https://api.crossref.org/works"
        short_probe = " ".join(probe.split()[:15])
        params = {
            "query": short_probe,
            "select": "URL,title,abstract",
            "rows": 15,
            "mailto": "research_turnitin_local@university.edu"
        }
        res = requests.get(url, params=params, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('message', {}).get('items', []):
                p_url = item.get('URL', '')
                title_list = item.get('title', [])
                title = title_list[0] if title_list else ""
                abstract = item.get('abstract', '')
                
                # Bersihkan tag HTML dari abstrak (CrossRef sering mengirim XML/HTML tags)
                import re
                abstract = re.sub(r'<[^>]+>', '', abstract)
                
                combined_text = f"{title}. {abstract}"
                if p_url and len(combined_text) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined_text)
    except Exception as e:
        print(f"[!] Warning: API/Scraper error -> {e}")
    return urls_found, texts_found

def fetch_openalex(probe):
    """Mencari full-text jurnal Indonesia via OpenAlex (250M+ Dokumen).
    Upgrade v3.3: pakai filter fulltext.search + language:id + is_oa:true
    untuk mendapat URL PDF langsung (bukan hanya abstrak metadata)."""
    urls_found = []
    texts_found = []
    try:
        short_probe = " ".join(probe.split()[:10])
        params = {
            "filter": f"language:id,open_access.is_oa:true,fulltext.search:{short_probe}",
            "per_page": 10,
            "select": "id,title,open_access,primary_location,abstract_inverted_index",
            "mailto": "research_turnitin_local@university.edu"
        }
        res = requests.get("https://api.openalex.org/works", params=params, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            for work in data.get("results", []):
                title = work.get('title') or ""
                loc = work.get('primary_location') or {}
                pdf_url = (work.get('open_access') or {}).get('oa_url') or \
                          (loc.get('pdf_url')) or \
                          (loc.get('landing_page_url'))
                if not pdf_url:
                    continue
                urls_found.append(pdf_url)
                abstract = work.get('abstract_inverted_index')
                abstract_text = ""
                if abstract:
                    word_index = []
                    for word, positions in abstract.items():
                        for pos in positions:
                            word_index.append((pos, word))
                    word_index.sort(key=lambda x: x[0])
                    abstract_text = " ".join([w[1] for w in word_index])
                texts_found.append((title + " " + abstract_text).strip())
    except Exception as e:
        print(f"[!] OpenAlex API error: {e}")
    return urls_found, texts_found

def fetch_google_scholar(probe):
    """Mencari repositori jurnal dari Google Scholar via ScrapingBee Proxy (Bypass CAPTCHA)"""
    urls_found = []
    try:
        import urllib.parse
        short_probe = " ".join(probe.split()[:15])
        query = urllib.parse.quote(short_probe)
        target_url = f"https://scholar.google.com/scholar?q={query}"
        
        import os
        scrapingbee_key = os.environ.get("SCRAPINGBEE_KEY", "")
        if not scrapingbee_key: return [], []
        api_url = "https://app.scrapingbee.com/api/v1/"
        params = {
            "api_key": scrapingbee_key,
            "url": target_url,
            "render_js": "false",
            "premium_proxy": "true",
            "country_code": "id"
        }
        res = requests.get(api_url, params=params, timeout=15)
        if res.status_code == 200:
            html = res.text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for h3 in soup.find_all('h3', class_='gs_rt'):
                a_tag = h3.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    urls_found.append(a_tag['href'])
    except Exception as e:
        print(f"[!] Warning: API/Scraper error -> {e}")
    return urls_found, []

def fetch_google_web(probe):
    """Mencari website publik & repositori dari Google Search biasa via ScrapingBee Proxy (Bypass CAPTCHA)"""
    urls_found = []
    try:
        import urllib.parse
        short_probe = " ".join(probe.split()[:15])
        
        import hashlib
        # Potong jadi 8 kata saja. 15 kata terlalu spesifik untuk search engine dan berujung 0 hasil
        short_probe = " ".join(probe.split()[:8])
        # DETERMINISME: varian query dari hash stabil probe (bukan random tanpa seed).
        variant = int(hashlib.md5(short_probe.encode("utf-8")).hexdigest(), 16) % 3
        if variant == 0:
            query = urllib.parse.quote(f'{short_probe} site:ac.id')
        elif variant == 1:
            query = urllib.parse.quote(f'{short_probe} filetype:pdf')
        else:
            query = urllib.parse.quote(short_probe)
            
        target_url = f"https://www.google.com/search?q={query}"
        
        import os
        scrapingbee_key = os.environ.get("SCRAPINGBEE_KEY", "")
        if not scrapingbee_key: return [], []
        api_url = "https://app.scrapingbee.com/api/v1/"
        params = {
            "api_key": scrapingbee_key,
            "url": target_url,
            "render_js": "false",
            "premium_proxy": "true",
            "country_code": "id"
        }
        res = requests.get(api_url, params=params, timeout=15)
        if res.status_code == 200:
            html = res.text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            # Ekstrak SEMUA link karena struktur Google berubah-ubah
            for a_tag in soup.find_all('a'):
                if 'href' in a_tag.attrs:
                    link = a_tag['href']
                    # Filter link valid (hindari link internal Google seperti accounts.google.com, dll)
                    if link.startswith('http') and 'google.com' not in link and 'google.co.id' not in link:
                        urls_found.append(link)
    except Exception as e:
        print(f"[!] Warning: API/Scraper error -> {e}")
    return urls_found, []

def fetch_garuda(probe):
    """Mencari Portal Jurnal Nasional (Garuda Kemdikbud/SINTA) via ScraperAPI Proxy"""
    urls_found = []
    try:
        import urllib.parse
        # Potong jadi 8 kata saja. 15 kata terlalu spesifik
        short_probe = " ".join(probe.split()[:8])
        query = urllib.parse.quote(short_probe)
        # Domain lama garuda.kemdikbud.go.id MATI (ConnectionError) sejak migrasi
        # Kemdikbud -> Kemdiktisaintek. Domain baru garuda.kemdiktisaintek.go.id hidup
        # (HTTP 200), selector a.title-article & path /documents tetap sama.
        target_url = f"https://garuda.kemdiktisaintek.go.id/documents?q={query}"
        
        import os
        scraperapi_key = os.environ.get("SCRAPERAPI_KEY", "")
        if not scraperapi_key: return [], []
        api_url = "https://api.scraperapi.com/"
        params = {
            "api_key": scraperapi_key,
            "url": target_url,
            "render": "false"
        }
        res = requests.get(api_url, params=params, timeout=15)
        if res.status_code == 200:
            html = res.text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for a_tag in soup.select('a.title-article'):
                if 'href' in a_tag.attrs:
                    url = a_tag['href']
                    if not url.startswith('http'):
                        url = "https://garuda.kemdiktisaintek.go.id" + url
                    urls_found.append(url)
    except Exception as e:
        print(f"[!] Warning: API/Scraper error -> {e}")
    return urls_found, []

def fetch_ddgs(probe):
    """Mencari website publik biasa via DuckDuckGo, dengan Prioritas Situs Kampus/Jurnal"""
    urls_found = []
    try:
        # Library duckduckgo_search lama (<=8.x) sudah mati (return 0). Utamakan paket
        # baru `ddgs`; fallback ke nama lama hanya bila paket baru tidak terpasang.
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        ddgs = DDGS()

        # FUZZY SEARCH KEMBALI!
        # Ekstraksi PDF sangat rawan typo (spasi hilang, dsb). Exact match mutlak sering berujung 0 hasil.
        # Kita gunakan Fuzzy Search di Search Engine dengan potongan 8 kata (standar Turnitin), bukan 15 kata!
        short_probe = " ".join(probe.split()[:8])

        import random, hashlib
        # DETERMINISME: pilih varian query berdasarkan hash STABIL probe. Python hash()
        # bawaan di-randomisasi per-proses (PYTHONHASHSEED) sehingga TIDAK reproducible
        # antar run; hashlib.md5 stabil. Probe sama -> varian sama -> korpus reproducible.
        # Ini syarat agar skor bisa dikalibrasi & dipertanggungjawabkan.
        variant = int(hashlib.md5(short_probe.encode("utf-8")).hexdigest(), 16) % 4
        if variant == 0:
            # PRIORITAS TERTINGGI: repositori indeks-besar (paling mungkin full-text)
            query = f'{short_probe} (site:123dok.com OR site:repository.bsi.ac.id OR site:etheses.uin-malang.ac.id OR site:doku.pub)'
        elif variant == 1:
            query = f'{short_probe} (jurnal OR repository OR skripsi OR eprints)'
        elif variant == 2:
            query = f'{short_probe} site:ac.id'
        else:
            query = short_probe

        # Ambil 25 hasil teratas untuk disortir dengan prioritas domain.
        # Backend 'auto' sering rotasi ke endpoint html.duckduckgo.com yang cert-nya
        # mismatch saat rate-limited (SSL CERTIFICATE_VERIFY_FAILED) -> 0 hasil & recall
        # hilang. Pin ke 'lite' (paling stabil), fallback berurutan bila kosong/gagal.
        results = []
        for backend in ("lite", "html", "auto"):
            try:
                results = ddgs.text(query, max_results=25, backend=backend)
                if results:
                    break
            except Exception:
                continue

        # SISTEM PRIORITAS via priority_domains.domain_priority (repositori akademik
        # Indonesia diutamakan). Skor tetap dari overlap nyata; ini hanya urutan crawl.
        try:
            from .priority_domains import domain_priority
        except ImportError:
            from priority_domains import domain_priority

        scored = []
        for res in list(results):
            if 'href' in res and res['href'].startswith('http'):
                scored.append((domain_priority(res['href']), res['href']))

        # Urutkan prioritas tertinggi dulu; ambil 12 teratas (naik dari 10 demi recall).
        scored.sort(key=lambda x: x[0], reverse=True)
        urls_found.extend([u for _, u in scored[:12]])
    except Exception as e:
        pass
    return urls_found, []

def fetch_doaj(probe):
    """Mencari artikel open-access di DOAJ (Directory of Open Access Journals — 9M+ articles)"""
    urls_found = []
    texts_found = []
    try:
        words = probe.split()
        short_probe = " ".join(words[:6])
        url = "https://doaj.org/api/search/articles/" + requests.utils.quote(short_probe)
        res = requests.get(url, params={"pageSize": 5}, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            for item in results:
                bibjson = item.get('bibjson', {})
                title = bibjson.get('title', '')
                abstract = bibjson.get('abstract', '')
                links = bibjson.get('link', [])
                p_url = ''
                for lnk in links:
                    if lnk.get('type') == 'fulltext':
                        p_url = lnk.get('url', '')
                        break
                if not p_url:
                    for ident in bibjson.get('identifier', []):
                        if ident.get('type') == 'doi':
                            p_url = f"https://doi.org/{ident.get('id', '')}"
                            break
                combined = f"{title}. {abstract}"
                if p_url and len(combined) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined)
    except Exception:
        pass
    return urls_found, texts_found

def fetch_arxiv(probe):
    """Mencari preprint di arXiv (2.4M+ papers, gratis tanpa API key). English STEM only."""
    urls_found = []
    texts_found = []
    try:
        import urllib.parse
        import re as _re
        short_probe = " ".join(probe.split()[:10])
        search_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{urllib.parse.quote(short_probe)}",
            "start": 0,
            "max_results": 3
        }
        res = requests.get(search_url, params=params, timeout=2.5)
        if res.status_code == 200:
            entries = _re.findall(r'<entry>(.*?)</entry>', res.text, _re.S)
            for entry in entries:
                t_match = _re.search(r'<title>(.*?)</title>', entry, _re.S)
                s_match = _re.search(r'<summary>(.*?)</summary>', entry, _re.S)
                id_match = _re.search(r'<id>(.*?)</id>', entry, _re.S)
                if t_match and s_match and id_match:
                    title = _re.sub(r'\s+', ' ', t_match.group(1)).strip()
                    summary = _re.sub(r'\s+', ' ', s_match.group(1)).strip()
                    link = id_match.group(1).strip()
                    combined = f"{title}. {summary}"
                    if len(combined) > 50:
                        urls_found.append(link)
                        texts_found.append(combined)
    except Exception:
        pass
    return urls_found, texts_found

def fetch_core(probe):
    """Mencari paper di CORE.ac.uk (300M+ papers). Butuh CORE_API_KEY (v3 Bearer token)."""
    urls_found = []
    texts_found = []
    import os
    core_key = os.environ.get("CORE_API_KEY", "")
    if not core_key:
        # Tanpa API key, CORE v3 konsisten timeout/401. Skip cepat agar tidak memblokir pipeline.
        return urls_found, texts_found
    try:
        short_probe = " ".join(probe.split()[:12])
        url = "https://api.core.ac.uk/v3/search/works"
        params = {"q": short_probe, "limit": 5}
        headers = {"Accept": "application/json", "Authorization": f"Bearer {core_key}"}
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('results', []):
                title = item.get('title', '')
                abstract = item.get('abstract', '') or ''
                p_url = ''
                for lnk in item.get('links', []):
                    if lnk.get('type') == 'download':
                        p_url = lnk.get('url', '')
                        break
                if not p_url:
                    p_url = item.get('downloadUrl') or item.get('sourceFulltextUrls', [''])[0] if item.get('sourceFulltextUrls') else ''
                if not p_url:
                    doi = item.get('doi', '')
                    if doi:
                        p_url = f"https://doi.org/{doi}"
                combined = f"{title}. {abstract}"
                if p_url and len(combined) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined)
    except Exception as e:
        print(f"[!] CORE API error: {e}")
    return urls_found, texts_found

def fetch_europe_pmc(probe):
    """Mencari artikel di Europe PMC (40M+ paper open-access, full-text gratis, tanpa API key)."""
    urls_found = []
    texts_found = []
    try:
        short_probe = " ".join(probe.split()[:8])
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            "query": f'"{short_probe}"',
            "format": "json",
            "pageSize": 5,
            "resultType": "core"
        }
        headers = {"User-Agent": "TurnitinLocalBot/4.0 (mailto:research_turnitin_local@university.edu)"}
        res = requests.get(url, params=params, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            results = data.get("resultList", {}).get("result", [])
            for item in results:
                title = item.get("title", "")
                abstract = item.get("abstractText", "")
                p_url = f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}"
                combined = f"{title}. {abstract}"
                if len(combined) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined)
    except Exception:
        pass
    return urls_found, texts_found

def fetch_onesearch_id(probe):
    """Mencari ke Indonesia OneSearch / IOS Perpusnas RI (Indeks 1.200+ Repositori & Jurnal Kampus se-Indonesia)."""
    urls_found = []
    try:
        short_probe = " ".join(probe.split()[:8])
        url = "https://onesearch.id/Search/Results"
        params = {"lookfor": short_probe}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, params=params, headers=headers, timeout=3.0)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            for a_tag in soup.select('a.title'):
                if 'href' in a_tag.attrs:
                    p_url = a_tag['href']
                    if not p_url.startswith('http'):
                        p_url = "https://onesearch.id" + p_url
                    urls_found.append(p_url)
    except Exception:
        pass
    return urls_found, []

def fetch_neliti(probe):
    """Mencari paper di Neliti (Reposisori Riset Terbesar Indonesia — 500.000+ Jurnal & Skripsi)."""
    urls_found = []
    try:
        short_probe = " ".join(probe.split()[:8])
        url = f"https://www.neliti.com/id/search?q={requests.utils.quote(short_probe)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=3.0)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            seen = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/publications/' in href or '/id/publications/' in href:
                    if not href.startswith('http'):
                        href = "https://www.neliti.com" + href
                    if href not in seen:
                        seen.add(href)
                        urls_found.append(href)
    except Exception:
        pass
    return urls_found, []

def fetch_rin_brin(probe):
    """Mencari riset & dataset nasional di RIN BRIN (Repositori Ilmiah Nasional — 300.000+ Data)."""
    urls_found = []
    texts_found = []
    try:
        short_probe = " ".join(probe.split()[:8])
        url = "https://rin.brin.go.id/api/search"
        params = {"q": short_probe, "per_page": 5}
        headers = {"User-Agent": "TurnitinClone/4.1 (mailto:skripsi_turnitin_local@university.ac.id)"}
        res = requests.get(url, params=params, headers=headers, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            items = data.get("data", {}).get("items", [])
            for item in items:
                title = item.get("name", "")
                snippet = item.get("description", "")
                p_url = item.get("url", "")
                combined = f"{title}. {snippet}"
                if p_url and len(combined) > 50:
                    urls_found.append(p_url)
                    texts_found.append(combined)
    except Exception:
        pass
    return urls_found, texts_found

# Session Circuit-Breaker: jika API eksternal gagal 3 kali berturut-turut, matikan untuk sisa probe run ini
_FAILED_APIS = set()
_FAILED_API_COUNTS = {}
_FAILED_APIS_LOCK = threading.Lock()

def _call_api_safe(api_name, fetch_func, probe):
    with _FAILED_APIS_LOCK:
        if api_name in _FAILED_APIS:
            return [], []
    try:
        urls, texts = fetch_func(probe)
        if urls or texts:
            with _FAILED_APIS_LOCK:
                _FAILED_API_COUNTS[api_name] = 0
        return urls, texts
    except Exception:
        with _FAILED_APIS_LOCK:
            _FAILED_API_COUNTS[api_name] = _FAILED_API_COUNTS.get(api_name, 0) + 1
            if _FAILED_API_COUNTS[api_name] >= 3:
                _FAILED_APIS.add(api_name)
        return [], []
        return [], []

def fetch_probe_multi(probe):
    """Mencari ke semua mesin secara serentak dengan free API fallbacks & Circuit Breaker Anti-RTO.
    Returns: (preloaded dict, normal_urls list, stats dict)"""

    # 1. API Akademik Indonesia & Internasional Prioritas
    u_ios, t_ios = _call_api_safe("IOS", fetch_onesearch_id, probe)
    u_neliti, t_neliti = _call_api_safe("Neliti", fetch_neliti, probe)
    u_brin, t_brin = _call_api_safe("BRIN", fetch_rin_brin, probe)
    u_ss, t_ss = _call_api_safe("SemanticScholar", fetch_semantic_scholar, probe)
    u_cr, t_cr = _call_api_safe("Crossref", fetch_crossref, probe)
    u_oa, t_oa = _call_api_safe("OpenAlex", fetch_openalex, probe)
    u_epmc, t_epmc = _call_api_safe("EuropePMC", fetch_europe_pmc, probe)

    # 1b. Additional free academic APIs
    u_doaj, t_doaj = _call_api_safe("DOAJ", fetch_doaj, probe)
    u_arxiv, t_arxiv = _call_api_safe("arXiv", fetch_arxiv, probe)
    u_core, t_core = _call_api_safe("CORE", fetch_core, probe)
    
    # 2. Try paid APIs
    u_gs, _ = fetch_google_scholar(probe)
    u_gw, _ = fetch_google_web(probe)
    u_gr, _ = fetch_garuda(probe)
    
    # 3. Try DuckDuckGo
    u_dd, _ = fetch_ddgs(probe)
    
    # 4. Direct search Indonesian repositories (no API limits, TAPI lambat: BSI ~15s/req).
    # Dibatasi global agar tidak jalan 75x (=375 request kampus). Hanya probe paling awal
    # (kalimat terpanjang/paling spesifik) yang menyisir repo lokal; sisanya sudah tercakup
    # API akademik + DDG. Repo tetap disisir menyeluruh via get_candidate_urls terpisah.
    u_repo, t_repo = [], []
    global _INDO_REPO_BUDGET
    # Klaim budget secara atomik (5 worker paralel): tanpa lock, read-modify-write bisa
    # ras -> jumlah crawl repo non-deterministik antar-run.
    _claim_repo = False
    with _INDO_REPO_LOCK:
        if _INDO_REPO_BUDGET > 0:
            _INDO_REPO_BUDGET -= 1
            _claim_repo = True
    if _claim_repo:
        try:
            from .indonesian_repos import search_all_indonesian_repos
            u_repo, t_repo = search_all_indonesian_repos(probe, max_repos=3, results_per_repo=2)
        except Exception as e:
            print(f"[!] Indonesian repos module error: {e}")
    
    # 5. NEW: Free API fallbacks with caching (jika paid APIs gagal)
    u_fallback, t_fallback = [], []
    try:
        from .free_api_fallbacks import search_with_fallbacks
        u_fallback, t_fallback = search_with_fallbacks(probe, use_cache=True)
    except Exception as e:
        print(f"[!] Free API fallbacks error: {e}")
    
    # Statistik per-API untuk probe ini
    stats = {
        "OneSearchID": len(u_ios),
        "Neliti": len(u_neliti),
        "SemanticScholar": len(u_ss),
        "Crossref": len(u_cr),
        "OpenAlex": len(u_oa),
        "EuropePMC": len(u_epmc),
        "DOAJ": len(u_doaj),
        "arXiv": len(u_arxiv),
        "CORE": len(u_core),
        "GoogleScholar": len(u_gs),
        "GoogleWeb": len(u_gw),
        "Garuda": len(u_gr),
        "DuckDuckGo": len(u_dd),
        "IndoRepos": len(u_repo),
        "Fallback": len(u_fallback),
    }
    
    # Gabungkan URL yang sudah ada abstraknya menjadi dictionary
    preloaded = {}
    for u, t in zip(u_ios, t_ios): preloaded[u] = t
    for u, t in zip(u_neliti, t_neliti): preloaded[u] = t
    for u, t in zip(u_ss, t_ss): preloaded[u] = t
    for u, t in zip(u_cr, t_cr): preloaded[u] = t
    for u, t in zip(u_epmc, t_epmc): preloaded[u] = t
    for u, t in zip(u_repo, t_repo): preloaded[u] = t
    for u, t in zip(u_doaj, t_doaj): preloaded[u] = t
    for u, t in zip(u_arxiv, t_arxiv): preloaded[u] = t
    for u, t in zip(u_core, t_core): preloaded[u] = t
    
    # OpenAlex dan Fallback CSE sering punya snippet/teks yang layak
    normal_urls = u_gs + u_gw + u_gr + u_dd
    
    for u, t in zip(u_oa, t_oa):
        if t and len(t) > 50:
            preloaded[u] = t
        else:
            normal_urls.append(u)
            
    for u, t in zip(u_fallback, t_fallback):
        if t and len(t) > 50:
            preloaded[u] = t
        else:
            normal_urls.append(u)
    
    return preloaded, normal_urls, stats

def get_candidate_urls(sentences, max_probes=100, progress_cb=None):
    """
    Fungsi ini kini mengembalikan dua hal:
    1. urls (List URL web biasa untuk discrape manual)
    2. preloaded_corpus (Dict berisi teks abstrak/jurnal berbayar yang langsung didapat via API)

    Strategi sampling 3-tier (75 probe):
    - Tier 1 (33%): Kalimat terpanjang (high-specificity, likely unique content)
    - Tier 2 (33%): Kalimat medium-length (balanced coverage)
    - Tier 3 (34%): Uniform sampling across document (ensures all chapters covered)
    """
    # Reset budget penyisiran repo Indonesia untuk run ini (probe Tier-1 didahulukan).
    # Dikunci agar konsisten dgn decrement ber-lock di fetch_probe_multi.
    global _INDO_REPO_BUDGET
    with _INDO_REPO_LOCK:
        _INDO_REPO_BUDGET = 15

    valid_sentences = [s for s in sentences if len(s.split()) >= 8]
    if len(valid_sentences) <= max_probes:
        probes = valid_sentences
    else:
        tier1_count = max_probes // 3
        tier2_count = max_probes // 3
        tier3_count = max_probes - tier1_count - tier2_count

        sorted_by_len = sorted(valid_sentences, key=lambda s: len(s.split()), reverse=True)

        tier1 = sorted_by_len[:tier1_count]

        mid_start = len(sorted_by_len) // 4
        mid_end = len(sorted_by_len) * 3 // 4
        mid_candidates = [s for s in sorted_by_len[mid_start:mid_end] if s not in tier1]
        if len(mid_candidates) >= tier2_count:
            step = len(mid_candidates) / tier2_count
            tier2 = [mid_candidates[int(i * step)] for i in range(tier2_count)]
        else:
            tier2 = mid_candidates

        used = set(id(s) for s in tier1 + tier2)
        uniform_candidates = [s for s in valid_sentences if id(s) not in used]
        if len(uniform_candidates) >= tier3_count:
            step = len(uniform_candidates) / tier3_count
            tier3 = [uniform_candidates[int(i * step)] for i in range(tier3_count)]
        else:
            tier3 = uniform_candidates

        probes = (tier1 + tier2 + tier3)[:max_probes]
        
    urls = set()
    preloaded_corpus = {}
    
    print(f"[API] Meluncurkan Bot AI & Browser Crawler untuk {len(probes)} Fingerprints...")
    
    # USE_COHERE_EXPANDER (default "0"=MATI): blok Cohere->DDG ini bottleneck utama
    # (Cohere trial 1 req/detik + 3 varian/probe x DDG yg sering kena rate-limit 429).
    # Sumber utama tetap datang dari DOAJ/Crossref/OpenAlex/Semantic Scholar + DDG
    # langsung di fase kedua (fetch_probe_multi). Nyalakan hanya bila butuh recall ekstra.
    if os.environ.get("USE_COHERE_EXPANDER", "0") == "1":
      try:
        # ========================================================================
        # COHERE QUERY-EXPANDER -> DUCKDUCKGO
        # Perplexity/Gemini/Tavily quota habis & Google CSE ditutup permanen.
        # Cohere web-search connector juga dihapus (15 Sep 2025). Yang tersisa &
        # gratis: Cohere chat (command-a) sebagai peng-EKSPAN query. Tiap probe
        # kita minta variasi frasa, lalu variasi itu dicari via DuckDuckGo (fetch_ddgs).
        # Ini menambah recall sumber tanpa bergantung pada API yang sudah mati.
        # ========================================================================
        def fetch_expanded(args):
            idx, probe = args
            found = set()
            for variant in cohere_expand_queries(probe, n=3):
                try:
                    v_urls, _ = fetch_ddgs(variant)
                    for u in v_urls:
                        if u and u.startswith('http'):
                            found.add(u)
                except Exception as e:
                    print(f"[!] fetch_ddgs varian gagal: {e}")
            return list(found)

        # max_workers=2: hormati Cohere trial 1 req/detik + hindari DDG rate-limit
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures_exp = {executor.submit(fetch_expanded, (i, p)): i for i, p in enumerate(probes)}
            for i, future in enumerate(concurrent.futures.as_completed(futures_exp)):
                if progress_cb:
                    progress_cb(futures_exp[future] + 1, len(probes) + len(probes))
                try:
                    for u in future.result():
                        urls.add(u)
                except Exception as e:
                    print(f"[!] expander future gagal: {e}")
      except Exception as e:
        print(f"[!] Cohere/DDG expander error: {e}")

    # --- blok API mati di bawah dinonaktifkan (disimpan sbagai referensi histori) ---
    if False:
        def fetch_pplx(args):
            idx, probe = args
            combined_urls = set()

            # 1. PERPLEXITY AI
            import time
            for attempt in range(3):
                try:
                    url_api = 'https://api.perplexity.ai/chat/completions'
                    import os
                    api_key = os.environ.get("PERPLEXITY_KEY", "")
                    if not api_key: raise Exception("No PERPLEXITY_KEY")
                    headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    }
                    payload = {
                        'model': 'sonar',
                        'messages': [
                            {'role': 'system', 'content': 'Find the exact academic journal or repository source for this text. Return URLs in citations.'},
                            {'role': 'user', 'content': f'Find exact source for: {probe}. Prioritize repository.bsi.ac.id, ejurnal.seminar-id.com, repository.umsu.ac.id, etheses.uin-malang.ac.id, ejournal.itn.ac.id, and PDF files.'}
                        ]
                    }
                    res = requests.post(url_api, json=payload, headers=headers, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        for u in data.get('citations', []):
                            combined_urls.add(u)
                        break # Sukses, keluar dari loop retry
                    elif res.status_code == 429: # Rate Limit
                        time.sleep(2 ** attempt) # Exponential backoff: 1s, 2s, 4s
                    else:
                        break # Error lain, hentikan retry
                except Exception as e:
                    if attempt == 2:
                        print(f"[!] Perplexity API Error: {e}")

            # 2. GEMINI AI GROUNDING (Sistem Load Balancer dengan Auto-Failover)
            import os
            gemini_env = os.environ.get("GEMINI_KEYS", "")
            if gemini_env:
                gemini_keys = gemini_env.split(',')
                for offset in range(len(gemini_keys)):
                    try:
                        # Coba key saat ini, jika gagal (429), maju ke key berikutnya (offset)
                        key_index = (idx + offset) % len(gemini_keys)
                        from google import genai
                        from google.genai import types
                        
                        client = genai.Client(api_key=gemini_keys[key_index])
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f'Find the exact URL source for this text: {probe}. Prioritize repository.bsi.ac.id, ejurnal.seminar-id.com, repository.umsu.ac.id, etheses.uin-malang.ac.id, ejournal.itn.ac.id, or site:ac.id',
                            config=types.GenerateContentConfig(
                                tools=[{'google_search': {}}],
                                temperature=0.0
                            )
                        )
                        if response.candidates:
                            for cand in response.candidates:
                                if cand.grounding_metadata and cand.grounding_metadata.grounding_chunks:
                                    for chunk in cand.grounding_metadata.grounding_chunks:
                                        if chunk.web and chunk.web.uri:
                                            combined_urls.add(chunk.web.uri)
                        break # Sukses, keluar dari loop failover
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower():
                            continue # Coba key berikutnya di iterasi loop
                        if offset == len(gemini_keys) - 1:
                            print(f"[!] Gemini API Error: {e}")
                
            # 3. COHERE AI GROUNDING
            for attempt in range(3):
                try:
                    import os
                    cohere_key = os.environ.get("COHERE_KEY", "")
                    if not cohere_key: raise Exception("No COHERE_KEY")
                    cohere_url = "https://api.cohere.ai/v1/chat"
                    headers = {
                        "Authorization": f"Bearer {cohere_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "message": f'Find the exact URL source for: "{probe}". Focus on repository.bsi.ac.id, ejurnal.seminar-id.com, repository.umsu.ac.id, etheses.uin-malang.ac.id, ejournal.itn.ac.id',
                        "model": "command-r-plus",
                        "connectors": [{"id": "web-search"}],
                        "temperature": 0.0
                    }
                    res = requests.post(cohere_url, json=payload, headers=headers, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        if 'documents' in data:
                            for doc in data['documents']:
                                if 'url' in doc:
                                    combined_urls.add(doc['url'])
                        break
                    elif res.status_code == 429:
                        time.sleep(2 ** attempt)
                    else:
                        break
                except Exception as e:
                    if attempt == 2:
                        print(f"[!] Cohere API Error: {e}")
                
            # 4. TAVILY AI SEARCH
            for attempt in range(3):
                try:
                    import os
                    tavily_key = os.environ.get("TAVILY_KEY", "")
                    if not tavily_key: raise Exception("No TAVILY_KEY")
                    tavily_url = "https://api.tavily.com/search"
                    payload = {
                        "api_key": tavily_key,
                        "query": f'"{probe}" site:ac.id OR ext:pdf',
                        "search_depth": "basic",
                        "max_results": 5
                    }
                    res = requests.post(tavily_url, json=payload, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        if 'results' in data:
                            for result in data['results']:
                                if 'url' in result:
                                    combined_urls.add(result['url'])
                        break
                    elif res.status_code == 429:
                        time.sleep(2 ** attempt)
                    else:
                        break
                except Exception as e:
                    if attempt == 2:
                        print(f"[!] Tavily API Error: {e}")
                
            return list(combined_urls)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures_pplx = {executor.submit(fetch_pplx, (i, p)): i for i, p in enumerate(probes)}
            for i, future in enumerate(concurrent.futures.as_completed(futures_pplx)):
                if progress_cb:
                    progress_cb(futures_pplx[future] + 1, len(probes) + len(probes))
                try:
                    c_urls = future.result()
                    for u in c_urls:
                        if u and u.startswith('http'):
                            urls.add(u)
                except Exception as e:
                    print(f"[!] pplx future gagal: {e}")
    # --- akhir blok API mati ---

    print(f"[API] Mencari jurnal dari {len(probes)} sampel kalimat via Semantic Scholar, Crossref & DuckDuckGo...")
    
    # Akumulasi statistik per-API lintas semua probe
    total_stats = {}
    probes_done = 0
    
    # Gunakan max_workers=5 agar ScrapingBee dan ScraperAPI tidak menolak request karena melanggar batas concurrency Free Tier
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(fetch_probe_multi, p) for p in probes]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if progress_cb:
                # Tambahkan offset progres dari Perplexity (100 kalimat)
                progress_cb(min(100, len(probes)) + i + 1, min(100, len(probes)) + len(probes))
            try:
                preloaded, ddg_urls, stats = future.result()
                
                # Akumulasikan statistik
                for api_name, count in stats.items():
                    total_stats[api_name] = total_stats.get(api_name, 0) + count
                
                # Masukkan hasil API langsung ke Corpus (tanpa perlu web-scrape)
                for u, t in preloaded.items():
                    preloaded_corpus[u] = t
                    
                # Masukkan hasil DuckDuckGo ke antrian URL scraping
                for u in ddg_urls:
                    if u not in preloaded_corpus:
                        urls.add(u)
                    
            except Exception as e:
                print(f"[!] Peringatan di get_candidate_urls worker: {e}")
            
            probes_done += 1
            # Cetak ringkasan progresif setiap 10 probe atau pada probe terakhir
            if probes_done % 10 == 0 or probes_done == len(probes):
                active = {k: v for k, v in total_stats.items() if v > 0}
                parts = [f"{k}:{v}" for k, v in sorted(active.items(), key=lambda x: -x[1])]
                total_found = sum(active.values())
                print(f"[API] Probe {probes_done}/{len(probes)} -- {total_found} sumber ditemukan | {', '.join(parts)}")
                
    print(f"\n[API] RANGKUMAN PENARIKAN SUMBER JURNAL (Total: {len(preloaded_corpus)} abstrak API + {len(urls)} web links):")
    active = {k: v for k, v in total_stats.items() if v > 0}
    for api_name, count in sorted(active.items(), key=lambda x: -x[1]):
        print(f"  |- {api_name:<18}: {count} sumber")
    return list(urls), preloaded_corpus

def scrape_url(url):
    """Mengekstrak teks mentah dari URL (Website atau PDF) menggunakan AbstractAPI Proxy untuk menembus WAF/Cloudflare"""
    if not is_safe_url(url):
        return url, "", 0
    total_bytes = 0
    # Banyak situs (Medium, repositori kampus) mengembalikan halaman kosong/blokir
    # tanpa User-Agent browser. Header ini menaikkan keberhasilan & kelengkapan teks.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    }
    try:
        import urllib.parse
        import os
        encoded_url = urllib.parse.quote(url)
        abstract_key = os.environ.get("ABSTRACT_KEY", "")
        if abstract_key:
            proxy_url = f"https://scrape.abstractapi.com/v1/?api_key={abstract_key}&url={encoded_url}"
            res = requests.get(proxy_url, timeout=4)
            if res.status_code != 200:
                res = requests.get(url, timeout=4, verify=False, headers=headers)
        else:
            res = requests.get(url, timeout=4, verify=False, headers=headers)
            
        if res.status_code == 200:
            total_bytes += len(res.content)
            import re
            
            # Deteksi jika file adalah PDF langsung
            if 'application/pdf' in res.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf'):
                import fitz
                doc = fitz.open(stream=res.content, filetype="pdf")
                text = ""
                try:
                    for page_num, page in enumerate(doc):
                        if page_num >= 30: break
                        text += page.get_text() + " "
                finally:
                    doc.close()
                text = re.sub(r'\s+', ' ', text).strip()
                return url, text, total_bytes
            else:
                # Parsing HTML biasa (Fast Scraping tanpa Deep PDF Crawl yang lambat)
                soup = BeautifulSoup(res.text, 'html.parser')
                for tag in soup(["script", "style", "nav", "footer", "header", "aside", "menu"]):
                    tag.decompose()
                text = soup.get_text(separator=' ')
                text = re.sub(r'\s+', ' ', text).strip()
                return url, text, total_bytes
    except Exception as e:
        pass
    return url, "", total_bytes

def scrape_all_candidates(urls, preloaded_corpus, progress_cb=None):
    """Mengeksekusi multi-threading untuk mengunduh web, lalu digabung dengan preloaded_corpus (Jurnal API).
    Bank lokal di-merge terlebih dahulu (cek lokal dulu, internet pelengkap)."""
    corpus = preloaded_corpus.copy()

    # BANK LOKAL (SQLite3): lookup instan via bank.db tanpa load memori raksasa
    bank_urls = get_bank_urls()
    found_urls = [u for u in urls if u in bank_urls]
    if found_urls:
        cached_texts = get_bank_texts(found_urls)
        corpus.update(cached_texts)
        print(f"[Bank] {len(cached_texts)} sumber ditemukan di bank.db lokal (skip scrape)")
    
    # Hapus URL yang sudah ada di bank / preloaded (tak perlu scrape ulang)
    urls = [u for u in urls if u not in bank_urls and u not in corpus]

    if not urls:
        save_to_corpus_bank(corpus)
        return corpus

    print(f"[Scraper] Bot Crawler mulai mengunduh {len(urls)} sumber web publik...")
    
    # Abaikan InsecureRequestWarning saat scrape blog/kampus yang SSL-nya mati
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    import time
    start_time = time.time()
    total_downloaded_bytes = 0
    # max_workers=8: 40 koneksi HTTPS serentak dari 1 IP memicu rate-limit server,
    # SSL handshake gagal, dan connection-pool jenuh (banyak sumber relevan gagal
    # download meski solo-nya sukses). 8 worker jauh lebih andal walau sedikit lambat.
    failed_urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(scrape_url, u): u for u in urls}
        total = len(futures)
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                url, text, downloaded_bytes = future.result()
                total_downloaded_bytes += downloaded_bytes
                if len(text) > 150: # Validasi panjang minimal teks
                    corpus[url] = text
                else:
                    failed_urls.append(futures[future])
            except Exception as e:
                failed_urls.append(futures[future])
                print(f"[!] Warning: API/Scraper error -> {e}")
            
            if progress_cb:
                elapsed = time.time() - start_time
                speed_mbps = (total_downloaded_bytes / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                if speed_mbps < 1.0:
                    speed_kbps = (total_downloaded_bytes / 1024) / elapsed if elapsed > 0 else 0
                    speed_str = f"{speed_kbps:.1f} KB/s"
                else:
                    speed_str = f"{speed_mbps:.2f} MB/s"
                progress_cb(i + 1, total, speed_str)

    # RETRY PASS: URL yang gagal (kosong/error) sering korban rate-limit sesaat, bukan
    # benar-benar mati. Coba sekali lagi dengan konkurensi sangat rendah (4 worker).
    if failed_urls:
        print(f"[Scraper] Retry {len(failed_urls)} sumber yang gagal (konkurensi rendah)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(scrape_url, u): u for u in failed_urls}
            for future in concurrent.futures.as_completed(futures):
                try:
                    url, text, downloaded_bytes = future.result()
                    total_downloaded_bytes += downloaded_bytes
                    if len(text) > 150:
                        corpus[url] = text
                except Exception:
                    pass

    # Simpan sumber baru ke bank lokal (makin kaya seiring waktu)
    save_to_corpus_bank(corpus)
    return corpus
