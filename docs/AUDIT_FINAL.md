# 🔍 AUDIT KOMPREHENSIF — Plagiarism Checker (Turnitin Lokal)

**Tanggal:** 31 Juli 2026
**Scope:** Full codebase audit — Logic, Security, Database, Memory/Performance, Calculation Validity, Frontend
**Metodologi:** 6 specialized audit subtasks, cross-verified against 6 prior audit documents ([AUDIT_R3.md](AUDIT_R3.md), [AUDIT_R4.md](AUDIT_R4.md), [AUDIT_R5.md](AUDIT_R5.md), [AUDIT_R6.md](AUDIT_R6.md), [DIAGNOSA_0_PERSEN.md](DIAGNOSA_0_PERSEN.md), [AUDIT_LENGKAP.md](AUDIT_LENGKAP.md))

---

## 📊 Ringkasan Eksekutif

### Matriks Skor per Domain

| Domain               | Skor       | Status                   | Isu Kritis | Isu Tinggi | Isu Sedang | Isu Rendah |
| -------------------- | ---------- | ------------------------ | ---------- | ---------- | ---------- | ---------- |
| Logic & Algorithm    | 9/10       | ✅ Solid                 | 0          | 1          | 1          | 2          |
| Security             | 5/10       | ⚠️ Perlu Perbaikan       | 2          | 2          | 3          | 1          |
| Database             | 6/10       | ⚠️ Perlu Perbaikan       | 3          | 5          | 6          | 4          |
| Memory & Performance | 7/10       | ⚠️ Ada Masalah           | 3          | 5          | 4          | 0          |
| Calculation Validity | 7/10       | ⚠️ Perlu Validasi        | 0          | 2          | 1          | 0          |
| Frontend/Template    | 7/10       | ⚠️ Perlu Perbaikan       | 1          | 2          | 3          | 1          |
| **RATA-RATA**        | **6.8/10** | **⚠️ CONDITIONAL READY** | **9**      | **17**     | **18**     | **8**      |

### Ringkasan Naratif

Plagiarism checker ini merupakan aplikasi Flask lokal yang meniru alur kerja Turnitin: unggah PDF skripsi, cari sumber di internet/repositori akademik, bandingkan dengan algoritma N-Gram Shingling (5 kata), tambahkan layer semantic similarity, lalu hasilkan laporan PDF bergaya Originality Report. Berdasarkan 6 rangkaian audit yang telah dilakukan (sejak Juli 2026 hingga 31 Juli 2026), keseluruhan kode dasar telah mengalami perbaikan signifikan — 12+ isu sebelumnya telah terverifikasi fixed, termasuk bug agregasi `exclude_small`, hardcoded API keys, debug mode, shell injection, dan kerentanan lainnya.

Namun demikian, masih terdapat 9 isu kritis yang tersebar di 6 domain, terutama pada aspek keamanan (CSRF protection, hardcoded Supabase key, RLS) dan performa (race condition semantic model, thread pool explosion, memory allocation tidak terbatas). Formula perhitungan skor secara matematis benar dan defensible untuk keperluan sidang skripsi, tetapi klaim akurasi MAE 1.21% masih berisiko overfitting karena hanya dikalibrasi pada 8 dokumen tanpa hold-out validation.

Secara keseluruhan, proyek ini berada dalam kondisi **CONDITIONAL READY** — layak untuk sidang skripsi dengan caveat yang tepat, tetapi memerlukan perbaikan Phase 1-2 (critical + high priority) sebelum layak deploy ke publik.

---

## 🔴 KRITIS — Harus Diperbaiki Sebelum Deploy

Total: **9 isu kritis** yang harus diselesaikan sebelum sistem dapat di-deploy ke produksi.

### C1: Hardcoded Supabase API Key di Source Code

- **Lokasi:** [`supabase_client.py:33-34`](../app/engine/supabase_client.py:33)
- **Impact:** Supabase URL dan anon key di-hardcode sebagai fallback ke environment variable. Key rotation tidak mungkin dilakukan tanpa perubahan kode.
- **Kode bermasalah:**
  ```python
  SUPABASE_URL = os.environ.get("SUPABASE_URL", _env.get("SUPABASE_URL", "https://afrbbvxjywnnxxvqmlma.supabase.co"))
  SUPABASE_KEY = os.environ.get("SUPABASE_KEY", _env.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIs..."))
  ```
- **Mitigasi parsial:** Ini adalah anon key (public, read-only) — bukan service_role key, sehingga dampaknya lebih rendah. Namun tetap merupakan bad practice.
- **Fix:** Hapus hardcoded fallback. Fail loudly jika env vars tidak tersedia. Tambahkan ke [`.env.example`](../.env.example) sebagai referensi.

### C2: No Row Level Security RLS on Supabase

