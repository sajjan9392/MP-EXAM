"""Send one FCM notification to topic 'all' (Pariksha Sarthi).
Manual run: uses IN_TITLE / IN_BODY. Scheduled run: only if live/ changed in the last 24 h."""
import json, os, subprocess, sys
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

title, body = (os.environ.get('IN_TITLE') or '').strip(), (os.environ.get('IN_BODY') or '').strip()
if not title:
    log = subprocess.run(['git', 'log', '--since=24 hours ago', '--name-only', '--pretty=format:', '--', 'live/'],
                         capture_output=True, text=True).stdout.split()
    if not log:
        print('live/ me 24 ghante se koi update nahi — notification nahi bheja'); sys.exit(0)
    if any(f.startswith('live/ca-') for f in log):
        title, body = '📰 नया करंट अफेयर्स आ गया', 'आज का करंट अफेयर्स पढ़ें और क्विज़ दें — Pariksha Sarthi'
    else:
        title, body = '✅ प्रश्न बैंक अपडेट हुआ', 'नए और सुधरे प्रश्न ऐप में जुड़ गए हैं — अभ्यास शुरू करें'
body = body or 'Pariksha Sarthi'
info = json.loads(os.environ['SA'])
cred = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/firebase.messaging'])
cred.refresh(Request())
msg = {'message': {'topic': 'all', 'notification': {'title': title, 'body': body},
                   'android': {'priority': 'NORMAL', 'ttl': '86400s'}}}
r = requests.post(f"https://fcm.googleapis.com/v1/projects/{info['project_id']}/messages:send",
                  headers={'Authorization': 'Bearer ' + cred.token}, json=msg, timeout=30)
print(r.status_code, r.text[:300]); r.raise_for_status()
