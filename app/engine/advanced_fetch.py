"""
Advanced Web Fetching untuk Plagiarism Checker
================================================

[UPGRADE 26 Sep] Mengadopsi arsitektur pengambilan web dari proyek chatbot
(FreeAIBot) yang sudah terbukti di produksi, disesuaikan untuk kebutuhan
plagiarism checker (fokus: URL web + halaman jurnal/repositori akademik).

Yang diadopsi dari sistem bot:
1. **Jina AI LLM Reader** (r.jina.ai) — merender halaman SPA/JavaScript menjadi
   Markdown bersih. Repositori kampus modern (OJS 3, DSpace 7, Next.js) sering
   mengirim shell kosong tanpa ini.
2. **Deteksi halaman challenge** — Jina kadang mengembalikan HTTP 200 berisi
   halaman Cloudflare "Just a moment..." / captcha. Body itu BUKAN isi halaman
   dan harus ditolak agar fallback direct-fetch tetap berjalan.
3. **SPA metadata extraction** — saat direct fetch hanya dapat shell kosong,
   ambil <title>/og:* agar tetap ada fakta halaman (judul jurnal, deskripsi).
4. **Semantic content extraction** — prioritaskan <article>/<main> sebelum
   fallback ke seluruh body (mengurangi navigasi/footer masuk ke korpus).
5. **Retry dengan koneksi hangat** — percobaan kedua hampir selalu berhasil
   untuk situs berat karena DNS+TLS sudah tersimpan.

Semua panggilan tetap melewati is_safe_url (SSRF shield) dari web_scraper.
"""

import os
import re
import logging
import urllib.parse

logger = logging.getLogger(__name__)

# Timeout konfigurasi (dapat di-override via env)
JINA_TIMEOUT = float(os.environ.get("JINA_TIMEOUT", "6"))
DIRECT_TIMEOUT = float(os.environ.get("SCRAPE_TIMEOUT_DIRECT", "12"))
MAX_CONTENT_CHARS = int(os.environ.get("SCRAPE_MAX_CHARS", "600000"))

# Pola halaman challenge/anti-bot yang dikembalikan sebagai "sukses"
_RE_CHALLENGE = re.compile(
    r"just a moment|attention required|cf-browser-verification|"
    r"enable javascript and cookies|checking your browser|"
    r"access denied|are you a robot|captcha|verify you are human|"
    r"ddos protection|please wait while we verify",
    re.I,
)

# Elemen non-konten yang dibuang sebelum ekstraksi teks
_RE_DROP_TAGS = re.compile(
    r"<(script|style|noscript|svg|iframe|nav|header|footer|aside|menu|form|button)\b[^>]*>.*?</\1>",
    re.I | re.S,
)
_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _clean_html_to_text(html: str, prefer_semantic: bool = True) -> str:
    """Konversi HTML menjadi teks bersih.

    Urutan penting: (1) isolasi <article>/<main> bila ada dan cukup besar,
    (2) buang elemen non-konten, (3) pertahankan struktur paragraf/heading,
    (4) decode entitas HTML.
    """
    if not html or not isinstance(html, str):
        return ""

    # (1) Isolasi konten semantik — hindari menu/footer/sidebar masuk korpus.
    if prefer_semantic:
        m = re.search(r"<(?:article|main)\b[^>]*>([\s\S]*?)</(?:article|main)>", html, re.I)
        if m and len(m.group(1)) > 400:
            html = m.group(1)

    # (2) Buang elemen non-konten & komentar.
    html = _RE_COMMENT.sub(" ", html)
    html = _RE_DROP_TAGS.sub(" ", html)

    # (3) Pertahankan batas blok agar kalimat tidak menempel.
    html = re.sub(r"<h[1-6]\b[^>]*>([\s\S]*?)</h[1-6]>", r"\n\n\1\n", html, flags=re.I)
    html = re.sub(r"<li\b[^>]*>([\s\S]*?)</li>", r"\n\1", html, flags=re.I)
    html = re.sub(r"</(?:p|div|tr|section|blockquote)>", "\n", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)

    # (4) Decode entitas HTML umum + normalisasi spasi.
    entities = {
        "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&apos;": "'",
        "&mdash;": " - ", "&ndash;": " - ", "&hellip;": "...",
    }
    for k, v in entities.items():
        html = html.replace(k, v)
    html = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))) if int(m.group(1)) < 0x10000 else " ", html)

    text = re.sub(r"[ \t\r\f\v]+", " ", html)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_spa_metadata(html: str) -> str:
    """Ambil metadata halaman SPA yang tidak bisa dirender tanpa JavaScript.

    SPA (Next.js/React/Vue di repositori kampus modern) mengirim shell kosong,
    tetapi <title> dan og:* hampir selalu terisi — cukup untuk memberi model
    fakta halaman (judul jurnal, deskripsi) tanpa mengarang.
    """
    if not html or not isinstance(html, str):
        return ""

    def pick(pattern: str) -> str:
        m = re.search(pattern, html, re.I)
        if not m:
            return ""
        val = re.sub(r"<[^>]+>", " ", m.group(1))
        val = re.sub(r"\s+", " ", val).strip()
        return val[:300]

    title = pick(r"<title[^>]*>([\s\S]*?)</title>")
    og_title = pick(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']')
    desc = pick(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']')
    og_desc = pick(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']')
    og_site = pick(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']')
    citation_title = pick(r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']')
    citation_author = pick(r'<meta[^>]+name=["\']citation_author["\'][^>]+content=["\']([^"\']+)["\']')
    citation_journal = pick(r'<meta[^>]+name=["\']citation_journal_title["\'][^>]+content=["\']([^"\']+)["\']')

    parts = []
    main_title = citation_title or og_title or title
    if main_title:
        parts.append(f"Judul: {main_title}")
    if citation_author:
        parts.append(f"Penulis: {citation_author}")
    if citation_journal:
        parts.append(f"Jurnal: {citation_journal}")
    if og_site:
        parts.append(f"Situs: {og_site}")
    main_desc = og_desc or desc
    if main_desc:
        parts.append(f"Deskripsi: {main_desc}")

    if not parts:
        return ""
    return "[Metadata Halaman]:\n" + "\n".join(parts)


