# Audit R5 — Comprehensive Security, Bug & Optimization Audit

**Tanggal:** 29 Juli 2026
**Auditor:** AI Agent (System-wide)
**Cakupan:** Full codebase — engine/, server.py, templates/, konfigurasi

---

## 1. RINGKASAN EKSEKUTIF

| Kategori     | Total  | Critical | High  | Medium | Low   |
| ------------ | ------ | -------- | ----- | ------ | ----- |
| Security     | 5      | 1        | 2     | 2      | 0     |
| Bugs         | 6      | 2        | 2     | 1      | 1     |
| Optimasi     | 5      | 0        | 1     | 2      | 2     |
| Code Quality | 4      | 0        | 1     | 2      | 1     |
| **TOTAL**    | **20** | **3**    | **6** | **7**  | **4** |

---

## 2. SECURITY VULNERABILITIES

### S-01 [CRITICAL] — `os.system()` Shell Injection Risk

**Lokasi:** `App/server.py:514-515`
**Kode:**

```python
os.system("taskkill /F /IMngrok.exe >nul 2>&1")
os.system(f"taskkill /F /PID{os.getpid()} >nul 2>&1")
```

**Masalah:** `os.system()` menjalankan perintah melalui shell (`cmd.exe` / `/bin/sh`). Jika ada karakter shell-spesial dalam PID atau variabel lain, dapat terjadi command injection. Meski `os.getpid()` aman, praktik ini tetap tidak aman untuk maintainability.

**Rekomendasi:** Ganti dengan `subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'], ...)` dengan `shell=False`.

### S-02 [HIGH] — No CSRF Protection

**Lokasi:** `App/server.py` — semua route POST
**Masalah:** Tidak ada token CSRF pada endpoint `/upload`, `/cancel/<file_id>`, `/check_frozen`. Meskipun session ownership check ada, aplikasi rentan terhadap Cross-Site Request Forgery.

**Dampak:** Attacker bisa memaksa user mengupload dokumen atau membatalkan proses yang sedang berjalan.

**Rekomendasi:** Implementasikan Flask-WTF CSRF protection atau token verification pada form upload.

### S-03 [HIGH] — Rate Limiting IP Bypass via X-Forwarded-For

**Lokasi:** `App/server.py:356`

```python
client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
```

**Masalah:** Prioritas `X-Forwarded-For` bisa dimanipulasi attacker untuk bypass rate limiting.

**Rekomendasi:** Gunakan hanya nilai dari trusted proxy atau gunakan library `flask-limiter` dengan key function yang tepat.

### S-04 [MEDIUM] — Secure Filename Tidak Konsisten

**Lokasi:** `App/server.py:60-64` dan `App/server.py:295-296`
**Masalah:** `secure_filename` dari `werkzeug.utils` sudah di-import tapi tidak digunakan secara konsisten. Beberapa path menggunakan regex manual yang mungkin tidak menangani semua edge case.

**Rekomendasi:** Gunakan `secure_filename()` secara konsisten untuk semua user-supplied filename.

### S-05 [MEDIUM] — Flask Session Tanpa HTTP-Only & Secure Flags

**Lokasi:** `App/server.py:33-34`

```python
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
```

**Masalah:** Session cookie tidak dikonfigurasi dengan `SESSION_COOKIE_HTTPONLY` dan `SESSION_COOKIE_SAMESITE`.

**Rekomendasi:** Tambahkan konfigurasi session cookie yang aman.

---

## 3. BUGS

### B-01 [CRITICAL] — Path Case Inconsistency (Windows vs Linux)

**Lokasi:** Multiple files — `.gitignore`, `Run_batch.py`, `server.py`
**Masalah:** Path menggunakan lowercase `app/` di beberapa tempat dan uppercase `App/` di tempat lain.

- `.gitignore:23-24`: `app/corpus_bank/*.db`, `app/corpus_bank/*.bak`
- `Run_batch.py:8`: `os.path.join(BASE_DIR, "app", "before_Commercial Standard")`
- `server.py`: Menggunakan `App/` untuk path absolut

**Dampak:** Pada Linux/macOS (case-sensitive), file tidak akan ditemukan dan aplikasi crash.

**Rekomendasi:** Standarisasi ke `App/` di semua tempat (sesuai struktur direktori aktual).

### B-02 [CRITICAL] — Thread Safety Race Condition on results_db

