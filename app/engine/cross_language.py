"""
Cross-Language Similarity — Deteksi Plagiat Terjemahan
=======================================================

[FITUR BARU 26 Sep] Celah paling umum yang tidak terdeteksi sistem
monolingual: mahasiswa menerjemahkan artikel/jurnal BERBAHASA INGGRIS ke
Bahasa Indonesia, lalu mengumpulkannya sebagai tulisan sendiri.

Sistem N-Gram + semantic monolingual tidak bisa menangkap ini karena:
- N-Gram: kata Indonesia tidak akan pernah sama dengan kata Inggris.
- Semantic (MiniLM multilingual): bisa menangkap kemiripan makna lintas
  bahasa, TETAPI hanya jika korpusnya memuat teks Inggris. Selama ini probe
  pencarian kita hanya berbahasa Indonesia, jadi sumber Inggris tidak pernah
  masuk korpus.

Solusi (dua arah):
1. **Translate probe ID -> EN** lalu cari di mesin akademik internasional
   (OpenAlex, Crossref, Semantic Scholar, CORE, arXiv) yang isinya Inggris.
   Sumber Inggris yang ditemukan dimasukkan ke korpus.
2. **Perbandingan lintas bahasa** memakai model multilingual yang sudah ada
   (paraphrase-multilingual-MiniLM-L12-v2 mendukung 50+ bahasa), sehingga
   kalimat Indonesia vs sumber Inggris tetap bisa dicocokkan maknanya.

Penerjemah: memakai Cohere API bila key tersedia (sudah dipakai untuk query
expander). Bila tidak tersedia, fallback ke daftar istilah akademik umum
(glosarium) + tetap menjalankan pencarian dengan kata kunci Inggris yang
diekstrak dari istilah teknis — lebih lemah, tapi tidak mematikan fitur.
"""

import os
import re
import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cohere_cycle = None


def _next_key():
    """Round-robin Cohere key (sama seperti web_scraper)."""
    global _cohere_cycle
    import itertools
    with _lock:
        if _cohere_cycle is None:
            keys = []
            seen = set()
            for name in ("COHERE_KEYS", "COHERE_KEY"):
                for k in os.environ.get(name, "").split(","):
                    k = k.strip()
                    if k and k not in seen:
                        seen.add(k)
                        keys.append(k)
            _cohere_cycle = itertools.cycle(keys) if keys else itertools.cycle([None])
        return next(_cohere_cycle)


# Glosarium fallback: istilah akademik Indonesia -> Inggris. Dipakai bila
# penerjemah LLM tidak tersedia. Bukan terjemahan penuh — hanya memastikan
# kata kunci teknis ikut ke query Inggris sehingga sumber relevan ditemukan.
_GLOSSARY = {
    "penelitian": "research", "analisis": "analysis", "sistem": "system",
    "metode": "method", "data": "data", "hasil": "result",
    "pengujian": "testing", "pengembangan": "development",
    "implementasi": "implementation", "algoritma": "algorithm",
    "klasifikasi": "classification", "deteksi": "detection",
    "pembelajaran": "learning", "mesin": "machine", "jaringan": "network",
    "saraf": "neural", "aplikasi": "application", "pengguna": "user",
    "basis": "database", "keamanan": "security", "informasi": "information",
    "teknologi": "technology", "komputer": "computer", "perangkat": "device",
    "lunak": "software", "keras": "hardware", "evaluasi": "evaluation",
    "performa": "performance", "akurasi": "accuracy", "model": "model",
    "pelatihan": "training", "pengolahan": "processing", "citra": "image",
    "teks": "text", "suara": "voice", "web": "web", "internet": "internet",
    "manajemen": "management", "kualitas": "quality", "layanan": "service",
    "pengukuran": "measurement", "variabel": "variable", "sampel": "sample",
    "populasi": "population", "hipotesis": "hypothesis", "uji": "test",
    "validitas": "validity", "reliabilitas": "reliability",
    "kuantitatif": "quantitative", "kualitatif": "qualitative",
    "deskriptif": "descriptive", "eksperimen": "experiment",
    "observasi": "observation", "wawancara": "interview",
    "kuesioner": "questionnaire", "responden": "respondent",
    "kesimpulan": "conclusion", "saran": "suggestion", "tujuan": "objective",
    "manfaat": "benefit", "batasan": "limitation", "kerangka": "framework",
}


def _glossary_translate(text: str) -> str:
    """Terjemahan berbasis glosarium (fallback tanpa API)."""
    words = re.findall(r"\w+", text.lower())
    english = [_GLOSSARY.get(w, "") for w in words]
    english = [w for w in english if w]
    # Tambahkan sisa kata yang panjang (nama entitas/proper noun sering sama)
    keep = [w for w in words if len(w) > 6 and w not in _GLOSSARY and w.isalpha()]
    combined = english[:8] + keep[:4]
    return " ".join(combined) if combined else text[:100]


def translate_to_english(text: str, max_chars: int = 400) -> str:
    """Terjemahkan teks Indonesia -> Inggris untuk pencarian lintas bahasa.

    Prioritas: Cohere API (kualitas tinggi) -> glosarium (fallback).
    Mengembalikan string kosong bila teks terlalu pendek / tidak ada sinyal.
    """
    if not text or len(text.strip()) < 15:
        return ""

    probe = text.strip()[:max_chars]
    key = _next_key()

    if key:
        try:
            import requests
            prompt = (
                "Translate the following Indonesian academic sentence to English. "
                "Output ONLY the translation, no quotes, no explanation, no preamble.\n\n"
                f"Sentence: {probe}"
            )
            res = requests.post(
                "https://api.cohere.ai/v2/chat",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "command-a-03-2025",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=15,
            )
            if res.status_code == 200:
                data = res.json()
                out = ""
                for block in data.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        out += block.get("text", "")
                out = out.strip().strip('"').strip()
                # Validasi: hasil harus mengandung huruf latin & panjang wajar
                if out and 10 < len(out) < 800 and re.search(r"[a-zA-Z]{3}", out):
                    # Buang prefiks penjelasan yang kadang ikut ("Translation:")
                    out = re.sub(r"^(?:translation|english|here is)[:\s]+", "", out, flags=re.I)
                    return out[:400]
        except Exception as e:
            logger.debug("Cohere translate gagal: %s", e)

    # Fallback glosarium
    return _glossary_translate(probe)


def build_english_probes(probes: list, max_probes: int = 6) -> list:
    """Bangun probe berbahasa Inggris dari probe Indonesia.

    Hanya probe terpanjang (paling informatif) yang diterjemahkan — hemat kuota
    dan waktu. Mengembalikan daftar unik.
    """
    if not probes:
        return []

    # Ambil probe terpanjang: paling banyak informasi teknis.
    ranked = sorted(probes, key=lambda s: len(s.split()), reverse=True)[:max_probes]
    english = []
    seen = set()
    for probe in ranked:
        en = translate_to_english(probe)
        if en and en.lower() not in seen:
            seen.add(en.lower())
            english.append(en)
    return english
