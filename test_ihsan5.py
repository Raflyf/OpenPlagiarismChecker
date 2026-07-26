from app.engine.extractor import clean_text
import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + " "

print(f"Original length: {len(text)}")

import re
text = re.sub(r'\s+', ' ', text).strip()
print(f"After regex sub: {len(text)}")

upper_text = text.upper()
chosen_idx = -1
for m in re.finditer(r'BAB\s+(?:I|1)\b', upper_text):
    idx = m.start()
    tail = text[m.end():m.end() + 40]
    dot_ratio = tail.count('.') / max(len(tail), 1)
    is_toc_entry = dot_ratio > 0.3 or bool(re.match(r'[\s\.]*\d{1,3}\s*$', tail[:15]))
    if not is_toc_entry:
        chosen_idx = idx
        break
if chosen_idx == -1:
    candidates = [m.start() for m in re.finditer(r'BAB\s+(?:I|1)\b', upper_text)
                  if m.start() < len(text) * 0.4]
    if candidates:
        chosen_idx = candidates[-1]

print(f"chosen_idx: {chosen_idx}")
if chosen_idx != -1 and chosen_idx < len(text) * 0.4:
    text = text[chosen_idx:]
    print(f"After bab1 cut: {len(text)}")

last_idx = max(text.upper().rfind('DAFTAR PUSTAKA'), text.upper().rfind('REFERENCES'))
print(f"last_idx: {last_idx}")
if last_idx > len(text) * 0.5:
    text = text[:last_idx]
    print(f"After biblio cut: {len(text)}")

text = re.sub(r'["""].*?["""]', '', text)
print(f"After quotes cut: {len(text)}")

