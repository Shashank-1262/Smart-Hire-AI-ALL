"""
All 10 new feature routes for SmartHire AI.
Imported into app.py via: from routes_new import register_routes; register_routes(app)
"""
import os, io, csv, json, secrets as _secrets
from flask import request, session, jsonify, redirect, url_for, render_template, send_file
from werkzeug.utils import secure_filename
from datetime import datetime

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")

# ─── helpers ──────────────────────────────────────────────────────────────────
def _db():
    import sqlite3
    DB = os.path.join(os.path.dirname(__file__), "smarthire.db")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def _extract_skills(text):
    known = ["Python","Java","JavaScript","C++","C","React","Node.js","Django","Flask",
             "SQL","MongoDB","PostgreSQL","MySQL","Machine Learning","Deep Learning",
             "TensorFlow","PyTorch","NLP","Data Science","AWS","Docker","Kubernetes",
             "Git","HTML","CSS","TypeScript","REST API","Pandas","NumPy","Scikit-learn",
             "R","Android","iOS","Swift","Kotlin","Spring Boot","FastAPI","Figma",
             "Power BI","Tableau","Excel","Linux","Redis","GraphQL"]
    return [k for k in known if k.lower() in text.lower()]

def _parse_resume(filepath):
    text = ""
    try:
        ext = filepath.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            from pdfminer.high_level import extract_text
            text = extract_text(filepath) or ""
        elif ext in ("doc","docx"):
            try:
                import docx as _docx
                d = _docx.Document(filepath)
                text = "\n".join(p.text for p in d.paragraphs)
            except Exception:
                pass
    except Exception:
        pass
    import re
    exp_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', text, re.IGNORECASE)
    exp_years = max((int(m) for m in exp_matches), default=0)
    emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w+', text)
    skills = _extract_skills(text)
    return {
        "skills": ", ".join(skills),
        "exp_years": exp_years,
        "email": emails[0] if emails else "",
        "snippet": text[:400].replace("\n"," ").strip(),
    }

