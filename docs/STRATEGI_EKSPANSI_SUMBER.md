# Strategi Ekspansi Sumber Daya — Mengejar Database Turnitin

**Versi:** 1.1
**Tanggal:** 29 Juli 2026
**Tujuan:** Memetakan celah sumber daya dan prioritas penambahan API/sumber baru

---

## 1. Posisi Saat Ini vs Turnitin

### Database Turnitin

| Kategori            | Jumlah              | Sifat                     |
| ------------------- | ------------------- | ------------------------- |
| Jurnal berlangganan | ~20.000+ judul      | Bayar/paywall             |
| Skripsi mahasiswa   | ~2 miliar+ halaman  | Proprietary (dari kampus) |
| Web crawled         | ~90 miliar+ halaman | Publik                    |
| Buku akademik       | ~1.3 juta+          | Campuran                  |

### Database Kita (Open Source)

| Kategori                   | Jumlah                         | Sifat           |
| -------------------------- | ------------------------------ | --------------- |
| API akademik internasional | 12 sumber                      | Gratis          |
| API Indonesia              | 3 sumber (IOS, Neliti, Garuda) | Gratis          |
| Repositori kampus langsung | ~50 domain                     | Manual scraping |
| Web search (DDG, Google)   | Tak terbatas                   | Rate limited    |
| **Jumlah total terindeks** | **Jauh di bawah Turnitin**     |                 |

### Kesimpulan Awal

Tidak mungkin menyaingi skala Turnitin secara absolut. Tapi kita bisa mendekati akurasi untuk dokumen bahasa Indonesia dengan pendekatan **quality over quantity** — sumber Indonesia yang relevan jauh lebih penting daripada miliaran halaman web global.

---

## 2. Audit Celah Sumber Daya Saat Ini

### Yang SUDAH ADA (Covered)

| Sumber                                   | Cakupan                                   |
| ---------------------------------------- | ----------------------------------------- |
| Indonesia OneSearch (IOS)                | 1.200+ repositori kampus via API resmi    |
| Neliti                                   | 500.000+ jurnal, tesis, skripsi Indonesia |
| Garuda (Kemdiktisaintek)                 | Portal jurnal nasional (free)             |
| Repositori langsung (EPrints/DSpace/OJS) | ~50 domain kampus prioritas               |
| DuckDuckGo + prioritas .ac.id            | Web publik dengan bias akademik           |
| Google Scholar (via ScrapingBee)         | Scholar global (English dominan)          |
| Google Web (via ScrapingBee)             | Web global                                |
| Semantic Scholar                         | 200M+ paper internasional                 |
| Crossref                                 | Metadata DOI universal                    |
| OpenAlex                                 | 250M+ paper (bisa filter bahasa)          |
| DOAJ                                     | 9M+ open-access journal articles          |
| Arxiv                                    | 2.4M+ preprint STEM                       |
| CORE                                     | 300M+ papers aggregator                   |
| OpenAIRE                                 | 100M+ publikasi Eropa                     |
| Europe PMC                               | 40M+ full-text biomedikal                 |
| HAL                                      | French multi-discipline                   |
| Unpaywall API                            | DOI to PDF open-access resolver           |

### Yang TIDAK ADA (Gaps)

| Gap                                                    | Dampak                                                 | Prioritas  |
| ------------------------------------------------------ | ------------------------------------------------------ | ---------- |
| G1 SINTA (sinta.kemdiktisaintek.go.id)                 | Metadata untuk prioritas domain                        | Medium     |
| G2 **MORAREF Kemenag** (moraref.kemenag.go.id)         | Ribuan jurnal UIN/IAIN/STAIN full-text                 | **TINGGI** |
| G3 Repositori UIN se-Indonesia (15+ UIN)               | Skripsi mahasiswa UIN dalam jumlah besar               | **TINGGI** |
| G4 **E-Thesis PTN besar** (UGM, UI, ITB, Unair, Undip) | Repositori tesis PTN besar                             | **TINGGI** |
| G5 Google Scholar Indonesia (query Bahasa Indonesia)   | Scholar dengan bias bahasa Indonesia                   | Medium     |
| G6 BASE (base-search.net)                              | 300M+ dokumen via OAI-PMH gratis                       | Medium     |
| G7 Internet Archive Scholar                            | 35M+ artikel, banyak overlap                           | Low        |
| G8 Scilit.net                                          | Database MDPI, overlap Semantic Scholar                | Low        |
| G9 Lens.org                                            | 200M+ scholarly records, free API                      | Medium     |
| G10 PubMed Central                                     | Sebagian sudah lewat Europe PMC                        | Low        |
| G11 DataCite/Zenodo                                    | Sebagian lewat OpenAIRE                                | Low        |
| G12 Repository UMS, UMM, UMY, UAD (UMMU cluster)       | Kampus swasta terbesar                                 | **TINGGI** |
| G13 Repository Telkom, Binus, Gunadarma                | Kampus swasta besar IT                                 | Medium     |
| G14 **OJS Langsung** (ribuan) — tanpa via IOS          | OJS adalah platform jurnal paling populer di Indonesia | **TINGGI** |
| G15 PDF langsung dari Google Search Indonesia          | filetype:pdf site:.ac.id                               | Medium     |
| G16 Portal Garuda domain baru (sejak migrasi)          | Kode sudah pakai garuda.kemdiktisaintek.go.id          | **TINGGI** |

