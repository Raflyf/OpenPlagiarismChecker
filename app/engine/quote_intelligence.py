"""
Quote Intelligence, Self-Exclusion & Matched Text Extraction
=============================================================

Tiga fitur Turnitin-parity dalam satu modul:

1. **Quote Intelligence** — Turnitin membedakan kutipan yang DISITASI
   (ada atribusi seperti "(Smith, 2024)" atau "menurut Smith (2024)")
   dari teks yang DISALIN tanpa atribusi. Versi lama sistem kita menghapus
   SEMUA kutipan -> kutipan tanpa sitasi lolos (false negative).

2. **Self-Exclusion** — kecualikan kecocokan dengan submission sebelumnya
   milik dokumen yang sama (mis. mahasiswa submit bab per bab, atau
   revisi). Turnitin punya opsi ini di pengaturan.

3. **Matched Text Extraction** — tampilkan teks sumber yang cocok agar
   pengguna bisa memverifikasi sendiri (Turnitin menampilkan ini
   side-by-side). Data matched_text sudah ada di semantic matches; modul
   ini mengekstraknya untuk N-Gram matches juga.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 1. QUOTE INTELLIGENCE
# ============================================================================

# Pola atribusi sitasi akademik (Indonesia & Inggris):
#   (Smith, 2024)  (Smith et al., 2024)  (Smith & Jones, 2024, hlm. 45)
#   (2024)  [1]  [1,2]  Superscript-style [12]
_RE_CITATION_PAREN = re.compile(
    r"\(\s*[A-Z][A-Za-z.'\-]+(?:\s+(?:et\s+al\.?|dkk\.?|&\s+[A-Z][A-Za-z.'\-]+))?"
    r"(?:,\s*\d{4}[a-z]?)?(?:\s*,\s*(?:hlm|hal|p|pp)\.?\s*\d+[-\d]*)?\s*\)"
)
_RE_CITATION_YEAR_ONLY = re.compile(r"\(\s*\d{4}[a-z]?\s*\)")
_RE_CITATION_BRACKET = re.compile(r"\[\s*\d{1,3}(?:\s*[,-]\s*\d{1,3})*\s*\]")
# "menurut Smith (2024)", "according to Smith (2024)", "Smith (2024) menyatakan"
_RE_CITATION_NARRATIVE = re.compile(
    r"\b(?:menurut|according\s+to|berdasarkan|based\s+on)\s+[A-Z][A-Za-z.'\-]+"
    r"(?:\s+(?:et\s+al\.?|dkk\.?))?\s*\(\s*\d{4}[a-z]?\s*\)",
    re.I,
)
# "Smith (2024) menyatakan/mengemukakan/berpendapat"
_RE_CITATION_AUTHOR_YEAR = re.compile(
    r"\b[A-Z][A-Za-z.'\-]+(?:\s+(?:et\s+al\.?|dkk\.?|&\s+[A-Z][A-Za-z.'\-]+))?\s*\(\s*\d{4}[a-z]?\s*\)"
)


def is_cited_quote(quote_text: str, surrounding_text: str) -> bool:
    """Apakah kutipan ini DISITASI (punya atribusi) atau disalin mentah?

    Memeriksa 60 karakter sebelum & sesudah kutipan untuk pola sitasi.
    """
    if not quote_text:
        return False
    ctx = surrounding_text or ""
    # Gabungkan konteks sebelum & sesudah (caller mengirimnya sekaligus)
    return bool(
        _RE_CITATION_PAREN.search(ctx)
        or _RE_CITATION_YEAR_ONLY.search(ctx)
        or _RE_CITATION_BRACKET.search(ctx)
        or _RE_CITATION_NARRATIVE.search(ctx)
        or _RE_CITATION_AUTHOR_YEAR.search(ctx)
    )


def split_quotes_by_citation(text: str) -> dict:
    """Pisahkan kutipan menjadi cited (disitasi) dan uncited (disalin mentah).

    Mengembalikan:
      {"cited": [teks kutipan...], "uncited": [teks kutipan...]}

    Kutipan yang disitasi boleh dikecualikan dari skor (praktik akademik sah).
    Kutipan TANPA sitasi tetap dihitung sebagai plagiarisme — ini yang versi
    lama sistem kita lewatkan karena semua kutipan dihapus tanpa pandang bulu.
    """
    result = {"cited": [], "uncited": []}
    if not text:
        return result

    patterns = [
        re.compile(r'"([^"]{10,500})"'),          # straight quotes
        re.compile(r"“([^”]{10,500})”"),          # smart quotes
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            quote = m.group(1)
            # [FIX 26 Sep] Konteks presisi: sitasi untuk sebuah kutipan hampir selalu
            # berada LANGSUNG sebelum ("Menurut Smith (2024), \"...\"") atau LANGSUNG
            # sesudah ("...\" (Smith, 2024)") kutipan — dipisah koma/spasi, bukan
            # kalimat baru. Versi pertama memakai 80 char dua arah sehingga sitasi
            # milik kutipan BERIKUTNYA ikut terbaca (false positive: kutipan tanpa
            # sitasi dianggap bersitasi lalu dikecualikan dari skor).
            before = text[max(0, m.start() - 70):m.start()]
            after_full = text[m.end():min(len(text), m.end() + 70)]
            # Ambil hanya sampai akhir kalimat yang sama (titik pertama menandakan
            # sitasi setelahnya milik kalimat/kutipan lain).
            end_of_sentence = re.search(r"[.!?]\s", after_full)
            after = after_full[:end_of_sentence.start() + 1] if end_of_sentence else after_full
            ctx = before + " " + after
            if is_cited_quote(quote, ctx):
                result["cited"].append(quote)
            else:
                result["uncited"].append(quote)
    return result


# ============================================================================
# 2. SELF-EXCLUSION
# ============================================================================

def normalize_filename_for_identity(filename: str) -> str:
    """Normalisasi nama file menjadi identitas dokumen (untuk self-exclusion).

    Menghapus suffix versi/revisi umum: 'skripsi_revisi2.pdf' & 'skripsi.pdf'
    dianggap dokumen yang sama.
    """
    if not filename:
        return ""
    base = re.sub(r"\.[a-z0-9]+$", "", filename.lower())
    # [FIX 26 Sep] Ubah separator (underscore/dash/titik) menjadi spasi DULU agar
    # `\b` bekerja — tanpa ini "skripsi_revisi2" tidak cocok karena `\b` menganggap
    # underscore sebagai karakter kata (word char), sehingga pola kata versi gagal.
    base = re.sub(r"[_\-.]+", " ", base)
    base = re.sub(r"\b(?:revisi|rev|versi|final|fix|edit|update|new|old|copy|salinan)\s*\d*\b", " ", base)
    base = re.sub(r"\b(?:v|ver)\s*\d+\b", " ", base)
    base = re.sub(r"\b(?:bab|chapter|section|part)\s*\d+\b", " ", base)
    base = re.sub(r"\b\d+\b", " ", base)  # angka lepas (mis. "skripsi 2")
    base = re.sub(r"[^a-z0-9]+", "", base)
    return base.strip()


def is_self_match(source_url: str, current_filename: str, current_hash: str) -> bool:
    """Apakah sumber ini adalah submission lama dari dokumen yang sama?

    Deteksi via prefix internal 'student-paper://' + kemiripan nama/identitas.
    """
    if not source_url or "student-paper://" not in source_url:
        return False

    # Format: student-paper://<filename>#<hash8>
    try:
        rest = source_url.split("student-paper://", 1)[1]
        src_filename, _, src_hash = rest.partition("#")
    except Exception:
        return False

    # Hash sama = dokumen identik (submission ulang)
    if src_hash and current_hash and src_hash == current_hash[:8]:
        return True

    # Identitas nama sama = dokumen yang sama dengan versi berbeda
    if normalize_filename_for_identity(src_filename) == normalize_filename_for_identity(current_filename):
        return True

    return False


# ============================================================================
# 3. MATCHED TEXT EXTRACTION (untuk N-Gram, selain semantic yang sudah ada)
# ============================================================================

def extract_matched_snippets(doc_words: list, is_matched: list, source_text: str,
                             min_words: int = 8, max_snippets: int = 5) -> list:
    """Ekstrak potongan teks dokumen yang match dengan sumber tertentu.

    Mengembalikan list dict {document_text, source_text} — pasangan teks yang
    cocok untuk ditampilkan side-by-side (seperti Turnpaper's match overview).
    """
    if not doc_words or not is_matched or not source_text:
        return []

    source_lower = source_text.lower()
    snippets = []
    start = None

    for i, matched in enumerate(is_matched):
        if matched and start is None:
            start = i
        elif not matched and start is not None:
            length = i - start
            if length >= min_words:
                snippet = " ".join(doc_words[start:i])
                # Cari padanan di teks sumber (potongan awal saja untuk verifikasi)
                probe = " ".join(doc_words[start:start + min(10, length)]).lower()
                src_idx = source_lower.find(probe)
                if src_idx >= 0:
                    src_snippet = source_text[src_idx:src_idx + len(snippet) + 60]
                else:
                    src_snippet = ""
                snippets.append({
                    "document_text": snippet[:400],
                    "source_text": src_snippet[:400] if src_snippet else "(teks sumber tidak dapat diambil ulang)",
                    "word_count": length,
                })
                if len(snippets) >= max_snippets:
                    return snippets
            start = None

    # Sisa di akhir dokumen
    if start is not None and len(doc_words) - start >= min_words:
        snippet = " ".join(doc_words[start:])
        snippets.append({
            "document_text": snippet[:400],
            "source_text": "(akhir dokumen)",
            "word_count": len(doc_words) - start,
        })

    return snippets[:max_snippets]
