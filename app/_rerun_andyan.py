import os, sys, json, hashlib
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.extractor import extract_text_auto, get_sentences
from engine.web_scraper import get_candidate_urls, scrape_all_candidates
from engine.shingling import calculate_similarity

path = 'before_turnitin/SKRIPSI ANDYAN AGUNG MAULANA 23%.pdf'
FROZEN = 'frozen_corpus'
doc_text, warns = extract_text_auto(os.path.join(os.path.dirname(__file__), path))
doc_hash = hashlib.md5(doc_text.encode('utf-8')).hexdigest()[:16]
fp = os.path.join(os.path.dirname(__file__), FROZEN, f'web_{doc_hash}.json')

sentences = get_sentences(doc_text)
print(f'[Andyan] {len(doc_text.split())} kata, {len(sentences)} kalimat')

urls, preloaded = get_candidate_urls(sentences, max_probes=250)
print(f'[Andyan] preloaded={len(preloaded)} scrape-urls={len(urls)}')
corpus = scrape_all_candidates(urls, preloaded)

with open(fp, 'w', encoding='utf-8') as f:
    json.dump(corpus, f, ensure_ascii=False)
print(f'[Andyan] korpus DIBEKUKAN ke {fp}: {len(corpus)} sumber')

sources, total_sim, phrases = calculate_similarity(
    doc_text, corpus, exclude_small=True, use_semantic=True, semantic_threshold=0.88)
print(f'[Andyan] SKOR LOKAL = {round(total_sim, 2)}%')
