import sqlite3
import os
from datetime import datetime, timedelta
import random

DB = os.path.join(os.path.dirname(__file__), "smarthire.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ── Check existing data ────────────────────────────────────────────────────────
def check_existing(conn):
    c = conn.cursor()
    students  = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    companies = c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    drives    = c.execute("SELECT COUNT(*) FROM drives").fetchone()[0]
    apps      = c.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    print("=" * 55)
    print("EXISTING DATA")
    print(f"  Students    : {students}")
    print(f"  Companies   : {companies}")
    print(f"  Drives      : {drives}")
    print(f"  Applications: {apps}")
    print("=" * 55)
    return {"students": students, "companies": companies, "drives": drives, "apps": apps}

# ── Companies ─────────────────────────────────────────────────────────────────
COMPANIES = [
    ("TCS", "hr@tcs.com", "tcs@123", "1800-209-3111", "Mumbai, Maharashtra",
     "IT Services", "https://www.tcs.com",
     "Tata Consultancy Services is a global IT services, consulting and business solutions organization."),
    ("Infosys", "careers@infosys.com", "infosys@123", "1800-425-4968", "Bengaluru, Karnataka",
     "IT Services", "https://www.infosys.com",
     "Infosys is a global leader in next-generation digital services and consulting."),
    ("Wipro", "talent@wipro.com", "wipro@123", "1800-102-5799", "Bengaluru, Karnataka",
     "IT Services", "https://www.wipro.com",
     "Wipro Limited is a leading global information technology, consulting and business process services company."),
    ("Google", "campus@google.com", "google@123", "+1-650-253-0000", "Hyderabad, Telangana",
     "Technology", "https://careers.google.com",
     "Google LLC is an American multinational technology company focusing on search engine, cloud computing, and AI."),
    ("Microsoft", "mscampus@microsoft.com", "msft@123", "+1-425-882-8080", "Hyderabad, Telangana",
     "Technology", "https://careers.microsoft.com",
     "Microsoft Corporation is an American multinational technology corporation producing software, electronics, and cloud services."),
]

# ── Students ──────────────────────────────────────────────────────────────────
STUDENTS = [
    # (name, email, pwd, phone, dob, branch, degree, year, cgpa, p12, p10, skills, bio, gender, location)
    ("Arjun Sharma",    "arjun.sharma@student.edu",   "pass@123", "9876543210", "2002-03-15",
     "CSE", "B.Tech", 4, 8.7, 88.4, 91.2,
     "Python,Java,Machine Learning,SQL,Django,Git",
     "Passionate about AI and backend development.", "Male", "Delhi"),
    ("Priya Nair",      "priya.nair@student.edu",     "pass@123", "9876543211", "2002-07-22",
     "CSE", "B.Tech", 4, 9.1, 92.0, 89.5,
     "Python,React,Node.js,MongoDB,REST API,Docker",
     "Full-stack developer with a love for clean UI.", "Female", "Kochi"),
    ("Rahul Verma",     "rahul.verma@student.edu",    "pass@123", "9876543212", "2001-11-05",
     "IT", "B.Tech", 4, 7.8, 80.0, 85.0,
     "Java,Spring Boot,MySQL,Git,Linux",
     "Backend enthusiast, loves building scalable systems.", "Male", "Pune"),
    ("Sneha Reddy",     "sneha.reddy@student.edu",    "pass@123", "9876543213", "2002-01-30",
     "IT", "B.Tech", 4, 8.3, 85.5, 87.0,
     "JavaScript,React,HTML,CSS,TypeScript,Figma",
     "UI/UX focused frontend developer.", "Female", "Hyderabad"),
    ("Karthik Menon",   "karthik.menon@student.edu",  "pass@123", "9876543214", "2001-09-18",
     "ECE", "B.Tech", 4, 7.5, 78.0, 82.0,
     "C,C++,Embedded Systems,Python,MATLAB",
     "Interested in IoT and embedded systems.", "Male", "Chennai"),
    ("Divya Patel",     "divya.patel@student.edu",    "pass@123", "9876543215", "2002-05-12",
     "ECE", "B.Tech", 4, 8.0, 83.0, 88.5,
     "Python,Data Science,NumPy,Pandas,Tableau",
     "Data enthusiast with strong analytical skills.", "Female", "Ahmedabad"),
    ("Amit Kumar",      "amit.kumar@student.edu",     "pass@123", "9876543216", "2001-12-25",
     "MECH", "B.Tech", 4, 7.2, 75.0, 79.0,
     "AutoCAD,SolidWorks,MATLAB,Python,Excel",
     "Mechanical engineer exploring data analytics.", "Male", "Jaipur"),
    ("Pooja Singh",     "pooja.singh@student.edu",    "pass@123", "9876543217", "2002-08-08",
     "MECH", "B.Tech", 4, 7.6, 79.5, 83.0,
     "Python,Excel,Power BI,SQL,AutoCAD",
     "Bridging mechanical engineering with data science.", "Female", "Lucknow"),
    ("Vikram Iyer",     "vikram.iyer@student.edu",    "pass@123", "9876543218", "2001-06-14",
     "EEE", "B.Tech", 4, 8.5, 87.0, 90.0,
     "Python,MATLAB,C,Embedded Systems,AWS",
     "Electrical engineer with cloud computing interest.", "Male", "Bengaluru"),
    ("Ananya Bose",     "ananya.bose@student.edu",    "pass@123", "9876543219", "2002-04-03",
     "EEE", "B.Tech", 4, 9.3, 94.0, 92.5,
     "Python,Machine Learning,TensorFlow,Deep Learning,NLP",
     "AI researcher passionate about neural networks.", "Female", "Kolkata"),
]

# ── Drives (per company: 3-5 drives) ─────────────────────────────────────────
# company_name -> list of (title, role, location, salary, deadline_offset_days,
#                          description, req_cgpa, req_degree, req_skills, req_year, status, created_offset)
DRIVES_TEMPLATE = {
    "TCS": [
        ("TCS NQT 2025 – Software Engineer", "Software Engineer",
         "Pan India", 350000, 60,
         "TCS National Qualifier Test for fresh graduates. Roles in application development and maintenance.",
         6.5, "B.Tech", "Python,Java,SQL", 4, "active", -90),
        ("TCS Digital – Full Stack Developer", "Full Stack Developer",
         "Hyderabad", 700000, 45,
         "Premium hiring for full-stack roles. Work on cutting-edge digital transformation projects.",
         7.5, "B.Tech", "React,Node.js,MongoDB,REST API", 4, "active", -60),
        ("TCS Research – Data Analyst", "Data Analyst",
         "Pune", 550000, -10,
         "Analyze large datasets to drive business insights. Strong SQL and Python skills required.",
         7.0, "B.Tech", "Python,SQL,Pandas,Tableau", 4, "closed", -120),
        ("TCS BPS – Business Analyst", "Business Analyst",
         "Chennai", 420000, 30,
         "Support business process transformation using data-driven insights.",
         6.5, "B.Tech", "Excel,SQL,Power BI", 4, "active", -45),
    ],
    "Infosys": [
        ("Infosys InfyTQ – Systems Engineer", "Systems Engineer",
         "Bengaluru", 380000, 50,
         "Entry-level systems engineering role. Training provided in Java, Python, and cloud technologies.",
         6.5, "B.Tech", "Java,Python,SQL,Git", 4, "active", -80),
        ("Infosys Power Programmer", "Software Developer",
         "Pune", 800000, 40,
         "Elite track for top performers. Work on AI/ML and cloud-native applications.",
         8.0, "B.Tech", "Python,Machine Learning,AWS,Docker", 4, "active", -55),
        ("Infosys – Cloud Engineer", "Cloud Engineer",
         "Hyderabad", 650000, -5,
         "Design and deploy cloud infrastructure on AWS and Azure.",
         7.5, "B.Tech", "AWS,Docker,Kubernetes,Linux", 4, "closed", -100),
        ("Infosys – Data Science Associate", "Data Scientist",
         "Bengaluru", 750000, 70,
         "Build predictive models and data pipelines for enterprise clients.",
         7.5, "B.Tech", "Python,Machine Learning,TensorFlow,SQL", 4, "active", -30),
    ],
    "Wipro": [
        ("Wipro WILP – Software Engineer", "Software Engineer",
         "Pan India", 360000, 55,
         "Work Integrated Learning Program. Earn while you learn with Wipro.",
         6.0, "B.Tech", "Java,C,SQL", 4, "active", -70),
        ("Wipro Turbo – Senior Developer", "Senior Software Developer",
         "Bengaluru", 650000, 35,
         "Fast-track program for high-potential candidates with strong coding skills.",
         7.5, "B.Tech", "Python,Java,Spring Boot,MySQL", 4, "active", -50),
        ("Wipro – QA Engineer", "QA Engineer",
         "Chennai", 420000, -15,
         "Manual and automated testing for enterprise applications.",
         6.5, "B.Tech", "Python,Selenium,SQL,Git", 4, "closed", -110),
    ],
    "Google": [
        ("Google STEP Intern – Software Engineering", "Software Engineering Intern",
         "Hyderabad", 1200000, 90,
         "Google's Student Training in Engineering Program. Work on real Google products.",
         8.5, "B.Tech", "Python,Java,C++,Data Structures,Algorithms", 4, "active", -40),
        ("Google – Associate Product Manager", "Associate Product Manager",
         "Hyderabad", 1800000, 75,
         "Drive product strategy and roadmap for Google's consumer products.",
         8.0, "B.Tech", "Python,SQL,Data Science,REST API", 4, "active", -35),
        ("Google – Machine Learning Engineer", "ML Engineer",
         "Hyderabad", 2200000, 80,
         "Build and deploy ML models at Google scale. Work with TensorFlow and Google Cloud.",
         8.5, "B.Tech", "Python,Machine Learning,TensorFlow,Deep Learning,NLP", 4, "active", -25),
        ("Google – Site Reliability Engineer", "SRE",
         "Hyderabad", 1900000, -20,
         "Ensure reliability and scalability of Google's infrastructure.",
         8.0, "B.Tech", "Python,Linux,Docker,Kubernetes,AWS", 4, "closed", -95),
        ("Google – UX Engineer", "UX Engineer",
         "Hyderabad", 1600000, 65,
         "Bridge design and engineering to create exceptional user experiences.",
         7.5, "B.Tech", "JavaScript,React,TypeScript,HTML,CSS,Figma", 4, "active", -20),
    ],
    "Microsoft": [
        ("Microsoft – Software Engineer II", "Software Engineer",
         "Hyderabad", 2000000, 85,
         "Build next-generation cloud services on Azure. Work with world-class engineers.",
         8.0, "B.Tech", "Python,Java,C++,Azure,Docker", 4, "active", -50),
        ("Microsoft – Data Engineer", "Data Engineer",
         "Hyderabad", 1700000, 70,
         "Design and build data pipelines for Microsoft's analytics platform.",
         7.5, "B.Tech", "Python,SQL,Azure,Spark,Pandas", 4, "active", -40),
        ("Microsoft – AI Research Intern", "AI Research Intern",
         "Hyderabad", 1500000, 60,
         "Conduct cutting-edge AI research with Microsoft Research India.",
         8.5, "B.Tech", "Python,Machine Learning,Deep Learning,TensorFlow,PyTorch", 4, "active", -30),
        ("Microsoft – DevOps Engineer", "DevOps Engineer",
         "Hyderabad", 1600000, -8,
         "Automate and streamline CI/CD pipelines for Microsoft products.",
         7.0, "B.Tech", "Docker,Kubernetes,Azure,Linux,Git", 4, "closed", -85),
    ],
}

# ── Insert helpers ────────────────────────────────────────────────────────────
def insert_companies(conn):
    c = conn.cursor()
    inserted = []
    skipped  = []
    for co in COMPANIES:
        name, email, pwd, phone, location, industry, website, about = co
        existing = c.execute("SELECT id FROM companies WHERE email=?", (email,)).fetchone()
        if existing:
            skipped.append(name)
            continue
        created = (datetime.now() - timedelta(days=random.randint(100, 200))).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO companies (name,email,pwd,phone,location,industry,website,about,created)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (name, email, pwd, phone, location, industry, website, about, created))
        inserted.append(name)
    conn.commit()
    return inserted, skipped


