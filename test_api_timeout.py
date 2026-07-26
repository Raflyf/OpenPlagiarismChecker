import requests
import time

urls = {
    'Crossref': 'https://api.crossref.org/works?query=test&rows=1',
    'Semantic Scholar': 'https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1',
    'DOAJ': 'https://doaj.org/api/search/articles/test?pageSize=1'
}

for name, url in urls.items():
    start = time.time()
    try:
        res = requests.get(url, timeout=8)
        dur = time.time() - start
        print(f"[{name}] Sukses HTTP {res.status_code} dalam {dur:.2f} detik")
    except Exception as e:
        dur = time.time() - start
        print(f"[{name}] ERROR: {e} dalam {dur:.2f} detik")
