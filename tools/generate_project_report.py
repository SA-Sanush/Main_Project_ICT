from __future__ import annotations

import html
import shlex
import shutil
import subprocess
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as app_module


OUT = ROOT / "reports" / "tas_project_report"
PAGES = OUT / "pages"
SCREENSHOTS = OUT / "screenshots"
RUNTIME = OUT / "runtime"
EDGE_PROFILE = OUT / "edge-profile"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def clean_output() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    PAGES.mkdir(parents=True)
    SCREENSHOTS.mkdir(parents=True)
    (RUNTIME / "uploads").mkdir(parents=True)
    (RUNTIME / "charts").mkdir(parents=True)
    EDGE_PROFILE.mkdir(parents=True)


def configure_app() -> None:
    app_module.DB_PATH = RUNTIME / "tas_reports.db"
    app_module.JOB_DATA_PATH = RUNTIME / "job_data.csv"
    app_module.UPLOAD_FOLDER = RUNTIME / "uploads"
    app_module.CHART_FOLDER = RUNTIME / "charts"
    app_module.RATE_LIMITS.clear()
    app_module.app.secret_key = "report-generation-secret"
    app_module.app.config.update(TESTING=True, CSRF_ENABLED=False, ADMIN_USERNAME="admin")
    app_module.init_db()
    app_module.load_job_data()


def make_file_page(name: str, body: bytes) -> Path:
    text = body.decode("utf-8", errors="replace")
    static_uri = (ROOT / "static").as_uri()
    text = text.replace('href="/static/', f'href="{static_uri}/')
    text = text.replace('src="/static/', f'src="{static_uri}/')
    text = text.replace('href="/', 'href="#')
    path = PAGES / f"{name}.html"
    path.write_text(text, encoding="utf-8")
    return path


def capture(page: Path, output_name: str, height: int = 1200) -> Path:
    target = SCREENSHOTS / f"{output_name}.png"
    args = [
        str(EDGE),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--user-data-dir=" + str(EDGE_PROFILE),
        "--window-size=1365," + str(height),
        "--screenshot=" + str(target),
        page.as_uri(),
    ]
    subprocess.run(edge_powershell(args), check=True, cwd=ROOT)
    return target


def edge_powershell(args: list[str]) -> list[str]:
    quoted = " ".join("'" + arg.replace("'", "''") + "'" for arg in args)
    return ["powershell", "-NoProfile", "-Command", "& " + quoted]


def render_app_screens() -> list[tuple[str, str, Path]]:
    screenshots: list[tuple[str, str, Path]] = []
    sample_resume = (
        b"Alex Analyst\nalex@example.com\nProfessional Summary: Data analyst with 3 years of "
        b"experience building SQL dashboards.\nWork Experience: Built Python and pandas "
        b"reports, delivered Tableau dashboards, automated stakeholder reporting, and "
        b"improved analytics documentation.\nEducation: BCA 2022.\nSkills: Python, SQL, "
        b"pandas, data visualization, communication, testing, git."
    )

    with app_module.app.test_client() as client:
        home = make_file_page("home", client.get("/").data)
        screenshots.append(("Fig 11.2.1", "Home page and resume upload form", capture(home, "01_home")))

        login = make_file_page("login", client.get("/login").data)
        screenshots.append(("Fig 11.2.2", "Login page", capture(login, "02_login", 950)))

        client.post("/login", data={"username": "admin", "password": "Password123!"})
        result_response = client.post(
            "/analyze",
            data={
                "job_title": "Data Analyst",
                "job_description": (
                    "Python SQL pandas Tableau dashboards reporting stakeholder communication "
                    "statistics analytics"
                ),
                "resume_file": (BytesIO(sample_resume), "alex_resume.txt"),
            },
            content_type="multipart/form-data",
        )
        result = make_file_page("result", result_response.data)
        screenshots.append(("Fig 11.2.3", "Resume analysis result page", capture(result, "03_result", 1600)))

        history = make_file_page("history", client.get("/history").data)
        screenshots.append(("Fig 11.2.4", "Scan history dashboard", capture(history, "04_history", 1200)))

        admin = make_file_page("admin", client.get("/admin").data)
        screenshots.append(("Fig 11.2.5", "Admin dashboard", capture(admin, "05_admin", 1500)))

        contact = make_file_page("contact", client.get("/contact").data)
        screenshots.append(("Fig 11.2.6", "Contact page", capture(contact, "06_contact", 1200)))

    return screenshots


def img_tag(path: Path) -> str:
    return f'<img src="{path.as_uri()}" alt="{html.escape(path.stem)}" />'


