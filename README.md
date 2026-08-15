# Rooman AI Resume Screening Agent

Rooman is a compact, explainable candidate-screening web application built for the **Rooman 24-Hour AI Agent Challenge**. It supports a single job description and a cohort of ten to thirty resumes, extracts readable text from PDF, DOCX, and permitted plain-text files, produces a transparent 0–100 match score, ranks candidates, displays skill gaps, and exports the completed analysis as CSV or JSON.

The product is intentionally structured as an interview-friendly full-stack project. React provides the refined, responsive workspace; the server validates uploads and invokes a focused Python document-analysis engine; and the Python layer keeps the core score deterministic while using an optional server-only LLM credential to refine explanations.

## Architecture

| Layer | Responsibility | Main implementation |
| --- | --- | --- |
| Browser application | Drag-and-drop upload, input feedback, ranking dashboard, score detail, and CSV/JSON export. | React, TypeScript, Tailwind CSS, and accessible UI primitives. |
| Server bridge | Validates file count, file extensions, base64 payloads, and a 3 MB per-file limit; creates a short-lived working directory; invokes the analyzer. | Express and typed server procedures. |
| Python analysis engine | Reads document text, identifies skills, experience, and education, calculates an explainable score, optionally calls an LLM, and returns ranked JSON. | Python 3, PyMuPDF, and `python-docx`. |
| Sample data | Provides an out-of-the-box job description, eleven sample resume fixtures, and pre-computed results. | `sample_data/`. |

## Quick Start

### Local prerequisites

Install Node.js 22+, Python 3.11+, and pnpm. The Python requirements are deliberately small and listed in `python_service/requirements.txt`.

```bash
pnpm install
python3 -m pip install -r python_service/requirements.txt
pnpm dev
```

Open the local address shown by the development server. Select **Explore demo results** to review the bundled pre-computed report immediately, with no uploads and no LLM configuration required.

### Optional LLM configuration

The deterministic screening pipeline works without a credential. To enrich the candidate rationale with an OpenAI-compatible LLM, set the following environment variable **only in the server environment**:

```bash
RESUME_LLM_API_KEY=your_server_only_api_key
```

The optional variables `RESUME_LLM_BASE_URL` and `RESUME_LLM_MODEL` select an OpenAI-compatible endpoint and model, respectively. No credential is hard-coded, sent to the browser, written to an export, or stored with sample data. If the LLM request fails, the screen completes with the deterministic explanation and reports an unobtrusive warning instead of failing the candidate ranking.

> **Security note:** Do not expose `RESUME_LLM_API_KEY` in frontend code, browser environment variables, committed `.env` files, screenshots, or logs.

## Using the Application

Upload one job description in PDF, DOCX, or TXT format, then add at least ten resumes in PDF or DOCX format. The interface accepts file selection and drag-and-drop. Each file is limited to 3 MB and a maximum of thirty resumes is accepted per analysis session to keep the request bounded and responsive.

After selection, choose **Screen & rank candidates**. The dashboard orders candidates from highest to lowest score. Selecting a candidate exposes the score ring, recommendation, matched skills, missing skills, experience summary, and a point-by-point scoring explanation. The **CSV** and **JSON** controls download the complete visible report directly from the browser.

## Scoring Methodology

The score is an evidence-based heuristic rather than a prediction of job performance. It intentionally uses only job-related textual evidence in the uploaded documents.

| Component | Weight | Evidence used |
| --- | ---: | --- |
| Required-skill alignment | 50 points | Exact or recognized alias matches between the job brief and resume. |
| Role-language relevance | 20 points | Overlap between meaningful job-description and resume terms. |
| Experience evidence | 20 points | Explicit years or date-range evidence compared with the stated role target. |
| Education signal | 10 points | Presence of a bachelor's, master's, or doctoral degree statement. |

The analyzer lists the points awarded for every component. A recommendation is mapped from the final score: **Strong hire** at 80+, **Hire** at 68–79, **Consider** at 52–67, and **No hire** below 52. Recommendations are decision-support labels, not automated hiring decisions.

## Sample Data

The repository includes eleven anonymized, fictional candidate fixtures, a Senior Data Analyst job brief, and a pre-computed report. See [`sample_data/README.md`](sample_data/README.md) for the file map. The demo action exists so the user can immediately demonstrate the ranking, drill-down, score explanations, and exports before gathering real documents.

## Error Handling

The app provides clear user-facing feedback for unsupported types, empty files, files over the limit, insufficient resume count, parse failures, image-only or unreadably short documents, invalid job descriptions, analyzer start failures, and LLM provider failures. A per-candidate LLM outage does not interrupt deterministic ranking.

## Testing

Run the TypeScript and Python suites separately:

```bash
pnpm test
pnpm check
cd python_service && python3 -m unittest test_resume_analyzer.py
```

The tests cover sample-cohort integrity, minimum cohort validation, LLM credential-handling behavior, score ordering, and analysis-session validation.

## Known Limitations

PDF text extraction works best with digital, text-based PDFs; scanned PDFs require OCR, which is intentionally excluded to keep the challenge build focused. Skill matching currently uses a curated vocabulary and aliases, so unfamiliar technologies can be missed. Experience parsing relies on explicit wording or date ranges. LLM output may vary by provider and model, so it only refines the explanation and does not replace the traceable core score. The app is a screening-assistance tool and requires human review for hiring decisions.

## Future Improvements

Future versions could add OCR for scans, richer skill ontologies, configurable role-specific weights, reviewer notes, protected data retention policies, bias monitoring, multilingual extraction, authentication-aware report history, and evaluation benchmarks against human-reviewed labels. For higher-volume use, the analysis bridge could move to an asynchronous queue while retaining the same explainable result contract.