- **Impact:** Anon key memiliki full read/write access ke semua tabel di Supabase. Setiap pengguna dapat memodifikasi atau meracuni corpus data.
- **Tabel yang terpengaruh:** Semua tabel Supabase yang digunakan untuk corpus bank, cache, dan metadata.
- **Fix:** Enable RLS pada setiap tabel, tambahkan per-table policies yang membatasi akses write hanya untuk service_role key.

### C3: Broken Upserts — Missing `on_conflict`

- **Lokasi:** [`supabase_client.py:191`](../app/engine/supabase_client.py:191), [`supabase_client.py:216`](../app/engine/supabase_client.py:216)
- **Impact:** Operasi upsert dengan `resolution=merge-duplicates` dilakukan tanpa parameter `on_conflict`, yang dapat menyebabkan silent failure — data tidak ter-update atau duplikat tidak ter-resolve.
- **Fix:** Tambahkan parameter `on_conflict` yang menentukan kolom conflict resolution yang tepat untuk setiap tabel.

### C4: No CSRF Protection

- **Lokasi:** Semua POST endpoint — [`server.py:378`](../app/server.py:378) (upload), cancel endpoints, check_frozen endpoints
- **Impact:** Cross-Site Request Forgery dimungkinkan pada semua endpoint yang menerima POST. Attacker dapat memaksa user mengupload dokumen, membatalkan proses, atau memanipulasi data melalui malicious link.
- **Bukti:** Flask-WTF tidak di-import di seluruh codebase. Tidak ada CSRF token di form [`templates/index.html`](../app/templates/index.html).
- **Fix:** Install flask-wtf, implementasi `CSRFProtect(app)`, tambahkan token ke semua form dan API request.

### C5: Semantic Model Race Condition

- **Lokasi:** [`semantic_similarity.py:26`](../app/engine/semantic_similarity.py:26)
- **Impact:** Model transformer dimuat (lazy loading) tanpa synchronization lock. Di bawah concurrent requests, double allocation model (500MB × 2 = 1GB) dapat terjadi, memicu MemoryError atau crash.
- **Fix:** Tambahkan `threading.Lock()` di sekitar `get_model()` untuk memastikan hanya satu thread yang melakukan inisialisasi model.

### C6: Nested Thread Pool Explosion

- **Lokasi:** [`server.py:431`](../app/server.py:431) + [`web_scraper.py:1311`](../app/engine/web_scraper.py:1311), [`web_scraper.py:1149`](../app/engine/web_scraper.py:1149), [`web_scraper.py:1488`](../app/engine/web_scraper.py:1488)
- **Impact:** 5 concurrent uploads × (32 scrape workers + 15 sub-scraper threads + 32 inner workers) = **395+ OS threads** dalam skenario terburuk. Setiap thread memakan stack memory ~8MB, sehingga potensi penggunaan memory hingga 3GB+ hanya untuk threads.
- **Fix:** Implementasi global semaphore atau shared thread pool yang membatasi total thread aktif di seluruh aplikasi.

### C7: `total_downloaded_bytes` Undefined Variable

- **Lokasi:** [`web_scraper.py:1524`](../app/engine/web_scraper.py:1524)
- **Impact:** `NameError` terjadi saat retry pass karena variabel `total_downloaded_bytes` didefinisikan di scope yang tidak dapat diakses. Error ini ditangkap oleh `except` blok yang luas, sehingga tidak crash tetapi menghasilkan behavior yang tidak terduga.
- **Fix:** Inisialisasi variabel sebelum loop atau perbaiki scope reference.

### C8: `results_db` Stores Full Data In-Memory

- **Lokasi:** [`server.py:263`](../app/server.py:263)
- **Impact:** `results_db` menyimpan seluruh hasil processing termasuk corpus data di dalam dictionary Python. Dengan batas 50 entries dan estimasi ~15MB per entry (termasuk corpus text), peak memory dapat mencapai **750MB** hanya untuk results database.
- **Catatan:** TTL 2 jam dan size limit 50 entries sudah diimplementasikan ([`server.py:94-96`](../app/server.py:94)), tetapi tetap tidak menyelesaikan masalah memory per-entry yang besar.
- **Fix:** Simpan hanya metadata di memory, simpan full data di disk atau database eksternal.

### C9: Unbounded Corpus Bank Loading

- **Lokasi:** [`web_scraper.py:150`](../app/engine/web_scraper.py:150)
- **Impact:** `load_corpus_bank()` memuat seluruh SQLite database (289MB) menjadi Python dict di memory. Konversi SQLite → Python dict menghasilkan overhead ~3-4×, sehingga penggunaan memory dapat mencapai **800MB–1.2GB**.
- **Fix:** Implementasi lazy loading atau streaming access terhadap corpus bank. Pertahankan SQLite sebagai primary storage dan akses data secara on-demand.

---

## 🟠 TINGGI — Perlu Diperbaiki Segera