def report_html(screenshots: list[tuple[str, str, Path]]) -> str:
    figure_rows = "\n".join(
        f"<tr><td>{fig}</td><td>{html.escape(title)}</td><td>Appendix</td></tr>"
        for fig, title, _ in screenshots
    )
    screenshot_blocks = "\n".join(
        f"<figure><figcaption>{fig} {html.escape(title)}</figcaption>{img_tag(path)}</figure>"
        for fig, title, path in screenshots
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Talent Acquisition System Project Report</title>
  <style>
    @page {{ size: A4; margin: 22mm 18mm; }}
    body {{ font-family: "Times New Roman", serif; color: #111; line-height: 1.45; }}
    h1, h2, h3 {{ font-family: Arial, sans-serif; page-break-after: avoid; }}
    h1 {{ text-align: center; font-size: 22px; margin-top: 0; text-transform: uppercase; }}
    h2 {{ font-size: 18px; margin-top: 28px; text-transform: uppercase; border-bottom: 1px solid #999; padding-bottom: 4px; }}
    h3 {{ font-size: 15px; margin-top: 18px; }}
    p, li {{ font-size: 13.5px; text-align: justify; }}
    .cover {{ display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 900px; text-align: center; page-break-after: always; }}
    .cover p {{ text-align: center; font-size: 15px; margin: 8px 0; }}
    .project-title {{ font-size: 24px; font-weight: 700; margin: 24px 0; }}
    .page-break {{ page-break-before: always; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 18px; }}
    th, td {{ border: 1px solid #777; padding: 7px; font-size: 13px; vertical-align: top; }}
    th {{ background: #efefef; }}
    .toc td:first-child {{ width: 72%; }}
    .code {{ font-family: Consolas, monospace; background: #f4f4f4; padding: 10px; white-space: pre-wrap; font-size: 11px; }}
    figure {{ page-break-inside: avoid; margin: 18px 0 28px; }}
    figcaption {{ font-weight: 700; font-family: Arial, sans-serif; font-size: 13px; margin-bottom: 8px; }}
    img {{ width: 100%; border: 1px solid #888; }}
    .center {{ text-align: center; }}
  </style>
</head>
<body>
  <section class="cover">
    <p class="project-title">TALENT ACQUISITION SYSTEM</p>
    <p>A project report submitted to ICT Academy of Kerala</p>
    <p>in partial fulfillment of the requirements for the certification of</p>
    <p><strong>ADVANCED PYTHON</strong></p>
    <p>submitted by</p>
    <p><strong>SASAN</strong></p>
    <br />
    <p><strong>ICT ACADEMY OF KERALA</strong></p>
    <p>THIRUVANANTHAPURAM, KERALA, INDIA</p>
    <p>MAY 2026</p>
  </section>

  <h1>List of Figures</h1>
  <table><tr><th>SL NO.</th><th>FIGURES</th><th>PAGE NO.</th></tr>{figure_rows}</table>

  <h1 class="page-break">Table of Contents</h1>
  <table class="toc">
    <tr><td>ABSTRACT</td><td>4</td></tr>
    <tr><td>1. PROBLEM DEFINITION</td><td>5</td></tr>
    <tr><td>2. INTRODUCTION</td><td>7</td></tr>
    <tr><td>3. SYSTEM ANALYSIS</td><td>8</td></tr>
    <tr><td>4. SYSTEM DESIGN</td><td>13</td></tr>
    <tr><td>5. PROJECT DESCRIPTION</td><td>16</td></tr>
    <tr><td>6. SYSTEM TESTING AND IMPLEMENTATION</td><td>19</td></tr>
    <tr><td>7. SYSTEM MAINTENANCE</td><td>22</td></tr>
    <tr><td>8. FUTURE ENHANCEMENTS</td><td>24</td></tr>
    <tr><td>9. CONCLUSION</td><td>25</td></tr>
    <tr><td>10. BIBLIOGRAPHY</td><td>26</td></tr>
    <tr><td>11. APPENDIX: SCREENSHOTS</td><td>27</td></tr>
  </table>

  <h2 class="page-break">Abstract</h2>
  <p>The Talent Acquisition System is a Flask-based web application developed to support resume analysis, role matching, scan history management, and administrator control of a job recommendation catalog. The system accepts PDF, DOCX, and TXT resumes, extracts readable text, evaluates the resume against defined talent acquisition criteria, compares it with an optional target job description, and presents a score with improvement suggestions.</p>
  <p>The application is designed for candidates, placement teams, and administrators who need a structured way to evaluate resume readiness. It replaces manual resume checking with a repeatable scoring workflow that considers contact information, summary quality, work experience, education, skills, TAS optimization, consistency, proofreading, file format, and role relevance. Logged-in users can save scan results, view a dashboard of previous scores, and export reports as PDF documents.</p>

  <h2>1. Problem Definition</h2>
  <h3>1.1 Overview</h3>
  <p>Resume screening is often performed manually, which makes feedback slow and inconsistent. Candidates may not know whether their resume contains enough role-specific keywords, measurable bullet points, or complete contact information. Recruiters and training teams also need a simple system that can store scan history and track improvement over time.</p>
  <h3>1.2 Problem Statement</h3>
  <p>The problem addressed by this project is the absence of an accessible local web platform that can analyze resumes, calculate a structured score, recommend suitable roles, and preserve previous analysis results. Manual review lacks automation, objective criteria, and instant feedback. The proposed system provides a browser-based solution using Python, Flask, SQLite, Pandas, and NLP-style rule extraction.</p>

  <h2>2. Introduction</h2>
  <p>The Talent Acquisition System is built as a Python Flask application with server-rendered HTML templates, CSS styling, JavaScript chart rendering, SQLite persistence, and local file parsing utilities. Users can upload resumes, enter a target job title and description, and receive a detailed report containing criteria scores, detected skills, estimated experience, action verbs, missing keywords, suggested improvements, and matching job roles.</p>
  <p>The system also includes authentication, registration, protected scan history, PDF export, contact form submission, and an administrator dashboard. The admin user can review contact messages and add new roles to the recommendation catalog, making the system adaptable to future job categories.</p>

  <h2>3. System Analysis</h2>
  <h3>3.1 Existing System</h3>
  <p>Existing resume evaluation is commonly performed through manual reading, spreadsheet checklists, or disconnected online tools. These approaches often do not retain history, do not explain scoring, and require repeated manual effort from mentors or recruiters.</p>
  <h3>3.2 Proposed System</h3>
  <p>The proposed system automates resume scanning and produces an actionable report. It validates file types, extracts text, checks the file signature, analyzes resume content, applies weighted scoring, recommends roles, stores results in SQLite, and presents dashboards for users and administrators.</p>
  <h3>3.3 Feasibility Study</h3>
  <table>
    <tr><th>Feasibility Area</th><th>Assessment</th></tr>
    <tr><td>Technical Feasibility</td><td>The project uses stable Python libraries including Flask, Pandas, NumPy, pypdf/PyPDF2 fallback, python-docx, and optional spaCy/OCR support.</td></tr>
    <tr><td>Operational Feasibility</td><td>The interface is simple enough for candidates and administrators. Users interact through upload forms, dashboards, and report pages.</td></tr>
    <tr><td>Economic Feasibility</td><td>The system runs locally with open-source tools and SQLite, so deployment and maintenance costs are low.</td></tr>
    <tr><td>Security Feasibility</td><td>The application uses hashed passwords, session cookies, CSRF protection, file size limits, upload validation, and rate limiting.</td></tr>
  </table>
  <h3>3.4 Technologies Used</h3>
  <ul>
    <li>Python for application logic, parsing, scoring, and report generation.</li>
    <li>Flask for routing, sessions, forms, templates, and HTTP responses.</li>
    <li>SQLite for users, reports, and contact message storage.</li>
    <li>Pandas and NumPy for structured job catalog handling and scoring support.</li>
    <li>HTML, CSS, and JavaScript for the user interface and canvas charts.</li>
    <li>Werkzeug security utilities for password hashing and secure filenames.</li>
  </ul>
  <h3>3.5 Language Specifications</h3>
  <p>The backend is implemented in Python. Flask decorators define routes such as <code>/</code>, <code>/login</code>, <code>/register</code>, <code>/history</code>, <code>/admin</code>, and <code>/analyze</code>. Jinja templates are used for page rendering, and JavaScript enhances upload validation and chart animation.</p>

  <h2>4. System Design</h2>
  <h3>4.1 System Architecture</h3>
  <p>The system follows a conventional web application architecture. The client browser submits requests to the Flask application. Flask validates input, reads or writes SQLite data, processes resumes, and returns rendered HTML templates. Static CSS and JavaScript support the interface.</p>
  <table>
    <tr><th>Layer</th><th>Responsibility</th></tr>
    <tr><td>Presentation Layer</td><td>Jinja templates, CSS, JavaScript, forms, dashboards, and result pages.</td></tr>
    <tr><td>Application Layer</td><td>Flask routes, authentication guards, rate limiting, scoring functions, and report export.</td></tr>
    <tr><td>Data Layer</td><td>SQLite tables for users, reports, contacts, plus CSV job catalog storage.</td></tr>
    <tr><td>Parsing Layer</td><td>PDF, DOCX, TXT extraction, file signature validation, and optional OCR support.</td></tr>
  </table>
  <h3>4.2 Database Design</h3>
  <table>
    <tr><th>Table</th><th>Purpose</th><th>Main Fields</th></tr>
    <tr><td>users</td><td>Stores login accounts</td><td>id, username, password_hash, created_at</td></tr>
    <tr><td>reports</td><td>Stores resume scan outputs</td><td>filename, uploaded_at, score, matched_jobs, criteria, suggestions, analysis</td></tr>
    <tr><td>contacts</td><td>Stores support/contact messages</td><td>name, email, subject, message, user_id, created_at</td></tr>
  </table>

  <h2>5. Project Description</h2>
  <p>The application begins with a resume upload screen where the user selects a supported file and optionally enters a target role. After submission, the server checks the extension and file signature, temporarily saves the file, extracts text, removes the upload, and analyzes the resume. The result page displays the total score, criteria breakdown, detected skills, experience estimate, action verbs, analysis steps, bullet rewrite suggestions, and recommended roles.</p>
  <p>Logged-in users can open the history dashboard to view total scans, average score, best score, recent uploads, and saved report details. The administrator can access the admin dashboard using the admin account, view system counts, add catalog roles, and review contact messages.</p>

  <h2>6. System Testing and Implementation</h2>
  <h3>6.1 System Testing</h3>
  <p>The project includes pytest tests for file validation, target role matching, skill synonym extraction, experience estimation, scoring weights, CSRF behavior, resume analysis, mismatched file rejection, contact validation, login/history/PDF export, and admin catalog updates.</p>
  <table>
    <tr><th>Test Area</th><th>Expected Result</th></tr>
    <tr><td>Resume upload</td><td>TXT/PDF/DOCX files are accepted and invalid extensions are rejected.</td></tr>
    <tr><td>Analysis workflow</td><td>A valid resume creates a score, suggestions, matched jobs, and saved report.</td></tr>
    <tr><td>Authentication</td><td>Protected pages redirect unauthenticated users to login.</td></tr>
    <tr><td>Admin dashboard</td><td>Only the configured admin username can access the admin page.</td></tr>
    <tr><td>PDF export</td><td>Saved reports export as valid PDF responses.</td></tr>
  </table>
  <h3>6.2 System Implementation</h3>
  <p>The implementation is contained mainly in <code>app.py</code>, with templates stored in <code>templates/</code>, CSS and JavaScript stored in <code>static/</code>, and automated tests stored in <code>tests/</code>. Runtime data is stored in <code>tas_reports.db</code> and job catalog entries are stored in <code>job_data.csv</code>.</p>

  <h2>7. System Maintenance</h2>
  <p>Maintenance tasks include backing up the SQLite database, rotating production secret keys, reviewing dependency versions, monitoring uploaded file limits, updating role keywords, and periodically running the pytest suite. Since the system uses a local CSV job catalog, administrators can expand the recommendation catalog without changing application code.</p>

  <h2>8. Future Enhancements</h2>
  <ul>
    <li>Add richer NLP models for section detection and semantic role matching.</li>
    <li>Add administrator controls for editing and deleting existing catalog roles.</li>
    <li>Add analytics exports for placement coordinators.</li>
    <li>Add email notification support for contact messages.</li>
    <li>Add cloud deployment configuration and production database support.</li>
    <li>Add visual resume section coverage charts and downloadable improvement plans.</li>
  </ul>

  <h2>9. Conclusion</h2>
  <p>The Talent Acquisition System successfully provides a structured resume analysis platform with authentication, scoring, role matching, history tracking, administrator management, and PDF export. The project demonstrates practical use of Flask, SQLite, file parsing, scoring logic, and browser-based presentation to solve a real talent acquisition support problem.</p>

  <h2>10. Bibliography</h2>
  <ul>
    <li>Flask Documentation: https://flask.palletsprojects.com/</li>
    <li>Werkzeug Documentation: https://werkzeug.palletsprojects.com/</li>
    <li>Python Documentation: https://docs.python.org/</li>
    <li>Pandas Documentation: https://pandas.pydata.org/docs/</li>
    <li>SQLite Documentation: https://www.sqlite.org/docs.html</li>
  </ul>

  <h2 class="page-break">11. Appendix: Screenshots</h2>
  {screenshot_blocks}
</body>
</html>"""


def write_report(screenshots: list[tuple[str, str, Path]]) -> tuple[Path, Path | None]:
    html_path = OUT / "Talent_Acquisition_System_Project_Report.html"
    html_path.write_text(report_html(screenshots), encoding="utf-8")
    pdf_path = OUT / "Talent_Acquisition_System_Project_Report.pdf"
    if EDGE.exists():
        subprocess.run(
            edge_powershell([
                str(EDGE),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-dev-shm-usage",
                "--allow-file-access-from-files",
                "--user-data-dir=" + str(EDGE_PROFILE),
                "--print-to-pdf=" + str(pdf_path),
                html_path.as_uri(),
            ]),
            check=True,
            cwd=ROOT,
        )
        return html_path, pdf_path
    return html_path, None


def main() -> None:
    clean_output()
    configure_app()
    screenshots = render_app_screens()
    html_path, pdf_path = write_report(screenshots)
    print(html_path)
    if pdf_path:
        print(pdf_path)


if __name__ == "__main__":
    main()
