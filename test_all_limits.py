import json
import glob
from app.engine.shingling import calculate_similarity
from app.engine.extractor import extract_text_from_pdf

# Rafly: 8.8%
# Hesti: 18%
# Ihsan: 18%
# Tsaura: 13%

files = {
    'Rafly': (r'd:\skripsi\project\plagiarism_checker\app\uploads\006b53a4-84d7-4ea2-975d-bfaf3ba1dd09.pdf', 'web_bf62354cfeb4871e.json'),
    'Hesti': (r'd:\skripsi\project\plagiarism_checker\app\uploads\05020c6a-6cd8-403d-8ab1-eb471887e221.pdf', 'web_269e860bcffc3619.json'),
    'Ihsan': (r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf', 'web_cfbc88383c076b1f.json'),
}

for name, (pdf, json_file) in files.items():
    try:
        doc_text, _, _, _ = extract_text_from_pdf(pdf, fast_mode=True, return_hidden=True)
        with open('app/frozen_corpus/' + json_file, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
        
        # Test None
        res_none, _, _, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_max_sources=None)
        score_none = res_none.get('total_similarity', 0)
        
        # Test 10
        res_10, _, _, _ = calculate_similarity(doc_text, corpus, use_semantic=True, semantic_max_sources=10)
        score_10 = res_10.get('total_similarity', 0)
        
        print(f"{name} -> None: {score_none:.2f}% | 10: {score_10:.2f}%")
    except Exception as e:
        print(f"Error {name}: {e}")
