import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + "\n"
print(f"Total RAW characters: {len(text)}")
import re
sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if len(s.split()) >= 8]
print(f"Total RAW sentences: {len(sentences)}")
