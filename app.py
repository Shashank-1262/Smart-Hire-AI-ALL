from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, send_file
from flask_mail import Mail, Message
import sqlite3, os, io, csv, json
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

app = Flask(__name__)
app.secret_key = "smarthire_ai_secret_2024"
DB = os.path.join(os.path.dirname(__file__), "smarthire.db")

# ── Mail config (update with real credentials) ────────────────────────────────
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'noreply.smarthire@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = ('SmartHire AI', os.environ.get('MAIL_USERNAME', 'noreply.smarthire@gmail.com'))
mail = Mail(app)

TELEGRAM_TOKEN  = os.environ.get('TELEGRAM_TOKEN', '')
UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_PHOTO   = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_RESUME  = {"pdf", "doc", "docx"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── DB ───────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, pwd TEXT,
        phone TEXT, dob TEXT, branch TEXT, degree TEXT,
        year INTEGER, cgpa REAL DEFAULT 0,
        p12 REAL DEFAULT 0, p10 REAL DEFAULT 0,
        skills TEXT DEFAULT '', bio TEXT DEFAULT '',
        gender TEXT DEFAULT '', location TEXT DEFAULT '',
        photo TEXT DEFAULT '', resume TEXT DEFAULT '',
        resume_uploaded_on TEXT DEFAULT '',
        experience TEXT DEFAULT '', education TEXT DEFAULT '',
        telegram_chat_id TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, pwd TEXT,
        phone TEXT, location TEXT, industry TEXT,
        website TEXT DEFAULT '', about TEXT DEFAULT '',
        logo TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS drives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, title TEXT, role TEXT,
        location TEXT, salary_min REAL DEFAULT 0, salary_max REAL DEFAULT 0,
        salary REAL DEFAULT 0,
        job_type TEXT DEFAULT 'Full-time',
        experience_level TEXT DEFAULT 'Entry Level',
        deadline TEXT, description TEXT DEFAULT '',
        requirements TEXT DEFAULT '',
        req_cgpa REAL DEFAULT 0, req_degree TEXT DEFAULT '',
        req_skills TEXT DEFAULT '', req_year INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active', is_public INTEGER DEFAULT 1,
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER, drive_id INTEGER,
        status TEXT DEFAULT 'applied',
        ai_score REAL DEFAULT 0,
        cover_letter TEXT DEFAULT '',
        applied_on TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, drive_id)
    );
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        proposed_slots TEXT DEFAULT '',
        confirmed_slot TEXT DEFAULT '',
        interviewer TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        student_id INTEGER,
        drive_id INTEGER,
        company_id INTEGER,
        role TEXT, salary TEXT, joining_date TEXT,
        template TEXT DEFAULT 'standard',
        letter_type TEXT DEFAULT 'offer',
        custom_fields TEXT DEFAULT '',
        generated_on TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        title TEXT, message TEXT,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_id INTEGER,
        title TEXT,
        questions TEXT DEFAULT '[]',
        time_limit INTEGER DEFAULT 30,
        passing_score INTEGER DEFAULT 60,
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS assessment_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER,
        student_id INTEGER,
        application_id INTEGER,
        score REAL DEFAULT 0,
        answers TEXT DEFAULT '{}',
        submitted_on TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(assessment_id, student_id)
    );
    CREATE TABLE IF NOT EXISTS bulk_imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        drive_id INTEGER,
        filename TEXT,
        total INTEGER DEFAULT 0,
        imported INTEGER DEFAULT 0,
        errors TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS reference_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        student_id INTEGER,
        referee_name TEXT,
        referee_email TEXT,
        referee_relation TEXT,
        token TEXT UNIQUE,
        status TEXT DEFAULT 'pending',
        response TEXT DEFAULT '',
        rating INTEGER DEFAULT 0,
        submitted_on TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS offer_signatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER UNIQUE,
        student_id INTEGER,
        token TEXT UNIQUE,
        signed INTEGER DEFAULT 0,
        signed_on TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit(); conn.close()

def migrate_db():
    conn = get_db(); c = conn.cursor()
    # students
    existing_s = [row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()]
    for col, defn in [
        ("gender","TEXT DEFAULT ''"),("location","TEXT DEFAULT ''"),
        ("photo","TEXT DEFAULT ''"),("resume","TEXT DEFAULT ''"),
        ("resume_uploaded_on","TEXT DEFAULT ''"),("experience","TEXT DEFAULT ''"),
        ("education","TEXT DEFAULT ''"),("telegram_chat_id","TEXT DEFAULT ''"),
    ]:
        if col not in existing_s:
            c.execute(f"ALTER TABLE students ADD COLUMN {col} {defn}")
    # companies
    existing_c = [row[1] for row in c.execute("PRAGMA table_info(companies)").fetchall()]
    for col, defn in [
        ("logo","TEXT DEFAULT ''"),
        ("suspended","INTEGER DEFAULT 0"),
        ("default_template","TEXT DEFAULT 'standard'"),
        ("brand_color","TEXT DEFAULT '#4f46e5'"),
    ]:
        if col not in existing_c:
            c.execute(f"ALTER TABLE companies ADD COLUMN {col} {defn}")
    # students — suspended flag
    existing_s2 = [row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()]
    if "suspended" not in existing_s2:
        c.execute("ALTER TABLE students ADD COLUMN suspended INTEGER DEFAULT 0")
    # drives
    existing_d = [row[1] for row in c.execute("PRAGMA table_info(drives)").fetchall()]
    for col, defn in [
        ("salary_min","REAL DEFAULT 0"),("salary_max","REAL DEFAULT 0"),
        ("job_type","TEXT DEFAULT 'Full-time'"),("experience_level","TEXT DEFAULT 'Entry Level'"),
        ("requirements","TEXT DEFAULT ''"),("is_public","INTEGER DEFAULT 1"),
    ]:
        if col not in existing_d:
            c.execute(f"ALTER TABLE drives ADD COLUMN {col} {defn}")
    # applications
    existing_a = [row[1] for row in c.execute("PRAGMA table_info(applications)").fetchall()]
    for col, defn in [("cover_letter","TEXT DEFAULT ''")]:
        if col not in existing_a:
            c.execute(f"ALTER TABLE applications ADD COLUMN {col} {defn}")
    # interviews - add video_link
    existing_i = [row[1] for row in c.execute("PRAGMA table_info(interviews)").fetchall()]
    for col, defn in [
        ("video_link","TEXT DEFAULT ''"),
        ("video_platform","TEXT DEFAULT 'zoom'"),
    ]:
        if col not in existing_i:
            c.execute(f"ALTER TABLE interviews ADD COLUMN {col} {defn}")
    # offers - add signature columns
    existing_o = [row[1] for row in c.execute("PRAGMA table_info(offers)").fetchall()]
    for col, defn in [
        ("signed","INTEGER DEFAULT 0"),
        ("signed_on","TEXT DEFAULT ''"),
    ]:
        if col not in existing_o:
            c.execute(f"ALTER TABLE offers ADD COLUMN {col} {defn}")
    conn.commit(); conn.close()

# ─── Notification helpers ─────────────────────────────────────────────────────
def send_notification(student_id, title, message, ntype="info"):
    """Store in-app notification."""
    db = get_db()
    db.execute("INSERT INTO notifications (student_id,title,message,type) VALUES (?,?,?,?)",
               (student_id, title, message, ntype))
    db.commit(); db.close()

def send_email_notification(to_email, subject, body_html):
    """Send email — silently fails if not configured."""
    try:
        if not app.config.get('MAIL_PASSWORD'):
            return
        msg = Message(subject, recipients=[to_email])
        msg.html = body_html
        mail.send(msg)
    except Exception:
        pass

def send_telegram(chat_id, text):
    """Send Telegram message — silently fails if not configured."""
    try:
        if not TELEGRAM_TOKEN or not chat_id:
            return
        import requests as req
        req.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass

