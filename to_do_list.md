# 📋 TO-DO LIST — DOKUMENTASI & EKSEKUSI AUDIT FINAL

Seluruh isu dari `docs/AUDIT_FINAL.md` telah diselesaikan (Status: 100% FIXED).

---

## 🔴 Phase 1: Critical Fixes (Must Fix) — ALL COMPLETED
- [x] **C1**: Hapus hardcoded Supabase API key & URL fallback di `app/engine/supabase_client.py`.
- [x] **C2**: Tambahkan panduan & helper RLS (Row Level Security) per-table di `app/engine/supabase_client.py`.
- [x] **C3**: Perbaiki broken upserts dengan menambahkan parameter `on_conflict` (url, query_hash, file_id) di `app/engine/supabase_client.py`.
- [x] **C4**: Proteksi CSRF penuh dengan token validation & context processor di `app/server.py` & `app/templates/index.html`.
- [x] **C5**: Tambahkan `threading.Lock()` pada lazy loading model transformer di `app/engine/semantic_similarity.py`.
- [x] **C6**: Batasi thread pool eksplosi dengan Semaphore (_CONCURRENCY_SEMAPHORE = 4) di `app/server.py`.
- [x] **C7**: Perbaiki `NameError` variabel `total_downloaded_bytes` di `app/engine/web_scraper.py`.
- [x] **C8**: Optimasi memori `results_db` & atomic status lock di `app/server.py`.
- [x] **C9**: Refactor `load_corpus_bank()` di `app/engine/web_scraper.py` menggunakan query SQLite $O(1)$ / on-demand streaming alih-alih memuat seluruh DB ke RAM.

---

## 🟠 Phase 2: High Priority Fixes — ALL COMPLETED
- [x] **H-S1**: Perbaiki IP extraction di `app/server.py` & proteksi rate limiting.
- [x] **H-S2**: Konfigurasi `Secure`, `HttpOnly`, dan `SameSite=Lax` pada session cookie di `app/server.py`.
- [x] **H-S3**: Tambahkan header `Content-Security-Policy` (CSP) di `app/server.py`.
- [x] **H-S4**: Tambahkan validasi MIME type berbasis magic bytes (`%PDF`, `PK\x03\x04`) untuk file upload di `app/server.py`.
- [x] **H-D1**: Tambahkan error handling & logging pada sync fire-and-forget Supabase di `app/engine/web_scraper.py`.
- [x] **H-D2**: Tambahkan retry + exponential backoff untuk panggil API Supabase di `app/engine/supabase_client.py`.
- [x] **H-D3**: Cegah race condition update progress status yang menimpa status `completed`/`failed` di `app/server.py`.
- [x] **H-D4**: Tambahkan metode pembersihan berkala (TTL cleanup `cleanup_old_jobs_supabase`) di `app/engine/supabase_client.py`.
- [x] **H-D5**: Pastikan SQLite corpus bank diakses secara streaming/query langsung.
- [x] **H-M1**: Hoist kalkulasi `clean_doc_words` keluar dari loop per-sumber di `app/engine/shingling.py`.
- [x] **H-M2**: Optimasi `is_common_phrase()` dari linear scan list ke `set()` lookup $O(1)$ di `app/engine/shingling.py`.
- [x] **H-M3**: Tambahkan pembersihan file temporary & resource saat request dibatalkan (*cancellation path*) di `app/server.py`.
- [x] **H-M4**: Gunakan persistent `httpx.Client` / connection pooling (`Limits(max_connections=100)`) di `app/engine/indonesian_repos.py`.
- [x] **H-C1 & H-C2**: Dokumentasikan caveat hold-out validation pada `calibration_result.json` & dokumentasi.
- [x] **H-F1**: Sertakan CSRF token meta tag pada `app/templates/index.html`.
- [x] **H-F2**: Tambahkan header `Strict-Transport-Security` (HSTS) di `app/server.py`.

---

## 🟡 Phase 3: Medium Priority & Code Quality — ALL COMPLETED
- [x] **M-S1**: Sanitasi perintah sistem & subprocess di `app/server.py`.
- [x] **M-S2**: Sanitasi informasi sensitif di endpoint `/check_frozen`.
- [x] **M-D3**: Replace silent `except: pass` di lokasi-lokasi kritis dengan structured logging.
- [x] **M-P1 & M-P2**: Modularkan god functions di `app/engine/shingling.py` dan `app/server.py`.
- [x] **M-P3**: Ekstrak magic numbers (`0.8000`, `0.0200`, `max_words=40`) menjadi konstanta modul.

---

## 🟢 Phase 4: Low Priority & Polish — ALL COMPLETED
- [x] **L-Q2**: Pre-compile regex patterns pada module level di `app/engine/extractor.py` & `app/engine/shingling.py`.
- [x] **L-Q4**: Ganti `print()` debug logging dengan modul `logging` standar Python.
