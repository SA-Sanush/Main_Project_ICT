from io import BytesIO
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

import pytest

import app as app_module


@pytest.fixture()
def client(monkeypatch):
    runtime_dir = Path("test_runtime") / uuid4().hex
    upload_dir = runtime_dir / "uploads"
    chart_dir = runtime_dir / "charts"
    upload_dir.mkdir(parents=True)
    chart_dir.mkdir(parents=True)

    monkeypatch.setattr(app_module, "DB_PATH", runtime_dir / "reports.db")
    monkeypatch.setattr(app_module, "JOB_DATA_PATH", runtime_dir / "job_data.csv")
    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", upload_dir)
    monkeypatch.setattr(app_module, "CHART_FOLDER", chart_dir)
    app_module.RATE_LIMITS.clear()

    app_module.app.config.update(TESTING=True, CSRF_ENABLED=False, ADMIN_USERNAME="admin")
    app_module.init_db()
    app_module.load_job_data()

    with app_module.app.test_client() as test_client:
        yield test_client


def test_allowed_file_validation():
    assert app_module.allowed_file("resume.pdf")
    assert app_module.allowed_file("resume.docx")
    assert app_module.allowed_file("resume.txt")
    assert not app_module.allowed_file("resume.exe")
    assert not app_module.allowed_file("resume")


def test_target_job_match_finds_missing_keywords():
    match = app_module.build_target_job_match(
        "Built Python dashboards with SQL and stakeholder reporting.",
        "Data Analyst",
        "Python SQL Tableau experimentation statistics stakeholder communication",
    )

    assert match is not None
    assert match["title"] == "Data Analyst"
    assert match["match_score"] > 0
    assert "python" in match["matched_keywords"]
    assert "tableau" in match["missing_keywords"]


def test_target_job_match_expands_title_only_full_stack_role():
    match = app_module.build_target_job_match(
        "Built React interfaces, Flask APIs, SQL models, Git workflows, and pytest tests.",
        "full stack developer",
        "",
    )

    assert match is not None
    assert match["match_score"] > 0
    assert {"javascript", "flask", "sql", "git", "testing"} & set(match["matched_keywords"])
    assert "developer" not in match["missing_keywords"]
    assert "stack" not in match["missing_keywords"]
    assert "machine learning" not in match["missing_keywords"]


def test_skill_extraction_understands_common_aliases():
    profile = app_module.extract_resume_profile(
        "Developed ML pipelines with REST APIs, Git workflows, and responsive design."
    )

    assert "machine learning" in profile["skills"]
    assert "api development" in profile["skills"]
    assert "git" in profile["skills"]
    assert "css" in profile["skills"]


def test_experience_estimate_ignores_education_only_years():
    profile = app_module.extract_resume_profile(
        "Education: ABC University, Bachelor of Computer Applications, 2018 - 2022. "
        "Projects: Built Python dashboards and SQL reports."
    )

    assert profile["experience_years"] == 0


def test_experience_estimate_uses_explicit_and_work_ranges():
    explicit_profile = app_module.extract_resume_profile(
        "Data Analyst with 3 years of experience building SQL dashboards."
    )
    range_profile = app_module.extract_resume_profile(
        "Work Experience: Junior Developer, 2020 - 2022. Software Engineer, 2022 - 2024."
    )

    assert explicit_profile["experience_years"] == 3
    assert range_profile["experience_years"] == 4


def test_role_adjusted_score_changes_weighting():
    criteria = {
        "Contact Information": 10,
        "Professional Summary": 4,
        "Work Experience": 5,
        "Education": 5,
        "Skills": 10,
        "TAS Optimization": 6,
        "Consistency": 6,
        "Proofreading": 8,
        "File Format": 10,
        "Relevance": 9,
    }

    default_score = app_module.calculate_weighted_score(criteria)
    analyst_score = app_module.calculate_role_adjusted_score(criteria, "Data Analyst")

    assert analyst_score != default_score
    assert app_module.scoring_weights_for_role("Data Analyst")["Skills"] > app_module.SCORING_WEIGHTS["Skills"]


def test_csrf_blocks_post_when_enabled(client):
    app_module.app.config["CSRF_ENABLED"] = True
    response = client.post("/contact", data={"name": "Alex", "email": "a@example.com", "message": "Hi"})
    app_module.app.config["CSRF_ENABLED"] = False

    assert response.status_code == 400


