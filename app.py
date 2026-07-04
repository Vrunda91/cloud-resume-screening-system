"""
app.py
-------------------------------------------------------
Cloud-Based AI Resume Screening System
Main Flask application: routes for job creation, resume upload,
AI-based scoring, and a ranked candidate dashboard.

Cloud deployment note (see project report, Chapter 4):
This Flask app is designed to be deployed on AWS Elastic Beanstalk
/ Azure App Service. `UPLOAD_FOLDER` below stands in for AWS S3
bucket storage, and `database.py` stands in for AWS RDS. Swapping
either requires changing only that one module.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash

import database
from utils.resume_parser import extract_text, guess_candidate_name
from utils.matcher import evaluate_resume

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.secret_key = "mca-project-secret-key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB per resume

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
database.init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    jobs = database.get_all_jobs()
    return render_template("index.html", jobs=jobs)


@app.route("/job/new", methods=["POST"])
def create_job():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    skills_raw = request.form.get("required_skills", "").strip()
    required_skills = [s.strip().lower() for s in skills_raw.split(",") if s.strip()]

    if not title or not description or not required_skills:
        flash("Please fill in job title, description, and at least one required skill.")
        return redirect(url_for("home"))

    job_id = database.add_job(title, description, required_skills)
    flash(f'Job "{title}" created successfully.')
    return redirect(url_for("dashboard", job_id=job_id))


@app.route("/job/<int:job_id>/upload", methods=["POST"])
def upload_resume(job_id):
    job = database.get_job(job_id)
    if not job:
        flash("Job not found.")
        return redirect(url_for("home"))

    files = request.files.getlist("resumes")
    if not files or files[0].filename == "":
        flash("Please select at least one resume file.")
        return redirect(url_for("dashboard", job_id=job_id))

    required_skills = job["required_skills"].split(",")

    for file in files:
        if file and allowed_file(file.filename):
            filename = file.filename
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_{filename}")
            file.save(save_path)

            try:
                text = extract_text(save_path)
            except Exception as e:
                flash(f"Could not read {filename}: {e}")
                continue

            candidate_name = guess_candidate_name(text, filename)
            result = evaluate_resume(text, job["description"], required_skills)

            database.add_candidate(
                job_id=job_id,
                candidate_name=candidate_name,
                filename=filename,
                storage_path=save_path,
                extracted_text=text[:5000],  # cap stored text
                matched_skills=result["matched_skills"],
                missing_skills=result["missing_skills"],
                match_score=result["final_score"],
            )
        else:
            flash(f"Skipped unsupported file: {file.filename}")

    return redirect(url_for("dashboard", job_id=job_id))


@app.route("/job/<int:job_id>/dashboard")
def dashboard(job_id):
    job = database.get_job(job_id)
    if not job:
        flash("Job not found.")
        return redirect(url_for("home"))

    candidates = database.get_ranked_candidates(job_id)
    for c in candidates:
        c["matched_skills"] = c["matched_skills"].split(",") if c["matched_skills"] else []
        c["missing_skills"] = c["missing_skills"].split(",") if c["missing_skills"] else []

    return render_template("dashboard.html", job=job, candidates=candidates)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
