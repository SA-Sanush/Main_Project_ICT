# Talent Acquisition System

A Flask web app that scans resumes, scores them against common TAS criteria, compares them with an optional target job description, recommends matching roles, and stores scan history for logged-in users.

## Features

- Upload resumes as PDF, DOCX, or TXT files.
- Extract resume text and score contact info, summary, work experience, education, skills, TAS optimization, consistency, proofreading, file format, and relevance.
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

## OCR for Scanned PDFs

The app can analyze scanned/image-based PDFs when OCR is installed.

Install the Python packages from `requirements.txt`, then install these system tools:

- Tesseract OCR
- Poppler

If they are not available on your system `PATH`, set:

```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:POPPLER_PATH="C:\path\to\poppler\Library\bin"
python app.py
```

Normal selectable-text PDFs, DOCX, and TXT files do not need OCR.
