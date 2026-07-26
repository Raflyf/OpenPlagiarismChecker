from app.engine.extractor import clean_text
import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + " "
import re
text = re.sub(r'\s+', ' ', text).strip()
chosen_idx = 20402
text = text[chosen_idx:75199]

quotes = [m.start() for m in re.finditer(r'["\u201c\u201d]', text)]
print(f"Number of quotes found: {len(quotes)}")
print("Quotes indices:")
for q in quotes:
    print(q, text[max(0, q-20):q+20])