**Lokasi:** `App/server.py` — `results_db` dictionary
**Masalah:** `RESULTS_DB_LOCK` digunakan di beberapa bagian kode, tapi tidak secara konsisten. Operasi read/write pada shared dictionary `results_db` dari multiple threads (main thread + background `process_document` thread) tanpa lock di beberapa tempat.

**Dampak:** Race condition dapat menyebabkan data corruption, status mismatch, atau crash.

**Rekomendasi:** Terapkan lock konsisten di ALL access ke `results_db`.

### B-03 [HIGH] — Memory Leak — results_db Tidak Terbatas

**Lokasi:** `App/server.py:103-118`

```python
def periodic_cleanup_task():
    """Background task membersihkan results_db dan file temporary lama."""
```

**Masalah:** Antara cleanup cycle (setiap 6 jam), `results_db` bisa membesar tanpa batas. Jika banyak file diupload dalam waktu singkat, penggunaan RAM melonjak.

**Rekomendasi:** Implementasi ukuran maksimum dictionary (LRU eviction) dan perpendek interval cleanup.

### B-04 [HIGH] — Orphaned Temporary Files

**Lokasi:** `App/server.py:199-202`

```python
frozen_tmp = frozen_path + ".tmp." + secrets.token_hex(4)
with open(frozen_tmp, "w", encoding="utf-8") as f:
    json.dump(corpus, f)
os.replace(frozen_tmp, frozen_path)
```

**Masalah:** Jika proses crash antara `open()` dan `os.replace()`, file `.tmp.*` akan tertinggal dan tidak dibersihkan. Akumulasi file sampah akan memenuhi disk.

**Rekomendasi:** Daftarkan cleanup untuk temporary files, atau gunakan context manager yang handle crash.

### B-05 [MEDIUM] — `check_cancelled()` Non-Atomic Read

**Lokasi:** `App/server.py:132-137`

```python
def check_cancelled():
    with RESULTS_DB_LOCK:
        entry = results_db.get(file_id, {})
    if entry.get('cancel_requested'):
```

**Masalah:** Lock hanya melindungi read dari dict, bukan read + check sequence. Antara release lock dan check `cancel_requested`, status bisa berubah.

**Rekomendasi:** Baca dan check dalam satu area lock.

### B-06 [LOW] — Error Message Information Disclosure

**Lokasi:** `App/server.py:261, 266`

```python
results_db[file_id].update({
    'status': 'error',
    'message': str(e)
})
```

**Masalah:** Exception message langsung diekspos ke client via API. Bisa saja berisi informasi sensitif (path, konfigurasi, dll).

**Rekomendasi:** Log error detail ke console/file, kirim pesan generik ke client.

---

## 4. OPTIMIZATION OPPORTUNITIES

### O-01 [HIGH] — No HTTP Connection Pooling

**Lokasi:** `App/engine/web_scraper.py`, `App/engine/free_api_fallbacks.py`, `App/engine/indonesian_repos.py`
**Masalah:** Menggunakan `requests.get()` langsung tanpa session. Setiap request membuat koneksi TCP baru.

```python
response = requests.get(url, timeout=10, headers=headers)
```

**Dampak:** Latensi tinggi, pemborosan resource TCP, potensi port exhaustion pada high-volume scraping.

**Rekomendasi:** Gunakan `requests.Session()` untuk connection reuse di semua HTTP calls.

### O-02 [MEDIUM] — ThreadPoolExecutor Tidak Pakai Context Manager

**Lokasi:** `App/engine/web_scraper.py`
**Masalah:** `ThreadPoolExecutor` digunakan tanpa `with` statement, sehingga `shutdown()` tidak dijamin dipanggil jika terjadi exception.

```python
executor = ThreadPoolExecutor(max_workers=SCRAPE_WORKERS)
# ... usage ...
# executor.shutdown() mungkin tidak terpanggil
```

**Rekomendasi:** Gunakan `with ThreadPoolExecutor(...) as executor:` untuk menjamin cleanup.

### O-03 [MEDIUM] — Large Corpus Loaded Entirely Into RAM

**Lokasi:** `App/engine/web_scraper.py` (bank loading)
**Masalah:** `bank.json` (ratusan MB) di-load ke RAM setiap startup. Ini tidak efisien.

**Rekomendasi:** Gunakan streaming JSON parser atau akses SQLite-based (bank.db) sebagai primary storage.