def notify_status_change(app_id, new_status):
    """Send notification (in-app + email + telegram) when application status changes."""
    db = get_db()
    row = db.execute("""SELECT a.*, s.name, s.email, s.telegram_chat_id,
                        d.title as drive_title, c.name as company_name
                        FROM applications a JOIN students s ON a.student_id=s.id
                        JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
                        WHERE a.id=?""", (app_id,)).fetchone()
    db.close()
    if not row: return
    labels = {'applied':'Applied','eligible':'Shortlisted','test':'Test Scheduled',
              'interview':'Interview Scheduled','selected':'Selected 🎉','rejected':'Application Rejected'}
    label = labels.get(new_status, new_status.capitalize())
    title = f"{label} – {row['company_name']}"
    msg   = f"Your application for '{row['drive_title']}' at {row['company_name']} is now: {label}"
    send_notification(row['student_id'], title, msg,
                      "success" if new_status=="selected" else "danger" if new_status=="rejected" else "info")
    email_body = f"<p>Hi {row['name']},</p><p>{msg}</p><p>Log in to SmartHire AI for details.</p>"
    send_email_notification(row['email'], f"[SmartHire AI] {title}", email_body)
    send_telegram(row['telegram_chat_id'], f"<b>{title}</b>\n{msg}")

# ─── AI helpers ───────────────────────────────────────────────────────────────
def ai_match_score(student, drive):
    score = 0
    if student['cgpa'] >= drive['req_cgpa']:          score += 30
    elif student['cgpa'] >= drive['req_cgpa'] - 0.5:  score += 15
    req = [s.strip().lower() for s in (drive['req_skills'] or '').split(',') if s.strip()]
    stu = [s.strip().lower() for s in (student['skills'] or '').split(',') if s.strip()]
    if req:
        matched = sum(1 for r in req if any(r in s or s in r for s in stu))
        score += int((matched / len(req)) * 40)
    else:
        score += 30
    if not drive['req_degree'] or student['degree'] == drive['req_degree']: score += 20
    else: score += 5
    if not drive['req_year'] or student['year'] >= drive['req_year']: score += 10
    return round(score, 1)

def ai_extract_skills(text):
    known = ["Python","Java","JavaScript","C++","C","React","Node.js","Django","Flask",
             "SQL","MongoDB","PostgreSQL","MySQL","Machine Learning","Deep Learning",
             "TensorFlow","PyTorch","NLP","Data Science","AWS","Docker","Kubernetes",
             "Git","HTML","CSS","TypeScript","REST API","Pandas","NumPy","Scikit-learn",
             "R","Android","iOS","Swift","Kotlin","Spring Boot","FastAPI","Figma",
             "Power BI","Tableau","Excel","Linux","Redis","GraphQL"]
    return [k for k in known if k.lower() in text.lower()]

def ai_questions(role, rtype="Technical"):
    bank = {
        "Technical": {
            "ml":["Explain overfitting and how to prevent it.","What is the bias-variance tradeoff?",
                  "How does gradient descent work?","Explain supervised vs unsupervised learning.","What is cross-validation?"],
            "web":["What is the JavaScript event loop?","Explain REST vs GraphQL.","What are React hooks?",
                   "How does HTTP caching work?","Explain CORS."],
            "default":["Explain stack vs queue with examples.","What is Big O notation?",
                       "Describe a challenging project you built.","Explain SOLID principles.",
                       "What is the difference between process and thread?"]
        },
        "HR":["Tell me about yourself.","Where do you see yourself in 5 years?",
              "Describe a conflict you resolved in a team.",
              "What are your greatest strengths and weaknesses?","Why do you want to join our company?"],
        "Aptitude":["A train travels 60 km/h for 2 hours. Distance?","5 workers finish a job in 10 days. Time for 10 workers?",
                    "Next: 2, 6, 12, 20, 30, ?","20% profit on ₹500 cost price. Selling price?","Simplify: (25×4)÷(5×2)"]
    }
    if rtype == "HR":       return bank["HR"]
    if rtype == "Aptitude": return bank["Aptitude"]
    r = role.lower()
    if any(k in r for k in ["ml","ai","data","machine"]): return bank["Technical"]["ml"]
    if any(k in r for k in ["web","front","back","full"]):  return bank["Technical"]["web"]
    return bank["Technical"]["default"]

