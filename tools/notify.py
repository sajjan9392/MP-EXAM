"""Send one FCM notification to topic 'all' (Pariksha Sarthi).
Manual run: uses IN_TITLE / IN_BODY. Push run (live/ca-index.json changed): only if the current-affairs date is new."""
import json, os, subprocess, sys
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

title, body = (os.environ.get('IN_TITLE') or '').strip(), (os.environ.get('IN_BODY') or '').strip()
if not title:
    # push run: only when this push brought a NEW current-affairs date (live/ca-index.json "updated" changed)
    def upd(txt):
        try: return (json.loads(txt).get('updated') or '').strip()
        except Exception: return ''
    try: now = upd(open('live/ca-index.json', encoding='utf-8').read())
    except Exception: now = ''
    before = (os.environ.get('BEFORE') or '').strip()
    old = ''
    if before and set(before) != {'0'}:
        old = upd(subprocess.run(['git', 'show', before + ':live/ca-index.json'], capture_output=True, text=True).stdout)
    if not now or now == old:
        print('current affairs ki nayi tarikh nahi (', old, '->', now, ') — notification nahi bheja'); sys.exit(0)
    MON = ['जनवरी', 'फरवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर']
    y, m, d = now.split('-')
    title = f'📰 {int(d)} {MON[int(m) - 1]} {y} का करंट अफेयर्स आ गया'
    body = 'आज सुबह की शुरुआत करंट अफेयर्स से करें — पढ़ें और क्विज़ दें'
body = body or 'Pariksha Sarthi'
info = json.loads(os.environ['SA'])
cred = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/firebase.messaging'])
cred.refresh(Request())
msg = {'message': {'topic': 'all', 'notification': {'title': title, 'body': body},
                   'android': {'priority': 'NORMAL', 'ttl': '86400s'}}}
r = requests.post(f"https://fcm.googleapis.com/v1/projects/{info['project_id']}/messages:send",
                  headers={'Authorization': 'Bearer ' + cred.token}, json=msg, timeout=30)
print(r.status_code, r.text[:300]); r.raise_for_status()