### O-04 [LOW] — Redundant Regex Compilation

**Lokasi:** `App/engine/extractor.py`
**Masalah:** Regex pattern digunakan langsung tanpa pre-compile, menyebabkan re-compile setiap pemanggilan.

**Rekomendasi:** Compile regex dengan `re.compile()` di module level.

### O-05 [LOW] — Unnecessary `str.strip()` Calls in Loop

**Lokasi:** `App/engine/shingling.py` — sentence processing loop
**Masalah:** Multiple `strip()` calls pada string yang sama bisa di-chain atau dieksekusi sekali saja.

**Rekomendasi:** Optimasi chaining atau simpan hasil strip.

---

## 5. CODE QUALITY

### Q-01 [HIGH] — Hardcoded Paths in Business Logic

**Lokasi:** `.gitignore`, `Run_batch.py:8`
**Masalah:** Path string `app/` di-hardcode langsung, bukan dari konfigurasi.

**Rekomendasi:** Gunakan BASE_DIR + os.path.join secara konsisten dari satu titik konfigurasi.

### Q-02 [MEDIUM] — Mixed Import Styles

**Lokasi:** Beberapa file `.py`
**Masalah:** Campuran absolute dan relative imports yang tidak konsisten:

```python
from .semantic_similarity import batch_semantic_check  # relative
# vs
from engine.web_scraper import get_candidate_urls  # absolute
```

**Rekomendasi:** Standardisasi ke satu style (prefer relative imports dalam package).

### Q-03 [MEDIUM] — Fungsi Dengan Parameter Terlalu Banyak

**Lokasi:** `App/engine/shingling.py:148`

```python
def calculate_similarity(doc_text, corpus, exclude_small=False, use_semantic=False,
                          semantic_threshold="auto", semantic_max_sources=None,
                          min_source_overlap=1, is_cancelled_cb=None):
```

**Masalah:** 8 parameter — indikasi fungsi melakukan terlalu banyak hal.

**Rekomendasi:** Refactor jadi class-based approach atau gunakan parameter object.

### Q-04 [LOW] — Print Statements for Debugging

**Lokasi:** Seluruh codebase
**Masalah:** Banyak `print()` statement untuk logging yang tidak bisa diatur levelnya.

**Rekomendasi:** Gunakan `logging` module dengan level configurable.

---

## 6. PRIORITAS PERBAIKAN

| Priority | ID   | Item                          | Effort   | Impact                                       |
| -------- | ---- | ----------------------------- | -------- | -------------------------------------------- |
| P0       | B-01 | Path case inconsistency       | 1 jam    | **CRITICAL** — Aplikasi tidak jalan di Linux |
| P0       | B-02 | Thread safety results_db      | 2 jam    | **CRITICAL** — Data corruption risk          |
| P0       | S-01 | os.system() -> subprocess     | 30 menit | **CRITICAL** — Security                      |
| P1       | S-02 | CSRF Protection               | 2 jam    | **HIGH** — Security                          |
| P1       | B-03 | Memory leak results_db        | 1 jam    | **HIGH** — Stability                         |
| P1       | O-01 | HTTP Connection Pooling       | 1 jam    | **HIGH** — Performance                       |
| P1       | S-03 | Rate limiting bypass fix      | 30 menit | **HIGH** — Security                          |
| P2       | O-02 | ThreadPoolExecutor cleanup    | 30 menit | **MEDIUM** — Reliability                     |
| P2       | B-04 | Orphaned temp files           | 30 menit | **MEDIUM** — Disk usage                      |
| P2       | S-04 | secure_filename consistency   | 30 menit | **MEDIUM** — Security                        |
| P3       | Q-01 | Hardcoded paths fix           | 1 jam    | **LOW** — Maintainability                    |
| P3       | B-05 | Atomic check_cancelled        | 30 menit | **LOW** — Reliability                        |
| P3       | Q-03 | Refactor calculate_similarity | 3 jam    | **LOW** — Maintainability                    |

---

## 7. METRIK KODE (ESTIMASI)

| Metric                        | Value                       |
| ----------------------------- | --------------------------- |
| Total Python files            | 10                          |
| Total lines (est)             | ~3500                       |
| Functions                     | ~40                         |
| Routes                        | 7                           |
| External package dependencies | 9                           |
| Thread count per request      | 1 daemon + N scrape workers |
| Total bug density             | ~5.7 bugs/KLOC              |
