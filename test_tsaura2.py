import json
from app.engine.shingling import calculate_similarity
from app.engine.extractor import extract_text_from_pdf

pdf_path = r'd:\skripsi\project\plagiarism_checker\app\uploads\b50bdf27-3303-4dc8-b35e-cda908957166.pdf'
with open('app/frozen_corpus/web_19b365d6c5160dde.json', 'r', encoding='utf-8') as f:
    corpus = json.load(f)

doc_text, _, _, _ = extract_text_from_pdf(pdf_path, fast_mode=True, return_hidden=True)

for thresh in [0.88, 0.89, 0.90, 0.91]:
    res, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_threshold=thresh)
    total_score = res.get('total_similarity', 0)
    print(f"Threshold {thresh} -> Score: {total_score}%")
