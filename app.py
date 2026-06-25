import json
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from urllib.parse import quote

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "jobs.json")
TARGET_CITY = "hyderabad"
TARGET_LOCATION_TEXT = "hyderabad, india"

DATA_SCIENCE_KEYWORDS = [
    "data scientist",
    "data science",
    "machine learning",
    "ml engineer",
    "ai engineer",
    "analytics engineer",
    "research scientist",
    "applied scientist",
    "data analyst",
    "business intelligence",
    "bi engineer",
]

ROLE_KEYWORDS = {
    "data-scientist": [
        "data scientist",
        "data science",
        "machine learning",
        "ml engineer",
        "ai engineer",
        "research scientist",
        "applied scientist",
    ],
    "data-analyst": [
        "data analyst",
        "analytics",
        "business intelligence",
        "bi analyst",
        "reporting analyst",
    ],
    "data-engineer": [
        "data engineer",
        "etl",
        "pipeline",
        "spark",
        "data platform",
        "warehouse",
        "dbt",
    ],
}

EXPERIENCE_KEYWORDS = [
    "entry level",
    "junior",
    "graduate",
    "intern",
    "0-1",
    "0-2",
    "0-3",
    "1 year",
    "2 years",
    "3 years",
    "1-2",
    "2-3",
    "1-3",
]

SENIOR_KEYWORDS = ["senior", "lead", "manager", "director", "principal", "staff", "architect"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}


def ensure_data_file() -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as handle:
            json.dump([], handle, indent=2)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def is_target_location(location: str, title: str = "", description: str = "") -> bool:
    text = normalize_text(f"{location} {title} {description}")
    if TARGET_CITY in text:
        return True
    if "telangana" in text and "india" in text:
        return True
    if "india" in text and TARGET_CITY in text:
        return True
    return False


def classify_role(title: str, description: str) -> str:
    text = f"{normalize_text(title)} {normalize_text(description)}"
    for role, keywords in ROLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return role
    return "data-scientist"


def is_data_science_role(title: str, description: str) -> bool:
    role = classify_role(title, description)
    return role in ROLE_KEYWORDS


def has_entry_or_mid_level_experience(title: str, description: str) -> bool:
    text = f"{normalize_text(title)} {normalize_text(description)}"
    if any(keyword in text for keyword in SENIOR_KEYWORDS):
        return False
    if any(keyword in text for keyword in EXPERIENCE_KEYWORDS):
        return True
    return True


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique_jobs: List[Dict[str, Any]] = []
    for job in jobs:
        key = job.get("url") or f"{job.get('company', '')}-{job.get('title', '')}"
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job)
    return unique_jobs


def make_job_payload(title: str, company: str, location: str, description: str, source: str, url: str) -> Dict[str, Any]:
    role = classify_role(title, description)
    return {
        "title": title.strip(),
        "company": company.strip() or "Unknown",
        "location": location.strip() or "Hyderabad, India",
        "description": re.sub(r"\s+", " ", description).strip()[:400],
        "experience": "0-3 years",
        "url": url,
        "source": source,
        "role": role,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_naukri_jobs() -> List[Dict[str, Any]]:
    try:
        url = "https://www.naukri.com/data-science-jobs-in-hyderabad?experience=0to3"
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        jobs: List[Dict[str, Any]] = []
        for anchor in soup.find_all("a", href=True):
            text = normalize_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "")
            if not text or len(text) < 8 or not href.startswith("http"):
                continue
            if not any(token in text for token in ["data scientist", "data science", "data analyst", "analytics", "machine learning", "ai", "ml", "data engineer", "etl", "pipeline", "spark", "warehouse", "dbt"]):
                continue
            title = text.title()
            jobs.append(make_job_payload(title, "Naukri", "Hyderabad, India", text, "Naukri", href))
            if len(jobs) >= 8:
                break
        return jobs
    except Exception as exc:
        print(f"Naukri error: {exc}")
        return []


def fetch_linkedin_jobs() -> List[Dict[str, Any]]:
    try:
        query = quote("data science jobs Hyderabad India")
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location=Hyderabad%2C%20Telangana%2C%20India&f_E=1%2C2%2C3"
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        jobs: List[Dict[str, Any]] = []
        for anchor in soup.find_all("a", href=True):
            text = normalize_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "")
            if not text or len(text) < 8 or not href.startswith("http"):
                continue
            if not any(token in text for token in ["data scientist", "data science", "machine learning", "analytics", "data analyst", "intern", "data engineer", "etl", "pipeline", "spark", "warehouse", "dbt"]):
                continue
            jobs.append(make_job_payload(text.title(), "LinkedIn", "Hyderabad, India", text, "LinkedIn", href))
            if len(jobs) >= 6:
                break
        return jobs
    except Exception as exc:
        print(f"LinkedIn error: {exc}")
        return []