---

## 3. Prioritas Rekomendasi — Ranking by Impact

### Tier 1: 🔴 High Impact

| #   | Sumber                                                   | Metode                                      | Estimasi Tambahan Korpus | Implementasi |
| --- | -------------------------------------------------------- | ------------------------------------------- | ------------------------ | ------------ |
| 1   | **MORAREF Kemenag**                                      | REST API + OAI-PMH fallback                 | ~200.000+ artikel        | 2-3 jam      |
| 2   | **E-Thesis PTN besar** (UGM, UI, ITB, Unair, Undip, IPB) | Web scraping langsung dari repository       | ~150.000+ skripsi/tesis  | 3-4 jam      |
| 3   | **Google Scholar Indonesia queries**                     | Parameter lr=lang_id + kata kunci Indonesia | ~50.000+ per dokumen     | 1 jam        |
| 4   | **OJS Crawler massal**                                   | OAI-PMH 500+ OJS Indonesia                  | ~500.000+ artikel        | 4-5 jam      |

### Tier 2: 🟡 Medium Impact

| #   | Sumber                                  | Metode                                     | Estimasi            | Implementasi |
| --- | --------------------------------------- | ------------------------------------------ | ------------------- | ------------ |
| 5   | **BASE** (base-search.net)              | OAI-PMH API gratis, 300M+ records          | ~50.000+ relevan RI | 2 jam        |
| 6   | **SINTA** (sinta.kemdiktisaintek.go.id) | Scrape daftar jurnal terakreditasi         | Metadata prioritas  | 1 jam        |
| 7   | Repository UMS, UMM, UMY, UAD           | Scrape langsung                            | ~30.000+            | 1-2 jam      |
| 8   | Repository Binus, Telkom, Gunadarma     | Scrape langsung                            | ~20.000+            | 1 jam        |
| 9   | PDF .ac.id langsung                     | Google: filetype:pdf site:.ac.id "skripsi" | ~50.000+            | 1 jam        |

### Tier 3: 🟢 Nice to Have

| #   | Sumber                   | Metode               | Estimasi |
| --- | ------------------------ | -------------------- | -------- |
| 10  | Lens.org API             | REST API (free tier) | 2 jam    |
| 11  | Internet Archive Scholar | REST API             | 1 jam    |
| 12  | Scilit                   | Web scraping         | 2 jam    |

---

## 4. Detail Implementasi Prioritas Tertinggi

### 4.1 MORAREF Kemenag (moraref.kemenag.go.id)

**Mengapa penting:** MORAREF adalah portal jurnal ilmiah Kementerian Agama RI. Mengindeks semua jurnal UIN/IAIN/STAIN se-Indonesia. Sumber yang tidak ada duanya — jurnal keagamaan tidak tercover oleh IOS/Garuda secara penuh.

**Strategi — 2 pendekatan berlapis:**

**Pendekatan A (Prioritas):** REST API JSON:

- Endpoint: `https://moraref.kemenag.go.id/api/v1/journal/search`
- Parameter: `q={query}`, `page=`, `limit=`
- Response: JSON dengan title, abstract, authors, journal name, URL

**⚠️ Peringatan Implementasi:** Portal MORAREF sering mengubah struktur internalnya. Endpoint API JSON kadang membutuhkan token/kredensial atau mengembalikan 403/404. WAJIB sediakan fallback.

