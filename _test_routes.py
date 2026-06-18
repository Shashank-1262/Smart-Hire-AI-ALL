import requests
s = requests.Session()
routes = [
    '/jobs', '/student/tracker', '/analytics', '/bulk/upload',
    '/assessment/create', '/offer/generate', '/letter/generate',
    '/payslip/generate', '/reference/bad-token', '/offer/sign/bad-token',
]
base = 'http://127.0.0.1:5001'
all_ok = True
for path in routes:
    r = s.get(base + path, allow_redirects=False, timeout=5)
    ok = r.status_code in (200, 302, 404)
    tag = 'OK  ' if ok else 'FAIL'
    if not ok:
        all_ok = False
    print(tag, r.status_code, path)
print('ALL PASSED' if all_ok else 'SOME FAILED')
