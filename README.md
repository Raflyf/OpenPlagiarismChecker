# OpenPlagiarismChecker

OpenPlagiarismChecker adalah sistem **open-source untuk deteksi plagiarisme dan kesamaan dokumen** yang dirancang terutama untuk dokumen akademik, dengan fokus khusus pada sumber berbahasa Indonesia.

Sistem menggabungkan **N-Gram Exact Matching** dan **Multilingual Semantic Similarity** untuk mendeteksi kemiripan teks secara langsung serta bagian yang berpotensi merupakan hasil parafrasa.

Berbeda dari platform deteksi plagiarisme tertutup, OpenPlagiarismChecker berfokus pada **transparansi, reproduktibilitas, dan keterbukaan algoritma**. Pipeline penilaian, proses pencarian sumber, perhitungan kemiripan, dan metodologi evaluasinya tersedia untuk diperiksa, diuji, dikembangkan, dan diperbaiki oleh komunitas.

> OpenPlagiarismChecker adalah proyek open-source independen. Proyek ini tidak berafiliasi, didukung, atau dimaksudkan untuk menggantikan layanan deteksi plagiarisme komersial mana pun.

---

## Apa Itu Proyek Ini (What this project is)
OpenPlagiarismChecker adalah mesin pemeriksa kesamaan dokumen akademik lokal. Sistem memproses file PDF, DOCX, dan TXT, lalu mengekstrak dan merujuk silang teks tersebut terhadap jutaan makalah akademik, jurnal, dan repositori institusi *open-access*. Dengan menggabungkan pencocokan struktural dan kontekstual, sistem ini memberikan transparansi bagi *developer* dan peneliti untuk memahami dan menganalisis kecocokan teks.

## Mengapa Proyek Ini Dibuat (Why it matters)
Akses terhadap sistem pemeriksaan plagiarisme dan kesamaan dokumen sering kali terbatas oleh langganan institusi, database tertutup, serta algoritma penilaian yang tidak dapat diperiksa secara publik. Proyek ini mengeksplorasi pendekatan alternatif menggunakan sumber akademik yang dapat diakses secara publik serta teknologi NLP open-source. Tujuannya adalah menyediakan alternatif yang dapat direproduksi bagi mahasiswa, developer, dan peneliti yang ingin menginspeksi cara kerja penilaian kesamaan dokumen dan memperbaikinya.

## Status Proyek (Project status)
Proyek ini dikembangkan secara aktif dan digunakan sebagai perangkat riset serta pembelajaran. Repositori ini disusun secara modular untuk memungkinkan perbaikan iteratif, pengujian, dan kontribusi komunitas secara langsung.

## Bagaimana Claude Akan Membantu (How Claude will help)
Claude akan digunakan untuk memfaktorkan ulang (*refactor*) kode, memperbaiki dokumentasi, meninjau *pull request*, membantu menjaga arsitektur agar lebih bersih, serta mempercepat pengembangan fitur-fitur uji otomatis dan fungsionalitas *open-source*.

---

## Fitur Utama

### N-Gram Exact Matching
Dokumen dianalisis menggunakan metode **5-word N-Gram shingling**. Engine mendeteksi bagian teks yang memiliki kecocokan langsung dengan sumber publik yang berhasil ditemukan. Setiap kata yang terdeteksi hanya berkontribusi satu kali terhadap skor akhir, meskipun bagian yang sama ditemukan pada beberapa sumber.

### Semantic Similarity
Bagian dokumen yang tidak cukup terdeteksi melalui N-Gram dianalisis kembali menggunakan model `paraphrase-multilingual-MiniLM-L12-v2`. Model sentence-transformer multilingual ini memungkinkan sistem mendeteksi kemiripan semantik, termasuk bagian teks yang telah diparafrase. Sistem mendeteksi CUDA secara otomatis apabila GPU yang kompatibel tersedia dan menggunakan CPU sebagai fallback.

### Pencarian Sumber Akademik
OpenPlagiarismChecker mencari kandidat sumber melalui berbagai indeks akademik publik, API, repositori, dan penyedia pencarian. Integrasi saat ini mencakup:
- Indonesia OneSearch
- Neliti
- MORAREF
- GARUDA
- BASE
- Europe PMC
- PubMed / NCBI
- Unpaywall
- Semantic Scholar
- OpenAlex
- Crossref
- DOAJ
- arXiv
- CORE
- Pencarian khusus ke lebih dari **70 repositori publik perguruan tinggi Indonesia**.

### Web Interface Lokal & Laporan PDF
Aplikasi menyediakan antarmuka web lokal untuk mengunggah dokumen, menjalankan analisis kesamaan, memeriksa sumber, membatalkan proses, dan mengekspor hasil ke dalam bentuk laporan PDF terstruktur.

### Pemrosesan Lokal dan Privasi
Aplikasi dijalankan secara lokal. Dokumen yang diunggah diproses melalui sesi yang terisolasi dan data sementara dibersihkan secara berkala.

