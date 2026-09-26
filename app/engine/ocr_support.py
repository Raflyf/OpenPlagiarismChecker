"""
OCR Support untuk PDF hasil scan
=================================

[MODUL BARU 26 Sep] Banyak skripsi di-upload sebagai PDF hasil scan (bukan PDF
digital). Tanpa OCR, file seperti itu menghasilkan 0 kata -> skor 0% (false
negative paling berbahaya: dokumen paling plagiat justru lolos).

Modul ini:
1. Mendeteksi PDF scan (rasio teks per halaman sangat rendah).
2. Melakukan OCR bila engine tersedia (Tesseract via pytesseract atau
   PyMuPDF's built-in OCR yang juga memakai Tesseract).
3. Bila OCR TIDAK tersedia, memberi peringatan eksplisit ke pengguna —
   tidak diam-diam menghasilkan skor 0% yang menyesatkan.

Instalasi OCR (opsional, untuk PDF scan):
  Windows : winget install UB-Mannheim.TesseractOCR
  Linux   : sudo apt install tesseract-ocr tesseract-ocr-ind
  macOS   : brew install tesseract tesseract-lang
  Python  : pip install pytesseract pillow

Catatan: Tesseract bahasa Indonesia (`ind`) sangat disarankan — tanpa itu
akurasi kata berbahasa Indonesia turun signifikan.
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# Ambang deteksi: rata-rata kata per halaman di bawah ini = kemungkinan scan.
_SCAN_WORDS_PER_PAGE = int(os.environ.get("OCR_SCAN_THRESHOLD_WORDS", "40"))

# Batas halaman yang di-OCR (OCR sangat lambat: ~2-5 detik/halaman).
_MAX_OCR_PAGES = int(os.environ.get("OCR_MAX_PAGES", "40"))


def _configure_tesseract():
    """Auto-konfigurasi path Tesseract & TESSDATA_PREFIX.

    [FIX 26 Sep] Windows tidak menambahkan Tesseract ke PATH secara default, dan
    bahasa Indonesia (ind.traineddata) sering tidak bisa ditulis ke
    C:\Program Files (butuh admin). Fungsi ini:
    1. Mencari binary tesseract di lokasi instalasi umum.
    2. Menunjuk TESSDATA_PREFIX ke folder user (%LOCALAPPDATA%\tessdata) bila
       ada — folder ini bisa ditulis tanpa admin sehingga bahasa tambahan
       (ind) bisa dipasang pengguna.
    """
    import shutil as _shutil
    try:
        import pytesseract
    except Exception:
        return

    # 1. Binary tesseract
    if not _shutil.which("tesseract"):
        for cand in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
        ):
            if os.path.exists(cand):
                pytesseract.pytesseract.tesseract_cmd = cand
                break

    # 2. TESSDATA_PREFIX ke folder user bila ada traineddata di sana
    if not os.environ.get("TESSDATA_PREFIX"):
        user_tessdata = os.path.expandvars(r"%LOCALAPPDATA%\tessdata")
        if os.path.isdir(user_tessdata) and any(
            f.endswith(".traineddata") for f in os.listdir(user_tessdata)
        ):
            os.environ["TESSDATA_PREFIX"] = user_tessdata


def is_tesseract_available() -> bool:
    """Cek apakah pytesseract + binary tesseract tersedia."""
    try:
        import pytesseract
        _configure_tesseract()
        from pytesseract import get_tesseract_version
        get_tesseract_version()
        return True
    except Exception:
        return False


def _available_languages() -> list:
    """Daftar bahasa Tesseract yang terinstall (mis. ['eng', 'ind'])."""
    try:
        import pytesseract
        _configure_tesseract()
        return list(pytesseract.get_languages(config=""))
    except Exception:
        return []


def looks_like_scanned_pdf(doc) -> bool:
    """Deteksi PDF hasil scan: teks sangat sedikit dibanding jumlah halaman.

    PDF digital normal punya ratusan kata/halaman. PDF scan punya 0-30 kata
    (hanya header/watermark yang mungkin masih teks digital).
    """
    try:
        page_count = len(doc)
        if page_count == 0:
            return False
        # Sample maks 5 halaman (halaman pertama biasanya cover — pakai tengah juga).
        sample_indices = [0]
        if page_count > 2:
            sample_indices.append(page_count // 2)
        if page_count > 4:
            sample_indices.append(page_count - 1)

        total_words = 0
        for idx in sample_indices:
            if idx < page_count:
                total_words += len(doc[idx].get_text().split())

        avg_words = total_words / len(sample_indices)
        is_scan = avg_words < _SCAN_WORDS_PER_PAGE
        if is_scan:
            logger.info(
                "PDF terdeteksi sebagai SCAN (rata-rata %.1f kata/halaman < %d).",
                avg_words, _SCAN_WORDS_PER_PAGE,
            )
        return is_scan
    except Exception:
        return False


def ocr_pdf(filepath: str, max_pages: int = None) -> str:
    """Jalankan OCR pada PDF scan. Mengembalikan teks hasil OCR (bisa kosong).

    Strategi bahasa: pakai 'ind+eng' bila bahasa Indonesia tersedia (skripsi
    Indonesia sering mencampur istilah Inggris), fallback ke 'eng'.
    """
    if max_pages is None:
        max_pages = _MAX_OCR_PAGES

    if not is_tesseract_available():
        logger.warning(
            "OCR diminta tetapi Tesseract tidak terpasang. "
            "Lihat docstring ocr_support.py untuk cara instalasi."
        )
        return ""

    try:
        import fitz
        import pytesseract
        from PIL import Image
        import io

        _configure_tesseract()
        langs = _available_languages()
        if "ind" in langs and "eng" in langs:
            lang = "ind+eng"
        elif "ind" in langs:
            lang = "ind"
        elif "eng" in langs:
            lang = "eng"
        else:
            lang = langs[0] if langs else "eng"

        doc = fitz.open(filepath)
        parts = []
        try:
            limit = min(len(doc), max_pages)
            for page_num in range(limit):
                page = doc[page_num]
                # Render 200 DPI (kompromi akurasi vs kecepatan; 300 DPI lebih
                # akurat tapi ~2x lebih lambat dan memori besar).
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(img, lang=lang)
                if page_text.strip():
                    parts.append(page_text)
                if page_num % 5 == 0:
                    logger.info("OCR halaman %d/%d...", page_num + 1, limit)
        finally:
            doc.close()

        full = "\n".join(parts)
        full = re.sub(r"[ \t]+", " ", full)
        full = re.sub(r"\n{3,}", "\n\n", full)
        logger.info("OCR selesai: %d karakter dari %d halaman.", len(full), min(len(doc) if 'doc' in dir() else 0, max_pages))
        return full.strip()
    except Exception as e:
        logger.warning("OCR gagal: %s", e)
        return ""


def ocr_status_message() -> str:
    """Pesan status untuk ditampilkan ke pengguna saat PDF scan tanpa OCR."""
    if is_tesseract_available():
        langs = _available_languages()
        has_ind = "ind" in langs
        return (
            "PDF ini terdeteksi sebagai hasil SCAN. OCR aktif"
            + ("" if has_ind else " (bahasa Indonesia belum terpasang — akurasi kata Indonesia bisa turun; "
               "install paket bahasa 'ind')")
            + "."
        )
    return (
        "PDF ini terdeteksi sebagai hasil SCAN (gambar, bukan teks digital). "
        "Sistem tidak dapat membaca isinya tanpa OCR, sehingga skor TIDAK dapat dihitung. "
        "Pasang Tesseract OCR untuk mengaktifkan dukungan PDF scan: "
        "Windows `winget install UB-Mannheim.TesseractOCR`, "
        "Linux `sudo apt install tesseract-ocr tesseract-ocr-ind`, "
        "lalu `pip install pytesseract pillow`."
    )
