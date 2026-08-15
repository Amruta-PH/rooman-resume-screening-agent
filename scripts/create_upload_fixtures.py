from pathlib import Path
import json
from docx import Document

target = Path("/tmp/rooman-upload-fixtures")
target.mkdir(parents=True, exist_ok=True)
(target / "job_description.txt").write_text("Senior Data Analyst role requiring 4 years of Python, SQL, statistics, data analysis, Tableau, communication, Git, AWS, Docker, NLP and machine learning experience.")

profiles = [
    "Ava Chen 6 years Python SQL statistics data analysis Tableau communication Git AWS Docker NLP machine learning. Master of Science.",
    "Priya Nair 7 years Python SQL data analysis NLP machine learning AWS Docker Git. Master of Science.",
    "Noah Williams 6 years Python SQL statistics Tableau Git AWS Docker data analysis. Bachelor of Science.",
    "Daniel Kim 5 years Python SQL statistics NLP machine learning AWS Git communication. PhD in Computer Science.",
    "Elena Rossi 4 years Python SQL statistics Tableau Git data analysis communication. Bachelor of Science.",
    "Marcus Reed 5 years Python SQL statistics Tableau Git data analysis communication. Bachelor of Science.",
    "Grace Okafor 6 years Python SQL data analysis communication Git AWS Docker leadership. Master of Science.",
    "Maya Patel 5 years SQL Tableau data analysis communication. Bachelor of Science.",
    "Sofia Martinez 3 years Python SQL statistics Tableau NLP data analysis communication. Master of Science.",
    "Jordan Blake 4 years Python SQL data analysis communication. Bachelor of Science.",
]
for index, profile in enumerate(profiles, 1):
    document = Document()
    document.add_paragraph(profile)
    document.save(target / f"candidate_{index:02d}.docx")
payload = {"job_path": str(target / "job_description.txt"), "resumes": [{"path": str(target / f"candidate_{index:02d}.docx"), "filename": f"candidate_{index:02d}.docx"} for index in range(1, 11)]}
(target / "analysis_input.json").write_text(json.dumps(payload))
print(target)
