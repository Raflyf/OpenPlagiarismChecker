# OpenPlagiarismChecker

Sebuah mesin pengecek kesamaan teks akademik *open-source* dengan arsitektur modular dan evaluasi yang dapat direproduksi.

Proyek ini mendeteksi kecocokan teks persis menggunakan pencocokan n-gram dan menangani teks yang diparafrasakan menggunakan *multilingual semantic similarity* (via Sentence Transformers). Sistem ini dirancang untuk evaluasi lokal yang dapat direproduksi, inspeksi algoritma yang transparan, dan eksperimentasi, dengan fokus khusus pada sumber-sumber akademik berbahasa Indonesia.

> **Disklaimer:** OpenPlagiarismChecker adalah proyek *open-source* independen. Proyek ini tidak berafiliasi, didukung, atau dimaksudkan untuk menggantikan layanan deteksi plagiarisme komersial mana pun.

---

## Apa Itu Proyek Ini (What this project is)
OpenPlagiarismChecker adalah mesin pemeriksa kesamaan dokumen lokal yang mengutamakan privasi. Sistem memproses file PDF, DOCX, dan TXT, mengekstrak teksnya, lalu merujuk silang teks tersebut terhadap jutaan makalah akademik, jurnal, dan repositori institusi *open-access*. Dengan menggabungkan pencocokan struktural (*n-gram shingling*) dan kontekstual (*semantic similarity*), sistem ini memberikan transparansi bagi para *developer* dan peneliti untuk memahami dan menganalisis kecocokan (tumpang tindih) teks.

## Mengapa Proyek Ini Penting (Why it matters)
Banyak perangkat deteksi plagiarisme bersifat tertutup, mahal, atau tidak transparan. Proyek ini menyediakan alternatif *open-source* yang dapat direproduksi bagi pelajar, developer, dan peneliti yang ingin menginspeksi cara kerja penilaian kesamaan dokumen dan memperbaikinya. Keseluruhan *pipeline*, strategi pencarian, algoritma *similarity*, dan metodologi evaluasi dibuka sepenuhnya untuk tinjauan dan kontribusi komunitas.

## Status Proyek (Project status)
Proyek ini dikembangkan secara aktif dan digunakan sebagai perangkat riset serta pembelajaran. Repositori ini disusun secara modular untuk memungkinkan perbaikan iteratif, pengujian otomatis, dan kontribusi komunitas secara langsung.

## Bagaimana Claude Akan Membantu (How Claude will help)
Claude akan digunakan untuk memfaktorkan ulang (*refactor*) kode, memperbaiki dokumentasi, meninjau *pull request*, membantu menjaga arsitektur agar lebih bersih, serta mempercepat pengembangan fitur-fitur uji otomatis dan fungsionalitas *open-source*.

---

## Fitur Utama
- **Pencocokan Teks Persis (Exact Match):** Menggunakan metode *5-word n-gram shingling* untuk mendeteksi kecocokan teks secara langsung.
- **Kesamaan Semantik (Semantic Similarity):** Memanfaatkan model `paraphrase-multilingual-MiniLM-L12-v2` untuk mendeteksi konten yang diparafrasakan.
- **Dukungan Format File:** Memproses format PDF, DOCX, dan TXT.
- **Antarmuka Web Lokal:** Dasbor lokal yang mudah digunakan untuk mengunggah dan menganalisis dokumen.
- **Ekspor Laporan:** Menghasilkan laporan kesamaan terstruktur dalam format HTML dan PDF.
- **Sumber Publik Ekstensif:** Melakukan pencarian dari 15+ API akademik dan repositori publik (seperti Indonesia OneSearch, Neliti, BASE, Semantic Scholar, OpenAlex, arXiv).
- **Codebase Modular:** Dirancang khusus untuk eksperimen dan kontribusi komunitas.

---

## Cara Kerja

1. **Ekstraksi Teks:** Membaca dan mem-parsing teks dari dokumen yang diunggah.
2. **Pengambilan Sampel:** Menghasilkan potongan frasa pendek (*probe*) dari dokumen.
3. **Pencarian Sumber:** Meminta data dari API publik dan repositori akademik menggunakan *probe*.
4. **Pengambilan Teks (Retrieval):** Mengunduh metadata *open-access* atau teks penuh dari kandidat sumber.
5. **Layer 1 - Exact Match:** Menerapkan *n-gram shingling* untuk menemukan segmen teks yang identik.
6. **Layer 2 - Semantic Match:** Menganalisis segmen yang tidak cocok menggunakan batas bawah semantik (*dynamic threshold*) untuk menemukan parafrasa.
7. **Penilaian Skor:** Menghitung rasio akhir antara jumlah kata yang cocok terhadap total jumlah kata dalam dokumen.

