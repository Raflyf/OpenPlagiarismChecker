import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + " "
upper_text = text.upper()
import re
print("Matches for BAB I:")
for m in re.finditer(r'\bBAB\s+I\b.*?(PENDAHULUAN|LATAR BELAKANG)', upper_text, re.DOTALL):
    print(m.start(), upper_text[m.start()-50:m.end()+50].replace('\n', ' '))
