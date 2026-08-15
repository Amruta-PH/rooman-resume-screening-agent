import tempfile
import unittest
from pathlib import Path

from resume_analyzer import AnalysisError, evaluate, extract_text, run


class ResumeAnalyzerTests(unittest.TestCase):
    def test_candidate_with_core_skills_scores_above_candidate_without_them(self):
        job = "Senior analyst needs 4 years Python SQL statistics Tableau and communication."
        strong = "Jamie Doe\n6 years Python SQL statistics Tableau communication. Master's in Analytics."
        weak = "Taylor Doe\n2 years Excel reporting. Bachelor's degree."
        self.assertGreater(evaluate(job, strong, "jamie.docx")["score"], evaluate(job, weak, "taylor.docx")["score"])

    def test_session_requires_ten_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            job = directory / "job.txt"
            job.write_text("Python SQL analyst role with 4 years of experience and Tableau.")
            resume = directory / "resume.txt"
            resume.write_text("Jordan Smith Python SQL Tableau 5 years Bachelor degree.")
            with self.assertRaises(AnalysisError):
                run({"job_path": str(job), "resumes": [{"path": str(resume), "filename": "resume.txt"}]})

    def test_extracts_text_from_docx_resume(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.docx"
            document = Document()
            document.add_paragraph("Morgan Lee — Python and SQL analyst")
            document.save(path)
            self.assertIn("Python and SQL analyst", extract_text(path))


if __name__ == "__main__":
    unittest.main()
