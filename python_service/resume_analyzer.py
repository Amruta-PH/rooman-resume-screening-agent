#!/usr/bin/env python3
"""Explainable, fault-tolerant resume scoring service.

The service intentionally keeps its core scoring deterministic. If the optional
RESUME_LLM_API_KEY is present, it asks the configured OpenAI-compatible endpoint
to refine each explanation without exposing credentials to the client.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_ALIASES = {
    "python": ["python"], "sql": ["sql", "postgresql", "mysql"], "machine learning": ["machine learning", "ml"],
    "data analysis": ["data analysis", "analytics", "data analytics"], "statistics": ["statistics", "statistical"],
    "pandas": ["pandas"], "numpy": ["numpy"], "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow"], "pytorch": ["pytorch"], "aws": ["aws", "amazon web services"],
    "docker": ["docker", "containerization"], "git": ["git", "github"], "tableau": ["tableau"],
    "power bi": ["power bi", "powerbi"], "excel": ["excel"], "nlp": ["nlp", "natural language processing"],
    "llm": ["llm", "large language model", "generative ai"], "communication": ["communication", "stakeholder"],
    "leadership": ["leadership", "team lead", "mentored"], "javascript": ["javascript", "typescript"],
}
DEGREE_PATTERNS = [
    ("PhD", r"\b(ph\.?d|doctorate)\b"), ("Master's", r"\b(m\.s\.|m\.sc|master(?:'s)?)\b"),
    ("Bachelor's", r"\b(b\.s\.|b\.sc|bachelor(?:'s)?)\b"),
]

class AnalysisError(Exception):
    pass

def clean_filename(value):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", Path(value).name)

def extract_text(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace").strip()
    if suffix == ".docx":
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs).strip()
        except Exception as exc:
            raise AnalysisError(f"Could not read DOCX file '{path.name}': {exc}") from exc
    if suffix == ".pdf":
        try:
            import fitz
            document = fitz.open(path)
            text = "\n".join(page.get_text() for page in document)
            document.close()
            return text.strip()
        except Exception as exc:
            raise AnalysisError(f"Could not read PDF file '{path.name}': {exc}") from exc
    raise AnalysisError(f"Unsupported file type for '{path.name}'. Use PDF, DOCX, or TXT where permitted.")

def extract_skills(text):
    lowered = text.lower()
    return sorted(skill for skill, aliases in SKILL_ALIASES.items() if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", lowered) for alias in aliases))

def extract_degree(text):
    lowered = text.lower()
    for degree, pattern in DEGREE_PATTERNS:
        if re.search(pattern, lowered):
            return degree
    return "Not stated"

def extract_years(text):
    matches = re.findall(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b", text.lower())
    explicit = max((int(value) for value in matches), default=0)
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    range_years = max(years) - min(years) if len(years) >= 2 else 0
    return min(45, max(explicit, range_years))

def candidate_name(text, filename):
    for line in text.splitlines()[:6]:
        compact = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        if 3 <= len(compact) <= 52 and 1 < len(compact.split()) <= 5 and not re.search(r"resume|curriculum|engineer|analyst|scientist", compact, re.I):
            return compact.title()
    return Path(filename).stem.replace("_", " ").replace("-", " ").title()

def token_set(value):
    return {t for t in re.findall(r"[a-z]{3,}", value.lower()) if t not in {"with", "from", "that", "have", "will", "your", "and", "the", "for"}}

def llm_enrichment(job, resume_text, candidate, fallback):
    key = os.getenv("RESUME_LLM_API_KEY", "").strip()
    if not key:
        return candidate, fallback, None
    base = os.getenv("RESUME_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("RESUME_LLM_MODEL", "gpt-4o-mini")
    prompt = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 260,
        "messages": [
            {"role": "system", "content": "You are a fair recruiting assistant. Extract only explicit, job-related resume evidence. Never infer protected traits or invent qualifications. Return JSON with skills (array chosen only from job_skills), education (PhD, Master's, Bachelor's, or Not stated), years (integer 0-45), and explanation (under 70 words)."},
            {"role": "user", "content": json.dumps({"job_skills": job["skills"], "required_years": job["years"], "resume_excerpt": resume_text[:6000], "deterministic_candidate": candidate, "deterministic_explanation": fallback})},
        ],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions", data=json.dumps(prompt).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = json.loads(response.read().decode())["choices"][0]["message"]["content"].strip()
            enriched = json.loads(content)
            approved_skills = sorted({skill for skill in enriched.get("skills", []) if skill in job["skills"]} | set(candidate["skills"]))
            education = enriched.get("education") if enriched.get("education") in {"PhD", "Master's", "Bachelor's", "Not stated"} else candidate["degree"]
            years = enriched.get("years") if isinstance(enriched.get("years"), int) and 0 <= enriched["years"] <= 45 else candidate["years"]
            return {"skills": approved_skills, "degree": education, "years": max(candidate["years"], years)}, str(enriched.get("explanation", ""))[:800] or fallback, None
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, TypeError, TimeoutError) as exc:
        return candidate, fallback, f"LLM analysis was unavailable ({str(exc)[:120]}). Deterministic extraction and scoring were used."

def evaluate(job_text, resume_text, filename):
    job_skills = extract_skills(job_text)
    job_years = extract_years(job_text)
    candidate_skills = extract_skills(resume_text)
    candidate_years = extract_years(resume_text)
    degree = extract_degree(resume_text)
    preliminary_candidate = {"skills": candidate_skills, "years": candidate_years, "degree": degree}
    preliminary_note = "Optional LLM extraction may refine explicit, job-related evidence; deterministic matching remains available as a fallback."
    enriched_candidate, llm_explanation, warning = llm_enrichment({"skills": job_skills, "years": job_years}, resume_text, preliminary_candidate, preliminary_note)
    candidate_skills, candidate_years, degree = enriched_candidate["skills"], enriched_candidate["years"], enriched_candidate["degree"]
    matching = sorted(set(job_skills) & set(candidate_skills))
    missing = sorted(set(job_skills) - set(candidate_skills))
    skill_score = round(50 * len(matching) / max(1, len(job_skills)))
    job_tokens, resume_tokens = token_set(job_text), token_set(resume_text)
    similarity = len(job_tokens & resume_tokens) / max(1, len(job_tokens | resume_tokens))
    relevance_score = round(20 * min(1, similarity * 4))
    experience_score = round(20 * min(1, candidate_years / max(1, job_years))) if job_years else 14
    education_score = 10 if degree != "Not stated" else 4
    score = max(0, min(100, skill_score + relevance_score + experience_score + education_score))
    recommendation = "Strong hire" if score >= 80 else "Hire" if score >= 68 else "Consider" if score >= 52 else "No hire"
    fallback = (
        f"Matched {len(matching)} of {len(job_skills)} identified job skills, contributing {skill_score}/50 points. "
        f"Resume-to-job language overlap contributed {relevance_score}/20; experience contributed {experience_score}/20 "
        f"based on {candidate_years or 'unstated'} years against a {job_years or 'not stated'}-year target; education contributed {education_score}/10."
    )
    explanation = llm_explanation if llm_explanation != preliminary_note else fallback
    return {
        "candidateName": candidate_name(resume_text, filename), "sourceFile": clean_filename(filename), "score": score,
        "recommendation": recommendation, "matchingSkills": matching, "missingSkills": missing,
        "experienceSummary": f"{candidate_years if candidate_years else 'Experience duration not stated'} years; {degree}",
        "education": degree, "scoreBreakdown": {"skills": skill_score, "relevance": relevance_score, "experience": experience_score, "education": education_score},
        "explanation": explanation, "llmWarning": warning,
    }

def run(payload):
    job_path = payload.get("job_path")
    resumes = payload.get("resumes") or []
    if not job_path:
        raise AnalysisError("A job description is required.")
    if len(resumes) < 10:
        raise AnalysisError("Upload at least 10 resumes to start an unbiased screening session.")
    job_text = extract_text(job_path)
    if len(job_text) < 40:
        raise AnalysisError("The job description appears empty or contains too little readable text.")
    candidates, warnings = [], []
    for item in resumes:
        text = extract_text(item["path"])
        if len(text) < 40:
            raise AnalysisError(f"'{item['filename']}' appears empty or image-only. Use a text-based PDF or DOCX.")
        result = evaluate(job_text, text, item["filename"])
        llm_warning = result.pop("llmWarning")
        if llm_warning:
            warnings.append(llm_warning)
        candidates.append(result)
    candidates.sort(key=lambda item: (-item["score"], item["candidateName"]))
    for index, candidate in enumerate(candidates, 1):
        candidate["rank"] = index
    return {"meta": {"totalCandidates": len(candidates), "jobSkills": extract_skills(job_text), "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), "method": "Explainable deterministic scoring with optional LLM explanation"}, "candidates": candidates, "warnings": sorted(set(warnings))}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(json.loads(Path(args.input).read_text())), ensure_ascii=False))
    except AnalysisError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(2)
    except Exception as exc:
        print(json.dumps({"error": f"Analysis failed safely: {str(exc)[:160]}"}))
        sys.exit(1)