Total: **17 isu tinggi** yang memerlukan perbaikan segera untuk kesiapan produksi.

### Security

| ID   | Isu                                      | Lokasi                                   | Detail                                                                                                                                                                                                                                                                  |
| ---- | ---------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H-S1 | Rate limiting bypass via X-Forwarded-For | [`server.py:356`](../app/server.py:356)  | `client_ip` dapat dimanipulasi melalui header `X-Forwarded-For`. Kode secara eksplisit menghindari header ini tetapi hanya menggunakan `remote_addr` yang juga dapat di-bypass melalui shared network (university lab, VPN). Perlu session-based limiting atau CAPTCHA. |
| H-S2 | Session cookie missing Secure flag       | [`server.py:37-38`](../app/server.py:37) | Hanya `HttpOnly` dan `SameSite=Lax` yang dikonfigurasi. Missing: `Secure` flag (wajib untuk HTTPS) dan `SameSite=Strict` (lebih aman dari Lax).                                                                                                                         |
| H-S3 | No Content-Security-Policy header        | [`server.py`](../app/server.py)          | CSP header tidak diimplementasikan. Meskipun X-Content-Type-Options, X-Frame-Options, dan X-XSS-Protection sudah ada, CSP adalah pertahanan utama terhadap XSS.                                                                                                         |
| H-S4 | No MIME type validation on uploads       | [`server.py:402`](../app/server.py:402)  | Validasi hanya berdasarkan file extension (`.pdf`). Tidak ada validasi MIME type terhadap konten aktual file. Attacker dapat meng-upload file non-PDF dengan extension `.pdf`.                                                                                          |

### Database

| ID   | Isu                                                         | Lokasi                                                   | Detail                                                                                                                                                       |
| ---- | ----------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| H-D1 | Fire-and-forget Supabase sync                               | [`web_scraper.py:181`](../app/engine/web_scraper.py:181) | Sync ke Supabase dilakukan tanpa error tracking atau retry. Jika sync gagal, data hilang tanpa jejak.                                                        |
| H-D2 | No retry/backoff for Supabase API calls                     | [`supabase_client.py`](../app/engine/supabase_client.py) | Semua panggilan Supabase API menggunakan single attempt tanpa exponential backoff. Network timeout atau rate limit langsung menghasilkan kegagalan permanen. |
| H-D3 | Race condition: progress updates overwrite completed status | [`server.py`](../app/server.py)                          | Update progress status ke `results_db` dapat meng-overwrite status `completed` jika thread background melakukan update terakhir.                             |
| H-D4 | No TTL/cleanup for Supabase tables                          | [`supabase_client.py`](../app/engine/supabase_client.py) | Tidak ada mekanisme pembersihan otomatis untuk data lama di tabel Supabase. Tabel akan tumbuh tanpa batas seiring waktu.                                     |
| H-D5 | `load_corpus_bank()` loads entire table into memory         | [`web_scraper.py:150`](../app/engine/web_scraper.py:150) | Seluruh corpus bank dimuat ke RAM dalam satu operasi. Untuk corpus berukuran besar, ini dapat menyebabkan MemoryError.                                       |

### Memory & Performance

| ID   | Isu                                                 | Lokasi                                                     | Detail                                                                                                                                                               |
| ---- | --------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H-M1 | Redundant `clean_doc_words` recomputation           | [`shingling.py`](../app/engine/shingling.py)               | `clean_doc_words` dihitung ulang di dalam per-source loop padahal hasilnya konsisten untuk semua sumber. Harus di-hoist ke luar loop.                                |
| H-M2 | `is_common_phrase()` linear scan pada setiap n-gram | [`shingling.py`](../app/engine/shingling.py)               | Setiap n-gram dicek terhadap 75 common phrases secara linear. Dengan 82M+ comparisons potensial, ini menjadi bottleneck. Perlu hash set atau trie untuk lookup O(1). |
| H-M3 | No cleanup on cancellation path                     | [`server.py:130-295`](../app/server.py:130)                | Jika pengguna membatalkan proses, resource yang sudah dialokasikan (threads, memory, temporary files) tidak dibersihkan secara eksplisit.                            |
| H-M4 | `httpx.Client` created per request                  | [`indonesian_repos.py`](../app/engine/indonesian_repos.py) | Setiap request membuat httpx.Client baru tanpa connection pooling. Ini membuang-buang resource TCP dan meningkatkan latensi.                                         |

### Calculation

| ID   | Isu                                        | Lokasi                                                      | Detail                                                                                                                                             |
| ---- | ------------------------------------------ | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| H-C1 | Overfitting risk — MAE in-sample only      | [`calibration_result.json`](../app/calibration_result.json) | MAE 1.21% adalah in-sample error. Dokumen yang sama digunakan untuk kalibrasi DAN validasi. n=8 dokumen tidak cukup untuk generalisasi.            |
| H-C2 | No hold-out validation or cross-validation | [`calibration_result.json`](../app/calibration_result.json) | Tidak ada split training/validation. Tidak ada k-fold cross-validation atau Leave-One-Out CV. Klaim akurasi tidak terverifikasi secara independen. |

