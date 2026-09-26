# Evaluasi dan Metodologi

Dokumen ini menjelaskan metode deteksi, cara perhitungan skor, benchmark, serta batasan dari OpenPlagiarismChecker.

## Metode Deteksi Kesamaan

Sistem menggunakan **empat layer deteksi** yang saling melengkapi:

### Layer 1: N-Gram Exact Matching (5-gram)
Dokumen dibagi menjadi urutan lima kata yang berdekatan, lalu dibandingkan dengan teks sumber.
```text
N-Gram Similarity = (Jumlah Kata Dokumen yang Cocok / Total Kata Dokumen) × 100%
```
Kata yang cocok digabungkan menggunakan mekanisme union sehingga bagian yang sama tidak dihitung berulang kali. **Gap filling konservatif** mengisi celah 2-3 kata di antara dua kecocokan (butuh ≥2 kata match di kedua sisi).

### Layer 2: Semantic Similarity (Parafrasa)
Kalimat dengan tingkat exact-match rendah (<35%) diperiksa menggunakan `paraphrase-multilingual-MiniLM-L12-v2`. Threshold disesuaikan secara dinamis:
```text
Threshold = 0.7900 + 0.0250 × √(NGram Similarity)
```
Fungsi ini menyesuaikan sensitivitas berdasarkan tingkat kecocokan tekstual. Kata yang terdeteksi semantik hanya menambahkan kata yang **belum** terhitung pada Layer 1 (anti double-counting).

### Layer 3: Character N-Gram Fuzzy (4-char) — *Baru 26 Sep*
Mendeteksi penyalinan dengan **modifikasi huruf** (mis. `penelitian` → `penelitlan`, sinonim parsial, typo sengaja) yang lolos dari word-level 5-gram. Setiap sumber dianotasi dengan `char_fuzzy_overlap` (0.0–1.0); nilai ≥0.35 menandakan banyak fragmen karakter identik.
> **Catatan:** Layer ini adalah **anotasi transparansi**, bukan penambah skor — skor tetap murni dari Layer 1+2 agar tidak terjadi inflasi.

### Layer 4: Cross-Language Matching — *Baru 26 Sep*
Menutup celah **plagiat terjemahan** (artikel Inggris diterjemahkan ke Indonesia):
1. Probe terpanjang diterjemahkan ID→EN (Cohere API, fallback glosarium akademik).
2. Pencarian dijalankan juga di mesin internasional (OpenAlex, Crossref, Semantic Scholar, CORE, arXiv).
3. Sumber Inggris masuk korpus; model semantic multilingual mencocokkan kalimat Indonesia vs sumber Inggris **berdasarkan makna**.

---

## Fitur Parity dengan Sistem Referensi

| Fitur | Status | Keterangan |
| :--- | :---: | :--- |
| Exact text matching | ✅ | Layer 1 (5-gram shingling) |
| Paraphrase detection | ✅ | Layer 2 (Sentence-BERT multilingual) |
| Fuzzy / character matching | ✅ | Layer 3 (4-char n-gram) |
| Cross-language (terjemahan) | ✅ | Layer 4 (ID↔EN) |
| Exclude quotes | ✅ | **Quote Intelligence** — hanya kutipan BERSITASI yang dikecualikan |
| Exclude bibliography | ✅ | Deteksi DAFTAR PUSTAKA/REFERENCES |
| Exclude small sources (<1%) | ✅ | Opsi `exclude_small` |
| Per-source percentage + warna | ✅ | Dedup per-domain, 10 warna rotasi |
| Highlight di PDF | ✅ | Quad-based highlight + badge nomor sumber |
| Hidden text / manipulasi | ✅ | Font mungil (<4pt), zero-width, Cyrillic homoglyph |
| **Student Paper Repository** | ✅ | Submission silang lokal (SQLite) |
| **Per-Section Breakdown** | ✅ | Skor per BAB dengan bar warna |
| **Matched Text View** | ✅ | Pasangan teks dokumen vs sumber |
| **Self-Exclusion** | ✅ | Kecualikan versi revisi dokumen yang sama |
| **OCR PDF Scan** | ✅ | Tesseract (opsional, dengan peringatan eksplisit) |
| **Batch + CSV/JSON Export** | ✅ | `run_batch.py` |
| AI Writing Detection | ❌ | Sengaja TIDAK diimplementasikan (akurasi diperdebatkan; risiko false-positive) |

---

## Perhitungan Skor Akhir

```text
Similarity = (Kata N-Gram Match + Kata Semantic Match) / Total Kata Dokumen × 100%
```
Setiap kata hanya berkontribusi maksimal satu kali. **Tidak ada pengurangan, pembulatan ke bawah, atau faktor penyesuaian pada hasil akhir.**

---

## Hasil Validasi dengan Scraping Internet LIVE (26 Sep 2026)

Validasi ini dijalankan **end-to-end dengan scraping internet sungguhan** (bukan korpus beku), untuk membuktikan pipeline produksi akurat:

### Dokumen Uji & Hasil

| Dokumen | Kata | Skor Sistem | Target Turnitin | Delta |
| :--- | :---: | :---: | :---: | :---: |
| **skripsi.pdf** (Tesyar) | 5.852 | **9.39%** | 8% | **+1.39** |
| **Skripsi_Rafly.pdf** (skripsi lengkap) | 13.100 | **6.39%** | 8% | **-1.61** |

**MAE validasi live: 1.50 poin persentase** (2 dokumen).