---

## Evaluasi Benchmark

Sistem dievaluasi terhadap *core benchmark* dokumen akademik terbaru untuk mengukur perbedaan (*gap*) skor mesin lokal dengan perangkat referensi industri.

**Core Benchmark (Dataset 2026)**

| Dokumen | Skor Lokal | Target Referensi | Delta (poin persentase) |
| :--- | :---: | :---: | :---: |
| Laila after paraphrase | 3.45% | 4% | -0.55 |
| Hesti | 16.91% | 18% | -1.09 |
| Fikri | 13.95% | 14% | -0.05 |
| Rafly | 8.90% | 8% | +0.90 |
| Andyan | 22.26% | 23% | -0.74 |
| Dias Maulana | 21.20% | 23% | -1.80 |
| Melani | 18.74% | 19% | -0.26 |
| Laila before paraphrase | 22.09% | 24% | -1.91 |

*(Catatan: Hasil ini mewakili performa pada dataset benchmark saat ini dan dievaluasi menggunakan metode Leave-One-Out Cross-Validation (LOOCV) untuk menguji stabilitas threshold. Hasil ini tidak menjamin margin perbedaan yang identik untuk seluruh jenis dokumen lainnya).*

---

## Instalasi

### Setup 1-Klik (1-Click Run)
*Clone* atau unduh repositori ini, lalu jalankan *script startup* sesuai sistem operasi Anda:
- **Windows:** Klik ganda file `run.bat`
- **Linux / macOS:** Buka terminal dan jalankan `./run.sh`

*Script* akan secara otomatis mengatur *virtual environment*, menginstal dependensi, dan membuka antarmuka web di `http://localhost:5001`.

### Instalasi Manual (Bagi Developer)
1. Clone repositori:
   ```bash
   git clone https://github.com/Raflyf/OpenPlagiarismChecker.git
   cd OpenPlagiarismChecker
   ```
2. Buat dan aktifkan *virtual environment*:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan *server*:
   ```bash
   cd app
   python server.py
   ```

---

## Arsitektur Proyek

```text
OpenPlagiarismChecker/
├── app/
│   ├── server.py                 # Flask server (port 5001 / 5000)
│   ├── run_batch.py              # Runner eksekusi evaluasi batch
│   ├── run_test_groundtruth.py   # Runner validasi & freeze corpus
│   ├── calibrate_threshold.py    # Kalibrasi threshold semantik
│   ├── test_documents/           # Dokumen uji & benchmark
│   ├── frozen_corpus/            # Korpus cache untuk evaluasi deterministik
│   ├── corpus_bank/              # Database cache SQLite3
│   ├── engine/
│   │   ├── extractor.py          # Ekstraksi dan parsing dokumen
│   │   ├── shingling.py          # Logika N-Gram & thresholding
│   │   ├── semantic_similarity.py# Pipeline Sentence-transformers
│   │   ├── web_scraper.py        # Pengambilan sumber web konkuren (concurrency)
│   │   ├── pdf_generator.py      # Ekspor Laporan PDF
│   │   ├── priority_domains.py   # Pemetaan repositori prioritas
│   │   ├── indonesian_repos.py   # Scraper langsung ke repositori kampus spesifik
│   │   └── free_api_fallbacks.py # Handler cadangan API gratis
│   ├── templates/                # Template antarmuka web (HTML)
│   └── static/                   # Aset CSS & JavaScript
└── requirements.txt
```

---

## Roadmap
- Memperluas kumpulan data benchmark independen lintas disiplin ilmu dan bahasa.
- Memperbaiki efisiensi penemuan sumber dan mengurangi *timeout* pengambilan data.
- Menyempurnakan penyaringan kesamaan semantik untuk menekan persentase *false-positive*.
- Menambahkan uji *unit testing* dan integrasi otomatis secara komprehensif.
- Memperbaiki dokumentasi *developer* untuk tiap komponen algoritma mesin deteksi.

---

## Kontribusi
Kontribusi komunitas sangat diterima. Anda dapat berpartisipasi dengan cara:
- Mengintegrasikan API akademik atau repositori kampus baru.
- Menambahkan dataset benchmark yang dapat diverifikasi.
- Menulis uji fungsional (*unit testing* dan *integration tests*).
- Mengoptimalkan performa pemrosesan paralel (CPU/GPU).
- Mengirimkan perbaikan *bug* (Bug fixes).

Silakan buat **Issue** baru atau kirimkan **Pull Request**.

---

## Lisensi
OpenPlagiarismChecker dirilis menggunakan **Lisensi MIT**.

Proyek ini ditujukan secara murni untuk riset open-source, pendidikan, eksperimen algoritma, dan analisis kesamaan dokumen secara independen.