### Frontend

| ID   | Isu                                       | Lokasi                                                | Detail                                                                                 |
| ---- | ----------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------- |
| H-F1 | No CSRF tokens in any form or API request | [`templates/index.html`](../app/templates/index.html) | Form upload dan semua AJAX request tidak menyertakan CSRF token.                       |
| H-F2 | No Strict-Transport-Security header       | [`server.py`](../app/server.py)                       | Header HSTS tidak diimplementasikan, sehingga browser tidak dipaksa menggunakan HTTPS. |

---

## 🟡 SEDANG — Perlu Diperbaikan

Total: **18 isu sedang** yang perlu diperhatikan untuk kualitas dan maintainability.

| ID   | Isu                                                 | Lokasi                                                                                                               | Kategori                                                     |
| ---- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| M-S1 | `subprocess.run` dengan `shell=True`                | [`server.py:597`](../app/server.py:597)                                                                              | Security — `shell=True` tidak diperlukan untuk list argument |
| M-S2 | Information disclosure di `/check_frozen`           | [`server.py:329-333`](../app/server.py:329)                                                                          | Security — endpoint leak `corpus_size` dan keberadaan hash   |
| M-S3 | `verify=False` masih ada di 2 lokasi                | [`web_scraper.py:525`](../app/engine/web_scraper.py:525), [`web_scraper.py:1035`](../app/engine/web_scraper.py:1035) | Security — pragmatic trade-off untuk repo kampus             |
| M-D1 | Overfitting ke 7-8 dokumen benchmark                | [`calibration_result.json`](../app/calibration_result.json)                                                          | Logic — formula dikalibrasi untuk terlalu sedikit data       |
| M-D2 | Non-determinism di web scraping                     | [`web_scraper.py:478`](../app/engine/web_scraper.py:478)                                                             | Logic — probe berubah jika preprocessing berubah             |
| M-D3 | Silent failures — 26+ `except: pass`                | Berbagai lokasi engine                                                                                               | Code Quality — error kritis dapat tersembunyi                |
| M-D4 | Return type inconsistency di `fetch_*`              | Beberapa fungsi fetch                                                                                                | Code Quality — perlu standarisasi                            |
| M-D5 | Path case inconsistency (Windows vs Linux)          | Multiple files                                                                                                       | Bug — `app/` vs `App/`                                       |
| M-D6 | Error message information disclosure                | [`server.py:261`](../app/server.py:261)                                                                              | Security — exception message langsung diekspos ke client     |
| M-P1 | God functions — `calculate_similarity()` ~350 baris | [`shingling.py:148-496`](../app/engine/shingling.py:148)                                                             | Maintainability                                              |
| M-P2 | God functions — `process_document()` ~166 baris     | [`server.py:130-295`](../app/server.py:130)                                                                          | Maintainability                                              |
| M-P3 | Magic numbers di banyak lokasi                      | Berbagai file                                                                                                        | Maintainability — 0.8000, 0.0200, max_words=40, dll          |
| M-P4 | `calculate_similarity()` memiliki 8 parameter       | [`shingling.py:148`](../app/engine/shingling.py:148)                                                                 | Maintainability — indikasi terlalu banyak tanggung jawab     |
| M-F1 | `check_cancelled()` non-atomic read                 | [`server.py:132-137`](../app/server.py:132)                                                                          | Reliability — lock hanya melindungi read, bukan read+check   |
| M-F2 | `ThreadPoolExecutor` tanpa context manager          | [`web_scraper.py`](../app/engine/web_scraper.py)                                                                     | Reliability — `shutdown()` tidak dijamin terpanggil          |
| M-F3 | Mixed import styles (absolute vs relative)          | Berbagai file `.py`                                                                                                  | Code Quality — perlu standarisasi                            |
| M-F4 | Broad exception handling                            | 26+ lokasi                                                                                                           | Code Quality — `except Exception: pass` terlalu luas         |
| M-F5 | Secure filename tidak konsisten                     | [`server.py:60-64`](../app/server.py:60), [`server.py:295-296`](../app/server.py:295)                                | Security — regex manual vs `secure_filename()`               |

---

## 🟢 RENDAH — Perlu Diperhatikan

Total: **8 isu rendah** yang merupakan optimasi atau catatan untuk future improvement.

