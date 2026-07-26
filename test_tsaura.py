import json
import hashlib
from app.engine.shingling import calculate_similarity

pdf_path = r'd:\skripsi\project\plagiarism_checker\app\uploads\b50bdf27-3303-4dc8-b35e-cda908957166.pdf'
with open('app/frozen_corpus/web_19b365d6c5160dde.json', 'r', encoding='utf-8') as f:
    corpus = json.load(f)

from app.engine.extractor import extract_text_from_pdf
doc_text, _, _, _ = extract_text_from_pdf(pdf_path, fast_mode=True, return_hidden=True)

print("Testing with threshold 0.88...")
res_88, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_threshold=0.88)
print(f"Total 0.88: {res_88}")

print("Testing with threshold 0.89...")
res_89, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_threshold=0.89)
print(f"Total 0.89: {res_89}")

print("Testing with threshold 0.90...")
res_90, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_threshold=0.90)
print(f"Total 0.90: {res_90}")
