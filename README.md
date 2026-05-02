# ATS Resume Scanner

A Flask web app that scans resumes, scores them against common ATS criteria, compares them with an optional target job description, recommends matching roles, and stores scan history for logged-in users.

## Features

- Upload resumes as PDF, DOCX, or TXT files.
- Extract resume text and score contact info, summary, work experience, education, skills, ATS optimization, consistency, proofreading, file format, and relevance.
- Paste a target job title and job description for role-specific relevance matching.
- View matched and missing keywords for the target role and built-in sample roles.
- Register, log in, and review saved scan history.
- Download saved scan reports as PDF files.
- Admin users can add recommendation catalog roles and review contact messages.
- Submit contact/support messages.
- Temporary upload handling: uploaded files are removed after parsing.
- Optional OCR fallback for scanned PDFs when Tesseract and Poppler are installed locally.

## Tech Stack

- Python
- Flask
- SQLite
- Pandas and NumPy
- pypdf
- python-docx
- spaCy, optional model support
- Local canvas chart rendering
- Optional pytesseract and pdf2image OCR support

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional, for better NLP entity extraction:

```powershell
python -m spacy download en_core_web_sm
```

Optional, for scanned-PDF OCR:

1. Install the Python packages from `requirements.txt`.
2. Install the Tesseract OCR binary.
3. Install Poppler and make sure its `bin` directory is on PATH.

Without those native OCR tools, the app still handles selectable-text PDF, DOCX, and TXT files.

## Run Locally

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-secret"
python app.py
```

Open `http://127.0.0.1:5000`.

For development debug mode:

```powershell
$env:FLASK_DEBUG = "1"
python app.py
```

## Testing

```powershell
pytest
```

## Configuration

- `FLASK_SECRET_KEY`: secret used for sessions and CSRF tokens.
- `FLASK_DEBUG=1`: enables Flask debug mode locally.
- `FLASK_RUN_HOST`: host to bind, defaults to `127.0.0.1`.
- `PORT`: port to bind, defaults to `5000`.
- `SPACY_MODEL`: spaCy model name, defaults to `en_core_web_sm`.
- `DISABLE_CSRF=1`: disables CSRF checks, mainly useful for local automated tests.
- `ADMIN_USERNAME`: username allowed to access `/admin`, defaults to `admin`.

## Runtime Files

The app creates runtime files locally:

- `ats_reports.db`
- `uploads/`
- `job_data.csv` if missing

The database and uploads are ignored by Git because they can contain private user data.

## Current Limitations

- Scoring combines rule checks with weighted term similarity, so it should still be treated as guidance rather than an official hiring or ATS result.
- Built-in job recommendations are based on a small local CSV. The target job description field gives more useful matching.
- Scanned PDF support depends on local Tesseract and Poppler installs.
- SQLite is suitable for a local/demo deployment, not a high-traffic production service.

## Good Next Improvements

- Replace keyword scoring with embeddings or a stronger semantic similarity model.
- Add email delivery or dashboard export for saved reports.
- Move from in-memory rate limiting to Redis-backed rate limiting for multi-process production.