**Pendekatan B (Fallback):** Jika API JSON gagal (403/404), gunakan OAI-PMH endpoint:

- `https://moraref.kemenag.go.id/oai?verb=ListRecords&metadataPrefix=oai_dc&set=journal`
- Format XML standar OAI-PMH, lebih stabil dari API JSON
- Parse dengan BeautifulSoup atau xml.etree.ElementTree

```python
def fetch_moraref(probe):
    """MORAREF Kemenag dengan fallback OAI-PMH"""
    urls, texts = [], []
    short_probe = " ".join(probe.split()[:8])

    # Pendekatan A: Coba REST API dulu
    try:
        params = {"q": short_probe, "page": 1, "limit": 10}
        resp = requests.get(
            "https://moraref.kemenag.go.id/api/v1/journal/search",
            params=params, timeout=(5, 10)
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                combined = f"{item.get('title','')}. {item.get('abstract','')}"
                if len(combined) > 50:
                    urls.append(item.get('url',''))
                    texts.append(combined)
            return urls, texts
    except Exception:
        pass

    # Pendekatan B: Fallback OAI-PMH
    try:
        oai_params = {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc",
            "set": "journal"
        }
        resp = requests.get(
            "https://moraref.kemenag.go.id/oai",
            params=oai_params, timeout=(10, 20)
        )
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            for record in root.iter("{http://www.openarchives.org/OAI/2.0/}record"):
                title_el = record.find(".//{http://purl.org/dc/elements/1.1/}title")
                desc_el = record.find(".//{http://purl.org/dc/elements/1.1/}description")
                if title_el is not None and title_el.text:
                    combined = title_el.text
                    if desc_el is not None and desc_el.text:
                        combined += ". " + desc_el.text
                    if probe.split()[0].lower() in combined.lower():
                        urls.append(f"https://moraref.kemenag.go.id/article/{title_el.text[:50]}")
                        texts.append(combined)
    except Exception:
        pass

    return urls, texts
```

**Estimasi:** 200.000+ artikel jurnal.
**Prioritas:** 🔴 TINGGI.

---

### 4.2 E-Thesis PTN Besar

**Mengapa penting:** Repositori tesis PTN besar (UGM, UI, ITB, Unair, Undip) berisi skripsi/tesis full-text yang SANGAT relevan sebagai sumber plagiarisme. Ini adalah sumber yang paling mungkin dipakai mahasiswa sebagai referensi.

**Target repositories:**
| Universitas | URL | Platform | Estimasi Dokumen |
|-------------|-----|----------|------------------|
| UGM | etd.repository.ugm.ac.id | EPrints | 50.000+ |
| UI | lib.ui.ac.id | Custom | 30.000+ |
| ITB | repository.itb.ac.id | DSpace | 20.000+ |
| Unair | repository.unair.ac.id | DSpace | 25.000+ |
| Undip | eprints.undip.ac.id | EPrints | 40.000+ |
| IPB | repository.ipb.ac.id | DSpace | 30.000+ |

**Strategi:** Buat fungsi `fetch_univ_repository()` spesifik per platform (EPrints/DSpace) dengan query pencarian + ambil full-text. Sudah ada pola dari `indonesian_repos.py` — tinggal perluas daftar repositori.

**Estimasi:** 150.000+ dokumen.

---

### 4.3 Google Scholar Indonesia Query

**Mengapa penting:** Google Scholar dengan query bahasa Indonesia akan mengembalikan sumber berbahasa Indonesia yang tidak muncul di query bahasa Inggris.

**⚠️ Catatan Teknis:**

- Parameter `hl=id` hanya mengubah **bahasa interface** (tampilan web) — **tidak** memfilter dokumen berbahasa Indonesia
- Solusi yang benar: Gunakan parameter **`lr=lang_id`** (Language Restrict) atau tambahkan query bias

**Strategi:**

- Ubah `fetch_google_scholar()` untuk menambahkan parameter `lr=lang_id`
- Tambahkan query bias dengan kata kunci Indonesia: "skripsi", "tesis", "jurnal", "penelitian", "analisis", "pengaruh", "hubungan", "studi kasus", "site:.ac.id"
- Gunakan Cohere (yang sudah ada) untuk generate variasi frasa Indonesia

