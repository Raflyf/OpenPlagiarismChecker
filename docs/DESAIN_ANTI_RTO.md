# Desain Anti-RTO — Eliminasi Request Time Out pada Scraping Pipeline

**Versi:** 1.2
**Tanggal:** 29 Juli 2026
**Status:** Final Arsitektur

---

## 1. Ringkasan Masalah

**Gejala:** Scraping sering RTO (Request Time Out) — progress stuck lama di fase "Mencocokkan sumber internet", kadang gagal total dengan error timeout.

### Akar Masalah (Root Causes)

| #   | Root Cause                                                                                                    | Dampak                                                                                   | Lokus                            |
| --- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------- |
| RC1 | `fetch_probe_multi` memanggil ~15 API **secara sekuensial** per probe                                         | Latensi per probe = Σ(latensi semua API). 200 probe × 15 API = 3000+ hop                 | `web_scraper.py:858-970`         |
| RC2 | Sebagian besar fetch function **tidak punya timeout eksplisit**                                               | Koneksi menggantung 30-120 detik (default OS) sebelum timeout                            | Semua `fetch_*()`                |
| RC3 | Circuit breaker (`_call_api_safe`) **tidak punya recovery time** — sekali gagal, mati permanen untuk sesi itu | API yang sedang rate-limited tidak pernah pulih                                          | `web_scraper.py:842-852`         |
| RC4 | Thread pool **fixed size** (16 worker) tanpa adaptasi                                                         | Jika 50% request timeout, 16 worker tetap mengirim 16 request serempak → memperparah RTO | `get_candidate_urls`             |
| RC5 | **DNS lookup berulang** untuk domain lambat (kampus Indonesia, Garuda)                                        | Tambahan 2-5 detik per request sebelum koneksi dimulai                                   | OS-level                         |
| RC6 | Proxy pihak ketiga (AbstractAPI, ScrapingBee) jadi **single point of failure**                                | Jika proxy lambat/error, scraping URL gagal total                                        | `scrape_url`, `fetch_google_web` |

---

## 2. Arsitektur Target — Multi-Layer Anti-RTO

```
                            ┌─────────────────────────┐
                            │   Layer 5: Progressive   │
                            │   Result Streaming       │
                            └─────────────────────────┘
                                        │
                            ┌─────────────────────────┐
                            │   Layer 4: Adaptive      │
                            │   Concurrency Control    │
                            └─────────────────────────┘
                                        │
                            ┌─────────────────────────┐
                            │   Layer 3: Smart Circuit │
                            │   Breaker + Recovery     │
                            └─────────────────────────┘
                                        │
                            ┌─────────────────────────┐
                            │   Layer 2: Parallel API  │
                            │   Groups + Timeout       │
                            └─────────────────────────┘
                                        │
                            ┌─────────────────────────┐
                            │   Layer 1: Connection    │
                            │   Hardening              │
                            └─────────────────────────┘
```

**Catatan:** Probe count **tetap 200** (tidak diubah). Semua optimasi dilakukan di layer transport, paralelisasi scheduling, dan fault tolerance — bukan di jumlah probe.

---

## 3. Layer 1 — Connection Hardening

### 3.1 Session Factory dengan HTTPAdapter Tuning

**Masalah:** `_get_session()` cuma bikin `requests.Session()` tanpa konfigurasi pool.

**Solusi:** Konfigurasi `HTTPAdapter` dengan:

- `pool_connections=30` (koneksi simultan ke host berbeda)
- `pool_maxsize=60` (maks koneksi per host)
- Retry adapter: `total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]`
- Default timeout pasang di adapter level via `TransportAdapter`

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _get_session():
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=30, pool_maxsize=60,
                              max_retries=retry)
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        s.headers.update({'User-Agent': 'Mozilla/5.0 ...'})
        _thread_local.session = s
    return _thread_local.session
