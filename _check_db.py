import sqlite3
conn = sqlite3.connect('smarthire.db')
sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
tables = [r[0] for r in conn.execute(sql).fetchall()]
print('All tables:', tables)
new_tables = ['assessments','assessment_results','bulk_imports','reference_checks','offer_signatures']
for t in new_tables:
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info({t})').fetchall()]
    status = 'OK' if cols else 'MISSING'
    print(f'  {status}: {t} -> {cols}')
conn.close()
