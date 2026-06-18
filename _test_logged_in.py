import requests
base = 'http://127.0.0.1:5001'
s = requests.Session()

# Login as student
r = s.post(base + '/login', data={'email': 'arjun.sharma@student.edu', 'pwd': 'pass@123', 'role': 'student'})
print('Student login:', r.status_code, r.url)

tests = [
    ('Student Tracker',       '/student/tracker'),
    ('Student Dashboard',     '/student'),
    ('Job Board',             '/jobs'),
]
for name, path in tests:
    r = s.get(base + path, timeout=5)
    print(f'  {name}: {r.status_code}', 'OK' if r.status_code == 200 else 'FAIL')

# Resume parse (no resume uploaded yet — should return error JSON)
r = s.post(base + '/student/resume/parse', data={})
print('  Resume parse (no file):', r.status_code, r.json())

s2 = requests.Session()
r = s2.post(base + '/login', data={'email': 'hr@tcs.com', 'pwd': 'tcs@123', 'role': 'company'})
print('\nCompany login:', r.status_code, r.url)

company_tests = [
    ('Company Dashboard',     '/company'),
    ('Bulk Upload Page',      '/bulk/upload'),
    ('Create Assessment',     '/assessment/create'),
    ('Analytics',             '/analytics'),
    ('Offer Generate',        '/offer/generate'),
    ('Letter Generate',       '/letter/generate'),
    ('Payslip Generate',      '/payslip/generate'),
]
for name, path in company_tests:
    r = s2.get(base + path, timeout=5)
    print(f'  {name}: {r.status_code}', 'OK' if r.status_code == 200 else 'FAIL')

# Admin tests
s3 = requests.Session()
r = s3.post(base + '/login', data={'email': 'admin@smarthire.ai', 'pwd': 'admin123', 'role': 'admin'})
print('\nAdmin login:', r.status_code, r.url)
r = s3.get(base + '/analytics', timeout=5)
print('  Admin Analytics:', r.status_code, 'OK' if r.status_code == 200 else 'FAIL')
r = s3.get(base + '/admin', timeout=5)
print('  Admin Dashboard:', r.status_code, 'OK' if r.status_code == 200 else 'FAIL')

print('\nAll done.')