```

### 3.2 DNS Caching

**Masalah:** DNS lookup berulang untuk domain lambat (repo kampus, garuda).

**Solusi:** Set socket default timeout + gunakan DNS cache via `urllib3`:

```python
import socket
socket.setdefaulttimeout(5)  # DNS timeout maks 5 detik
# urllib3 already caches DNS internally with connection pool
```

### 3.3 Timeout Wajib di Semua Fetch Function

**Aturan:** Setiap `requests.get()`/`Session.get()` HARUS punya parameter `timeout=(connect, read)`.

| Function                             | Current Timeout | Target Timeout |
| ------------------------------------ | --------------- | -------------- |
| `scrape_url` (proxy)                 | 8s              | 10s            |
| `fetch_semantic_scholar`             | none            | (5, 10)        |
| `fetch_crossref`                     | none            | (3, 8)         |
| `fetch_openalex`                     | none            | (5, 15)        |
| `fetch_google_scholar` (ScrapingBee) | none            | (8, 15)        |
| `fetch_google_web` (ScrapingBee)     | none            | (8, 15)        |
| `fetch_garuda`                       | none            | (5, 10)        |
| `fetch_ddgs`                         | none            | (3, 8)         |
| `fetch_doaj`                         | none            | (5, 10)        |
| `fetch_arxiv`                        | none            | (5, 10)        |
| `fetch_core`                         | none            | (5, 10)        |
| `fetch_openaire`                     | none            | (5, 15)        |
| `fetch_hal`                          | none            | (5, 10)        |
| `fetch_europe_pmc`                   | none            | (5, 10)        |
| `fetch_onesearch_id`                 | none            | (5, 10)        |
| `fetch_neliti`                       | none            | (5, 10)        |
| `search_google_custom`               | none            | (3, 8)         |
| `search_duckduckgo_html`             | none            | (3, 8)         |

---

## 4. Layer 2 — Parallel API Groups + Timeout per Group

### 4.1 Restrukturasi `fetch_probe_multi`

**Masalah Saat Ini:** API dipanggil sekuensial (satu per satu). 15 API × 200 probe = 3000 hop serial.

**Solusi:** Kelompokkan API dalam 4 groups yang dijalankan paralel via `ThreadPoolExecutor` dengan timeout per group:

| Group              | Anggota                                           | Timeout     | Prioritas                     |
| ------------------ | ------------------------------------------------- | ----------- | ----------------------------- |
| **A — Akademik**   | Semantic Scholar, Crossref, OpenAlex, DOAJ, Arxiv | 15s         | Tertinggi — sumber akademik   |
| **B — Indonesia**  | IOS (OneSearch), Neliti, Garuda                   | 12s         | Tinggi — repositori kampus RI |
| **C — Web Publik** | DDGS, Google Web, Google Scholar                  | 10s         | Sedang — paling rawan RTO     |
| **D — Pelengkap**  | CORE, OpenAIRE, HAL, EuropePMC                    | 20s (async) | Rendah — tidak memblokir      |

### 4.2 ⚠️ Peringatan: Nested ThreadPool (Refinement Kritis)

**Masalah:** `get_candidate_urls` sudah menjalankan 200 probes paralel dengan `ThreadPoolExecutor(max_workers=16)`. Jika SETIAP probe memanggil `ThreadPoolExecutor(max_workers=4)` untuk parallel API groups, total thread aktif bisa melonjak ke **16 × 4 = 64 thread** → GIL contention, CPU thrashing, malah makin lambat.

**Solusi — pilih salah satu:**

**Opsi A (Rekomendasi — Quick Win):** Batasi upper-level worker pool menjadi **5-8 thread** saja. Cukup karena API groups sudah paralel di dalamnya:

```python
# Di get_candidate_urls — turun dari 16 ke 8
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(fetch_probe_multi, p) for p in probes]
```

**Opsi B (Lanjutan — Performa Maksimal):** Gunakan `asyncio` + `aiohttp` untuk internal API calls. Thread pool tetap 16, tapi internal fetch paralel via async I/O (1 thread, non-blocking):

```python
async def fetch_probe_multi_async(probe):
    async with aiohttp.ClientSession() as session:
        group_a = asyncio.create_task(_fetch_group_async("academic", probe, session))
        group_b = asyncio.create_task(_fetch_group_async("indonesia", probe, session))
        group_c = asyncio.create_task(_fetch_group_async("web", probe, session))
        group_d = asyncio.create_task(_fetch_group_async("supplement", probe, session))
        done, _ = await asyncio.wait([group_a, group_b, group_c, group_d], timeout=22)
```

**Rekomendasi:** Opsi A untuk quick wins (30 menit implementasi). Opsi B untuk fase 2 jika performa masih perlu ditingkatkan.

### 4.3 Implementasi Parallel Fetch

```python
def fetch_probe_multi(probe):
    """Parallel API groups with individual timeouts per group.
    Probe count tetap 200 — paralelisasi di level grup, bukan jumlah probe."""
    results = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_group, "academic", probe): "academic",
            executor.submit(_fetch_group, "indonesia", probe): "indonesia",
            executor.submit(_fetch_group, "web", probe): "web",
            executor.submit(_fetch_group, "supplement", probe): "supplement",
        }

        for future in as_completed(futures, timeout=22):
            group_name = futures[future]
            try:
                results[group_name] = future.result()
            except TimeoutError:
                results[group_name] = ({}, [], {})  # skip grup timeout

    # Merge all results
    preloaded, normal_urls, stats = {}, [], {}
    for p, u, s in results.values():
        preloaded.update(p)
        normal_urls.extend(u)
    return preloaded, normal_urls, stats