def insert_students(conn):
    c = conn.cursor()
    inserted = []
    skipped  = []
    for s in STUDENTS:
        name, email, pwd, phone, dob, branch, degree, year, cgpa, p12, p10, skills, bio, gender, location = s
        existing = c.execute("SELECT id FROM students WHERE email=?", (email,)).fetchone()
        if existing:
            skipped.append(name)
            continue
        created = (datetime.now() - timedelta(days=random.randint(60, 150))).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO students
                     (name,email,pwd,phone,dob,branch,degree,year,cgpa,p12,p10,skills,bio,gender,location,created)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (name, email, pwd, phone, dob, branch, degree, year, cgpa, p12, p10,
                   skills, bio, gender, location, created))
        inserted.append(name)
    conn.commit()
    return inserted, skipped


def insert_drives(conn):
    c = conn.cursor()
    inserted = []
    skipped  = []
    today = datetime.now()
    for company_name, drive_list in DRIVES_TEMPLATE.items():
        company = c.execute("SELECT id FROM companies WHERE name=?", (company_name,)).fetchone()
        if not company:
            print(f"  [WARN] Company '{company_name}' not found, skipping its drives.")
            continue
        cid = company[0]
        for d in drive_list:
            title, role, loc, salary, deadline_offset, desc, req_cgpa, req_degree, req_skills, req_year, status, created_offset = d
            existing = c.execute("SELECT id FROM drives WHERE company_id=? AND title=?", (cid, title)).fetchone()
            if existing:
                skipped.append(title)
                continue
            deadline = (today + timedelta(days=deadline_offset)).strftime("%Y-%m-%d")
            created  = (today + timedelta(days=created_offset)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""INSERT INTO drives
                         (company_id,title,role,location,salary,deadline,description,
                          req_cgpa,req_degree,req_skills,req_year,status,created)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (cid, title, role, loc, salary, deadline, desc,
                       req_cgpa, req_degree, req_skills, req_year, status, created))
            inserted.append(f"{company_name} – {title}")
    conn.commit()
    return inserted, skipped