def fetch_with_jina(url: str) -> str:
    """Baca halaman via Jina AI LLM Reader (merender JS -> Markdown).

    Mengembalikan string kosong bila Jina gagal atau mengembalikan halaman
    challenge. Timeout pendek: Jina biasanya membalas 403 cepat atau timeout
    penuh — menunggu lama membuang jatah waktu direct fetch.
    """
    try:
        import requests
        res = requests.get(
            f"https://r.jina.ai/{url}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/plain",
            },
            timeout=JINA_TIMEOUT,
        )
        if res.status_code != 200:
            return ""
        text = res.text or ""
        # Tolak halaman challenge yang menyamar sebagai sukses.
        if _RE_CHALLENGE.search(text[:1500]):
            return ""
        if len(text) < 120:
            return ""
        return text[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


def fetch_direct(url: str, session=None, headers: dict = None) -> str:
    """Direct fetch dengan retry koneksi-hangat + ekstraksi bertingkat.

    Tingkat 1: teks dari <article>/<main> atau body penuh.
    Tingkat 2: metadata SPA bila body tidak menghasilkan apa-apa.
    """
    import requests

    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.5",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    }
    if headers:
        default_headers.update(headers)

    getter = session.get if session is not None else requests.get

    # Retry 2x: percobaan kedua hampir selalu berhasil karena DNS+TLS sudah hangat.
    for attempt in range(2):
        try:
            res = getter(
                url, timeout=DIRECT_TIMEOUT, headers=default_headers,
                allow_redirects=True, verify=True,
            )
        except requests.exceptions.SSLError:
            try:
                res = getter(
                    url, timeout=DIRECT_TIMEOUT, headers=default_headers,
                    allow_redirects=True, verify=False,
                )
            except Exception:
                continue
        except Exception:
            continue

        if res is None or res.status_code != 200:
            return ""

        raw = res.text or ""
        if not raw:
            return ""

        text = _clean_html_to_text(raw)
        if text and len(text) > 200:
            return text[:MAX_CONTENT_CHARS]

        # Body terlalu tipis -> coba metadata SPA.
        meta = extract_spa_metadata(raw)
        if meta and len(meta) > 60:
            return meta

        # Ada konten tapi pendek — masih berguna bila > 60 char.
        if text and len(text) > 60:
            return text[:MAX_CONTENT_CHARS]
        break

    return ""


def fetch_page_advanced(url: str, session=None, headers: dict = None) -> str:
    """Ambil isi halaman dengan rantai bertingkat: Jina Reader -> direct fetch.

    Ini titik masuk utama yang dipakai web_scraper.scrape_url(). Semua pemanggil
    WAJIB sudah memvalidasi URL dengan is_safe_url sebelum memanggil fungsi ini.
    """
    if not url:
        return ""

    # PDF/dokumen biner: Jina Reader bisa mengembalikan teks; direct fetch tidak.
    is_binary = bool(re.search(r"\.(?:pdf|docx?|xlsx?|pptx?)(?:[?#]|$)", url, re.I))

    # 1. Jina Reader (juga menangani PDF & SPA).
    content = fetch_with_jina(url)
    if content and len(content) > 120:
        return content

    # 2. Direct fetch untuk HTML (biner tidak berguna via requests text).
    if not is_binary:
        content = fetch_direct(url, session=session, headers=headers)
        if content:
            return content

    return ""