```

### 4.4 Early Exit Optimization

Jika Group A (akademik) sudah mengembalikan ≥5 sumber relevan, skip Group C (web publik — paling rawan RTO):

```python
def _fetch_group(group_name, probe):
    results = []
    if group_name == "academic":
        for api_func in ACADEMIC_APIS:
            u, t = call_api_safe_v2(api_func.__name__, api_func, probe)
            results.append((u, t))
            # Early exit: jika sudah dapat ≥5 sumber relevan
            if len([r for r in results if r[0]]) >= 5:
                break
    ...
```

---

## 5. Layer 3 — Smart Circuit Breaker + Time-Based Recovery

### 5.1 Masalah Saat Ini

`_call_api_safe` hanya cek `_FAILED_APIS` dict — jika ada di situ, API mati PERMANEN untuk sesi itu. Tidak ada mekanisme recovery.

### 5.2 Desain Circuit Breaker

```python
class APICircuitBreaker:
    """
    Circuit breaker per API dengan time-based graduated backoff.
    State machine: CLOSED → OPEN (N detik) → HALF_OPEN → CLOSED
    """
    BACKOFF = [30, 120, 600]  # graduated: 30s → 2m → 10m

    def __init__(self):
        self._failures = {}      # api_name → consecutive failures
        self._open_until = {}    # api_name → timestamp recovery
        self._lock = threading.Lock()

    def is_available(self, api_name):
        with self._lock:
            if api_name not in self._open_until:
                return True
            if time.time() >= self._open_until[api_name]:
                del self._open_until[api_name]  # HALF-OPEN
                return True
            return False

    def record_failure(self, api_name):
        with self._lock:
            n = self._failures.get(api_name, 0) + 1
            self._failures[api_name] = n
            idx = min(n - 1, len(self.BACKOFF) - 1)
            self._open_until[api_name] = time.time() + self.BACKOFF[idx]

    def record_success(self, api_name):
        with self._lock:
            self._failures.pop(api_name, None)
            self._open_until.pop(api_name, None)
```

### 5.3 Replace `_call_api_safe`

```python
_circuit_breaker = APICircuitBreaker()

def call_api_safe_v2(api_name, fetch_func, probe):
    if not _circuit_breaker.is_available(api_name):
        return [], []
    try:
        urls, texts = fetch_func(probe)
        _circuit_breaker.record_success(api_name)
        return urls, texts
    except Exception as e:
        _circuit_breaker.record_failure(api_name)
        return [], []
```

---

## 6. Layer 4 — Adaptive Concurrency Control

### 6.1 Dynamic Thread Pool Sizing

Thread pool mengecil jika RTO rate tinggi untuk mencegah snowball effect:

```python
class AdaptiveThreadPool:
    def __init__(self, max_workers=8):  # turun dari 16
        self.max_workers = max_workers
        self.current_workers = max_workers
        self.recent_timeouts = deque(maxlen=20)

    def get_workers(self):
        if self.recent_timeouts:
            rate = sum(self.recent_timeouts) / len(self.recent_timeouts)
        else:
            rate = 0.0
        if rate > 0.3:  # >30% request timeout
            self.current_workers = max(4, self.current_workers - 2)
        else:
            self.current_workers = min(self.max_workers, self.current_workers + 1)
        return self.current_workers
```

### 6.2 ⚠️ Timeout Escalation + SSRF Safety

Jika suatu request gagal timeout 2× berturut-turut di URL yang sama → bypass proxy (langsung HTTP tanpa AbstractAPI) sebagai fallback.

**WAJIB:** URL yang di-fallback tanpa proxy TETAP harus melewati fungsi sanitasi `is_safe_url()` untuk mencegah SSRF:

```python
def scrape_url_with_fallback(url):
    # Safety check WAJIB sebelum FALLBACK APAPUN
    if not is_safe_url(url):
        return url, "", 0

    # Coba dengan proxy dulu
    if abstract_key:
        try:
            return _scrape_via_proxy(url)
        except (requests.Timeout, requests.ConnectionError):
            pass  # fallback ke direct

    # Fallback direct HTTP — AMAN karena sudah lolos is_safe_url
    return _scrape_direct(url)