def ai_match_score(student_row, drive_row):
    """Replicate the app's scoring logic."""
    score = 0
    cgpa     = student_row["cgpa"]
    req_cgpa = drive_row["req_cgpa"]
    if cgpa >= req_cgpa:
        score += 30
    elif cgpa >= req_cgpa - 0.5:
        score += 15

    req = [s.strip().lower() for s in (drive_row["req_skills"] or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student_row["skills"]   or "").split(",") if s.strip()]
    if req:
        matched = sum(1 for r in req if any(r in s or s in r for s in stu))
        score += int((matched / len(req)) * 40)
    else:
        score += 30

    if not drive_row["req_degree"] or student_row["degree"] == drive_row["req_degree"]:
        score += 20
    else:
        score += 5

    if not drive_row["req_year"] or student_row["year"] >= drive_row["req_year"]:
        score += 10
    return round(score, 1)


def insert_applications(conn):
    """
    Each student applies to 2-4 drives.
    Spread applied_on across 2024-01 to 2025-06 for timeline charts.
    Statuses spread across all 6 states.
    """
    c = conn.cursor()
    inserted = 0
    skipped  = 0

    all_students = c.execute("SELECT * FROM students").fetchall()
    all_drives   = c.execute("SELECT * FROM drives").fetchall()

    if not all_students or not all_drives:
        print("  [WARN] No students or drives found – skipping applications.")
        return 0, 0

    # Build a dict for easy lookup
    drives_by_id = {d["id"]: d for d in all_drives}

    # Status progression pool – spread realistically
    status_pool = (
        ["applied"] * 3 +
        ["eligible"] * 3 +
        ["test"] * 2 +
        ["interview"] * 2 +
        ["selected"] * 2 +
        ["rejected"] * 2
    )

    # Date range: 2024-01-01 to 2025-06-30
    start_date = datetime(2024, 1, 1)
    end_date   = datetime(2025, 6, 30)
    date_range_days = (end_date - start_date).days

    random.seed(42)  # reproducible

    for student in all_students:
        sid = student["id"]
        # Pick 2-4 drives to apply to
        num_apps = random.randint(2, 4)
        chosen_drives = random.sample(all_drives, min(num_apps, len(all_drives)))

        for drive in chosen_drives:
            did = drive["id"]
            existing = c.execute(
                "SELECT id FROM applications WHERE student_id=? AND drive_id=?", (sid, did)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            score  = ai_match_score(dict(student), dict(drive))
            status = random.choice(status_pool)
            # Spread applied_on across the date range
            offset   = random.randint(0, date_range_days)
            applied_on = (start_date + timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S")

            c.execute("""INSERT INTO applications (student_id, drive_id, status, ai_score, applied_on)
                         VALUES (?,?,?,?,?)""",
                      (sid, did, status, score, applied_on))
            inserted += 1

    conn.commit()
    return inserted, skipped

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(DB):
        print(f"[ERROR] Database not found at:\n  {DB}")
        return

    conn = get_db()

    print("\n📊 STEP 1 – Checking existing data...")
    check_existing(conn)

    print("\n🏢 STEP 2 – Inserting companies...")
    ins_co, skip_co = insert_companies(conn)
    for n in ins_co:   print(f"  ✅ Added   : {n}")
    for n in skip_co:  print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n🎓 STEP 3 – Inserting students...")
    ins_st, skip_st = insert_students(conn)
    for n in ins_st:   print(f"  ✅ Added   : {n}")
    for n in skip_st:  print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n📋 STEP 4 – Inserting drives...")
    ins_dr, skip_dr = insert_drives(conn)
    for n in ins_dr:   print(f"  ✅ Added   : {n}")
    for n in skip_dr:  print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n📝 STEP 5 – Inserting applications...")
    ins_ap, skip_ap = insert_applications(conn)
    print(f"  ✅ Added   : {ins_ap} applications")
    print(f"  ⏭  Skipped : {skip_ap} (already exist)")

    print("\n" + "=" * 55)
    print("FINAL SUMMARY")
    check_existing(conn)

    # Show application status breakdown
    c = conn.cursor()
    print("\nApplication status breakdown:")
    rows = c.execute(
        "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:<12}: {r[1]}")

    print("\nAI score range:")
    row = c.execute("SELECT MIN(ai_score), MAX(ai_score), ROUND(AVG(ai_score),1) FROM applications").fetchone()
    print(f"  Min={row[0]}  Max={row[1]}  Avg={row[2]}")

    print("\nApplications per month (sample):")
    rows = c.execute("""
        SELECT strftime('%Y-%m', applied_on) as month, COUNT(*) as cnt
        FROM applications GROUP BY month ORDER BY month LIMIT 10
    """).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]} applications")

    conn.close()
    print("\n✅ Seeding complete!")

if __name__ == "__main__":
    main()