```python
def fetch_google_scholar(probe):
    """Google Scholar dengan filter bahasa Indonesia"""
    # Parameter lr=lang_id untuk filter bahasa Indonesia
    # Bukan hl=id (yang hanya ubah bahasa interface)
    params = {
        "q": f'{probe} site:.ac.id OR "skripsi" OR "tesis" OR "jurnal"',
        "hl": "id",
        "lr": "lang_id",  # Language restrict: Indonesian
    }
    # ... sisanya sama
```

**Estimasi:** 50.000+ sumber relevan per dokumen.

---

### 4.4 OJS Crawler Massal

**Mengapa penting:** Indonesia memiliki ribuan instalasi OJS (Open Journal Systems) di kampus-kampus. Platform jurnal paling populer di Indonesia. Banyak jurnal OJS tidak terindeks IOS/Garuda.

**⚠️ Catatan Teknis:**

- OJS versi 3.x **tidak memiliki API search JSON bawaan**
- Jangan gunakan endpoint API JSON untuk OJS — tidak akan berfungsi
- Solusi yang benar:

**Pendekatan A (Prioritas):** **OAI-PMH endpoint** — hampir semua OJS mengaktifkannya:

- Format: `{ojs_url}/oai?verb=ListRecords&metadataPrefix=oai_dc`
- Response XML standar OAI-PMH
- Bisa filter dengan `&set=journal:article`

**Pendekatan B (Fallback):** **Form GET** langsung ke search OJS:

- Format: `{ojs_url}/search/search?query={query}`
- Parse HTML hasilnya dengan BeautifulSoup

```python
def fetch_ojs(probe):
    """OJS Crawler via OAI-PMH + form GET fallback"""
    urls, texts = [], []
    short_probe = " ".join(probe.split()[:8])

    for ojs_url in OJS_REGISTRY:
        # Pendekatan A: OAI-PMH
        try:
            oai_url = f"{ojs_url}/oai?verb=ListRecords&metadataPrefix=oai_dc"
            resp = requests.get(oai_url, timeout=(5, 10))
            if resp.status_code == 200:
                # Parse XML... cari yang cocok dengan probe
                pass
        except Exception:
            pass

        # Pendekatan B: Form GET fallback
        try:
            search_url = f"{ojs_url}/search/search?query={short_probe}"
            resp = requests.get(search_url, timeout=(5, 10))
            if resp.status_code == 200:
                # Parse HTML... ekstrak judul & abstrak
                pass
        except Exception:
            pass

    return urls, texts
```

**Daftar OJS besar yang diketahui:**

```
ejournal.undip.ac.id
ejournal.uin-malang.ac.id
ejournal.uin-suka.ac.id
ejournal.unesa.ac.id
ejournal.upi.edu
ejournal.umm.ac.id
ejournal.ums.ac.id
jurnal.ugm.ac.id
journal.ui.ac.id
journal.unair.ac.id
journal.itb.ac.id
...
```

**Estimasi:** 500.000+ artikel jurnal.

---

### 4.5 BASE (Bielefeld Academic Search Engine)

**Mengapa penting:** BASE adalah mesin pencari akademik terbesar yang gratis dan open access. 300M+ dokumen dari 10.000+ sumber. API gratis tanpa rate limit berarti.

**API Endpoint:** `https://api.base-search.net/v3/search?query={query}&l=en&limit=20`

**Implementasi:** Fungsi `fetch_base()` di web_scraper.py.

---

## 5. Arsitektur Integrasi Sumber Baru

### 5.1 Group Baru di Parallel API Groups

```
                          fetch_probe_multi()
├──────────┬──────────┬──────────┬──────────────────┤
│ Group A  │ Group B  │ Group C  │ Group E (NEW)    │
│ Academic │ Indonesia│ Web      │ Indo Repository  │
├──────────┼──────────┼──────────┼──────────────────┤
│ Semantic │ IOS      │ DDGS     │ MORAREF          │
│ Scholar  │ Neliti   │ Google   │ E-Thesis PTN     │
│ Crossref │ Garuda   │ Web      │ OJS Crawler      │
│ OpenAlex │          │ Scholar  │ Repositori       │
│ DOAJ     │          │          │ Langsung         │
│ Arxiv    │          │          │ BASE             │
├──────────┼──────────┼──────────┼──────────────────┤
│ Timeout  │ Timeout  │ Timeout  │ Timeout          │
│ 15s      │ 12s      │ 10s      │ 20s              │
└──────────┴──────────┴──────────┴──────────────────┘
```

