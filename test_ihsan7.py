from app.engine.extractor import clean_text
import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + " "

import re
text = re.sub(r'\s+', ' ', text).strip()
upper_text = text.upper()
chosen_idx = 20402
text = text[chosen_idx:75199]

quotes = [m.start() for m in re.finditer(r'["""“”.]', text) if text[m.start()] in '"“”']
print(f"Number of quotes found: {len(quotes)}")
print("First 10 quote indices:", quotes[:10])
print("Distances between pairs:")
for i in range(0, min(10, len(quotes)-1), 2):
    print(quotes[i+1] - quotes[i])
