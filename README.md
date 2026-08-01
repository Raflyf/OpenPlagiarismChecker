# OpenPlagiarismChecker

Mesin pengecek kesamaan teks akademik *open-source* dengan arsitektur modular, berfokus pada sumber berbahasa Indonesia. Proyek ini mendeteksi kecocokan teks persis menggunakan n-gram dan menangani parafrasa dengan *multilingual semantic similarity*.

> **Disklaimer:** Ini adalah proyek riset *open-source* independen dan tidak dimaksudkan untuk menggantikan layanan deteksi plagiarisme institusional resmi.

---

## Apa Itu Proyek Ini
OpenPlagiarismChecker adalah mesin pemeriksa kesamaan dokumen lokal yang mengutamakan privasi. Sistem memproses file PDF, DOCX, dan TXT, mengekstrak teksnya, lalu merujuk silang ke jutaan makalah akademik *open-access*. Dengan menggabungkan pencocokan struktural dan kontekstual, sistem ini membantu developer dan peneliti menganalisis tumpang-tindih teks secara transparan.

## Mengapa Proyek Ini Dibuat
Banyak perangkat deteksi plagiarisme bersifat tertutup dan mahal. Proyek ini menyediakan alternatif riset *open-source* yang dapat direproduksi. Tujuannya adalah membuka seluruh *pipeline*, strategi pencarian, dan algoritma *similarity* agar dapat diinspeksi, diuji, dan diperbaiki oleh komunitas.

## Status Proyek
Proyek ini dikembangkan secara aktif sebagai perangkat riset. Repositori ini disusun secara modular untuk memfasilitasi eksperimen algoritma, pengujian, dan kontribusi komunitas.

## Bagaimana Claude Akan Membantu
Claude akan digunakan untuk memfaktorkan ulang (*refactor*) kode, merapikan dokumentasi, meninjau *pull request*, menjaga standar arsitektur perangkat lunak, serta mempercepat implementasi uji otomatis (*automated tests*).

---

## Fitur Utama
- **Exact Text Matching:** Pencocokan langsung menggunakan *5-word n-gram shingling*.
- **Semantic Similarity:** Mendeteksi parafrasa menggunakan model Sentence Transformers.
- **Dukungan Format:** Memproses dokumen PDF, DOCX, dan TXT.
- **Web Interface Lokal:** Dasbor sederhana untuk analisis dan ekspor laporan PDF/HTML.
- **Sumber Akademik Ekstensif:** Pencarian konkuren ke berbagai pangkalan data riset.
- **Pemrosesan Terisolasi:** Data dieksekusi secara lokal demi menjaga privasi dokumen.

### Sumber Akademik yang Dijangkau
Sistem mengumpulkan data dari 15+ sumber publik, di antaranya:
- **Indonesia OneSearch (IOS) & Neliti:** Mengindeks ratusan ribu jurnal dan repositori lokal.
- **GARUDA & MORAREF:** Database publikasi resmi Indonesia.
- **BASE & OpenAlex:** Mesin pencari akademik global raksasa.
- **E-Thesis Repositori:** Pemindaian spesifik ke lebih dari 70 repositori perguruan tinggi Indonesia.
- **Semantic Scholar, PubMed, & arXiv:** Jaringan metadata literatur terbuka.

*(Untuk membaca lebih detail tentang metode ekstraksi, penghitungan skor, dan performa evaluasi benchmark, lihat **[docs/evaluation.md](docs/evaluation.md)**).*

---

## Cara Kerja Sistem

```text
Ekstraksi Teks → Sampling Teks → Pencarian Multi-Sumber → 
Retrieval Open-Access → N-Gram Matching → Semantic Matching → Kalkulasi Skor
```

---

## Instalasi (1-Click Run)

*Clone* repositori ini, lalu jalankan script *startup* sesuai sistem operasi Anda:

- **Windows:** Klik ganda file `run.bat`
- **Linux / macOS:** Buka terminal dan jalankan `./run.sh`

Aplikasi akan otomatis menginstal dependensi dan membuka *browser* ke `http://localhost:5001`.

**Untuk instalasi manual:**
```bash
git clone https://github.com/Raflyf/OpenPlagiarismChecker.git
cd OpenPlagiarismChecker
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cd app && python server.py
```

---

## Arsitektur Proyek

```text
OpenPlagiarismChecker/
├── app/
│   ├── engine/                   # Modul logika (N-Gram, Semantic, Web Scraper, Extractor)
│   ├── templates/                # Antarmuka web (HTML)
│   ├── test_documents/           # Dokumen uji
│   ├── server.py                 # Flask server 
│   ├── run_test_groundtruth.py   # Runner pengujian benchmark
│   └── ...
├── docs/
│   └── evaluation.md             # Data benchmark, validasi, dan keterbatasan
└── requirements.txt
```

---

## Kontribusi & Roadmap
Pengembangan saat ini berfokus pada: (1) Memperluas dataset *benchmark* independen, (2) Mengurangi tingkat *false-positive* semantik, dan (3) Menambahkan *unit testing* komprehensif.

Kontribusi berupa integrasi API baru, dataset benchmark, dan perbaikan algoritma sangat disambut baik melalui **Issue** atau **Pull Request**.

---

## Lisensi
Dirilis di bawah **Lisensi MIT**. Proyek ini ditujukan untuk penelitian open-source dan pendidikan.