def _scrape_direct(url):
    """Direct HTTP scrape tanpa proxy — hanya dipanggil setelah is_safe_url."""
    headers = {'User-Agent': 'Mozilla/5.0 ...'}
    resp = requests.get(url, headers=headers, timeout=(5, 10))
    resp.raise_for_status()
    return url, resp.text, len(resp.text)
```

---

## 7. Layer 5 — Progressive Result Streaming

### 7.1 Pipeline Non-Blocking

**Masalah Saat Ini:** `process_document` menunggu SEMUA scraping selesai sebelum mulai generate report.

**Solusi:** Kirim hasil parsial secara progresif:

```
Timeline:
T+0s   → Mulai scraping (status UI: "Mencari sumber...")
T+3s   → Group A (Akademik) selesai → similarity parsial
T+6s   → Group B (Indonesia) selesai → update similarity
T+10s  → Group C (Web) selesai → update similarity
T+12s  → Scrape URL batch 1 selesai → update
T+18s  → Scrape URL batch 2 selesai → final
T+22s  → Report siap
```

Implementasi dengan callback progresif:

```python
def process_with_progress(probes, progress_cb=None):
    # Phase 1: Parallel API groups
    with ThreadPoolExecutor(max_workers=4) as ex:
        future = ex.submit(fetch_all_groups_parallel, probes)
        try:
            result = future.result(timeout=5)
            progress_cb(30, "Sumber akademik terkumpul")
        except TimeoutError:
            progress_cb(20, "Masih mencari sumber...")
    ...
```

---

## 8. Quick Wins — Urutan Eksekusi

| #   | Item                                                                 | Estimasi | Dampak                          |
| --- | -------------------------------------------------------------------- | -------- | ------------------------------- |
| 1   | Tambah `timeout=(3, 8)` ke semua `requests.get()` di fetch functions | 30 menit | **TINGGI** — cegah hang         |
| 2   | Ganti `_call_api_safe` dengan circuit breaker time-based             | 30 menit | **TINGGI** — API pulih otomatis |
| 3   | Parallel API groups + upper worker 5-8                               | 1 jam    | **TINGGI** — potong latensi 15× |
| 4   | HTTPAdapter + Retry di `_get_session`                                | 15 menit | **SEDANG**                      |
| 5   | Dynamic thread pool sizing                                           | 30 menit | **SEDANG**                      |
| 6   | Progressive status reporting                                         | 1 jam    | **RENDAH** — UX                 |

---

## 9. Perbandingan Performa (Estimasi)

| Skenario                  | Sebelum                                       | Sesudah (Layer 1-3)                           |
| ------------------------- | --------------------------------------------- | --------------------------------------------- |
| Semua API hidup           | 200 probe × 15 API sequential ≈ **>60 detik** | 200 probe × 4 groups parallel ≈ **<20 detik** |
| 3 API mati (RTO)          | Sequential: 3 × 30s timeout = **+90 detik**   | Circuit breaker skip 3 API dalam **<1 detik** |
| ScrapingBee rate limited  | Proxy gagal, scraping **0%**                  | Fallback direct HTTP, tetap dapat hasil       |
| Jaringan Indonesia lambat | DNS lookup 2-5s per request                   | DNS cache + pool reuse, **0 detik**           |

Dengan Layer 1-3, RTO rate diprediksi turun **80-90%**.

---

## 10. Risiko & Mitigasi

| Risiko                       | Dampak           | Mitigasi                               |
| ---------------------------- | ---------------- | -------------------------------------- |
| Parallel API kena rate limit | API 429          | Circuit breaker sudah handle           |
| Nested threadpool 64 thread  | GIL contention   | Upper worker dibatasi 5-8 (Opsi A)     |
| DNS caching basi             | Domain pindah IP | Cache TTL 300 detik                    |
| Proxy down total             | Scraping gagal   | Direct HTTP fallback + is_safe_url     |
| SSRF via fallback direct     | Security hole    | **WAJIB** is_safe_url sebelum fallback |

---

## 11. Kesimpulan

- **Probe count:** Tetap 200 (tidak diubah)
- **Estimasi implementasi:** 2-3 jam (semua layer), 1-2 jam (quick wins)
- **Target:** RTO rate turun 80-90%, latensi scraping turun 3×
- **Keamanan:** SSRF safety via is_safe_url di semua jalur fallback

Urutan eksekusi: Layer 1 → Layer 3 → Layer 2 → Layer 4 → Layer 5