def fetch_google_jobs() -> List[Dict[str, Any]]:
    try:
        query = quote("data science jobs hyderabad india")
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        jobs: List[Dict[str, Any]] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            text = normalize_text(anchor.get_text(" ", strip=True))
            if not href.startswith("http") or not href.startswith(("https://www.linkedin.com", "https://www.naukri.com", "https://in.indeed.com")):
                continue
            if not any(token in text for token in ["data scientist", "data science", "machine learning", "analyst", "analytics", "data engineer", "etl", "pipeline", "spark", "warehouse", "dbt"]):
                continue
            jobs.append(make_job_payload(text.title(), "Google Search", "Hyderabad, India", text, "Google", href))
            if len(jobs) >= 6:
                break
        return jobs
    except Exception as exc:
        print(f"Google error: {exc}")
        return []


def fetch_sample_jobs() -> List[Dict[str, Any]]:
    return [
        {
            "title": "Junior Data Scientist",
            "company": "Example Labs",
            "location": "Hyderabad, India",
            "description": "A beginner-friendly role focused on analytics and dashboarding in Hyderabad.",
            "experience": "0-1 years",
            "url": "https://example.com/jobs/1",
            "source": "Sample",
            "role": "data-scientist",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Data Science Intern",
            "company": "Growth AI",
            "location": "Hyderabad, India",
            "description": "Work on experimentation, forecasting, and reporting for an early-stage team.",
            "experience": "0-1 years",
            "url": "https://example.com/jobs/2",
            "source": "Sample",
            "role": "data-scientist",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Associate Data Analyst",
            "company": "InsightWorks",
            "location": "Hyderabad, India",
            "description": "Entry-level analytics role with SQL, Python, and dashboards.",
            "experience": "0-2 years",
            "url": "https://example.com/jobs/3",
            "source": "Sample",
            "role": "data-analyst",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Junior Data Engineer",
            "company": "DataForge",
            "location": "Hyderabad, India",
            "description": "Entry-level role building ETL pipelines and data warehouses with Spark.",
            "experience": "0-2 years",
            "url": "https://example.com/jobs/4",
            "source": "Sample",
            "role": "data-engineer",
            "posted_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def collect_jobs() -> List[Dict[str, Any]]:
    ensure_data_file()
    jobs: List[Dict[str, Any]] = []
    jobs.extend(fetch_naukri_jobs())
    jobs.extend(fetch_linkedin_jobs())
    jobs.extend(fetch_google_jobs())
    jobs.extend(fetch_sample_jobs())

    jobs = [
        job
        for job in jobs
        if is_target_location(job.get("location", ""), job.get("title", ""), job.get("description", ""))
        and is_data_science_role(job.get("title", ""), job.get("description", ""))
        and has_entry_or_mid_level_experience(job.get("title", ""), job.get("description", ""))
    ]
    for job in jobs:
        job.setdefault("role", classify_role(job.get("title", ""), job.get("description", "")))
    jobs = deduplicate_jobs(jobs)
    jobs.sort(key=lambda item: item.get("posted_at", ""), reverse=True)
    with open(DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(jobs, handle, indent=2)
    return jobs


@app.route("/")
def index():
    role = request.args.get("role", "all")
    with open(DATA_FILE, "r", encoding="utf-8") as handle:
        jobs = json.load(handle)
    if role != "all":
        jobs = [job for job in jobs if job.get("role") == role]
    return render_template("index.html", jobs=jobs, selected_role=role)


@app.route("/api/jobs")
def api_jobs():
    role = request.args.get("role", "all")
    with open(DATA_FILE, "r", encoding="utf-8") as handle:
        jobs = json.load(handle)
    if role != "all":
        jobs = [job for job in jobs if job.get("role") == role]
    return jsonify({"count": len(jobs), "jobs": jobs, "generated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/refresh")
def refresh_jobs_endpoint():
    jobs = collect_jobs()
    return jsonify({"count": len(jobs), "status": "refreshed"})


ensure_data_file()

scheduler = None
if __name__ == "__main__":
    collect_jobs()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(collect_jobs, "cron", hour=2, minute=0, timezone="Asia/Kolkata")
    scheduler.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