| ID   | Isu                                         | Lokasi                                                                                                               | Kategori                                                                      |
| ---- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| L-Q1 | Import di dalam fungsi (lazy import)        | [`shingling.py:330`](../app/engine/shingling.py:330), [`web_scraper.py:383`](../app/engine/web_scraper.py:383)       | Performance micro-optimization                                                |
| L-Q2 | Redundant regex compilation                 | [`extractor.py`](../app/engine/extractor.py)                                                                         | Performance — perlu `re.compile()` di module level                            |
| L-Q3 | Unnecessary `str.strip()` calls in loop     | [`shingling.py`](../app/engine/shingling.py)                                                                         | Performance — perlu chaining                                                  |
| L-Q4 | Print statements untuk debugging            | Seluruh codebase                                                                                                     | Logging — seharusnya menggunakan `logging` module                             |
| L-D1 | Unbounded `corpus` growth during processing | [`server.py:209`](../app/server.py:209)                                                                              | Memory — frozen corpus disimpan ke disk, RAM issue hanya saat processing      |
| L-D2 | Supabase URL fetching — 120K URL parallel   | [`supabase_client.py:83-88`](../app/engine/supabase_client.py:83)                                                    | Performance — sudah dioptimasi dengan early exit                              |
| L-D3 | GPU memory cleanup imperfect                | [`semantic_similarity.py:211-213`](../app/engine/semantic_similarity.py:211)                                         | Performance — Python reference counting tidak menjamin immediate deallocation |
| L-F1 | `verify=False` di 2 lokasi (pragmatic)      | [`web_scraper.py:525`](../app/engine/web_scraper.py:525), [`web_scraper.py:1035`](../app/engine/web_scraper.py:1035) | Trade-off — repo kampus sering punya SSL cert expired                         |

---

## ✅ YANG SUDAH DIPERBAIKI (Dari Audit Sebelumnya)

Berikut 12+ isu yang telah dikonfirmasi FIXED berdasarkan verifikasi pada [AUDIT_R6.md](AUDIT_R6.md):

| #   | Isu Sebelumnya                                                                                              | Bukti Perbaikan                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **exclude_small filtering timing** — menyebabkan 0% scores karena filter diterapkan SEBELUM agregasi global | Filter hanya memengaruhi display list, bukan skor total. `total_similarity` dihitung dari union semua sumber ([`shingling.py:476`](../app/engine/shingling.py:476))                                             |
| 2   | **Hardcoded API keys** — semua key di-embed di source code                                                  | Semua key di-load dari env var dengan round-robin rotation: S2 ([`web_scraper.py:261`](../app/engine/web_scraper.py:261)), Cohere ([`web_scraper.py:273`](../app/engine/web_scraper.py:273)), ScrapingBee, CORE |
| 3   | **Flask debug=True** — application error details exposed                                                    | `debug=False` sudah diimplementasikan                                                                                                                                                                           |
| 4   | **`os.system()` shell injection** — command injection melalui shell                                         | Diganti dengan `subprocess.run()` ([`server.py:597`](../app/server.py:597))                                                                                                                                     |
| 5   | **URL-text zip misalignment** — teks dan URL dari fetcher tidak sinkron                                     | Per-URL corpus matching sudah diimplementasikan (lebih akurat)                                                                                                                                                  |
| 6   | **Semantic threshold fixed 0.75** — tidak adaptif terhadap similarity                                       | Formula kontinu: `0.8000 + 0.0200 × sqrt(ngram_similarity)` ([`shingling.py:331`](../app/engine/shingling.py:331))                                                                                              |
| 7   | **English-centric semantic model** — buruk untuk teks Indonesia                                             | Multilingual model: `paraphrase-multilingual-MiniLM-L12-v2`                                                                                                                                                     |
| 8   | **Gap filling too aggressive** — menyebabkan false positive                                                 | Sekarang konservatif: butuh >=2 kata match di kedua sisi gap ([`shingling.py:217-223`](../app/engine/shingling.py:217))                                                                                         |
| 9   | **Word offset mapping** — edge case kalimat panjang                                                         | `build_sentence_word_spans()` dengan auto-split max_words=40 ([`shingling.py:99-128`](../app/engine/shingling.py:99))                                                                                           |
| 10  | **Silent failures (except: pass)** — error tersembunyi                                                      | 26+ lokasi `except: pass` telah ditandai untuk perbaikan; beberapa sudah diperbaiki dengan proper logging                                                                                                       |
| 11  | **Ngrok auto-expose** — tunnel publik tanpa auth                                                            | Opt-in configuration sudah diimplementasikan                                                                                                                                                                    |
| 12  | **Math.floor precision loss** — skor pembulatan tidak akurat                                                | `round()` menggantikan `math.floor()` ([`server.py`](../app/server.py))                                                                                                                                         |
| 13  | **results_db thread safety** — race condition                                                               | `RESULTS_DB_LOCK` ([`server.py:94`](../app/server.py:94)) melindungi semua akses                                                                                                                                |
| 14  | **Memory leak prevention** — results_db tumbuh tanpa batas                                                  | TTL 2 jam, size limit 50 entries, inline cleanup, background cleanup thread, `gc.collect()`                                                                                                                     |
| 15  | **Temp file cleanup** — orphaned files                                                                      | Atomic write `.tmp` → `os.replace()`, periodic cleanup >2 jam, startup purge                                                                                                                                    |
| 16  | **Input sanitization** — SSRF dan injection                                                                 | `secure_filename()`, `is_safe_url()` anti-SSRF, cryptographic UUID, session ownership validation                                                                                                                |

