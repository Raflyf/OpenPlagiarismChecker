import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath('app/run_test_groundtruth.py')))
from app.engine.extractor import extract_text_auto, get_sentences
from app.engine.web_scraper import get_candidate_urls, scrape_all_candidates
from app.engine.shingling import calculate_similarity

tests = [
    ("15210103_MUHAMMAD IHSAN PERMANA_SKRIPSI 18%.pdf", 18),
    ("Hesti_skripsi_final_before_turnitin 18%.pdf", 18),
    ("Rafly FIrmansyah - Skripsi_Fix 8%.pdf", 8)
]
os.environ["REFRESH"] = "1"
os.environ["BSI_COOKIE"] = "XSRF-TOKEN=eyJpdiI6IklRSXh1dVhzNXdxMEM5dUxXNkdsZnc9PSIsInZhbHVlIjoiQ2xvczdBVHd4YTFOcy82MGxQcCtTR2wxeWR6ejdUOVBtL05kMjRnRGZJZ0I0Mmd6VkYwM1pUcTBVWDRmTXFUSEtmczNLWXlWL1lOLytJenJGYjMwUWoyaUtoQThDQ1Q2N3pYMEpOVGNlSlVRcm9TNEVRTDVFTHNCN3pMLytYN2ciLCJtYWMiOiI5MGQyMzFiOTg0YmQ3NDYyOGQxNjM5MmJkMjc1ODgzYzViZmQ0Mzg2ZWJkNWJlYzFjMTY1ODU1YzgzYzUwZjFhIiwidGFnIjoiIn0%3D; repository_ubsi_session=eyJpdiI6Imt1dmZVN3FYVmJ5cUd2aHpYYWx6V3c9PSIsInZhbHVlIjoiME90cmU0NmJWdnBzclVRd3Fva0pLZXN3bzEzc0U0MmttbHhON1FYRDBCajludTl6RUtWMDdSaVZndVFuS2hsU3VpSFRqUURjajVmMEF0QjBaSFc5ZU5hMGtENDJGbHh0REQ1UDJSY2VuQkxwbE04RW85eDB6QVVQY2ErMDBkdFkiLCJtYWMiOiJkMTFmZTdiNDYxZmFjOTQ4YmNmY2M2Y2U3ZjUxMzg1YTMzODQ3NTJmNDA1ZmY0NDMyODkzMGQ2YzRkODI5MGY4IiwidGFnIjoiIn0%3D"

for name, tgt in tests:
    path = os.path.join("D:/skripsi/project/plagiarism_checker/app/before_turnitin", name)
    print(f"\n============================================================")
    print(f"[{name}] target Turnitin = {tgt}%")
    print(f"============================================================")
    
    t0 = time.time()
    doc_text, warns = extract_text_auto(path)
    sentences = get_sentences(doc_text)
    
    adaptive_probes = max(180, min(200, int(len(sentences) / 1.5)))
    urls, preloaded = get_candidate_urls(sentences, max_probes=adaptive_probes)
    corpus = scrape_all_candidates(urls, preloaded)
    
    # EXCLUDE_SMALL = FALSE (Mengejar target Turnitin)
    res, total_sim, _ = calculate_similarity(doc_text, corpus, exclude_small=False, use_semantic=True, semantic_threshold=0.88)
    dt = time.time() - t0
    
    print(f"[{name}] SKOR LOKAL = {round(total_sim,1)}%  (target {tgt}%)  [{int(dt)}s]", flush=True)