---

## Cara Kerja

```text
PDF / DOCX / TXT
        ↓
Ekstraksi Teks
        ↓
Sampling Dokumen
        ↓
Pencarian Sumber Akademik
        ↓
Pengambilan Teks Sumber
        ↓
5-Gram Exact Matching
        ↓
Semantic Similarity
        ↓
Agregasi Skor
        ↓
Laporan Kesamaan
```

Kandidat sumber akademik dikumpulkan secara khusus berdasarkan isi dokumen yang sedang dianalisis. Database SQLite lokal (`bank.db`) terutama berfungsi sebagai cache untuk sumber publik yang sebelumnya telah diambil sehingga mengurangi pengunduhan berulang dan mempercepat analisis berikutnya.

---

## Metode Deteksi Kesamaan

### Layer 1: N-Gram Exact Matching
Dokumen dibagi menjadi urutan lima kata yang berdekatan. Urutan tersebut kemudian dibandingkan dengan teks dari sumber yang berhasil ditemukan.
```text
N-Gram Similarity = (Jumlah Kata Dokumen yang Cocok / Total Kata Dokumen) × 100%
```
Kata yang cocok digabungkan menggunakan mekanisme union sehingga bagian yang sama tidak dihitung berulang kali.

### Layer 2: Semantic Similarity
Kalimat dengan tingkat exact-match yang rendah diperiksa oleh semantic similarity layer menggunakan `paraphrase-multilingual-MiniLM-L12-v2`.
Threshold semantic disesuaikan secara dinamis menggunakan fungsi Continuous Square-Root Auto-Thresholding:
```text
Threshold = 0.7900 + 0.0250 × √(NGram Similarity)
```
Fungsi ini dikembangkan untuk menyesuaikan sensitivitas semantic similarity berdasarkan tingkat kecocokan tekstual. Semantic match hanya menambahkan kata yang belum terhitung pada layer N-Gram sehingga tidak terjadi double counting.

---

## Perhitungan Skor Akhir

```text
Similarity = (Kata N-Gram Match + Kata Semantic Match) / Total Kata Dokumen × 100%
```

Setiap kata dalam dokumen hanya dapat berkontribusi satu kali terhadap skor akhir.

---

## Evaluasi

Dataset evaluasi saat ini terdiri dari **11 dokumen akademik nyata** yang telah memiliki skor kesamaan dari sistem referensi eksternal. 

Subset evaluasi utama terdiri dari **8 dokumen Core Benchmark 2026**.

| Dokumen | OpenPlagiarismChecker | Referensi | Selisih |
| :--- | :---: | :---: | :---: |
| Laila after parafrase | 3.45% | 4% | -0.55 |
| Hesti | 16.91% | 18% | -1.09 |
| Fikri | 13.95% | 14% | -0.05 |
| Rafly | 8.90% | 8% | +0.90 |
| Andyan | 22.26% | 23% | -0.74 |
| Dias Maulana | 21.20% | 23% | -1.80 |
| Melani | 18.74% | 19% | -0.26 |
| Laila before parafrase | 22.09% | 24% | -1.91 |

**Mean Absolute Error (MAE) pada Core Benchmark 2026 saat ini: 0.91 poin persentase.**

Tiga dokumen tahun 2025 dipertahankan sebagai dataset pembanding sekunder:

| Dokumen | OpenPlagiarismChecker | Referensi | Selisih |
| :--- | :---: | :---: | :---: |
| Muhammad Ihsan | 20.69% | 18% | +2.69 |
| Tsaura Halwa | 16.76% | 13% | +3.76 |
| Tesyar | 9.79% | 8% | +1.79 |

Hasil tersebut harus dipahami sebagai performa pada **benchmark proyek saat ini**, bukan sebagai bukti bahwa sistem memiliki tingkat akurasi yang sama pada seluruh jenis dokumen.

---

## Metodologi Validasi

Pendekatan threshold juga dievaluasi menggunakan **Leave-One-Out Cross-Validation (LOOCV)** pada Core Benchmark 2026 yang tersedia. Tujuannya adalah mengurangi risiko parameter threshold hanya menyesuaikan diri terhadap dokumen tertentu pada benchmark. Hasil saat ini menunjukkan error yang relatif stabil pada sampel validasi yang tersedia.

Namun, ukuran benchmark masih terbatas. Dataset yang jauh lebih besar dan mencakup berbagai institusi, bidang ilmu, tipe dokumen, bahasa, serta tahun publikasi diperlukan sebelum membuat klaim generalisasi yang lebih luas. Keterbatasan tersebut secara eksplisit diakui oleh proyek ini.

---

## Keterbatasan

### Hanya Mengakses Sumber Publik
OpenPlagiarismChecker tidak dapat mereplikasi indeks privat yang dimiliki platform deteksi plagiarisme komersial. Sistem komersial dapat memiliki akses terhadap dokumen mahasiswa privat, jurnal berlisensi, repositori institusi tertutup, dan dokumen historis yang tidak tersedia secara publik. Proyek ini berfokus pada **sumber publik dan sumber akademik open-access**. Dokumen yang tidak pernah tersedia pada internet publik mungkin tidak dapat ditemukan.

