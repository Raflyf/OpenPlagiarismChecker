# Graph Report - .  (2026-07-31)

## Corpus Check
- Large corpus: 59 files ╖ ~24,875,094 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 226 nodes · 318 edges · 27 communities (14 shown, 13 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]

## God Nodes (most connected - your core abstractions)
1. `search_with_fallbacks()` - 10 edges
2. `is_supabase_configured()` - 9 edges
3. `search_repository_direct()` - 8 edges
4. `scrape_all_candidates()` - 8 edges
5. `process_document()` - 8 edges
6. `extract_text_auto()` - 7 edges
7. `safe_get()` - 7 edges
8. `calculate_similarity()` - 7 edges
9. `extract_text_from_pdf()` - 6 edges
10. `extract_text_from_docx()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `check_frozen()` --calls--> `extract_text_auto()`  [EXTRACTED]
  app/server.py → app/engine/extractor.py
- `process_document()` --calls--> `extract_text_auto()`  [EXTRACTED]
  app/server.py → app/engine/extractor.py
- `get_cached_results()` --calls--> `get_cached_results_supabase()`  [EXTRACTED]
  app/engine/free_api_fallbacks.py → app/engine/supabase_client.py
- `save_to_cache()` --calls--> `save_to_cache_supabase()`  [EXTRACTED]
  app/engine/free_api_fallbacks.py → app/engine/supabase_client.py
- `process_document()` --calls--> `calculate_similarity()`  [EXTRACTED]
  app/server.py → app/engine/shingling.py

## Import Cycles
- None detected.

## Communities (27 total, 13 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (20): check_frozen(), _check_rate_limit(), cleanup_old_files(), get_frozen_path(), periodic_cleanup_task(), process_document(), Cek apakah file yang di-drop sudah memiliki korpus beku (frozen corpus).     En, Check rate limit for IP. Returns (allowed, remaining_time) (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (20): Script Migrasi Otomatis dari bank.db SQLite Lokal ke Supabase Cloud Database. Me, run_migration(), report(), _clean_str(), get_bank_texts_supabase(), get_bank_urls_supabase(), get_cached_results_supabase(), get_job_status_supabase() (+12 more)

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (22): _get_cache_conn(), get_cache_key(), get_cached_results(), Free API Fallbacks - Pencarian Web dengan DuckDuckGo + Google CSE (opsional). D, Menggunakan library duckduckgo_search (DDGS) yang jauh lebih handal     dalam m, Search MORAREF Kemenag (Kementerian Agama RI)     Mengakses portal jurnal ilmia, Search BASE (Bielefeld Academic Search Engine)     Database 300 juta+ publikasi, Search Internet Archive Scholar (35M+ publikasi ilmiah & skripsi terdigitalisasi (+14 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (17): discover_docs(), Auto-discover dokumen validasi di before_turnitin/.     Target Turnitin diambil, clean_text(), detect_manipulation(), extract_text_auto(), extract_text_from_docx(), extract_text_from_pdf(), extract_text_from_txt() (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (19): detect_platform(), google_site_search_fallback(), Direct scraping untuk repository kampus Indonesia tanpa batasan API. Strategi:, Search langsung ke repository tanpa API.     Mendeteksi platform (EPrints, DSpa, Gunakan HTTPX dengan HTTP/2 untuk mem-bypass WAF/Firewall kampus, Deteksi platform repository dari URL dan HTML, Search UBSI custom platform (repository.bsi.ac.id, repository.nusamandiri.ac.id), Search EPrints repository (format: eprints.*.ac.id) (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (17): batch_semantic_check(), calculate_semantic_similarity(), find_semantic_matches(), get_model(), Semantic Similarity Module for Paraphrase Detection Uses sentence-transformers, Load and cache the sentence-transformers model.     Using 'paraphrase-multiling, Calculate semantic similarity between two sentences., build_sentence_word_spans() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (12): fetch_arxiv(), fetch_europe_pmc(), fetch_google_web(), fetch_hal(), fetch_moraref(), fetch_openaire(), Mencari website publik & repositori dari Google Search biasa via ScrapingBee Pro, Mencari preprint di arXiv (2.4M+ papers, gratis tanpa API key). English STEM onl (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (14): get_bank_texts(), get_bank_urls(), _get_download_bytes(), init_bank_db(), load_corpus_bank(), Mengambil teks spesifik HANYA untuk target_urls dari bank.db lokal (instan <1ms), Mengeksekusi multi-threading untuk mengunduh web, lalu digabung dengan preloaded, Load seluruh isi bank.db sebagai dict (untuk backward compatibility Pemanggil). (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.20
Nodes (10): cohere_expand_queries(), fetch_semantic_scholar(), _load_keys(), _next_cohere_key(), _next_s2_key(), Kumpulkan key dari beberapa env var (comma-separated), buang duplikat & kosong., Ambil S2 key berikutnya secara round-robin (thread-safe). None bila tak ada key., Ambil Cohere key berikutnya secara round-robin (thread-safe). None bila tak ada (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.38
Nodes (4): APICircuitBreaker, _call_api_safe(), call_api_safe_v2(), Panggil API dengan circuit breaker v2 (auto-recovery).

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (6): fetch_garuda(), fetch_pubmed(), _get_session(), Mendapatkan requests.Session untuk thread saat ini (thread-safe)., Mencari Portal Jurnal Nasional (Garuda Kemdikbud/SINTA) — direct scrape tanpa pr, Mencari publikasi biomedis di PubMed/NCBI (30M+ paper, gratis, tanpa API key).

### Community 11 - "Community 11"
Cohesion: 0.40
Nodes (4): domain_priority(), Kembalikan skor prioritas domain (semakin tinggi semakin diutamakan) untuk     m, fetch_ddgs(), Mencari website publik biasa via DuckDuckGo, dengan Prioritas Situs Kampus/Jurna

### Community 13 - "Community 13"
Cohesion: 0.40
Nodes (5): _add_download_bytes(), is_safe_url(), Mengekstrak teks mentah dari URL (Website atau PDF) menggunakan AbstractAPI Prox, Sanitasi URL anti-SSRF: memblokir IP privat/local, loopback, dan metadata endpoi, scrape_url()

## Knowledge Gaps
- **1 isolated node(s):** `run.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_document()` connect `Community 0` to `Community 1`, `Community 3`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `AdaptiveThreadPool` connect `Community 12` to `Community 6`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `call_api_safe_v2()` connect `Community 9` to `Community 6`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **What connects `Mendeteksi trik mahasiswa untuk mencurangi Turnitin`, `Ekstrak teks, BUANG span dengan font mungil (< 4pt) yang tak terbaca mata.`, `Extract text from PDF with robust error handling` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.13438735177865613 - nodes in this community are weakly interconnected._