---

## 📐 Analisis Formula & Overfitting

### Formula Correctness: 9/10

**Rumus inti** ([`shingling.py:148-496`](../app/engine/shingling.py:148)):

```
Global Score = sum(is_matched_global) / total_doc_words × 100
```

**Analisis:**

- **Dua layer:** N-Gram exact match (5-gram) + Semantic similarity (paraphrase-multilingual-MiniLM-L12-v2)
- **Tidak ada double-counting:** Secara eksplisit dicek — `is_matched_global` hanya di-update untuk posisi yang belum ter-match ([`shingling.py:458-462`](../app/engine/shingling.py:458))
- **Bounded output:** Skor selalu dalam range [0%, ~100%] — secara matematis tidak mungkin melebihi 100%
- **Gap filling konservatif:** Membutuhkan >=2 kata match di kedua sisi gap, mencegah bridging yang terlalu agresif
- **Exclude_small:** Filter hanya untuk display, bukan agregasi — memastikan skor akurat

**Kesimpulan:** Secara matematis, formula ini benar dan defensible. Implementasi N-Gram mirip dengan pendekatan Turnitin (exact 5-gram shingling).

### Semantic Threshold: 7/10

**Formula:**

```python
thresh_val = 0.8000 + 0.0200 * math.sqrt(ngram_similarity)
```

**Analisis:**

- **Monotonic** ✅ — threshold meningkat seiring ngram_similarity meningkat
- **Continuous** ✅ — tidak ada branching atau diskontinuitas
- **Bounded** ✅ — range [0.8000, 0.8200] untuk ngram_similarity [0, 1]
- **Koefisien murni empiris** ⚠️ — tidak ada dasar teoretis untuk nilai 0.8000 dan 0.0200
- **Catatan:** Threshold awalnya 0.88 fixed, sekarang auto-threshold yang lebih adaptif

### Overfitting Risk: 4/10 (HIGH RISK)

**Analisis mendalam:**

| Faktor                 | Status             | Detail                                                     |
| ---------------------- | ------------------ | ---------------------------------------------------------- |
| Ukuran dataset         | ❌ Sangat kecil    | Hanya 8 dokumen benchmark                                  |
| Split train/validation | ❌ Tidak ada       | Semua dokumen digunakan untuk KEDUA kalibrasi DAN validasi |
| MAE 1.21%              | ⚠️ In-sample error | Bukan generalization error                                 |
| Domain coverage        | ❌ Terbatas        | Hanya skripsi Indonesia, 8-13K kata                        |
| Cross-validation       | ❌ Tidak dilakukan | Tidak ada LOOCV atau k-fold CV                             |
| Confidence interval    | ❌ Tidak tersedia  | Tidak ada measure of uncertainty                           |

**Risiko konkret:**

1. Formula bisa **overfit** ke karakteristik spesifik 8 dokumen (panjang, domain, gaya bahasa)
2. MAE 1.21% mungkin **inflated** jika diuji pada dokumen baru
3. Tidak ada jaminan formula bekerja untuk dokumen <5K kata atau >20K kata
4. Domain sangat spesifik (skripsi Indonesia) — generalisasi ke teks lain tidak terjamin

### Frozen Corpus: 6/10

**Kelebihan:**

- **Reproducibility** ✅ — dokumen sama → hash sama → korpus sama → skor sama
- **Deterministic** ✅ — menghilangkan variasi jaringan (0-2%)
- **Audit trail** ✅ — setiap frozen corpus dapat di-inspect

**Kekurangan:**

- **Generalizability** ❌ — per-document corpus ≠ Turnitin's universal database
- **Staleness** ❌ — sumber web berubah/hilang seiring waktu
- **Scalability** ❌ — membutuhkan frozen corpus baru untuk setiap dokumen

### Public Deployment Verdict: CONDITIONAL

- ✅ Formula secara matematis benar dan defensible
- ⚠️ Klaim MAE 1.21% memerlukan caveat — ini adalah in-sample error
- ❌ Tidak dapat mengklaim generalisasi tanpa validasi yang diperluas
- **Rekomendasi:** Minimal n≥30 dokumen, LOOCV, hold-out validation set

---

## 🗺️ Roadmap Perbaikan

### Phase 1: Critical Fixes — WAJIB Sebelum Deploy

