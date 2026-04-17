import os
import re
import csv
import json
import sqlite3
import traceback
from ast import literal_eval
from datetime import datetime
from functools import wraps
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
CHART_FOLDER = BASE_DIR / "static" / "images"
JOB_DATA_PATH = BASE_DIR / "job_data.csv"
DB_PATH = BASE_DIR / "ats_reports.db"
ALLOWED_EXTENSIONS = {"pdf", "txt"}

app = Flask(__name__)
app.secret_key = "ats_secret_key_2026"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["CHART_FOLDER"] = str(CHART_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

UPLOAD_FOLDER.mkdir(exist_ok=True)
CHART_FOLDER.mkdir(parents=True, exist_ok=True)

CONTACT_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\+?\d[\d\s().-]{6,}\d")
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

COMMON_TYPO = ["teh", "recieve", "acheive", "managment", "objecive", "formaing", "resposible", "seperated"]

JOB_KEYWORDS = [
    "communication", "problem solving", "technical", "leadership", "python", "sql", "flask",
    "data analysis", "teamwork", "project", "documentation", "presentation", "analytics",
    "stakeholders", "roadmap", "testing", "bug", "portfolio", "linkedin"
]

DEFAULT_JOBS = [
    {
        "title": "Data Analyst",
        "keywords": "python, sql, pandas, data visualization, problem solving, communication, reporting",
        "description": "Analyze datasets, create dashboards, and deliver insights to business stakeholders."
    },
    {
        "title": "Software Engineer",
        "keywords": "python, javascript, flask, sql, git, testing, agile, code review",
        "description": "Design and implement applications, maintain code quality, and collaborate on engineering teams."
    },
    {
        "title": "Product Manager",
        "keywords": "communication, roadmap, stakeholders, analytics, strategy, prioritization",
        "description": "Define product direction, coordinate teams, and shape customer-focused roadmaps."
    },
    {
        "title": "Technical Writer",
        "keywords": "documentation, editing, communication, clarity, process, technical writing",
        "description": "Produce clear technical guides, manuals, and user-facing content for engineering teams."
    },
    {
        "title": "Digital Marketing Specialist",
        "keywords": "seo, content, analytics, copywriting, branding, social media, campaign",
        "description": "Create campaigns, analyze performance, and develop customer-facing digital content."
    }
]


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reports ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "user_id INTEGER,"
            "filename TEXT,"
            "uploaded_at TEXT,"
            "score INTEGER,"
            "matched_jobs TEXT,"
            "criteria TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS contacts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT,"
            "email TEXT,"
            "subject TEXT,"
            "message TEXT,"
            "created_at TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "username TEXT UNIQUE,"
            "password_hash TEXT"
            ")"
        )
        conn.commit()
        create_default_user(conn)
        ensure_reports_user_scope(conn)
        assign_legacy_reports_to_default_user(conn)
    finally:
        conn.close()


def create_default_user(conn: sqlite3.Connection) -> None:
    cursor = conn.execute("SELECT 1 FROM users LIMIT 1")
    if cursor.fetchone() is None:
        password_hash = generate_password_hash("Password123!")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash),
        )
        conn.commit()


def get_primary_history_user_row(conn: sqlite3.Connection) -> tuple[int, str] | None:
    row = conn.execute(
        "SELECT id, username FROM users WHERE username <> ? ORDER BY id ASC LIMIT 1",
        ("admin",),
    ).fetchone()
    if row:
        return row
    return conn.execute(
        "SELECT id, username FROM users WHERE username = ? LIMIT 1",
        ("admin",),
    ).fetchone()


