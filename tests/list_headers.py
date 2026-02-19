import json
# jhajdhfas
sample_path = r"c:\Users\Dell\Desktop\resume_parser\resume_parser1\processed_resumes\BE.pdf_20260219_123106\clean_text.json"
with open(sample_path, 'r', encoding='utf-8') as f:
    clean_text = json.load(f)["content"]

headers = set()
for line in clean_text.splitlines():
    if line.startswith("##"):
        headers.add(line)

for h in sorted(list(headers)):
    print(h)
