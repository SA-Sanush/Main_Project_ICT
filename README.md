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
