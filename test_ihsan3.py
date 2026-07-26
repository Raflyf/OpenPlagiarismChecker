import fitz
doc = fitz.open(r'd:\skripsi\project\plagiarism_checker\app\uploads\4df17cb0-175d-46af-bbe1-210114fe6f00.pdf')
text = ""
for page in doc:
    text += page.get_text() + " "
upper_text = text.upper()
import re
print("Matches for LAMPIRAN:")
for m in re.finditer(r'\bLAMPIRAN\b', upper_text):
    print(m.start(), upper_text[m.start()-50:m.end()+50])

print("Matches for DAFTAR PUSTAKA:")
for m in re.finditer(r'\bDAFTAR\s+PUSTAKA\b', upper_text):
    print(m.start(), upper_text[m.start()-50:m.end()+50])
