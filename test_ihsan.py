from app.engine.extractor import extract_text_from_pdf, clean_text
import re

pdf_path = r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf'
text, _ = extract_text_from_pdf(pdf_path, fast_mode=True)
sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if len(s.split()) >= 8]
print(f"Total extracted text length: {len(text)}")
print(f"Total sentences: {len(sentences)}")

# Let's print the first 200 characters and the last 200 characters
print("START:")
print(text[:200])
print("\nEND:")
print(text[-200:])