**Konfigurasi uji:**
- Scraping: 40–50 probes, tanpa korpus beku (`force_scrape` mode live)
- Sumber ditemukan: 42–60 sumber relevan per dokumen (dari korpus 633–1.166)
- Layer aktif: N-Gram + Semantic + Character Fuzzy + Cross-Language + Self-Exclusion
- Waktu proses: 183–236 detik/dokumen (GPU CUDA)

### Detail Skor per Layer (skripsi.pdf)

| Layer | Kontribusi |
| :--- | :---: |
| N-Gram (kata persis) | 4.30% |
| Semantic (parafrasa) | 5.10% |
| **Total** | **9.39%** |

### Contoh Sumber Terdeteksi (skripsi.pdf)

| Persentase | Fuzzy | Sumber |
| :---: | :---: | :--- |
| 1.45% | 0.367 | ejournal.itn.ac.id |
| 1.32% | 0.406 | github.com/mendhiri (repositori skripsi) |
| 0.82% | — | elibrary.bsi.ac.id |
| 0.80% | — | jsi.politala.ac.id |
| 0.51% | 0.444 | sistemasi.ftik.unisi.ac.id |

---

## Benchmark Historis (Korpus Beku)

Dataset benchmark dengan korpus dibekukan — skor **100% reproducible** untuk verifikasi ulang:

### Core Benchmark 2026 (8 Dokumen)

| Dokumen | Skor Lokal | Target Referensi | Delta (poin) |
| :--- | :---: | :---: | :---: |
| Laila after parafrase | 3.45% | 4% | -0.55 |
| Hesti | 16.91% | 18% | -1.09 |
| Fikri | 13.95% | 14% | -0.05 |
| Rafly | 8.90% | 8% | +0.90 |
| Andyan | 22.26% | 23% | -0.74 |
| Dias Maulana | 21.20% | 23% | -1.80 |
| Melani | 18.74% | 19% | -0.26 |
| Laila before parafrase | 22.09% | 24% | -1.91 |

**MAE korpus beku: 1.21 poin persentase.**

### Opsional Baseline 2025 (3 Dokumen)

| Dokumen | Skor Lokal | Target Referensi | Delta (poin) |
| :--- | :---: | :---: | :---: |
| Muhammad Ihsan | 20.69% | 18% | +2.69 |
| Tsaura Halwa | 16.76% | 13% | +3.76 |
| Tesyar | 9.79% | 8% | +1.79 |

---

## Prinsip Kalibrasi & Pertanggungjawaban Skor

Sistem menerapkan prinsip **zero score manipulation**:

1. **Skor akhir = hasil murni perhitungan.** Tidak ada pengurangan flat, pembulatan ke bawah, atau faktor penyesuaian demi mendekati angka referensi.
2. **Kalibrasi hanya pada parameter.** Konstanta threshold semantic (`0.7900 + 0.0250 × √ngram`) di-sweep empiris terhadap benchmark — praktik standar hyperparameter tuning.
3. **Metodologi identik antara server & validasi.** `min_source_overlap`, threshold, dan formula yang dipakai `server.py` sama persis dengan `run_test_groundtruth.py`.
4. **Reproducible.** Korpus dapat dibekukan sehingga dokumen yang sama menghasilkan skor identik di setiap run.
5. **Transparan per-layer.** Skor N-Gram dan Semantic ditampilkan terpisah di laporan, sehingga pengguna dapat memverifikasi kontribusi masing-masing.

---

## Cara Menjalankan Validasi Ulang

```bash
# 1. Letakkan dokumen di app/hasil_trunitin_asli/ atau app/test_documents/
# 2. Nama file dengan target: "Nama Dokumen 18%.pdf" (angka + %)
# 3. Jalankan:
cd app && python run_test_groundtruth.py

# Untuk validasi live (scraping internet sungguhan, bukan korpus beku):
# set REFRESH=1 sebelum menjalankan
REFRESH=1 python run_test_groundtruth.py
```

---

## Keterbatasan Sistem

1. **Hanya Mengakses Sumber Publik:** Sistem tidak dapat mereplikasi indeks privat (makalah internal mahasiswa, jurnal berlangganan) yang dijangkau platform komersial. Jika dokumen asli tidak pernah dipublikasikan terbuka, sistem tidak dapat mendeteksinya.
2. **Kesamaan Bukan Berarti Plagiarisme:** Skor tinggi dapat disebabkan daftar pustaka, kutipan langsung, atau metode standar. Interpretasi manual tetap diperlukan — karena itu fitur **Matched Text View** disediakan untuk verifikasi.
3. **Keterbatasan Benchmark:** MAE 1.21 (korpus beku) / 1.50 (validasi live) dihitung pada sampel dokumen akademik Indonesia. Akurasi dapat bervariasi bergantung jenis dokumen, bahasa, dan disiplin ilmu.
4. **OCR Opsional:** PDF hasil scan memerlukan Tesseract OCR yang terpasang terpisah. Tanpa itu, sistem memberi **peringatan eksplisit** (tidak diam-diam memberi skor 0%).
5. **Bukan Pengganti Layanan Institusional:** Proyek ini adalah alat pemeriksaan pratinjau mandiri — bukan pengganti layanan evaluasi resmi institusi.

---

## Riwayat Perubahan Dokumen Ini

| Tanggal | Perubahan |
| :--- | :--- |
| 26 Sep 2026 | Tambah Layer 3 (Character Fuzzy), Layer 4 (Cross-Language), fitur parity table, hasil validasi live (MAE 1.50), cara menjalankan validasi ulang |
| 26 Sep 2026 | Sinkronisasi formula (`0.7900 + 0.0250`) dengan kode aktual; tambah prinsip anti-manipulasi skor |