def parse_report_payload(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        try:
            return literal_eval(value)
        except (ValueError, SyntaxError):
            return fallback


def summarize_matched_jobs(matched_jobs_value: str | None) -> str:
    parsed = parse_report_payload(matched_jobs_value, [])
    if isinstance(parsed, list):
        titles = []
        for item in parsed:
            if isinstance(item, dict):
                title = item.get("title")
                if title:
                    titles.append(title)
            elif isinstance(item, str) and item.strip():
                titles.append(item.strip())
        return ", ".join(titles) if titles else "None"
    if isinstance(parsed, str):
        return parsed
    return "None"


def get_accessible_user_ids(conn: sqlite3.Connection, current_user_id: int) -> list[int]:
    accessible_user_ids = [current_user_id]
    primary_row = get_primary_history_user_row(conn)
    admin_row = conn.execute(
        "SELECT id FROM users WHERE username = ? LIMIT 1",
        ("admin",),
    ).fetchone()
    if primary_row and current_user_id == primary_row[0] and admin_row and admin_row[0] != current_user_id:
        accessible_user_ids.append(admin_row[0])
    return accessible_user_ids


def load_job_data() -> pd.DataFrame:
    if not JOB_DATA_PATH.exists():
        with open(JOB_DATA_PATH, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["title", "keywords", "description"])
            writer.writeheader()
            for row in DEFAULT_JOBS:
                writer.writerow(row)
    return pd.read_csv(JOB_DATA_PATH)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except Exception:
        return ""
    return "\n".join(text_parts)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def detect_contact_info(text: str) -> int:
    score = 0
    if CONTACT_PATTERN.search(text):
        score += 5
    if "linkedin.com" in text or "portfolio" in text or "github.com" in text:
        score += 5
    return min(score, 10)


def detect_summary(text: str) -> int:
    markers = ["summary", "objective", "experience", "achievements", "years of experience", "result-oriented"]
    hits = sum(1 for marker in markers if marker in text)
    return min(10, max(0, hits * 2))


def detect_experience(text: str) -> int:
    bullets = text.count("- ") + text.count("•") + text.count("* ")
    role_keywords = len(re.findall(r"\b(?:managed|led|developed|implemented|engineered|designed|built|achieved|improved|created)\b", text))
    if bullets >= 4 and role_keywords >= 3:
        return 10
    if bullets >= 2 and role_keywords >= 2:
        return 8
    if bullets >= 1 and role_keywords >= 1:
        return 6
    return 3 if "experience" in text else 0


def detect_education(text: str) -> int:
    degree_words = ["bachelor", "master", "phd", "university", "college", "degree", "graduat"]
    hits = sum(1 for word in degree_words if word in text)
    year_matches = len(YEAR_PATTERN.findall(text))
    score = min(10, hits * 2 + min(year_matches, 2) * 2)
    if "gpa" in text and ("3.5" in text or "3.6" in text or "3.7" in text or "3.8" in text or "4.0" in text):
        score += 2
    return min(score, 10)


def detect_skills(text: str) -> int:
    tech_skills = ["python", "sql", "excel", "flask", "pandas", "matplotlib", "javascript", "html", "css"]
    soft_skills = ["communication", "teamwork", "problem solving", "leadership", "adaptability", "collaboration", "organization"]
    found = sum(1 for skill in tech_skills + soft_skills if skill in text)
    return min(10, found * 2)


def detect_ats_optimization(text: str) -> int:
    hits = sum(1 for keyword in JOB_KEYWORDS if keyword in text)
    return min(10, hits * 2)


def detect_consistency(text: str) -> int:
    date_formats = re.findall(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b", text)
    bullets = text.count("- ") + text.count("•") + text.count("* ")
    pattern = 10 if bullets >= 3 and len(date_formats) >= 2 else 6 if bullets >= 2 else 4
    return pattern


def detect_proofreading(text: str) -> int:
    typo_count = sum(text.count(mistake) for mistake in COMMON_TYPO)
    punctuation_issues = len(re.findall(r"\s{2,}", text))
    score = 10 - min(6, typo_count + punctuation_issues)
    return max(0, score)


def detect_relevance(text: str) -> int:
    if "high school" in text and any(word in text for word in ["bachelor", "master", "university", "college"]):
        return 6
    if "high school" in text and "degree" not in text:
        return 4
    return 10


def build_criteria_scores(text: str, extension: str) -> dict:
    criteria_scores = {
        "Contact Information": detect_contact_info(text),
        "Professional Summary": detect_summary(text),
        "Work Experience": detect_experience(text),
        "Education": detect_education(text),
        "Skills": detect_skills(text),
        "ATS Optimization": detect_ats_optimization(text),
        "Consistency": detect_consistency(text),
        "Proofreading": detect_proofreading(text),
        "File Format": 10 if extension.lower() == "pdf" else 0,
        "Relevance": detect_relevance(text),
    }
    return criteria_scores


def generate_chart(criteria_scores: dict, output_path: Path) -> None:
    categories = list(criteria_scores.keys())
    values = np.array(list(criteria_scores.values()))
    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    bars = ax.barh(categories, values, color=["#4C84FF" if v >= 7 else "#FCA311" for v in values])
    ax.set_xlim(0, 10)
    ax.set_xlabel("Score per Criterion")
    ax.set_title("Resume ATS Criteria Match Breakdown")
    ax.invert_yaxis()
    for bar, value in zip(bars, values):
        ax.text(value + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(value)}/10", va="center", fontsize=9)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def find_applicable_jobs(text: str) -> list:
    jobs_df = load_job_data()
    text_lower = text.lower()
    recommendations = []
    for _, row in jobs_df.iterrows():
        keywords = [kw.strip() for kw in str(row["keywords"]).split(",") if kw.strip()]
        matches = sum(1 for kw in keywords if kw in text_lower)
        ratio = matches / max(len(keywords), 1)
        if ratio >= 0.3:
            recommendations.append({
                "title": row["title"],
                "description": row.get("description", ""),
                "match_score": int(ratio * 100),
                "matched_keywords": [kw for kw in keywords if kw in text_lower]
            })
    recommendations.sort(key=lambda item: item["match_score"], reverse=True)
    return recommendations[:5]


def save_report(user_id: int | None, filename: str, score: int, matched_jobs: list, criteria_scores: dict) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO reports (user_id, filename, uploaded_at, score, matched_jobs, criteria) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                filename,
                datetime.utcnow().isoformat(),
                score,
                json.dumps(matched_jobs),
                json.dumps(criteria_scores),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_contact_submission(name: str, email: str, subject: str, message: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO contacts (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, subject, message, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_user(username: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password_hash": row[2]}
        return None
    finally:
        conn.close()


def get_current_user() -> dict | None:
    username = session.get("user")
    if not username:
        return None
    return get_user(username)


def create_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def ensure_reports_user_scope(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(reports)").fetchall()]
    if "user_id" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER")
        conn.commit()


def assign_legacy_reports_to_default_user(conn: sqlite3.Connection) -> None:
    primary_row = get_primary_history_user_row(conn)
    if primary_row:
        conn.execute(
            "UPDATE reports SET user_id = ? WHERE user_id IS NULL",
            (primary_row[0],),
        )
        conn.commit()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("user") is None:
            flash("Please log in to access that page.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        flash("You are already logged in.", "success")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = user["username"]
            flash(f"Welcome back, {user['username']}.", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"):
        flash("You are already logged in.", "success")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return redirect(url_for("register"))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            flash("Username can only contain letters, numbers, dots, underscores, and hyphens.", "error")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return redirect(url_for("register"))
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if get_user(username):
            flash("That username is already registered. Please choose another one.", "error")
            return redirect(url_for("register"))

        if create_user(username, password):
            flash("Account created successfully. Please log in with your new credentials.", "success")
            return redirect(url_for("login"))

        flash("We could not create your account right now. Please try again.", "error")
        return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please fill in your name, email, and message.", "error")
            return redirect(url_for("contact"))
        save_contact_submission(name, email, subject, message)
        flash("Your message has been sent. You will be contacted shortly.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        resume_file = request.files.get("resume_file")
        if not resume_file or resume_file.filename == "":
            flash("Please upload a resume file in PDF or TXT format.", "error")
            return redirect(request.url)

        filename = secure_filename(resume_file.filename)
        if not allowed_file(filename):
            flash("Only PDF and TXT resume uploads are supported.", "error")
            return redirect(request.url)

        try:
            file_ext = filename.rsplit(".", 1)[1].lower()
            save_path = UPLOAD_FOLDER / filename
            resume_file.save(save_path)
            extracted_text = ""
            if file_ext == "pdf":
                extracted_text = extract_text_from_pdf(save_path)
            else:
                extracted_text = save_path.read_text(encoding="utf-8", errors="ignore")

            if not extracted_text.strip():
                flash("Unable to parse text from the uploaded resume. Please verify the file contents.", "error")
                return redirect(request.url)

            text = normalize_text(extracted_text)
            criteria_scores = build_criteria_scores(text, file_ext)
            total_score = int(np.clip(sum(criteria_scores.values()) * 1, 0, 100))
            chart_path = CHART_FOLDER / "score_chart.png"
            generate_chart(criteria_scores, chart_path)
            matched_jobs = find_applicable_jobs(text)
            current_user = get_current_user()
            save_report(
                current_user["id"] if current_user else None,
                filename,
                total_score,
                matched_jobs,
                criteria_scores,
            )

            return render_template(
                "result.html",
                filename=filename,
                score=total_score,
                criteria_scores=criteria_scores,
                chart_url=url_for("static", filename="images/score_chart.png"),
                matched_jobs=matched_jobs,
            )
        except Exception as e:
            traceback.print_exc()
            flash(f"An unexpected error occurred while processing the resume: {e}", "error")
            return redirect(request.url)

    return render_template("index.html")


@app.route("/history")
@login_required
def history():
    current_user = get_current_user()
    conn = sqlite3.connect(DB_PATH)
    try:
        accessible_user_ids = get_accessible_user_ids(conn, current_user["id"])
        placeholders = ", ".join(["?"] * len(accessible_user_ids))
        raw_rows = conn.execute(
            f"SELECT id, filename, uploaded_at, score, matched_jobs "
            f"FROM reports WHERE user_id IN ({placeholders}) ORDER BY uploaded_at DESC LIMIT 20",
            tuple(accessible_user_ids),
        ).fetchall()
    finally:
        conn.close()
    rows = [
        {
            "id": row[0],
            "filename": row[1],
            "uploaded_at": row[2],
            "score": row[3],
            "matched_jobs_summary": summarize_matched_jobs(row[4]),
        }
        for row in raw_rows
    ]
    return render_template("history.html", rows=rows)


@app.route("/history/<int:report_id>")
@login_required
def history_detail(report_id: int):
    current_user = get_current_user()
    conn = sqlite3.connect(DB_PATH)
    try:
        accessible_user_ids = get_accessible_user_ids(conn, current_user["id"])
        placeholders = ", ".join(["?"] * len(accessible_user_ids))
        row = conn.execute(
            f"SELECT id, filename, uploaded_at, score, matched_jobs, criteria "
            f"FROM reports WHERE id = ? AND user_id IN ({placeholders})",
            (report_id, *accessible_user_ids),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        flash("That history entry is not available for this account.", "error")
        return redirect(url_for("history"))

    matched_jobs = parse_report_payload(row[4], [])
    criteria_scores = parse_report_payload(row[5], {})
    if isinstance(matched_jobs, str):
        matched_jobs = [{"title": title.strip()} for title in matched_jobs.split(",") if title.strip()]
    if not isinstance(matched_jobs, list):
        matched_jobs = []
    if not isinstance(criteria_scores, dict):
        criteria_scores = {}

    return render_template(
        "history_detail.html",
        report={
            "id": row[0],
            "filename": row[1],
            "uploaded_at": row[2],
            "score": row[3],
        },
        matched_jobs=matched_jobs,
        criteria_scores=criteria_scores,
    )


if __name__ == "__main__":
    init_db()
    load_job_data()
    app.run(debug=True, host="0.0.0.0", port=5000)