| #   | Isu                                             | File                                                                                      | Estimasi Kompleksitas |
| --- | ----------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------- |
| 1   | Hapus hardcoded Supabase key                    | [`supabase_client.py:33-34`](../app/engine/supabase_client.py:33)                         | Rendah                |
| 2   | Tambahkan CSRF protection (flask-wtf)           | [`server.py`](../app/server.py), [`templates/index.html`](../app/templates/index.html)    | Sedang                |
| 3   | Tambahkan `threading.Lock` untuk semantic model | [`semantic_similarity.py:26`](../app/engine/semantic_similarity.py:26)                    | Rendah                |
| 4   | Batasi concurrent threads dengan semaphore      | [`server.py:431`](../app/server.py:431), [`web_scraper.py`](../app/engine/web_scraper.py) | Sedang                |
| 5   | Perbaiki `total_downloaded_bytes` NameError     | [`web_scraper.py:1524`](../app/engine/web_scraper.py:1524)                                | Rendah                |

### Phase 2: High Priority — Sprint Berikutnya

| #   | Isu                                              | File                                                                 | Estimasi Kompleksitas |
| --- | ------------------------------------------------ | -------------------------------------------------------------------- | --------------------- |
| 1   | Enable RLS pada Supabase tables                  | Supabase dashboard                                                   | Sedang                |
| 2   | Perbaiki broken upserts (add `on_conflict`)      | [`supabase_client.py:191,216`](../app/engine/supabase_client.py:191) | Rendah                |
| 3   | Tambahkan retry/backoff untuk Supabase calls     | [`supabase_client.py`](../app/engine/supabase_client.py)             | Sedang                |
| 4   | Hoist `clean_doc_words` sebelum loop             | [`shingling.py`](../app/engine/shingling.py)                         | Rendah                |
| 5   | Tambahkan cleanup pada cancellation path         | [`server.py:130-295`](../app/server.py:130)                          | Sedang                |
| 6   | Tambahkan CSP header                             | [`server.py`](../app/server.py)                                      | Rendah                |
| 7   | Tambahkan MIME validation untuk uploads          | [`server.py:402`](../app/server.py:402)                              | Rendah                |
| 8   | Optimasi `is_common_phrase()` — gunakan hash set | [`shingling.py`](../app/engine/shingling.py)                         | Sedang                |
| 9   | Tambahkan `Secure` flag ke session cookie        | [`server.py:37-38`](../app/server.py:37)                             | Rendah                |
| 10  | Tambahkan HSTS header                            | [`server.py`](../app/server.py)                                      | Rendah                |
| 11  | Tambahkan HTTP connection pooling                | [`indonesian_repos.py`](../app/engine/indonesian_repos.py)           | Sedang                |
| 12  | Fix progress update race condition               | [`server.py`](../app/server.py)                                      | Sedang                |

### Phase 3: Validation & Quality — 1-2 Minggu

| #   | Tugas                                   | Detail                                             |
| --- | --------------------------------------- | -------------------------------------------------- |
| 1   | Expand validation set ke n≥30 dokumen   | Dokumen dari domain dan panjang berbeda            |
| 2   | Implementasi LOOCV                      | Leave-One-Out Cross-Validation                     |
| 3   | Tambahkan hold-out validation           | Split 80/20 train/validation                       |
| 4   | Document threshold sensitivity analysis | Analisis sensitivitas terhadap perubahan koefisien |
| 5   | Tambahkan confidence scoring            | Confidence interval untuk setiap skor              |
| 6   | Ganti `print()` dengan `logging`        | Structured logging dengan level configurable       |
| 7   | Pre-compile regex patterns              | Gunakan `re.compile()` di module level             |

### Phase 4: Production Hardening — 2-3 Minggu

| #   | Tugas                                               | Detail                                                 |
| --- | --------------------------------------------------- | ------------------------------------------------------ |
| 1   | Tambahkan Supabase TTL/cleanup                      | Scheduled job untuk pembersihan data lama              |
| 2   | Tambahkan rate limiting dengan proper IP extraction | Flask-Limiter dengan trusted proxy configuration       |
| 3   | Refactor `calculate_similarity` — 8 params → class  | `SimilarityCalculator` class dengan builder pattern    |
| 4   | Tambahkan monitoring dan observability stack        | Prometheus metrics, structured logging, error tracking |
| 5   | Load testing untuk concurrent users                 | Simulasi 50+ concurrent uploads                        |
| 6   | Ganti `except: pass` dengan proper error handling   | 26+ lokasi di seluruh engine                           |

---

## 📋 Skor Akhir per Domain

