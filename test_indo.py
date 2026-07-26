from app.engine.indonesian_repos import search_all_indonesian_repos
import os
from dotenv import load_dotenv

load_dotenv()

probe = "Tabel IV.20 Hasil Precision, Recall, dan F1-Score"
urls, texts = search_all_indonesian_repos(probe)

print("Found", len(urls), "urls")
for u in urls:
    print(u)