### Similarity Tidak Otomatis Berarti Plagiarisme
Skor kesamaan tidak dengan sendirinya membuktikan adanya pelanggaran akademik. Kutipan, daftar pustaka, istilah standar, bagian metodologi, serta penggunaan teks yang sah dapat meningkatkan similarity score. Hasil tetap perlu diinterpretasikan oleh pengguna atau pihak akademik yang berwenang.

### Ruang Lingkup Benchmark
MAE 0.91 poin persentase yang dilaporkan berlaku pada Core Benchmark 2026 yang digunakan saat ini. Angka tersebut bukan jaminan margin error untuk semua dokumen. Perluasan dan diversifikasi benchmark merupakan salah satu fokus pengembangan proyek.

### Penggunaan Institusional
Proyek ini **tidak dimaksudkan untuk menggantikan sistem pemeriksaan resmi milik institusi**. OpenPlagiarismChecker paling sesuai digunakan untuk pemeriksaan mandiri, penelitian, eksperimen algoritma, dan analisis kesamaan dokumen.

---

## Instalasi

### Instalasi 1-Click
Clone atau download repository ini.
- **Windows:** Jalankan `run.bat`
- **Linux / macOS:** Jalankan `./run.sh`

Script setup akan menangani environment, dependensi, konfigurasi, startup aplikasi, dan pembukaan browser secara otomatis di `http://localhost:5001`.

### Instalasi Manual
1. Clone repository:
   ```bash
   git clone https://github.com/Raflyf/OpenPlagiarismChecker.git
   cd OpenPlagiarismChecker
   ```
2. Buat virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Aktifkan environment (Windows: `.venv\Scripts\activate`, Linux/macOS: `source .venv/bin/activate`).
4. Install dependensi: `pip install -r requirements.txt`
5. Jalankan server:
   ```bash
   cd app
   python server.py
   ```

---

## Arsitektur Proyek

```text
OpenPlagiarismChecker/
├── app/
│   ├── server.py                 # Flask server 
│   ├── run_batch.py              # Batch execution runner
│   ├── run_test_groundtruth.py   # Validation runner
│   ├── calibrate_threshold.py    # Semantic threshold calibration
│   ├── test_documents/           # Benchmark documents
│   ├── frozen_corpus/            # Cached deterministic evaluation corpus
│   ├── corpus_bank/              # SQLite3 cache database
│   ├── engine/
│   │   ├── extractor.py          # Document parsing
│   │   ├── shingling.py          # N-Gram logic & thresholding
│   │   ├── semantic_similarity.py# Sentence-transformers pipeline
│   │   ├── web_scraper.py        # Concurrent web retrieval
│   │   ├── pdf_generator.py      # Report export
│   │   ├── priority_domains.py   # Academic repository mapping
│   │   ├── indonesian_repos.py   # Targeted repository scraper
│   │   └── free_api_fallbacks.py # API fallback handlers
│   ├── templates/                # Web interface HTML
│   └── static/                   # CSS and JS assets
└── requirements.txt
```

---

## Teknologi

Teknologi utama yang digunakan: Python, Flask, SQLite, PyTorch, Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`), N-Gram Shingling, Semantic Similarity, Concurrent Web Retrieval, dan PDF/DOCX Text Extraction.

---

## Keamanan dan Privasi

Aplikasi memiliki beberapa mekanisme perlindungan:
- Session-isolated reports.
- Validasi tipe file dan MIME.
- CSRF protection.
- Rate limiting.
- SSRF protection.
- Pembatasan concurrent processing.
- Atomic database operations.
- Pembersihan dokumen sementara.
- Memory guard untuk semantic processing.

---

## Tujuan Pengembangan & Kontribusi

Prioritas pengembangan saat ini meliputi memperluas benchmark, meningkatkan source discovery, mengurangi false-positive, menambah automated testing, dan memperbaiki dokumentasi developer.

Kontribusi dari komunitas sangat terbuka. Jika menemukan bug atau memiliki ide pengembangan, silakan membuka **Issue** atau **Pull Request**.

---

## Transparansi Penelitian

Proyek ini secara sengaja membuka metodologi retrieval, algoritma similarity, fungsi threshold, metodologi evaluasi, dan keterbatasan sistem. Dengan pendekatan ini, developer dan peneliti dapat mereproduksi hasil, mengkritisi keputusan desain, serta mengusulkan pendekatan yang lebih baik.

---

## Lisensi & Author

OpenPlagiarismChecker dirilis menggunakan **MIT License**.
Proyek ditujukan untuk penelitian open-source, pendidikan, eksperimen, dan analisis kesamaan dokumen.

**Dibuat oleh:** Rafly Firmansyah
