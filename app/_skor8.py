"""Hitung skor tiap dokumen di before_turnitin dari FROZEN WEB (web_<hash>.json) yg
di-generate saat user upload di localhost. Cocokkan via hash isi teks (identik logika
server). Deterministik -> angka = yg user lihat di web."""
import os, sys, json, glob, re, hashlib, time
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.extractor import extract_text_auto
from engine.shingling import calculate_similarity

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "before_turnitin")
FROZEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frozen_corpus")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_skor8.txt")

processed = set()
if os.path.exists(LOG):
    with open(LOG, "r", encoding="utf-8") as f:
        for line in f:
            if "skor=" in line or "belum ada" in line:
                m = re.search(r'\[(.*?)\s*\]', line)
                if m: processed.add(m.group(1).strip())

def w(s):
    with open(LOG, "a", encoding="utf-8") as f: f.write(s + "\n")
    print(s, flush=True)

for path in sorted(glob.glob(os.path.join(BASE, "*"))):
    if not path.lower().endswith((".pdf", ".docx")): continue
    fn = os.path.basename(path)
    if fn[:34].strip() in processed:
        print(f"[{fn[:34]:34}] (Skipped, already in log)")
        continue
    m = re.search(r'(\d+)\s*%', fn)
    target = m.group(1)+"%" if m else "?"
    doc_text, _ = extract_text_auto(path)
    doc_hash = hashlib.md5(doc_text.encode("utf-8")).hexdigest()[:16]
    fp = os.path.join(FROZEN, f"web_{doc_hash}.json")
    if not os.path.exists(fp):
        # Fallback: cari file yang diawali dengan nama file aslinya (misal "Skripsi_Laila_Romadona...")
        # Hapus ekstensi dan persentase
        clean_name = re.sub(r'\s*\d+%\.(pdf|docx)$', '', fn, flags=re.IGNORECASE)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_name)
        # Ambil maksimal 40 karakter pertama (sesuai format lama)
        fallback_pattern = os.path.join(FROZEN, f"{clean_name[:40]}*.json")
        matches = glob.glob(fallback_pattern)
        
        if matches:
            fp = matches[0]
            print(f"[{fn[:34]:34}] Menggunakan fallback korpus: {os.path.basename(fp)}")
        else:
            w(f"[{fn[:34]:34}] target={target:4} FROZEN-WEB belum ada (hash {doc_hash})")
            continue
    corpus = json.load(open(fp, encoding="utf-8"))
    t0 = time.time()
    _, total, _ = calculate_similarity(doc_text, corpus, exclude_small=True,
                                       use_semantic=True, semantic_threshold=0.88)
    w(f"[{fn[:34]:34}] target={target:4} skor={total:.1f}%  corpus={len(corpus)} [{int(time.time()-t0)}s]")
w("SELESAI")