def register_routes(app):

    # =========================================================================
    # FEATURE 1 — Resume Parsing
    # =========================================================================
    @app.route("/student/resume/parse", methods=["POST"])
    def parse_resume():
        if session.get("role") != "student":
            return jsonify({"error":"unauthorized"}), 403
        db = _db()
        row = db.execute("SELECT resume FROM students WHERE id=?", (session["uid"],)).fetchone()
        db.close()
        if not row or not row["resume"]:
            return jsonify({"error":"No resume uploaded yet"})
        filepath = os.path.join(UPLOAD_FOLDER, row["resume"])
        if not os.path.exists(filepath):
            return jsonify({"error":"File not found"})
        result = _parse_resume(filepath)
        # Auto-save skills back to profile if user confirms (flag=1)
        if request.form.get("save") == "1" and result["skills"]:
            db2 = _db()
            db2.execute("UPDATE students SET skills=? WHERE id=?",
                        (result["skills"], session["uid"]))
            db2.commit(); db2.close()
        return jsonify(result)

    # =========================================================================
    # FEATURE 2 — Skill Assessment Module
    # =========================================================================
    @app.route("/assessment/<int:drive_id>")
    def assessment_page(drive_id):
        if session.get("role") != "student":
            return redirect(url_for("login"))
        db = _db()
        assessment = db.execute(
            "SELECT * FROM assessments WHERE drive_id=?", (drive_id,)).fetchone()
        if not assessment:
            db.close()
            return redirect(url_for("student_dash"))
        # Check if already taken
        app_row = db.execute(
            "SELECT id FROM applications WHERE student_id=? AND drive_id=?",
            (session["uid"], drive_id)).fetchone()
        already = db.execute(
            "SELECT * FROM assessment_results WHERE assessment_id=? AND student_id=?",
            (assessment["id"], session["uid"])).fetchone()
        drive = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
        db.close()
        questions = json.loads(assessment["questions"] or "[]")
        return render_template("assessment.html",
            assessment=assessment, questions=questions,
            drive=drive, already=already)

    @app.route("/assessment/<int:drive_id>/submit", methods=["POST"])
    def submit_assessment(drive_id):
        if session.get("role") != "student":
            return redirect(url_for("login"))
        db = _db()
        assessment = db.execute(
            "SELECT * FROM assessments WHERE drive_id=?", (drive_id,)).fetchone()
        if not assessment:
            db.close(); return redirect(url_for("student_dash"))
        questions = json.loads(assessment["questions"] or "[]")
        answers = {}
        correct = 0
        for i, q in enumerate(questions):
            ans = request.form.get(f"q{i}", "")
            answers[str(i)] = ans
            if ans == q.get("answer", ""):
                correct += 1
        score = round((correct / len(questions) * 100), 1) if questions else 0
        app_row = db.execute(
            "SELECT id FROM applications WHERE student_id=? AND drive_id=?",
            (session["uid"], drive_id)).fetchone()
        app_id = app_row["id"] if app_row else None
        try:
            db.execute("""INSERT INTO assessment_results
                (assessment_id,student_id,application_id,score,answers)
                VALUES (?,?,?,?,?)""",
                (assessment["id"], session["uid"], app_id,
                 score, json.dumps(answers)))
            db.commit()
        except Exception:
            pass
        # Auto-shortlist if passes
        if score >= assessment["passing_score"] and app_id:
            db.execute("UPDATE applications SET status='eligible' WHERE id=?", (app_id,))
            db.commit()
        db.close()
        return redirect(url_for("student_dash") + f"?section=applications&assess_score={score}")

    @app.route("/assessment/create", methods=["GET","POST"])
    def create_assessment():
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        if request.method == "POST":
            f = request.form
            questions_raw = []
            i = 0
            while f.get(f"q_text_{i}"):
                questions_raw.append({
                    "text":    f.get(f"q_text_{i}",""),
                    "options": [f.get(f"q_opt_{i}_0",""), f.get(f"q_opt_{i}_1",""),
                                f.get(f"q_opt_{i}_2",""), f.get(f"q_opt_{i}_3","")],
                    "answer":  f.get(f"q_ans_{i}",""),
                })
                i += 1
            db = _db()
            db.execute("""INSERT INTO assessments (drive_id,title,questions,time_limit,passing_score)
                VALUES (?,?,?,?,?)""",
                (int(f["drive_id"]), f["title"],
                 json.dumps(questions_raw),
                 int(f.get("time_limit",30)),
                 int(f.get("passing_score",60))))
            db.commit(); db.close()
            return redirect(url_for("company_dash") + "?section=drives")
        db = _db()
        if session.get("role") == "company":
            drives = db.execute(
                "SELECT * FROM drives WHERE company_id=? AND status='active'",
                (session["uid"],)).fetchall()
        else:
            drives = db.execute("SELECT d.*, c.name as company_name FROM drives d JOIN companies c ON d.company_id=c.id").fetchall()
        db.close()
        return render_template("create_assessment.html", drives=[dict(d) for d in drives])

    @app.route("/drive/<int:drive_id>/assessment_results")
    def drive_assessment_results(drive_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        db = _db()
        assessment = db.execute("SELECT * FROM assessments WHERE drive_id=?", (drive_id,)).fetchone()
        results = []
        if assessment:
            results = db.execute("""SELECT ar.*, s.name, s.email, s.cgpa, s.branch
                FROM assessment_results ar JOIN students s ON ar.student_id=s.id
                WHERE ar.assessment_id=? ORDER BY ar.score DESC""",
                (assessment["id"],)).fetchall()
        drive = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
        db.close()
        return render_template("assessment_results.html",
            drive=drive, assessment=assessment, results=results)


    # =========================================================================
    # FEATURE 3 — Bulk Hiring CSV Upload
    # =========================================================================
    @app.route("/bulk/upload", methods=["GET","POST"])
    def bulk_upload():
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        if request.method == "POST":
            f = request.files.get("csv_file")
            drive_id = int(request.form.get("drive_id", 0))
            if not f or not f.filename.endswith(".csv"):
                return render_template("bulk_upload.html",
                    error="Please upload a valid CSV file.", drives=_get_drives())
            content = f.read().decode("utf-8-sig", errors="replace")
            reader  = csv.DictReader(io.StringIO(content))
            rows    = list(reader)
            db = _db()
            imported = 0
            errors   = []
            for i, row in enumerate(rows, 1):
                name  = (row.get("name") or row.get("Name") or "").strip()
                email = (row.get("email") or row.get("Email") or "").strip()
                if not name or not email:
                    errors.append(f"Row {i}: missing name or email")
                    continue
                existing = db.execute(
                    "SELECT id FROM students WHERE email=?", (email,)).fetchone()
                if existing:
                    sid = existing["id"]
                else:
                    try:
                        db.execute("""INSERT INTO students
                            (name,email,pwd,phone,branch,degree,year,cgpa,skills)
                            VALUES (?,?,?,?,?,?,?,?,?)""",
                            (name, email,
                             "bulk_" + _secrets.token_hex(4),
                             row.get("phone",""),
                             row.get("branch",""),
                             row.get("degree","B.Tech"),
                             int(row.get("year",0) or 0),
                             float(row.get("cgpa",0) or 0),
                             row.get("skills","")))
                        db.commit()
                        sid = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
                    except Exception as e:
                        errors.append(f"Row {i} ({email}): {e}")
                        continue
                if drive_id:
                    from app import ai_match_score
                    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
                    drive   = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
                    score   = ai_match_score(student, drive) if drive else 0
                    try:
                        db.execute("""INSERT OR IGNORE INTO applications
                            (student_id,drive_id,ai_score,status) VALUES (?,?,?,'applied')""",
                            (sid, drive_id, score))
                        db.commit()
                    except Exception:
                        pass
                imported += 1
            cid = session["uid"] if session.get("role") == "company" else 0
            db.execute("""INSERT INTO bulk_imports
                (company_id,drive_id,filename,total,imported,errors)
                VALUES (?,?,?,?,?,?)""",
                (cid, drive_id, f.filename, len(rows), imported, "\n".join(errors[:10])))
            db.commit(); db.close()
            return render_template("bulk_upload.html",
                success=True, imported=imported,
                total=len(rows), errors=errors[:10],
                drives=_get_drives())
        return render_template("bulk_upload.html", drives=_get_drives())

    def _get_drives():
        db = _db()
        if session.get("role") == "company":
            drives = db.execute(
                "SELECT * FROM drives WHERE company_id=?", (session["uid"],)).fetchall()
        else:
            drives = db.execute(
                "SELECT d.*, c.name as company_name FROM drives d JOIN companies c ON d.company_id=c.id").fetchall()
        db.close()
        return [dict(d) for d in drives]

    # =========================================================================
    # FEATURE 4 — Video Interview Link
    # =========================================================================
    @app.route("/app/<int:app_id>/video_interview", methods=["POST"])
    def set_video_interview(app_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        video_link     = request.form.get("video_link","").strip()
        video_platform = request.form.get("video_platform","zoom")
        slots          = request.form.get("slots","")
        interviewer    = request.form.get("interviewer","")
        notes          = request.form.get("notes","")
        db = _db()
        existing = db.execute(
            "SELECT id FROM interviews WHERE application_id=?", (app_id,)).fetchone()
        if existing:
            db.execute("""UPDATE interviews SET
                video_link=?,video_platform=?,proposed_slots=?,interviewer=?,notes=?,status='pending'
                WHERE application_id=?""",
                (video_link, video_platform, slots, interviewer, notes, app_id))
        else:
            db.execute("""INSERT INTO interviews
                (application_id,video_link,video_platform,proposed_slots,interviewer,notes)
                VALUES (?,?,?,?,?,?)""",
                (app_id, video_link, video_platform, slots, interviewer, notes))
        db.execute("UPDATE applications SET status='interview' WHERE id=?", (app_id,))
        db.commit()
        drive_row = db.execute("SELECT drive_id FROM applications WHERE id=?", (app_id,)).fetchone()
        db.close()
        # Notify candidate
        from app import notify_status_change
        notify_status_change(app_id, "interview")
        if drive_row:
            return redirect(url_for("drive_applicants", drive_id=drive_row["drive_id"]))
        return redirect(url_for("company_dash"))


    # =========================================================================
    # FEATURE 5 — Multiple PDF Templates (offer/letter/payslip)
    # =========================================================================
    # Template selection already passed via form field `template` in existing
    # generate_offer / generate_letter / generate_payslip routes.
    # We extend generate_offer_letter_pdf to branch on template style.
    @app.route("/templates/preview/<string:tpl>")
    def preview_template(tpl):
        """Return a small HTML preview card for a letter template."""
        templates = {
            "standard": {"name":"Standard","color":"#4f46e5","accent":"#eef2ff"},
            "modern":   {"name":"Modern","color":"#059669","accent":"#d1fae5"},
            "minimal":  {"name":"Minimal","color":"#374151","accent":"#f9fafb"},
            "bold":     {"name":"Bold","color":"#dc2626","accent":"#fee2e2"},
            "executive":{"name":"Executive","color":"#7c3aed","accent":"#ede9fe"},
        }
        t = templates.get(tpl, templates["standard"])
        return jsonify(t)

    # =========================================================================
    # FEATURE 6 — Candidate Application Tracker
    # =========================================================================
    @app.route("/student/tracker")
    def application_tracker():
        if session.get("role") != "student":
            return redirect(url_for("login"))
        db = _db()
        apps = db.execute("""
            SELECT a.*,
                   d.title, d.role, d.location as job_loc, d.salary,
                   d.job_type, d.experience_level,
                   c.name as company_name,
                   i.video_link, i.confirmed_slot, i.proposed_slots, i.status as iv_status,
                   ar.score as assess_score
            FROM applications a
            JOIN drives d ON a.drive_id=d.id
            JOIN companies c ON d.company_id=c.id
            LEFT JOIN interviews i ON i.application_id=a.id
            LEFT JOIN assessments asmnt ON asmnt.drive_id=d.id
            LEFT JOIN assessment_results ar ON ar.assessment_id=asmnt.id AND ar.student_id=a.student_id
            WHERE a.student_id=?
            ORDER BY a.applied_on DESC
        """, (session["uid"],)).fetchall()
        db.close()
        STATUS_ORDER = {"applied":1,"eligible":2,"test":3,"interview":4,"selected":5,"rejected":6}
        pipeline = [dict(a) for a in apps]
        for p in pipeline:
            p["step"] = STATUS_ORDER.get(p["status"], 1)
        return render_template("tracker.html", apps=pipeline)

    # =========================================================================
    # FEATURE 7 — Recruiter Analytics
    # =========================================================================
    @app.route("/analytics")
    def recruiter_analytics():
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        db = _db()
        cid_filter = ""
        params = []
        if session.get("role") == "company":
            cid_filter = " AND d.company_id=?"
            params = [session["uid"]]

        # Time-to-hire: avg days from applied → selected
        tth = db.execute(f"""
            SELECT d.id as drive_id, d.title,
                   ROUND(AVG(
                     JULIANDAY(
                       (SELECT MAX(a2.applied_on) FROM applications a2
                        WHERE a2.student_id=a.student_id AND a2.drive_id=a.drive_id)
                     ) - JULIANDAY(a.applied_on)
                   ),1) as avg_days,
                   COUNT(a.id) as hired
            FROM applications a
            JOIN drives d ON a.drive_id=d.id
            WHERE a.status='selected' {cid_filter}
            GROUP BY d.id ORDER BY d.created DESC
        """, params).fetchall()

        # Applications per job
        apps_per_job = db.execute(f"""
            SELECT d.title, d.role,
                   COUNT(a.id) as total,
                   SUM(CASE WHEN a.status='eligible' THEN 1 ELSE 0 END) as shortlisted,
                   SUM(CASE WHEN a.status='interview' THEN 1 ELSE 0 END) as interviewed,
                   SUM(CASE WHEN a.status='selected' THEN 1 ELSE 0 END) as offered,
                   SUM(CASE WHEN a.status='rejected' THEN 1 ELSE 0 END) as rejected
            FROM drives d
            LEFT JOIN applications a ON a.drive_id=d.id
            WHERE 1=1 {cid_filter}
            GROUP BY d.id ORDER BY total DESC
        """, params).fetchall()

        # Shortlist-to-offer ratio per drive
        ratios = []
        for r in apps_per_job:
            sl = r["shortlisted"] or 0
            of = r["offered"] or 0
            ratios.append({
                "title": r["title"],
                "shortlisted": sl,
                "offered": of,
                "ratio": f"{round(of/sl*100)}%" if sl > 0 else "—",
            })

        # Source funnel totals
        funnel = db.execute(f"""
            SELECT
              COUNT(*) as total,
              SUM(CASE WHEN a.status='eligible' THEN 1 ELSE 0 END) as shortlisted,
              SUM(CASE WHEN a.status='interview' THEN 1 ELSE 0 END) as interviewed,
              SUM(CASE WHEN a.status='selected' THEN 1 ELSE 0 END) as offered
            FROM applications a
            JOIN drives d ON a.drive_id=d.id
            WHERE 1=1 {cid_filter}
        """, params).fetchone()

        # Monthly trend
        monthly = db.execute(f"""
            SELECT strftime('%Y-%m', a.applied_on) as month,
                   COUNT(*) as apps,
                   SUM(CASE WHEN a.status='selected' THEN 1 ELSE 0 END) as hired
            FROM applications a JOIN drives d ON a.drive_id=d.id
            WHERE 1=1 {cid_filter}
            GROUP BY month ORDER BY month DESC LIMIT 12
        """, params).fetchall()

        db.close()
        return render_template("recruiter_analytics.html",
            tth=tth, apps_per_job=apps_per_job, ratios=ratios,
            funnel=funnel, monthly=list(reversed(monthly)))


    # =========================================================================
    # FEATURE 8 — Reference Check Workflow
    # =========================================================================
    @app.route("/app/<int:app_id>/reference_request", methods=["POST"])
    def request_reference(app_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        f = request.form
        referee_name     = f.get("referee_name","")
        referee_email    = f.get("referee_email","")
        referee_relation = f.get("referee_relation","")
        token = _secrets.token_urlsafe(24)
        db = _db()
        app_row = db.execute(
            "SELECT student_id, drive_id FROM applications WHERE id=?", (app_id,)).fetchone()
        db.execute("""INSERT INTO reference_checks
            (application_id,student_id,referee_name,referee_email,referee_relation,token)
            VALUES (?,?,?,?,?,?)""",
            (app_id, app_row["student_id"], referee_name, referee_email, referee_relation, token))
        db.commit()
        drive_id = app_row["drive_id"]
        db.close()
        # In production: send email to referee with the token link
        # from app import send_email_notification
        # ref_link = url_for('submit_reference', token=token, _external=True)
        # send_email_notification(referee_email, "Reference Request", f"<p>Please submit a reference at: {ref_link}</p>")
        return redirect(url_for("drive_applicants", drive_id=drive_id))

    @app.route("/reference/<string:token>", methods=["GET","POST"])
    def submit_reference(token):
        db = _db()
        ref = db.execute(
            "SELECT * FROM reference_checks WHERE token=?", (token,)).fetchone()
        if not ref:
            db.close()
            return "Invalid or expired reference link.", 404
        if request.method == "POST":
            f = request.form
            db.execute("""UPDATE reference_checks SET
                status='submitted', response=?, rating=?, submitted_on=?
                WHERE token=?""",
                (f.get("response",""),
                 int(f.get("rating",3)),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 token))
            db.commit(); db.close()
            return render_template("reference_thanks.html")
        student = db.execute(
            "SELECT name FROM students WHERE id=?", (ref["student_id"],)).fetchone()
        db.close()
        return render_template("reference_form.html", ref=ref, student=student)

    @app.route("/drive/<int:drive_id>/references")
    def drive_references(drive_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        db = _db()
        refs = db.execute("""
            SELECT rc.*, s.name as student_name, s.email as student_email
            FROM reference_checks rc
            JOIN applications a ON rc.application_id=a.id
            JOIN students s ON rc.student_id=s.id
            WHERE a.drive_id=?
            ORDER BY rc.created DESC
        """, (drive_id,)).fetchall()
        drive = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
        db.close()
        return render_template("drive_references.html", refs=refs, drive=drive)

    # =========================================================================
    # FEATURE 9 — Diversity / Skill-Gap Dashboard
    # =========================================================================
    @app.route("/drive/<int:drive_id>/diversity")
    def drive_diversity(drive_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        db = _db()
        drive = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
        if not drive:
            db.close(); return redirect(url_for("company_dash"))

        # Gender breakdown
        gender = db.execute("""
            SELECT COALESCE(s.gender,'Not Specified') as gender, COUNT(*) as cnt
            FROM applications a JOIN students s ON a.student_id=s.id
            WHERE a.drive_id=? GROUP BY s.gender
        """, (drive_id,)).fetchall()

        # Branch breakdown
        branch = db.execute("""
            SELECT s.branch, COUNT(*) as cnt
            FROM applications a JOIN students s ON a.student_id=s.id
            WHERE a.drive_id=? GROUP BY s.branch ORDER BY cnt DESC
        """, (drive_id,)).fetchall()

        # Location diversity
        location = db.execute("""
            SELECT COALESCE(s.location,'Unknown') as location, COUNT(*) as cnt
            FROM applications a JOIN students s ON a.student_id=s.id
            WHERE a.drive_id=? GROUP BY s.location ORDER BY cnt DESC LIMIT 10
        """, (drive_id,)).fetchall()

        # Skill gap: required vs applicant skills
        req_skills = [s.strip().lower() for s in (drive["req_skills"] or "").split(",") if s.strip()]
        applicants = db.execute("""
            SELECT s.skills FROM applications a JOIN students s ON a.student_id=s.id
            WHERE a.drive_id=?
        """, (drive_id,)).fetchall()
        skill_coverage = {}
        for sk in req_skills:
            count = sum(1 for a in applicants
                       if any(sk in t.strip().lower() for t in (a["skills"] or "").split(",")))
            skill_coverage[sk] = {
                "count": count,
                "pct": round(count/len(applicants)*100) if applicants else 0
            }

        # CGPA distribution buckets
        cgpa_dist = {"<6": 0, "6-7": 0, "7-8": 0, "8-9": 0, "9+": 0}
        all_applicants = db.execute("""
            SELECT s.cgpa FROM applications a JOIN students s ON a.student_id=s.id
            WHERE a.drive_id=?
        """, (drive_id,)).fetchall()
        for r in all_applicants:
            c = r["cgpa"] or 0
            if   c < 6:   cgpa_dist["<6"] += 1
            elif c < 7:   cgpa_dist["6-7"] += 1
            elif c < 8:   cgpa_dist["7-8"] += 1
            elif c < 9:   cgpa_dist["8-9"] += 1
            else:         cgpa_dist["9+"] += 1

        db.close()
        return render_template("drive_diversity.html",
            drive=drive, gender=gender, branch=branch,
            location=location, skill_coverage=skill_coverage,
            cgpa_dist=cgpa_dist, total=len(applicants))

    # =========================================================================
    # FEATURE 10 — E-Signature on Offer Letters
    # =========================================================================
    @app.route("/offer/<int:offer_id>/esign_invite", methods=["POST"])
    def esign_invite(offer_id):
        if session.get("role") not in ("company","admin"):
            return redirect(url_for("login"))
        token = _secrets.token_urlsafe(32)
        db = _db()
        try:
            offer = db.execute("SELECT * FROM offers WHERE id=?", (offer_id,)).fetchone()
            db.execute("""INSERT OR REPLACE INTO offer_signatures
                (offer_id,student_id,token) VALUES (?,?,?)""",
                (offer_id, offer["student_id"], token))
            db.commit()
        except Exception:
            pass
        db.close()
        # In production: email the sign link to the student
        # sign_link = url_for('esign_page', token=token, _external=True)
        return redirect(url_for("company_dash"))

    @app.route("/offer/sign/<string:token>", methods=["GET","POST"])
    def esign_page(token):
        db = _db()
        sig = db.execute(
            "SELECT * FROM offer_signatures WHERE token=?", (token,)).fetchone()
        if not sig:
            db.close(); return "Invalid or expired signature link.", 404
        offer = db.execute("""
            SELECT o.*, s.name as candidate_name, c.name as company_name
            FROM offers o JOIN students s ON o.student_id=s.id
            JOIN companies c ON o.company_id=c.id
            WHERE o.id=?
        """, (sig["offer_id"],)).fetchone()
        if request.method == "POST":
            ip = request.remote_addr or "unknown"
            db.execute("""UPDATE offer_signatures SET
                signed=1, signed_on=?, ip_address=? WHERE token=?""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip, token))
            db.execute("UPDATE offers SET signed=1, signed_on=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sig["offer_id"]))
            db.commit(); db.close()
            return render_template("esign_confirmed.html", offer=offer)
        db.close()
        return render_template("esign_page.html", sig=sig, offer=offer)

    @app.route("/offer/<int:offer_id>/sign_status")
    def offer_sign_status(offer_id):
        if session.get("role") not in ("company","admin","student"):
            return jsonify({"error":"unauthorized"})
        db = _db()
        sig = db.execute(
            "SELECT * FROM offer_signatures WHERE offer_id=?", (offer_id,)).fetchone()
        db.close()
        if not sig:
            return jsonify({"signed": False, "message": "No signature request sent"})
        return jsonify({
            "signed": bool(sig["signed"]),
            "signed_on": sig["signed_on"] or "",
            "message": "Signed ✓" if sig["signed"] else "Awaiting signature"
        })

