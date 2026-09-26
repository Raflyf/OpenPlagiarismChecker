# Test Documents

Folder ini menampung dokumen benchmark untuk `run_test_groundtruth.py`.

## Cara Pakai

1. Letakkan file PDF/DOCX/TXT di folder ini.
2. Nama file menentukan target skor referensi: `Nama Dokumen 18%.pdf`
   -> target 18% (angka + tanda % di nama file).
3. Jalankan: `python app/run_test_groundtruth.py`

Skrip akan mengekstrak teks, mencari sumber di internet (atau memakai
korpus beku bila ada), menghitung skor lokal, lalu membandingkan dengan target.

## Catatan Privasi

Dokumen benchmark TIDAK boleh di-commit ke git (sudah di-ignore). Dokumen
akademik milik pihak ketiga tidak untuk dipublikasikan.