# ─── PDF generation helpers ───────────────────────────────────────────────────
def generate_offer_letter_pdf(data):
    """Generate offer/joining letter PDF. Returns bytes."""
    # Resolve brand color from template style
    tpl_colors = {
        "standard": "#4f46e5", "modern":   "#059669",
        "minimal":  "#374151", "bold":     "#dc2626",
        "executive":"#7c3aed",
    }
    tpl      = data.get("template", "standard")
    accent   = data.get("brand_color") or tpl_colors.get(tpl, "#4f46e5")
    acc_clr  = colors.HexColor(accent)
    acc_light = colors.HexColor(accent + "22") if len(accent) == 7 else colors.HexColor("#eef2ff")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{data.get('company_name','Company Name')}</b>",
                            ParagraphStyle('hdr', fontSize=18, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph(data.get('company_address',''),
                            ParagraphStyle('sub', fontSize=10, alignment=TA_CENTER, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=acc_clr))
    story.append(Spacer(1, 0.5*cm))
    ttype = data.get('letter_type', 'offer')
    heading = "OFFER LETTER" if ttype == 'offer' else "JOINING LETTER" if ttype == 'joining' else "APPOINTMENT LETTER"
    story.append(Paragraph(f"<b>{heading}</b>",
                            ParagraphStyle('h2', fontSize=14, alignment=TA_CENTER, spaceAfter=12,
                                           textColor=acc_clr)))
    story.append(Paragraph(f"Date: {data.get('generated_on', datetime.now().strftime('%d %B %Y'))}",
                            ParagraphStyle('date', fontSize=10, alignment=TA_RIGHT)))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(f"Dear <b>{data.get('candidate_name','')}</b>,", styles['Normal']))
    story.append(Spacer(1, 0.3*cm))
    body = (
        f"We are pleased to offer you the position of <b>{data.get('role','')}</b> at "
        f"<b>{data.get('company_name','')}</b>. After reviewing your application and interview performance, "
        f"we believe you will be a valuable addition to our team."
    )
    story.append(Paragraph(body, styles['Normal']))
    story.append(Spacer(1, 0.4*cm))
    tbl_data = [
        ["Position",       data.get('role','')],
        ["Department",     data.get('department','Engineering')],
        ["Location",       data.get('location','')],
        ["CTC / Salary",   data.get('salary','')],
        ["Date of Joining",data.get('joining_date','')],
        ["Employment Type",data.get('job_type','Full-time')],
    ]
    t = Table(tbl_data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor(accent + "22") if len(accent)==7 else colors.HexColor("#eef2ff")),
        ('TEXTCOLOR',  (0,0), (0,-1), acc_clr),
        ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 10),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e5f0')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f8f9ff')]),
        ('PADDING',    (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "This offer is subject to satisfactory completion of background verification and submission of required documents.",
        ParagraphStyle('note', fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Yours sincerely,", styles['Normal']))
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph(f"<b>{data.get('hr_name','HR Manager')}</b>", styles['Normal']))
    story.append(Paragraph(f"{data.get('hr_title','Human Resources')}", styles['Normal']))
    story.append(Paragraph(f"<b>{data.get('company_name','')}</b>", styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf

def generate_relieving_letter_pdf(data):
    """Generate relieving / experience letter PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{data.get('company_name','')}</b>",
                            ParagraphStyle('hdr', fontSize=18, alignment=TA_CENTER, spaceAfter=4)))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#059669')))
    story.append(Spacer(1, 0.6*cm))
    ltype = data.get('letter_type','relieving')
    heading = "RELIEVING LETTER" if ltype == 'relieving' else "EXPERIENCE LETTER"
    story.append(Paragraph(f"<b>{heading}</b>",
                            ParagraphStyle('h2', fontSize=14, alignment=TA_CENTER, spaceAfter=12,
                                           textColor=colors.HexColor('#059669'))))
    story.append(Paragraph(f"Date: {data.get('generated_on', datetime.now().strftime('%d %B %Y'))}",
                            ParagraphStyle('date', fontSize=10, alignment=TA_RIGHT)))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(f"To Whom It May Concern,", styles['Normal']))
    story.append(Spacer(1, 0.3*cm))
    body = (
        f"This is to certify that <b>{data.get('candidate_name','')}</b> was employed with "
        f"<b>{data.get('company_name','')}</b> as <b>{data.get('role','')}</b> "
        f"from <b>{data.get('from_date','')}</b> to <b>{data.get('to_date','')}</b>. "
        f"During this period, {data.get('candidate_name','').split()[0]} demonstrated excellent "
        f"professionalism and dedication."
    )
    story.append(Paragraph(body, styles['Normal']))
    if ltype == 'relieving':
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"{data.get('candidate_name','').split()[0]} has been relieved from services "
            f"on {data.get('to_date','')} and has no dues pending. We wish them all the best.",
            styles['Normal']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Yours sincerely,", styles['Normal']))
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph(f"<b>{data.get('hr_name','HR Manager')}</b>", styles['Normal']))
    story.append(Paragraph(data.get('hr_title','Human Resources'), styles['Normal']))
    story.append(Paragraph(f"<b>{data.get('company_name','')}</b>", styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf

def generate_payslip_pdf(data):
    """Generate payslip PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{data.get('company_name','')}</b>",
                            ParagraphStyle('hdr', fontSize=16, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("SALARY SLIP",
                            ParagraphStyle('h2', fontSize=13, alignment=TA_CENTER, spaceAfter=6,
                                           textColor=colors.HexColor('#4f46e5'))))
    story.append(Paragraph(f"For the month of: <b>{data.get('month','')}</b>",
                            ParagraphStyle('sub', fontSize=10, alignment=TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e5f0')))
    story.append(Spacer(1, 0.4*cm))
    emp = [
        ["Employee Name", data.get('candidate_name',''), "Employee ID", data.get('emp_id','')],
        ["Designation",   data.get('role',''),           "Department",  data.get('department','')],
        ["Bank Account",  data.get('bank_acc','—'),      "PAN",         data.get('pan','—')],
    ]
    et = Table(emp, colWidths=[4*cm,5.5*cm,3.5*cm,4*cm])
    et.setStyle(TableStyle([
        ('FONTSIZE',(0,0),(-1,-1),9),('PADDING',(0,0),(-1,-1),6),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#e2e5f0')),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.HexColor('#f8f9ff'),colors.white]),
    ]))
    story.append(et)
    story.append(Spacer(1, 0.5*cm))
    earnings = [
        ["EARNINGS","Amount (₹)","DEDUCTIONS","Amount (₹)"],
        ["Basic Salary",    data.get('basic','0'),     "PF (12%)",           data.get('pf','0')],
        ["HRA",             data.get('hra','0'),       "Professional Tax",   data.get('prof_tax','0')],
        ["Special Allowance", data.get('special','0'),"Income Tax (TDS)",   data.get('tds','0')],
        ["Other Allowances",data.get('other_allow','0'),"Other Deductions",  data.get('other_ded','0')],
        ["Gross Earnings",  data.get('gross','0'),     "Total Deductions",   data.get('total_ded','0')],
    ]
    pt = Table(earnings, colWidths=[5*cm,3.5*cm,5*cm,3.5*cm])
    pt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#4f46e5')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),
        ('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#eef2ff')),
        ('FONTSIZE',(0,0),(-1,-1),9),('PADDING',(0,0),(-1,-1),7),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#e2e5f0')),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),('ALIGN',(3,0),(3,-1),'RIGHT'),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.5*cm))
    net = data.get('net_pay','0')
    story.append(Paragraph(f"<b>Net Pay: ₹{net}</b>",
                            ParagraphStyle('net', fontSize=12, alignment=TA_RIGHT,
                                           textColor=colors.HexColor('#059669'))))
    doc.build(story)
    buf.seek(0)
    return buf

# ─── Init on startup ──────────────────────────────────────────────────────────
with app.app_context():
    init_db()
    migrate_db()
    from routes_new import register_routes
    register_routes(app)

# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    db = get_db()
    stats = {
        "students":  db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"],
        "companies": db.execute("SELECT COUNT(*) as c FROM companies").fetchone()["c"],
        "drives":    db.execute("SELECT COUNT(*) as c FROM drives WHERE status='active'").fetchone()["c"],
        "placed":    db.execute("SELECT COUNT(DISTINCT student_id) as c FROM applications WHERE status='selected'").fetchone()["c"],
    }
    db.close()
    return render_template("index.html", stats=stats)

# ── Public job board ──────────────────────────────────────────────────────────
@app.route("/jobs")
def job_board():
    search   = request.args.get("q","").strip()
    location = request.args.get("location","").strip()
    job_type = request.args.get("job_type","").strip()
    exp_lvl  = request.args.get("exp_level","").strip()
    db = get_db()
    query = """SELECT d.*, c.name as company_name, c.industry, c.logo,
                      COUNT(a.id) as app_count
               FROM drives d JOIN companies c ON d.company_id=c.id
               LEFT JOIN applications a ON a.drive_id=d.id
               WHERE d.status='active' AND d.is_public=1"""
    params = []
    if search:
        query += " AND (d.title LIKE ? OR d.role LIKE ? OR c.name LIKE ? OR d.description LIKE ?)"
        params += [f"%{search}%"]*4
    if location:
        query += " AND d.location LIKE ?"
        params.append(f"%{location}%")
    if job_type:
        query += " AND d.job_type=?"
        params.append(job_type)
    if exp_lvl:
        query += " AND d.experience_level=?"
        params.append(exp_lvl)
    query += " GROUP BY d.id ORDER BY d.created DESC"
    jobs = db.execute(query, params).fetchall()
    locations = [r['location'] for r in db.execute("SELECT DISTINCT location FROM drives WHERE status='active'").fetchall()]
    db.close()
    return render_template("job_board.html", jobs=jobs, locations=locations,
                           search=search, location=location, job_type=job_type, exp_lvl=exp_lvl)

@app.route("/jobs/<int:drive_id>")
def job_detail(drive_id):
    db = get_db()
    job = db.execute("""SELECT d.*, c.name as company_name, c.industry, c.about as company_about,
                               c.website, c.logo
                        FROM drives d JOIN companies c ON d.company_id=c.id
                        WHERE d.id=? AND d.is_public=1""", (drive_id,)).fetchone()
    if not job:
        db.close(); return redirect(url_for('job_board'))
    app_count = db.execute("SELECT COUNT(*) as c FROM applications WHERE drive_id=?", (drive_id,)).fetchone()["c"]
    already_applied = False
    if session.get('role') == 'student':
        r = db.execute("SELECT id FROM applications WHERE student_id=? AND drive_id=?",
                       (session['uid'], drive_id)).fetchone()
        already_applied = r is not None
    db.close()
    return render_template("job_detail.html", job=job, app_count=app_count, already_applied=already_applied)

# ─── Auth ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pwd   = request.form.get("pwd","").strip()
        role  = request.form.get("role","")
        if role == "admin":
            if email == "admin@smarthire.ai" and pwd == "admin123":
                session.update({"uid":0,"role":"admin","name":"Admin","email":email})
                return redirect(url_for("admin_dash"))
            return render_template("login.html", error="Invalid admin credentials.")
        table = "students" if role == "student" else "companies"
        db = get_db()
        row = db.execute(f"SELECT * FROM {table} WHERE email=?", (email,)).fetchone()
        db.close()
        if not row: return render_template("login.html", error="Account not found.")
        if row["pwd"] != pwd: return render_template("login.html", error="Wrong password.")
        session.update({"uid":row["id"],"role":role,"name":row["name"],"email":email})
        return redirect(url_for("student_dash" if role=="student" else "company_dash"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/register/student", methods=["GET","POST"])
def student_register():
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO students (name,email,pwd,phone,dob,branch,degree,year,cgpa,p12,p10,skills,bio,experience,education)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],f.get("dob",""),
                 f.get("branch",""),f.get("degree","B.Tech"),int(f.get("year",0) or 0),
                 float(f.get("cgpa",0) or 0),float(f.get("p12",0) or 0),float(f.get("p10",0) or 0),
                 f.get("skills",""),f.get("bio",""),f.get("experience",""),f.get("education","")))
            db.commit(); db.close()
            return render_template("student_register.html", success=True)
        except sqlite3.IntegrityError:
            db.close()
            return render_template("student_register.html", error="Email already registered.")
    return render_template("student_register.html")

@app.route("/register/company", methods=["GET","POST"])
def company_register():
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO companies (name,email,pwd,phone,location,industry,website,about)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],
                 f["location"],f["industry"],f.get("website",""),f.get("about","")))
            db.commit(); db.close()
            return render_template("company_register.html", success=True)
        except sqlite3.IntegrityError:
            db.close()
            return render_template("company_register.html", error="Email already registered.")
    return render_template("company_register.html")

# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/student")
def student_dash():
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drives_raw = db.execute("""
        SELECT d.*, c.name as company_name, c.industry, c.logo,
               a.id as app_id, a.status as app_status, a.ai_score
        FROM drives d JOIN companies c ON d.company_id=c.id
        LEFT JOIN applications a ON a.drive_id=d.id AND a.student_id=?
        WHERE d.status='active' ORDER BY d.created DESC
    """, (session["uid"],)).fetchall()
    drives = []
    for d in drives_raw:
        row = dict(d)
        row['computed_score'] = row['ai_score'] if (row['app_id'] and row['ai_score']) else ai_match_score(student, d)
        drives.append(row)
    my_apps = db.execute("""
        SELECT a.*, d.title, d.role, d.salary, d.job_type, d.location as job_loc,
               c.name as company_name, c.logo,
               i.confirmed_slot, i.status as iv_status
        FROM applications a JOIN drives d ON a.drive_id=d.id
        JOIN companies c ON d.company_id=c.id
        LEFT JOIN interviews i ON i.application_id=a.id
        WHERE a.student_id=? ORDER BY a.applied_on DESC
    """, (session["uid"],)).fetchall()
    unapplied = [d for d in drives if not d["app_id"]]
    recommendations = sorted([{"drive":d,"score":d["computed_score"]} for d in unapplied],
                              key=lambda x: x["score"], reverse=True)[:3]
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for a in my_apps:
        if a["status"] in status_counts: status_counts[a["status"]] += 1
    notifs = db.execute("SELECT * FROM notifications WHERE student_id=? ORDER BY created DESC LIMIT 20",
                        (session["uid"],)).fetchall()
    unread = db.execute("SELECT COUNT(*) as c FROM notifications WHERE student_id=? AND is_read=0",
                        (session["uid"],)).fetchone()["c"]
    db.close()
    skills_list = [s.strip() for s in (student["skills"] or "").split(",") if s.strip()]
    return render_template("student_dash.html", student=student, drives=drives, my_apps=my_apps,
                           skills_list=skills_list, recommendations=recommendations,
                           status_counts=status_counts, notifs=notifs, unread=unread)

@app.route("/apply/<int:drive_id>", methods=["POST"])
def apply(drive_id):
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drive   = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
    if not drive: db.close(); return redirect(url_for("student_dash"))
    score        = ai_match_score(student, drive)
    cover_letter = request.form.get("cover_letter","")
    try:
        db.execute("INSERT INTO applications (student_id,drive_id,ai_score,cover_letter) VALUES (?,?,?,?)",
                   (session["uid"], drive_id, score, cover_letter))
        db.commit()
    except sqlite3.IntegrityError:
        pass
    db.close()
    return redirect(request.referrer or url_for("student_dash"))

@app.route("/student/notifications/read", methods=["POST"])
def mark_notifs_read():
    if session.get("role") != "student": return jsonify({"ok":False})
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1 WHERE student_id=?", (session["uid"],))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/student/profile/update", methods=["POST"])
def student_profile_update():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.form
    db = get_db()
    db.execute("""UPDATE students SET name=?,phone=?,dob=?,branch=?,degree=?,year=?,cgpa=?,
                  p12=?,p10=?,skills=?,bio=?,gender=?,location=?,experience=?,education=?,telegram_chat_id=?
                  WHERE id=?""",
               (f.get("name"),f.get("phone"),f.get("dob"),f.get("branch"),f.get("degree"),
                int(f.get("year",0) or 0),float(f.get("cgpa",0) or 0),
                float(f.get("p12",0) or 0),float(f.get("p10",0) or 0),
                f.get("skills",""),f.get("bio",""),f.get("gender",""),f.get("location",""),
                f.get("experience",""),f.get("education",""),f.get("telegram_chat_id",""),
                session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=profile")

@app.route("/student/interview/<int:iv_id>/confirm", methods=["POST"])
def confirm_interview(iv_id):
    if session.get("role") != "student": return redirect(url_for("login"))
    slot = request.form.get("slot","")
    db = get_db()
    db.execute("UPDATE interviews SET confirmed_slot=?,status='confirmed' WHERE id=?", (slot, iv_id))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=applications")

@app.route("/student/upload/photo", methods=["POST"])
def upload_photo():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("photo")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "#profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_PHOTO: return redirect(url_for("student_dash") + "#profile")
    filename = f"photo_{session['uid']}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    db = get_db()
    db.execute("UPDATE students SET photo=? WHERE id=?", (filename, session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=profile")

@app.route("/student/upload/resume", methods=["POST"])
def upload_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("resume")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "?section=profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_RESUME: return redirect(url_for("student_dash") + "?section=profile")
    filename = f"resume_{session['uid']}_{secure_filename(f.filename)}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    uploaded_on = datetime.now().strftime("%d %b %Y")
    db = get_db()
    db.execute("UPDATE students SET resume=?, resume_uploaded_on=? WHERE id=?",
               (filename, uploaded_on, session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=profile")

@app.route("/student/resume/download")
def download_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    row = db.execute("SELECT resume FROM students WHERE id=?", (session["uid"],)).fetchone()
    db.close()
    if not row or not row["resume"]: return "No resume uploaded", 404
    return send_from_directory(UPLOAD_FOLDER, row["resume"], as_attachment=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  COMPANY / RECRUITER ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/company")
def company_dash():
    if session.get("role") != "company": return redirect(url_for("login"))
    db = get_db()
    company_row = db.execute("SELECT * FROM companies WHERE id=?", (session["uid"],)).fetchone()
    company = dict(company_row) if company_row else {}
    drives  = db.execute("""
        SELECT d.*,
               COUNT(a.id) as app_count,
               COUNT(DISTINCT CASE WHEN a.status='selected'  THEN a.student_id END) as selected_count,
               COUNT(DISTINCT CASE WHEN a.status='interview' THEN a.student_id END) as interview_count,
               SUM(CASE WHEN a.status='eligible'  THEN 1 ELSE 0 END) as eligible_count,
               SUM(CASE WHEN a.status='test'       THEN 1 ELSE 0 END) as test_count,
               SUM(CASE WHEN a.status='rejected'   THEN 1 ELSE 0 END) as rejected_count
        FROM drives d LEFT JOIN applications a ON a.drive_id=d.id
        WHERE d.company_id=? GROUP BY d.id ORDER BY d.created DESC
    """, (session["uid"],)).fetchall()
    total_apps       = sum(d["app_count"]       or 0 for d in drives)
    total_selected   = sum(d["selected_count"]  or 0 for d in drives)
    total_interviews = sum(d["interview_count"] or 0 for d in drives)
    stats = {"drives":len(drives),"apps":total_apps,"selected":total_selected,
             "interviews":total_interviews,"offers":total_selected}
    status_rows = db.execute("""SELECT a.status, COUNT(*) as cnt
        FROM applications a JOIN drives d ON a.drive_id=d.id
        WHERE d.company_id=? GROUP BY a.status""", (session["uid"],)).fetchall()
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for r in status_rows:
        if r["status"] in status_counts: status_counts[r["status"]] = r["cnt"]
    timeline = db.execute("""SELECT DATE(a.applied_on) as day, COUNT(*) as cnt,
               SUM(CASE WHEN a.status IN ('eligible','test','interview','selected') THEN 1 ELSE 0 END) as shortlisted
        FROM applications a JOIN drives d ON a.drive_id=d.id
        WHERE d.company_id=? GROUP BY DATE(a.applied_on) ORDER BY day ASC LIMIT 30""",
        (session["uid"],)).fetchall()
    db.close()
    return render_template("company_dash.html", company=company, drives=drives, stats=stats,
        status_counts=status_counts,
        timeline_labels=[r["day"] for r in timeline],
        timeline_apps=[r["cnt"] for r in timeline],
        timeline_shortlist=[r["shortlisted"] for r in timeline])

@app.route("/drive/create", methods=["GET","POST"])
def create_drive():
    if session.get("role") != "company": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        db = get_db()
        salary_min = float(f.get("salary_min") or f.get("salary") or 0)
        salary_max = float(f.get("salary_max") or salary_min)
        salary     = salary_max
        db.execute("""INSERT INTO drives
            (company_id,title,role,location,salary,salary_min,salary_max,job_type,experience_level,
             deadline,description,requirements,req_cgpa,req_degree,req_skills,req_year,is_public)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session["uid"],f["title"],f["role"],f["location"],salary,salary_min,salary_max,
             f.get("job_type","Full-time"),f.get("experience_level","Entry Level"),
             f["deadline"],f.get("description",""),f.get("requirements",""),
             float(f.get("req_cgpa",0) or 0),f.get("req_degree",""),
             f.get("req_skills",""),int(f.get("req_year",0) or 0),
             1 if f.get("is_public") else 0))
        db.commit(); db.close()
        return redirect(url_for("company_dash") + "?section=drives")
    return render_template("create_drive.html")

@app.route("/drive/<int:drive_id>/toggle", methods=["POST"])
def toggle_drive(drive_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    db = get_db()
    d = db.execute("SELECT status FROM drives WHERE id=? AND company_id=?",
                   (drive_id, session["uid"])).fetchone()
    if d:
        new_status = "closed" if d["status"] == "active" else "active"
        db.execute("UPDATE drives SET status=? WHERE id=?", (new_status, drive_id))
        db.commit()
    db.close()
    return redirect(url_for("company_dash") + "?section=drives")

@app.route("/drive/<int:drive_id>/applicants")
def drive_applicants(drive_id):
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    db = get_db()
    if session.get("role") == "company":
        drive = db.execute("SELECT * FROM drives WHERE id=? AND company_id=?",
                           (drive_id, session["uid"])).fetchone()
    else:
        drive = db.execute("SELECT d.*,c.name as company_name FROM drives d JOIN companies c ON d.company_id=c.id WHERE d.id=?",
                           (drive_id,)).fetchone()
    if not drive: db.close(); return redirect(url_for("company_dash"))
    sort_by = request.args.get("sort","ai_score")
    status_filter = request.args.get("status","")
    q_filter = request.args.get("q","")
    query = """SELECT a.*, s.name as sname, s.email as semail, s.cgpa, s.branch,
                      s.degree, s.skills, s.phone, s.resume,
                      i.id as iv_id, i.proposed_slots, i.confirmed_slot, i.status as iv_status
               FROM applications a JOIN students s ON a.student_id=s.id
               LEFT JOIN interviews i ON i.application_id=a.id
               WHERE a.drive_id=?"""
    params = [drive_id]
    if status_filter: query += " AND a.status=?"; params.append(status_filter)
    if q_filter: query += " AND (s.name LIKE ? OR s.email LIKE ?)"; params += [f"%{q_filter}%"]*2
    order = "a.ai_score DESC" if sort_by == "ai_score" else "a.applied_on DESC"
    query += f" ORDER BY {order}"
    apps = db.execute(query, params).fetchall()
    db.close()
    return render_template("drive_applicants.html", drive=drive, apps=apps,
                           sort_by=sort_by, status_filter=status_filter, q_filter=q_filter)

@app.route("/app/<int:app_id>/status", methods=["POST"])
def update_status(app_id):
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    status = request.form.get("status")
    db = get_db()
    db.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    db.commit()
    row = db.execute("SELECT drive_id FROM applications WHERE id=?", (app_id,)).fetchone()
    db.close()
    notify_status_change(app_id, status)
    return redirect(url_for("drive_applicants", drive_id=row["drive_id"]))

@app.route("/app/<int:app_id>/bulk_status", methods=["POST"])
def bulk_update_status(app_id):
    """Used for bulk shortlist / reject from applicants page."""
    if session.get("role") not in ("company","admin"): return jsonify({"ok":False})
    status = request.json.get("status")
    ids    = request.json.get("ids", [])
    db = get_db()
    for aid in ids:
        db.execute("UPDATE applications SET status=? WHERE id=?", (status, aid))
        db.commit()
        notify_status_change(aid, status)
    db.close()
    return jsonify({"ok":True})

# ── Interview scheduling ──────────────────────────────────────────────────────
@app.route("/app/<int:app_id>/schedule_interview", methods=["POST"])
def schedule_interview(app_id):
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    slots      = request.form.get("slots","")
    interviewer= request.form.get("interviewer","")
    notes      = request.form.get("notes","")
    db = get_db()
    existing = db.execute("SELECT id FROM interviews WHERE application_id=?", (app_id,)).fetchone()
    if existing:
        db.execute("UPDATE interviews SET proposed_slots=?,interviewer=?,notes=?,status='pending' WHERE application_id=?",
                   (slots, interviewer, notes, app_id))
    else:
        db.execute("INSERT INTO interviews (application_id,proposed_slots,interviewer,notes) VALUES (?,?,?,?)",
                   (app_id, slots, interviewer, notes))
    db.execute("UPDATE applications SET status='interview' WHERE id=?", (app_id,))
    db.commit()
    row = db.execute("SELECT drive_id FROM applications WHERE id=?", (app_id,)).fetchone()
    db.close()
    notify_status_change(app_id, "interview")
    return redirect(url_for("drive_applicants", drive_id=row["drive_id"]))

# ── Offer letter generation ───────────────────────────────────────────────────
@app.route("/offer/generate", methods=["GET","POST"])
def generate_offer():
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        db = get_db()
        app_id = int(f.get("application_id",0))
        app_row = db.execute("""SELECT a.*, s.name, s.email, s.telegram_chat_id,
                                d.title, d.role, d.job_type, d.location, c.name as cname
                                FROM applications a JOIN students s ON a.student_id=s.id
                                JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
                                WHERE a.id=?""", (app_id,)).fetchone()
        if not app_row: db.close(); return redirect(url_for("company_dash"))
        offer_id = db.execute("""INSERT INTO offers
            (application_id,student_id,drive_id,company_id,role,salary,joining_date,template,letter_type,custom_fields)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (app_id, app_row["student_id"], app_row["drive_id"],
             app_row["company_id"] if "company_id" in app_row.keys() else session["uid"],
             f.get("role",""), f.get("salary",""), f.get("joining_date",""),
             f.get("template","standard"), f.get("letter_type","offer"),
             f.get("custom_fields",""))).lastrowid
        db.execute("UPDATE applications SET status='selected' WHERE id=?", (app_id,))
        db.commit()
        # ── Dedicated offer letter notification ───────────────────────────────
        role_val        = f.get("role", "")
        salary_val      = f.get("salary", "")
        joining_val     = f.get("joining_date", "")
        company_val     = app_row["cname"]
        candidate_name  = app_row["name"]
        # 1) In-app notification
        notif_title = "🎉 Offer Letter Ready"
        notif_msg   = (f"Congratulations {candidate_name}! Your offer letter from {company_val} is ready. "
                       f"Role: {role_val} | CTC: {salary_val} | Joining: {joining_val}.")
        send_notification(app_row["student_id"], notif_title, notif_msg, "success")
        # 2) HTML email with offer summary table
        email_html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;">
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;border-radius:12px 12px 0 0;">
    <h1 style="color:#ffffff;margin:0;font-size:22px;">🎉 Congratulations, {candidate_name}!</h1>
    <p style="color:#e0e7ff;margin:8px 0 0;font-size:14px;">Your offer letter is ready for download.</p>
  </div>
  <div style="padding:28px 32px;border:1px solid #e2e5f0;border-top:none;border-radius:0 0 12px 12px;">
    <p style="color:#374151;font-size:14px;margin-top:0;">
      We are delighted to inform you that <strong>{company_val}</strong> has extended a formal offer to you.
      Please find the key details of your offer below:
    </p>
    <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
      <tr style="background:#eef2ff;">
        <td style="padding:10px 14px;font-weight:700;color:#4f46e5;border:1px solid #e2e5f0;width:40%;">Position</td>
        <td style="padding:10px 14px;color:#111827;border:1px solid #e2e5f0;"><strong>{role_val}</strong></td>
      </tr>
      <tr>
        <td style="padding:10px 14px;font-weight:700;color:#4f46e5;border:1px solid #e2e5f0;">Company</td>
        <td style="padding:10px 14px;color:#111827;border:1px solid #e2e5f0;">{company_val}</td>
      </tr>
      <tr style="background:#f8f9ff;">
        <td style="padding:10px 14px;font-weight:700;color:#4f46e5;border:1px solid #e2e5f0;">CTC / Salary</td>
        <td style="padding:10px 14px;color:#059669;font-weight:700;border:1px solid #e2e5f0;">{salary_val}</td>
      </tr>
      <tr>
        <td style="padding:10px 14px;font-weight:700;color:#4f46e5;border:1px solid #e2e5f0;">Date of Joining</td>
        <td style="padding:10px 14px;color:#111827;border:1px solid #e2e5f0;"><strong>{joining_val}</strong></td>
      </tr>
    </table>
    <p style="color:#6b7280;font-size:13px;">
      Please log in to <strong>SmartHire AI</strong> to download your official offer letter PDF and complete the e-signature process.
    </p>
    <div style="margin-top:24px;padding:14px 18px;background:#f0fdf4;border-left:4px solid #059669;border-radius:6px;">
      <p style="margin:0;color:#065f46;font-size:13px;font-weight:600;">
        ✅ Next steps: Download your offer letter → Review the terms → Complete e-signature → Confirm your joining date.
      </p>
    </div>
    <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
      This is an automated notification from SmartHire AI. Please do not reply to this email.
    </p>
  </div>
</div>"""
        send_email_notification(
            app_row["email"],
            f"[SmartHire AI] 🎉 Offer Letter Ready – {company_val}",
            email_html
        )
        # 3) Telegram message
        tg_msg = (
            f"🎉 <b>Offer Letter Ready!</b>\n\n"
            f"Congratulations, <b>{candidate_name}</b>!\n\n"
            f"📋 <b>Role:</b> {role_val}\n"
            f"🏢 <b>Company:</b> {company_val}\n"
            f"💰 <b>CTC / Salary:</b> {salary_val}\n"
            f"📅 <b>Joining Date:</b> {joining_val}\n\n"
            f"Log in to SmartHire AI to download your offer letter and complete the e-signature."
        )
        send_telegram(app_row["telegram_chat_id"], tg_msg)
        # 4) Also fire the generic status-change notification
        notify_status_change(app_id, "selected")
        db.close()
        return redirect(url_for("download_offer", offer_id=offer_id))
    # GET — show form
    db = get_db()
    if session.get("role") == "company":
        apps = db.execute("""SELECT a.id, s.name, d.title, d.role FROM applications a
                             JOIN students s ON a.student_id=s.id JOIN drives d ON a.drive_id=d.id
                             WHERE d.company_id=? AND a.status IN ('interview','eligible','selected')
                             ORDER BY a.applied_on DESC""", (session["uid"],)).fetchall()
        company = db.execute("SELECT * FROM companies WHERE id=?", (session["uid"],)).fetchone()
    else:
        apps = db.execute("""SELECT a.id, s.name, d.title, d.role, c.name as company_name
                             FROM applications a JOIN students s ON a.student_id=s.id
                             JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
                             WHERE a.status IN ('interview','eligible','selected')
                             ORDER BY a.applied_on DESC""").fetchall()
        company = None
    db.close()
    return render_template("generate_offer.html",
                           apps=[dict(a) for a in apps],
                           company=dict(company) if company else None,
                           default_template=(company["default_template"] if company and company["default_template"] else "standard"),
                           brand_color=(company["brand_color"] if company and company["brand_color"] else "#4f46e5"))

@app.route("/offer/<int:offer_id>/download")
def download_offer(offer_id):
    if session.get("role") not in ("company","admin","student"): return redirect(url_for("login"))
    db = get_db()
    offer = db.execute("""SELECT o.*, s.name as candidate_name, c.name as company_name,
                                 c.location, c.about
                          FROM offers o JOIN students s ON o.student_id=s.id
                          JOIN companies c ON o.company_id=c.id
                          WHERE o.id=?""", (offer_id,)).fetchone()
    db.close()
    if not offer: return "Not found", 404
    data = dict(offer)
    data['generated_on'] = data['generated_on'][:10] if data.get('generated_on') else datetime.now().strftime('%d %B %Y')
    buf = generate_offer_letter_pdf(data)
    fname = f"offer_{offer['candidate_name'].replace(' ','_')}_{offer_id}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)

# ── Relieving / Experience letter ─────────────────────────────────────────────
@app.route("/letter/generate", methods=["GET","POST"])
def generate_letter():
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    if request.method == "POST":
        f    = request.form
        data = {
            "candidate_name": f.get("candidate_name",""),
            "company_name":   f.get("company_name",""),
            "role":           f.get("role",""),
            "from_date":      f.get("from_date",""),
            "to_date":        f.get("to_date",""),
            "hr_name":        f.get("hr_name","HR Manager"),
            "hr_title":       f.get("hr_title","Human Resources"),
            "letter_type":    f.get("letter_type","relieving"),
            "generated_on":   datetime.now().strftime("%d %B %Y"),
        }
        buf   = generate_relieving_letter_pdf(data)
        fname = f"{data['letter_type']}_{data['candidate_name'].replace(' ','_')}.pdf"
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)
    db = get_db()
    if session.get("role") == "company":
        company = db.execute("SELECT * FROM companies WHERE id=?", (session["uid"],)).fetchone()
        students = db.execute("""SELECT DISTINCT s.name, s.email, d.role FROM applications a
                                 JOIN students s ON a.student_id=s.id JOIN drives d ON a.drive_id=d.id
                                 WHERE d.company_id=? AND a.status='selected'""",
                              (session["uid"],)).fetchall()
    else:
        company  = None
        students = db.execute("""SELECT DISTINCT s.name, s.email, d.role, c.name as company_name
                                 FROM applications a JOIN students s ON a.student_id=s.id
                                 JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
                                 WHERE a.status='selected'""").fetchall()
    db.close()
    return render_template("generate_letter.html",
                           company=dict(company) if company else None,
                           students=[dict(s) for s in students])

# ── Payslip ───────────────────────────────────────────────────────────────────
@app.route("/payslip/generate", methods=["GET","POST"])
def generate_payslip():
    if session.get("role") not in ("company","admin"): return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        # Compute net pay from form inputs
        try:
            gross    = float(f.get("basic",0))+float(f.get("hra",0))+float(f.get("special",0))+float(f.get("other_allow",0))
            total_d  = float(f.get("pf",0))+float(f.get("prof_tax",0))+float(f.get("tds",0))+float(f.get("other_ded",0))
            net_pay  = gross - total_d
        except ValueError:
            gross = total_d = net_pay = 0
        data = dict(f)
        data.update({"gross":str(round(gross,2)),"total_ded":str(round(total_d,2)),"net_pay":str(round(net_pay,2))})
        buf   = generate_payslip_pdf(data)
        fname = f"payslip_{f.get('candidate_name','').replace(' ','_')}_{f.get('month','')}.pdf"
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)
    db = get_db()
    if session.get("role") == "company":
        company = db.execute("SELECT * FROM companies WHERE id=?", (session["uid"],)).fetchone()
        emp_list = db.execute("""SELECT DISTINCT s.name, s.email, d.role FROM applications a
                                 JOIN students s ON a.student_id=s.id JOIN drives d ON a.drive_id=d.id
                                 WHERE d.company_id=? AND a.status='selected'""",
                              (session["uid"],)).fetchall()
    else:
        company  = None
        emp_list = db.execute("""SELECT DISTINCT s.name, s.email, d.role, c.name as company_name
                                 FROM applications a JOIN students s ON a.student_id=s.id
                                 JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
                                 WHERE a.status='selected'""").fetchall()
    db.close()
    return render_template("generate_payslip.html",
                           company=dict(company) if company else None,
                           emp_list=[dict(e) for e in emp_list])

@app.route("/company/profile/update", methods=["POST"])
def company_profile_update():
    if session.get("role") != "company": return redirect(url_for("login"))
    f = request.form
    db = get_db()
    db.execute("""UPDATE companies SET name=?,phone=?,location=?,industry=?,website=?,about=?,
                  default_template=?,brand_color=? WHERE id=?""",
               (f.get("name"),f.get("phone"),f.get("location"),f.get("industry"),
                f.get("website",""),f.get("about",""),
                f.get("default_template","standard"),
                f.get("brand_color","#4f46e5"),
                session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("company_dash") + "?section=profiles")

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/admin")
def admin_dash():
    if session.get("role") != "admin": return redirect(url_for("login"))
    db = get_db()
    stats = {
        "students":  db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"],
        "companies": db.execute("SELECT COUNT(*) as c FROM companies").fetchone()["c"],
        "drives":    db.execute("SELECT COUNT(*) as c FROM drives").fetchone()["c"],
        "apps":      db.execute("SELECT COUNT(*) as c FROM applications").fetchone()["c"],
        "selected":  db.execute("SELECT COUNT(DISTINCT student_id) as c FROM applications WHERE status='selected'").fetchone()["c"],
    }
    placement_rate = min(round((stats["selected"]/stats["students"]*100),1),100.0) if stats["students"] else 0
    drives = db.execute("""SELECT d.*, c.name as company_name, COUNT(a.id) as app_count
        FROM drives d JOIN companies c ON d.company_id=c.id
        LEFT JOIN applications a ON a.drive_id=d.id
        GROUP BY d.id ORDER BY d.created DESC LIMIT 10""").fetchall()
    students = db.execute("""SELECT s.*, COUNT(a.id) as app_count, MAX(a.ai_score) as best_score
        FROM students s LEFT JOIN applications a ON a.student_id=s.id
        GROUP BY s.id ORDER BY s.created DESC""").fetchall()
    student_apps = {}
    for s in students:
        apps = db.execute("""SELECT a.status,a.ai_score,a.applied_on,d.title,d.role,c.name as company_name
            FROM applications a JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
            WHERE a.student_id=? ORDER BY a.applied_on DESC""", (s["id"],)).fetchall()
        student_apps[s["id"]] = [dict(a) for a in apps]
    companies = db.execute("""SELECT co.*,
               COUNT(DISTINCT d.id) as drive_count,
               COUNT(a.id) as app_count,
               COUNT(DISTINCT CASE WHEN a.status='selected' THEN a.student_id END) as selected_count
        FROM companies co LEFT JOIN drives d ON d.company_id=co.id
        LEFT JOIN applications a ON a.drive_id=d.id
        GROUP BY co.id ORDER BY co.created DESC""").fetchall()
    company_drives = {}; company_applicants = {}; company_selected = {}
    for co in companies:
        cid = co["id"]
        company_drives[cid] = db.execute("""SELECT d.*, COUNT(a.id) as app_count
            FROM drives d LEFT JOIN applications a ON a.drive_id=d.id
            WHERE d.company_id=? GROUP BY d.id ORDER BY d.created DESC""", (cid,)).fetchall()
        company_applicants[cid] = db.execute("""SELECT s.name,s.email,s.branch,s.cgpa,
            a.status,a.ai_score,a.applied_on,d.title as drive_title
            FROM applications a JOIN students s ON a.student_id=s.id
            JOIN drives d ON a.drive_id=d.id
            WHERE d.company_id=? ORDER BY a.applied_on DESC""", (cid,)).fetchall()
        company_selected[cid] = [r for r in company_applicants[cid] if r["status"]=="selected"]
    branch_stats = db.execute("""SELECT s.branch, COUNT(a.id) as placed
        FROM applications a JOIN students s ON a.student_id=s.id
        WHERE a.status='selected' GROUP BY s.branch ORDER BY placed DESC""").fetchall()
    monthly = db.execute("""SELECT strftime('%Y-%m', a.applied_on) as month,
        COUNT(*) as apps, SUM(CASE WHEN a.status='selected' THEN 1 ELSE 0 END) as placed
        FROM applications a GROUP BY month ORDER BY month ASC LIMIT 12""").fetchall()
    top_companies = db.execute("""SELECT c.name, COUNT(a.id) as hired
        FROM applications a JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
        WHERE a.status='selected' GROUP BY c.id ORDER BY hired DESC LIMIT 5""").fetchall()
    status_rows = db.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall()
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for r in status_rows:
        if r["status"] in status_counts: status_counts[r["status"]] = r["cnt"]
    recent_students  = db.execute("SELECT id,name,email,'student' as type,created FROM students ORDER BY created DESC LIMIT 5").fetchall()
    recent_companies = db.execute("SELECT id,name,email,'company' as type,created FROM companies ORDER BY created DESC LIMIT 5").fetchall()
    recent_regs = sorted(list(recent_students)+list(recent_companies), key=lambda x: x["created"], reverse=True)[:10]
    all_apps_for_offers = db.execute("""SELECT a.id, s.name, d.title, d.role, c.name as company_name
        FROM applications a JOIN students s ON a.student_id=s.id
        JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
        WHERE a.status IN ('interview','eligible','selected')
        ORDER BY a.applied_on DESC""").fetchall()
    all_selected = db.execute("""SELECT DISTINCT s.name, s.email, d.role, c.name as company_name
        FROM applications a JOIN students s ON a.student_id=s.id
        JOIN drives d ON a.drive_id=d.id JOIN companies c ON d.company_id=c.id
        WHERE a.status='selected'""").fetchall()
    db.close()
    return render_template("admin_dash.html",
        stats=stats, placement_rate=placement_rate,
        drives=drives, students=students, companies=companies,
        student_apps=student_apps, company_drives=company_drives,
        company_applicants=company_applicants, company_selected=company_selected,
        branch_stats=branch_stats,
        monthly_labels=[r["month"] for r in monthly],
        monthly_apps=[r["apps"] for r in monthly],
        monthly_placed=[r["placed"] for r in monthly],
        top_companies=top_companies, status_counts=status_counts, recent_regs=recent_regs,
        all_apps_for_offers=all_apps_for_offers, all_selected=all_selected)

@app.route("/admin/register/student", methods=["GET","POST"])
def admin_register_student():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form; db = get_db()
        try:
            db.execute("""INSERT INTO students (name,email,pwd,phone,dob,branch,degree,year,cgpa,p12,p10,skills,bio)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],f["dob"],f["branch"],f["degree"],
                 int(f["year"]),float(f["cgpa"]),float(f["p12"]),float(f["p10"]),
                 f.get("skills",""),f.get("bio","")))
            db.commit(); db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&msg=student_added")
        except Exception as e:
            db.close()
            return render_template("admin_dash.html", reg_error=str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

@app.route("/admin/register/company", methods=["GET","POST"])
def admin_register_company():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form; db = get_db()
        try:
            db.execute("""INSERT INTO companies (name,email,pwd,phone,location,industry,website,about)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],
                 f["location"],f["industry"],f.get("website",""),f.get("about","")))
            db.commit(); db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&msg=company_added")
        except Exception as e:
            db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&err="+str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

@app.route("/admin/drives")
def admin_all_drives():
    if session.get("role") != "admin": return redirect(url_for("login"))
    db = get_db()
    drives = db.execute("""SELECT d.*, c.name as company_name, COUNT(a.id) as app_count
        FROM drives d JOIN companies c ON d.company_id=c.id
        LEFT JOIN applications a ON a.drive_id=d.id
        GROUP BY d.id ORDER BY d.created DESC""").fetchall()
    db.close()
    return jsonify([dict(d) for d in drives])

# ── Admin student/company action routes ───────────────────────────────────────
@app.route("/admin/student/<int:sid>/action", methods=["POST"])
def admin_student_action(sid):
    if session.get("role") != "admin": return redirect(url_for("login"))
    action = request.form.get("action","")
    db = get_db()
    if action == "suspend":
        student = db.execute("SELECT suspended FROM students WHERE id=?", (sid,)).fetchone()
        if student:
            new_val = 0 if (student["suspended"] or 0) else 1
            db.execute("UPDATE students SET suspended=? WHERE id=?", (new_val, sid))
            db.commit()
    elif action == "delete":
        db.execute("DELETE FROM notifications WHERE student_id=?", (sid,))
        db.execute("DELETE FROM assessment_results WHERE student_id=?", (sid,))
        db.execute("DELETE FROM applications WHERE student_id=?", (sid,))
        db.execute("DELETE FROM students WHERE id=?", (sid,))
        db.commit()
    db.close()
    return redirect(url_for("admin_dash") + "?section=students")

@app.route("/admin/company/<int:cid>/action", methods=["POST"])
def admin_company_action(cid):
    if session.get("role") != "admin": return redirect(url_for("login"))
    action = request.form.get("action","")
    db = get_db()
    if action == "suspend":
        company = db.execute("SELECT suspended FROM companies WHERE id=?", (cid,)).fetchone()
        if company:
            new_val = 0 if (company["suspended"] or 0) else 1
            db.execute("UPDATE companies SET suspended=? WHERE id=?", (new_val, cid))
            db.commit()
    elif action == "delete":
        # Get all drive IDs for this company
        drive_ids = [r["id"] for r in db.execute("SELECT id FROM drives WHERE company_id=?", (cid,)).fetchall()]
        for did in drive_ids:
            app_ids = [r["id"] for r in db.execute("SELECT id FROM applications WHERE drive_id=?", (did,)).fetchall()]
            for aid in app_ids:
                db.execute("DELETE FROM interviews WHERE application_id=?", (aid,))
                db.execute("DELETE FROM offers WHERE application_id=?", (aid,))
            db.execute("DELETE FROM applications WHERE drive_id=?", (did,))
            db.execute("DELETE FROM assessments WHERE drive_id=?", (did,))
        db.execute("DELETE FROM drives WHERE company_id=?", (cid,))
        db.execute("DELETE FROM companies WHERE id=?", (cid,))
        db.commit()
    db.close()
    return redirect(url_for("admin_dash") + "?section=companies")

# ── AI API endpoints ──────────────────────────────────────────────────────────
@app.route("/ai/match/<int:drive_id>")
def ai_match(drive_id):
    if session.get("role") != "student": return jsonify({"error":"unauthorized"})
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drive   = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
    db.close()
    if not drive: return jsonify({"error":"not found"})
    score = ai_match_score(student, drive)
    req = [s.strip() for s in (drive["req_skills"] or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student["skills"] or "").split(",") if s.strip()]
    matched = [r for r in req if any(r.lower() in s or s in r.lower() for s in stu)]
    missing = [r for r in req if r not in matched]
    return jsonify({"score":score,"matched":matched,"missing":missing,"cgpa_ok":student["cgpa"]>=drive["req_cgpa"]})

@app.route("/ai/questions")
def get_questions():
    role  = request.args.get("role","Software Engineer")
    rtype = request.args.get("round","Technical")
    return jsonify({"questions":ai_questions(role,rtype),"role":role,"round":rtype})

@app.route("/ai/extract", methods=["POST"])
def extract_skills():
    text = request.json.get("text","")
    return jsonify({"skills":ai_extract_skills(text)})

@app.route("/ai/rank/<int:drive_id>")
def ai_rank_candidates(drive_id):
    """Return all candidates for a drive ranked by AI score."""
    if session.get("role") not in ("company","admin"): return jsonify({"error":"unauthorized"})
    db = get_db()
    apps = db.execute("""SELECT a.id, a.ai_score, s.name, s.email, s.cgpa, s.skills, a.status
        FROM applications a JOIN students s ON a.student_id=s.id
        WHERE a.drive_id=? ORDER BY a.ai_score DESC""", (drive_id,)).fetchall()
    db.close()
    return jsonify([dict(a) for a in apps])

@app.route("/chatbot", methods=["POST"])
def chatbot():
    msg = request.json.get("message","").lower()
    if any(w in msg for w in ["interview","schedule","when"]):
        reply = "Your interviews are listed in 'My Applications'. Check the status column for scheduled rounds."
    elif any(w in msg for w in ["eligible","qualify"]):
        reply = "Eligibility is checked automatically. The AI match score shows how well you fit each role."
    elif any(w in msg for w in ["score","match","ai"]):
        reply = "Your AI match score is based on CGPA, skills, degree, and year of passing vs job requirements."
    elif any(w in msg for w in ["job","drive","opening"]):
        reply = "Browse all active drives in 'Explore Drives' or on the public Job Board at /jobs."
    elif any(w in msg for w in ["offer","letter"]):
        reply = "Offer letters are generated by your recruiter. You'll be notified once one is ready."
    elif any(w in msg for w in ["status","applied"]):
        reply = "Track applications in 'My Applications'. Flow: Applied → Eligible → Test → Interview → Selected."
    elif any(w in msg for w in ["hello","hi","hey"]):
        reply = f"Hi {session.get('name','there')}! 👋 I'm SmartHire AI. Ask me about jobs, eligibility, or your applications."
    else:
        reply = "I can help with: job eligibility, application status, AI match scores, interview prep, and skill tips!"
    return jsonify({"reply":reply})

# ── Static file serving ───────────────────────────────────────────────────────
@app.route("/resume/<path:filename>")
def serve_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    init_db(); migrate_db()
    print("\n✅  SmartHire AI — Campus Hiring Management System")
    print("   Open: http://127.0.0.1:5001\n")
    app.run(debug=True, port=5001)
