import requests
base = 'http://127.0.0.1:5001'
s = requests.Session()
s.post(base + '/login', data={'email': 'hr@tcs.com', 'pwd': 'tcs@123', 'role': 'company'})

failing = ['/bulk/upload', '/assessment/create', '/offer/generate', '/letter/generate', '/payslip/generate']
for path in failing:
    r = s.get(base + path, timeout=5)
    if r.status_code != 200:
        # Find the error message in response
        text = r.text
        # Find Traceback or ValueError
        for keyword in ['jinja2', 'TemplateNotFound', 'Error', 'Traceback', 'KeyError', 'TypeError']:
            idx = text.lower().find(keyword.lower())
            if idx != -1:
                print(f'\n--- {path} ({r.status_code}) ---')
                print(text[max(0,idx-50):idx+300])
                break
        else:
            print(f'\n--- {path} ({r.status_code}) ---')
            print(text[:400])
