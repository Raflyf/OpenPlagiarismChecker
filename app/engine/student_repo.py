"""
Student Paper Repository — Fitur setara "Student Paper Repository" Turnitin
============================================================================

[FITUR BARU 26 Sep] Turnitin punya repositori internal: setiap dokumen yang
pernah di-submit disimpan dan diperiksa silang dengan submission berikutnya.
Ini yang membuat Turnitin mendeteksi "kemiripan dengan paper mahasiswa lain"
yang tidak ada di internet.

Modul ini mengimplementasikan hal yang sama secara lokal:
- Setiap dokumen yang selesai dianalisis disimpan (teks + metadata) di SQLite.
- Sebelum analisis internet, dokumen baru diperiksa dulu terhadap repositori ini
  (instan, tanpa jaringan).
- Hasil dari repositori internal diberi label sumber "Student Paper Repository"
  sehingga pengguna tahu asal kecocokan.

PRIVASI & ETIKA:
- Repositori bersifat LOKAL (tidak diunggah ke internet, tidak di-commit ke git).
- Nama file disimpan untuk identifikasi; teks lengkap hanya di disk lokal.
- Bisa dinonaktifkan via env STUDENT_REPO_ENABLED=0.
- Bisa dibersihkan via fungsi clear_repository() atau menghapus file DB.

Cara kerja (sama seperti Turnitin):
1. analyze() memanggil check_against_repository() sebelum scraping internet.
2. Kecocokan dikembalikan sebagai sumber tambahan dengan prefix khusus.
3. Setelah analisis selesai, save_document() menyimpan dokumen ke repositori.
"""

import os
import re
import time
import sqlite3
import logging
import threading
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_DB_PATH = os.path.join(_BASE_DIR, "..", "corpus_bank", "student_repo.db")

_lock = threading.Lock()
_initialized = False

# Prefix URL internal agar mudah dibedakan dari sumber internet di laporan
INTERNAL_PREFIX = "student-paper://"

# Batas ukuran: repositori tumbuh seiring submission; simpan teks yang dipotong
_MAX_TEXT_CHARS = int(os.environ.get("STUDENT_REPO_MAX_CHARS", "300000"))


def is_enabled() -> bool:
    """Repositori aktif secara default; bisa dimatikan via env."""
    return os.environ.get("STUDENT_REPO_ENABLED", "1") != "0"


def _init_db():
    global _initialized
    if _initialized:
        return
    os.makedirs(os.path.dirname(_REPO_DB_PATH), exist_ok=True)
    with _lock:
        with sqlite3.connect(_REPO_DB_PATH, timeout=10.0) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    doc_hash TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    submitted_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(doc_hash)")
            conn.commit()
    _initialized = True


def save_document(doc_hash: str, filename: str, text: str) -> bool:
    """Simpan dokumen ke repositori internal (dipanggil setelah analisis selesai).

    Idempoten: dokumen dengan hash sama tidak disimpan dua kali (INSERT OR REPLACE
    memperbarui timestamp). Mengembalikan True bila tersimpan.
    """
    if not is_enabled():
        return False
    if not doc_hash or not text or len(text) < 200:
        return False

    try:
        _init_db()
        word_count = len(text.split())
        # Dokumen sangat pendek (< 300 kata) tidak layak jadi pembanding.
        if word_count < 300:
            return False

        with _lock:
            with sqlite3.connect(_REPO_DB_PATH, timeout=10.0) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO papers (doc_hash, filename, text, word_count, submitted_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (doc_hash, filename[:200], text[:_MAX_TEXT_CHARS], word_count, time.time()),
                )
                conn.commit()
        logger.info("[StudentRepo] Dokumen tersimpan: %s (%d kata)", filename[:50], word_count)
        return True
    except Exception as e:
        logger.warning("[StudentRepo] Gagal menyimpan dokumen: %s", e)
        return False


def check_against_repository(doc_hash: str, doc_text: str, min_overlap_ngrams: int = 5) -> Dict[str, str]:
    """Periksa dokumen baru terhadap repositori internal.

    Mengembalikan dict {url_palsu: teks_dokumen_lama} untuk dokumen yang punya
    overlap signifikan. Format url_palsu: "student-paper://<filename>#<hash8>".

    Efisiensi: memuat SEMUA teks dari DB bisa berat bila repositori besar.
    Karena itu pembandingan memakai pendekatan dua tahap:
      1. Ambil daftar kandidat (semua dokumen — untuk repo kecil-menengah ini OK).
      2. Untuk setiap kandidat, hitung overlap n-gram cepat; simpan hanya yang lolos.
    Untuk repositori > 1000 dokumen, tambahkan pre-filter TF-IDF di masa depan.
    """
    if not is_enabled() or not doc_text or len(doc_text) < 200:
        return {}

    try:
        _init_db()
        with _lock:
            with sqlite3.connect(_REPO_DB_PATH, timeout=10.0) as conn:
                cur = conn.execute("SELECT doc_hash, filename, text FROM papers")
                rows = cur.fetchall()
    except Exception as e:
        logger.warning("[StudentRepo] Gagal membaca repositori: %s", e)
        return {}

    if not rows:
        return {}

    # N-gram dokumen baru (5-gram, sama dengan mesin utama)
    def ngrams(text: str, n: int = 5) -> set:
        words = re.sub(r"[^\w\s]", "", text).lower().split()
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

    new_grams = ngrams(doc_text)
    if not new_grams:
        return {}

    matches = {}
    for old_hash, old_filename, old_text in rows:
        if old_hash == doc_hash:
            continue  # dokumen yang sama persis, bukan kecocokan
        old_grams = ngrams(old_text)
        if not old_grams:
            continue
        overlap = len(new_grams & old_grams)
        if overlap >= min_overlap_ngrams:
            key = f"{INTERNAL_PREFIX}{old_filename}#{old_hash[:8]}"
            matches[key] = old_text
            logger.info("[StudentRepo] Kecocokan internal: %s (%d n-gram overlap)", old_filename[:50], overlap)

    return matches


def repository_stats() -> Dict[str, int]:
    """Statistik repositori untuk dashboard."""
    try:
        _init_db()
        with _lock:
            with sqlite3.connect(_REPO_DB_PATH, timeout=5.0) as conn:
                cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(word_count), 0) FROM papers")
                count, total_words = cur.fetchone()
        return {"documents": count or 0, "total_words": total_words or 0}
    except Exception:
        return {"documents": 0, "total_words": 0}


def clear_repository() -> bool:
    """Kosongkan repositori (untuk privasi / reset)."""
    try:
        _init_db()
        with _lock:
            with sqlite3.connect(_REPO_DB_PATH, timeout=10.0) as conn:
                conn.execute("DELETE FROM papers")
                conn.commit()
        logger.info("[StudentRepo] Repositori dikosongkan.")
        return True
    except Exception as e:
        logger.warning("[StudentRepo] Gagal mengosongkan: %s", e)
        return False
