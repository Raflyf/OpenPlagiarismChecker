# Dokumentasi Web App Turnitin Lokal

Dokumen ini merangkum arsitektur, alur kerja, dan changelog konseptual aplikasi web
(localhost) pengecek plagiarisme. Dibaca bersama [README.md](../README.md).

## 1. Tujuan

Menyediakan pengecek plagiarisme lokal gratis yang meniru perilaku Turnitin untuk
membantu mahasiswa mengecek skripsi sebelum submit Turnitin resmi. Skor diusahakan
se-valid mungkin terhadap Turnitin asli (validasi 6 dokumen: MAE 1.25pt).

## 2. Arsitektur Berkas

```
app/
├── server.py            Flask server (port 5001) orkestrasi process_document
├── run_test_groundtruth.py Runner validasi freeze corpus (acuan metodologi)
├── engine/
│   ├── extractor.py     Ekstraksi PDF/DOCX/TXT anti-manipulasi
│   ├── shingling.py     N-Gram matching + agregasi global union semantic orchestration
│   ├── semantic_similarity.py  # sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
│   ├── web_scraper.py   Multi-source crawler + API bank corpus (cache) + Anti-RTO
│   └── pdf_generator.py Report PDF bergaya Turnitin (highlight per-sumber)
├── corpus_bank/         Bank corpus (CACHE URL->teks, tumbuh tiap pemakaian)
├── frozen_corpus/*.json Korpus beku per-dokumen validasi (skor deterministik)
├── templates/index.html Halaman upload
└── templates/report.html Halaman hasil
```

## 3. Alur Pemrosesan (process_document)

Localhost memakai **metodologi identik dengan groundtruth** `run_test_groundtruth.py`
agar skor konsisten dan dapat dipertanggungjawabkan:

1. **Ekstraksi teks** `extract_text_from_pdf`: buang front-matter, daftar pustaka,
   kutipan (opsional), deteksi manipulasi (zero-width, Cyrillic homoglyph, tiny-font).
2. **Cari kandidat sumber** `get_candidate_urls` (100 probe): scrape internet KHUSUS
   dokumen ini: Semantic Scholar, Crossref, OpenAlex, DOAJ, arXiv, CORE, DuckDuckGo,
   repositori kampus Indonesia.
3. **Unduh isi sumber** `scrape_all_candidates`: download multi-thread. **Bank corpus
   dipakai sebagai CACHE**: URL yang sudah pernah diunduh diambil instan (skip download),
   sumber baru otomatis disimpan bank (auto-freeze). Bank mempercepat tanpa mengubah
   komposisi korpus.
4. **Skoring** `calculate_similarity` (parameter default identik groundtruth):
   Layer 1: N-Gram 5-gram exact match + gap-filling konservatif + union global.
   Layer 2: Semantic (selalu nyala) untuk kalimat yang lolos N-Gram (<30% match).
   Skor = (kata ter-match union / total kata) \* 100%.
5. **PDF report** `generate_report_pdf`: highlight berwarna per-sumber ala Turnitin,
   halaman ORIGINALITY REPORT, daftar PRIMARY SOURCES.

## 4. Anti-RTO System (Eliminasi Request Time Out)

**Versi:** 1.24 — 29 Juli 2026

Sistem Anti-RTO mengeliminasi timeout pada scraping pipeline dengan 9 layer perbaikan:

### Layer 1: Timeout Constants & Connection Pooling

- Konstanta global `_REQUEST_TIMEOUT=15`, `_SCRAPE_TIMEOUT=30`
- Pool koneksi ditingkatkan: `_POOL_CONNECTIONS=30`, `_POOL_MAXSIZE=80`
- Retry strategy pada HTTPAdapter: 2x retry dengan backoff 0.5s, status [429,500,502,503,504]

### Layer 2: Timeout pada Semua Fetch Functions

- Semua `requests.get()` kini menggunakan `_REQUEST_TIMEOUT`
- Scrape URL menggunakan `_SCRAPE_TIMEOUT` yang lebih panjang (30 detik)

### Layer 3: APICircuitBreaker (Auto-Recovery)

- Kelas `APICircuitBreaker` menggantikan `_FAILED_APIS` set statis
- State: CLOSED (normal) → OPEN (gagal, cooldown 120 detik) → HALF-OPEN (uji coba)
- Cooldown otomatis 120 detik sebelum API dicoba kembali
- Fungsi `call_api_safe_v2()` sebagai pengganti `_call_api_safe()`

### Layer 4: Parallel API Groups

- `fetch_probe_multi()` direstruktur menjadi paralel per grup:
  - **Grup 1** (Indonesia): IOS, Neliti
  - **Grup 2** (Internasional): Semantic Scholar, Crossref, OpenAlex, EuropePMC
  - **Grup 3** (Tambahan): DOAJ, arXiv, CORE, OpenAIRE, HAL
  - **Grup 4** (Google): Google Scholar, Google Web
- Setiap grup dijalankan paralel dengan `ThreadPoolExecutor(max_workers=len(group))`
- DuckDuckGo sebagai fallback non-blocking

### Layer 5: Penurunan Worker Pool

- `get_candidate_urls()`: max_workers dari 16 → 8
- `scrape_all_candidates()`: max_workers dari 15 → 8

### Layer 6: AdaptiveThreadPool

- Dynamic thread pool yang menyesuaikan ukuran berdasarkan rasio timeout
- Threshold turun: jika >30% request timeout, kurangi 2 worker
- Threshold naik: jika <10% timeout, tambah 1 worker (max=8, min=2)
- Cooldown: 30 detik antar penyesuaian

### Layer 7: Delegasi Circuit Breaker

- `_call_api_safe()` sekarang mendelegasikan ke `call_api_safe_v2()`
- Backward compatible — semua caller lama tetap berfungsi

### Layer 8: Scrape URL Safety & Fallback

- `is_safe_url()` memvalidasi URL sebelum scrape (cegah SSRF)
- AbstractAPI proxy sebagai primary → direct connection sebagai fallback
- PDF detection + content-length limit (20 MB)

### Layer 9: Progressive Status

- `progress_cb` sudah didukung di `get_candidate_urls()` dan `scrape_all_candidates()`
- Server.py memanfaatkan callback untuk update progress bar real-time

## 5. Changelog Konseptual

| Tanggal     | Versi | Perubahan                                                                                              |
| ----------- | ----- | ------------------------------------------------------------------------------------------------------ |
| 29 Jul 2026 | 1.24  | Implementasi Anti-RTO: APICircuitBreaker, parallel groups, AdaptiveThreadPool, timeout standardization |
| ...         | ...   | Riwayat sebelumnya (lihat commit history)                                                              |