def test_analyze_txt_resume_saves_report_and_deletes_temp_upload(client):
    data = {
        "job_title": "Data Analyst",
        "job_description": "SQL dashboards analytics stakeholder reporting",
        "resume_file": (
            BytesIO(b"Alex Analyst\nalex@example.com\nPython SQL pandas dashboards analytics communication"),
            "resume.txt",
        ),
    }

    response = client.post("/analyze", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"Total Score" in response.data
    assert b"Detected explicit skills" in response.data
    assert b"Analysis Steps" in response.data
    assert b"Suggested Bullet Rewrites" in response.data
    assert not any(app_module.UPLOAD_FOLDER.rglob("*.txt"))


def test_pdf_ocr_fallback_extracts_scanned_text(monkeypatch):
    runtime_dir = Path("test_runtime") / uuid4().hex
    runtime_dir.mkdir(parents=True)
    pdf_path = runtime_dir / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 scanned placeholder")
    fake_tesseract = SimpleNamespace(image_to_string=lambda image: "Alex OCR\nPython SQL")

    monkeypatch.setattr(app_module, "extract_text_from_pdf", lambda path: "")
    monkeypatch.setattr(app_module, "convert_from_path", lambda *args, **kwargs: ["page-image"])
    monkeypatch.setattr(app_module, "pytesseract", fake_tesseract)
    monkeypatch.setattr(app_module, "tesseract_is_available", lambda: True)
    monkeypatch.setattr(app_module, "poppler_is_available", lambda: True)

    assert app_module.extract_resume_text(pdf_path, "pdf") == "Alex OCR\nPython SQL"
    assert app_module.LAST_OCR_ERROR == ""


def test_pdf_ocr_failure_explains_missing_poppler(monkeypatch):
    runtime_dir = Path("test_runtime") / uuid4().hex
    runtime_dir.mkdir(parents=True)
    pdf_path = runtime_dir / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 scanned placeholder")
    fake_tesseract = SimpleNamespace(image_to_string=lambda image: "")

    monkeypatch.setattr(app_module, "extract_text_from_pdf", lambda path: "")
    monkeypatch.setattr(app_module, "convert_from_path", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("poppler missing")))
    monkeypatch.setattr(app_module, "pytesseract", fake_tesseract)
    monkeypatch.setattr(app_module, "tesseract_is_available", lambda: True)
    monkeypatch.setattr(app_module, "poppler_is_available", lambda: True)

    assert app_module.extract_resume_text(pdf_path, "pdf") == ""
    assert "Poppler" in app_module.unreadable_resume_message("pdf")


def test_pdf_ocr_preflight_reports_missing_native_tools(monkeypatch):
    monkeypatch.setattr(app_module, "pytesseract", SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="tesseract")))
    monkeypatch.setattr(app_module, "convert_from_path", lambda *args, **kwargs: [])
    monkeypatch.setattr(app_module.shutil, "which", lambda command: None)
    monkeypatch.setattr(app_module, "COMMON_TESSERACT_PATHS", [])

    assert "Tesseract OCR" in app_module.ocr_unavailable_message()


def test_pdf_ocr_preflight_names_missing_python_packages(monkeypatch):
    monkeypatch.setattr(app_module, "pytesseract", None)
    monkeypatch.setattr(app_module, "convert_from_path", None)

    message = app_module.ocr_unavailable_message()

    assert "pytesseract" in message
    assert "pdf2image" in message


def test_rewrite_resume_bullets_generates_local_fix():
    rewrites = app_module.rewrite_resume_bullets(
        "- Helped with reports for business team",
        "Data Analyst",
    )

    assert rewrites
    assert rewrites[0]["before"] == "Helped with reports for business team"
    assert "measurable outcomes" in rewrites[0]["after"]


def test_rejects_file_with_mismatched_extension(client):
    response = client.post(
        "/analyze",
        data={
            "resume_file": (BytesIO(b"not a pdf file"), "resume.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"does not match its extension" in response.data


def test_contact_rejects_invalid_email(client):
    response = client.post(
        "/contact",
        data={"name": "Alex", "email": "not-an-email", "message": "Hi"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"valid email address" in response.data


def test_register_login_history_and_pdf_export(client):
    client.post(
        "/register",
        data={"username": "alex", "password": "Password123!", "confirm_password": "Password123!"},
    )
    client.post("/login", data={"username": "alex", "password": "Password123!"})
    client.post(
        "/analyze",
        data={
            "job_title": "Software Engineer",
            "job_description": "Python Flask SQL testing",
            "resume_file": (BytesIO(b"alex@example.com\nBuilt Python Flask APIs with SQL tests."), "resume.txt"),
        },
        content_type="multipart/form-data",
    )

    history = client.get("/history")
    assert history.status_code == 200
    assert b"resume.txt" in history.data

    conn = app_module.sqlite3.connect(app_module.DB_PATH)
    report_id = conn.execute("SELECT id FROM reports ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()
    export = client.get(f"/history/{report_id}/export.pdf")
    detail = client.get(f"/history/{report_id}")

    assert b"Detected explicit skills" in detail.data
    assert b"Analysis Steps" in detail.data
    assert export.status_code == 200
    assert export.data.startswith(b"%PDF")
    assert export.headers["Content-Type"] == "application/pdf"


def test_admin_can_add_catalog_role(client):
    client.post(
        "/register",
        data={"username": "admin", "password": "Password123!", "confirm_password": "Password123!"},
    )
    client.post("/login", data={"username": "admin", "password": "Password123!"})
    response = client.post(
        "/admin",
        data={
            "title": "UX Designer",
            "keywords": "figma, research, prototyping",
            "description": "Design usable product workflows.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"UX Designer" in response.data
