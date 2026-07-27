import json, os, warnings
warnings.filterwarnings('ignore')
from app.engine.extractor import extract_text_auto
from app.engine.shingling import calculate_similarity

path = r"d:\skripsi\project\plagiarism_checker\app\before_turnitin\15210233_TsauraHalwaQur'ani-2 13%.pdf"
frozen_path = r"d:\skripsi\project\plagiarism_checker\app\frozen_corpus\15210233_TsauraHalwaQur_ani_2.json"

with open(frozen_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)
doc_text, _ = extract_text_auto(path)

print("TSAURA SCORE CHECK:")
_, ngram_sim, _ = calculate_similarity(doc_text, corpus, exclude_small=True, use_semantic=False)
print(f"N-Gram only: {ngram_sim:.2f}%")

for t in [0.85, 0.86, 0.87, 0.88, 0.89, 0.90]:
    _, total_sim, _ = calculate_similarity(doc_text, corpus, exclude_small=True, use_semantic=True, semantic_threshold=t)
    print(f"Threshold {t:.2f}: {total_sim:.2f}% (delta vs 13.0%: {total_sim - 13.0:+.2f}pt)")