### 5.2 Prioritas Waktu Eksekusi

| Phase           | Sumber      | Kapan Jalan             | Bisa Di-skip Jika?        |
| --------------- | ----------- | ----------------------- | ------------------------- |
| Phase 1 (0-3s)  | Group A + B | Langsung                | —                         |
| Phase 2 (3-8s)  | Group C + E | Setelah Group A selesai | Jika Group A >= 10 sumber |
| Phase 3 (8-20s) | Scrape URL  | Paralel                 | Jika tidak ada URL        |

### 5.3 Database Korpus yang Diperluas

```python
class CorpusSource:
    IOS = "ios"
    NELITI = "neliti"
    GARUDA = "garuda"
    MORAREF = "moraref"      # NEW
    ETHESIS = "ethesis"       # NEW
    OJS = "ojs"              # NEW
    BASE = "base"            # NEW
    REPOSITORY = "repository"
    SCHOLAR = "scholar"
    WEB = "web"
    SEMANTIC = "semantic_scholar"
```

---

## 6. Dampak yang Diharapkan

### 6.1 Cakupan Korpus Indonesia

| Sumber                              | Sebelum           | Sesudah (estimasi) |
| ----------------------------------- | ----------------- | ------------------ |
| IOS (OneSearch)                     | ~1.200 repositori | ~1.200 repositori  |
| Neliti                              | ~500.000 dokumen  | ~500.000 dokumen   |
| Garuda                              | ~500.000 dokumen  | ~500.000 dokumen   |
| MORAREF (BARU)                      | 0                 | ~200.000 dokumen   |
| E-Thesis PTN (BARU)                 | 0                 | ~150.000 dokumen   |
| OJS Crawler (BARU)                  | 0                 | ~500.000 dokumen   |
| BASE (BARU)                         | 0                 | ~50.000 relevan RI |
| **Total estimasi korpus Indonesia** | **~1.5M**         | **~2.85M (+90%)**  |

### 6.2 Dampak pada Skor Similarity

- Gap akurasi saat ini ≈ 2-5% dari Turnitin (MAE ~2.10)
- Dengan korpus Indonesia +90%, gap diprediksi turun ke **1-2%**
- Kasus false-negative (skor 0% padahal seharusnya tinggi) akan berkurang drastis

---

## 7. Rekomendasi Eksekusi

| Sprint       | Isi                                                           | Estimasi |
| ------------ | ------------------------------------------------------------- | -------- |
| **Sprint 1** | MORAREF + E-Thesis PTN (UGM, UI, ITB) + Google Scholar ID fix | 4 jam    |
| **Sprint 2** | OJS Crawler + Repositori tambahan                             | 5 jam    |
| **Sprint 3** | BASE API + Repositori UMS/UMM/UAD                             | 2 jam    |
| **Sprint 4** | Kalibrasi ulang threshold + validasi                          | 2 jam    |

### Quick Win (1 jam pertama):

1. `fetch_moraref()` — REST API + OAI-PMH fallback
2. `fetch_base()` — base-search.net API
3. Fix `fetch_google_scholar()` — ganti hl=id jadi lr=lang_id + query bias
4. Perluas daftar `INDONESIAN_REPOSITORIES` di `indonesian_repos.py`

---

## 8. Keterbatasan yang Harus Diterima

Turnitin tetap unggul di:

1. Student paper repository — 2 miliar+ halaman (subscription model)
2. Publisher paywall content — Elsevier, Springer, Taylor & Francis, IEEE
3. Skala global — 90 miliar+ halaman web

Tapi untuk skripsi bahasa Indonesia, sumber di atas sudah mencakup >90% dari yang mungkin diplagiat.

---

## 9. Arahan Implementasi

Daftar fungsi baru yang perlu dibuat:

1. `fetch_moraref(probe)` — moraref.kemenag.go.id (REST API + OAI-PMH fallback)
2. `fetch_ethesis(probe)` — ethesis PTN (UGM, UI, ITB, dll)
3. `fetch_ojs(probe)` — OJS registry massal (OAI-PMH + form GET)
4. `fetch_base(probe)` — base-search.net
5. Fix `fetch_google_scholar()` — parameter `lr=lang_id` + query bias Indonesia