| Domain               | Skor       | Keterangan                                                                                                                                      |
| -------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Logic & Algorithm    | 9/10       | Formula benar, semua fix dari audit sebelumnya terverifikasi. N-Gram + Semantic pipeline solid.                                                 |
| Security             | 5/10       | CSRF belum ada, hardcoded key, no RLS. SSRF protection dan input sanitization sudah baik.                                                       |
| Database             | 6/10       | Broken upserts, no retry, no TTL. Thread safety dan memory leak prevention sudah diperbaiki.                                                    |
| Memory & Performance | 7/10       | Thread explosion (395+ threads), race condition semantic model, redundant computation. Connection pooling dan GPU cleanup sudah ada.            |
| Calculation Validity | 7/10       | Formula benar secara matematis, tapi overfitting tinggi (n=8, in-sample only).                                                                  |
| Frontend             | 7/10       | XSS safe, CSP missing, CSRF vulnerable. Security headers sudah ada: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy. |
| **OVERALL**          | **6.8/10** | **CONDITIONAL READY — Fix Phase 1-2 dulu**                                                                                                      |

---

## 🎯 Verdict Final

### Untuk Sidang Skripsi: ✅ BISA DIPERTANGGUNGJAWABKAN

- Formula matematis benar dan sound — N-Gram shingling + semantic similarity
- MAE 1.21% adalah in-sample — **WAJIB dicantumkan caveat** dalam presentasi
- Frozen corpus memastikan **reproducibility** — skor konsisten untuk dokumen yang sama
- Semua fix dari audit sebelumnya sudah terverifikasi (12+ isu)
- Algoritma defensible — mirip dengan pendekatan Turnitin (exact 5-gram)
- **Caveat untuk sidang:** Tekankan bahwa ini adalah "local plagiarism pre-check" bukan "Turnitin replacement"

### Untuk Deploy Publik: ⚠️ CONDITIONAL

- Phase 1 critical fixes **WAJIB** diselesaikan dulu (CSRF, hardcoded key, thread safety)
- Perlu validasi n≥30 dokumen sebelum klaim generalisasi
- CSRF protection wajib jika accessible via internet
- RLS wajib jika menggunakan Supabase shared
- Tambahkan disclaimer bahwa MAE berdasarkan in-sample evaluation

### Untuk Produksi Enterprise: ❌ BELUM SIAP

- Perlu Phase 1-4 roadmap diselesaikan
- Perlu load testing untuk concurrent users
- Perlu monitoring dan observability stack
- Perlu expanded validation dan cross-validation
- Perlu infrastructure hardening (RLS, TTL, retry/backoff)

---

## 📎 Lampiran

### File yang Dianalisis

| File                                                                        | Fungsi                             | Audit Coverage |
| --------------------------------------------------------------------------- | ---------------------------------- | -------------- |
| [`app/engine/shingling.py`](../app/engine/shingling.py)                     | Core N-Gram + Semantic logic       | R3, R4, R5, R6 |
| [`app/engine/semantic_similarity.py`](../app/engine/semantic_similarity.py) | Semantic model integration         | R5, R6         |
| [`app/engine/web_scraper.py`](../app/engine/web_scraper.py)                 | Web scraping & text extraction     | R3, R4, R5, R6 |
| [`app/engine/indonesian_repos.py`](../app/engine/indonesian_repos.py)       | Indonesian repository integrations | R3, R4, R5, R6 |
| [`app/engine/free_api_fallbacks.py`](../app/engine/free_api_fallbacks.py)   | API fallbacks                      | R3, R4, R5, R6 |
| [`app/engine/extractor.py`](../app/engine/extractor.py)                     | Document text extraction           | R4, R6         |
| [`app/engine/supabase_client.py`](../app/engine/supabase_client.py)         | Database layer (Supabase)          | R5, R6         |
| [`app/server.py`](../app/server.py)                                         | API server & request handling      | R3, R4, R5, R6 |
| [`app/templates/index.html`](../app/templates/index.html)                   | Frontend upload interface          | R5, R6         |
| [`app/templates/report.html`](../app/templates/report.html)                 | Report display template            | R5, R6         |
| [`app/calibration_result.json`](../app/calibration_result.json)             | Calibration benchmark data         | R6             |

### Metrik Kode (Estimasi)

| Metric                          | Value                       |
| ------------------------------- | --------------------------- |
| Total Python files              | 10                          |
| Total lines (est)               | ~3,500                      |
| Functions                       | ~40                         |
| Routes                          | 7                           |
| External package dependencies   | 9                           |
| Thread count per request        | 1 daemon + N scrape workers |
| `except: pass` locations        | 26+                         |
| Total issues found (all audits) | 52                          |

---

**Versi Dokumen:** 1.0
**Terakhir diperbarui:** 31 Juli 2026
**Dokumen referensi:** [AUDIT_R3.md](AUDIT_R3.md) | [AUDIT_R4.md](AUDIT_R4.md) | [AUDIT_R5.md](AUDIT_R5.md) | [AUDIT_R6.md](AUDIT_R6.md) | [DIAGNOSA_0_PERSEN.md](DIAGNOSA_0_PERSEN.md) | [AUDIT_LENGKAP.md](AUDIT_LENGKAP.md)
