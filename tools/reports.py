"""Pariksha Sarthi — daily digest of 'गलती बताएँ' reports.
Reads new docs from Firestore `reports` (last DAYS days) with the FCM service account,
groups them by question and sends a private Telegram message to the admin (TG_ADMIN chat id).
Also writes reports.json (uploaded as a workflow artifact) so the question bank can be fixed.
If TG_ADMIN is not set yet, it prints the private chats that have messaged the bot (to find your chat id)."""
import glob, json, os, sys, time, datetime, requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

DAYS = float(os.environ.get('DAYS') or 1.05)
TOKEN = os.environ.get('TG_TOKEN', '')
ADMIN = (os.environ.get('TG_ADMIN') or '').strip()
TYPES = {'ans': 'उत्तर गलत', 'q': 'प्रश्न/विकल्प में गलती', 'exp': 'व्याख्या गलत', 'img': 'चित्र नहीं दिख रहा', 'other': 'अन्य'}

def tg(method, **kw):
    r = requests.post(f'https://api.telegram.org/bot{TOKEN}/{method}', json=kw, timeout=30)
    return r.json()

if not ADMIN:
    u = tg('getUpdates')
    seen = {}
    for x in u.get('result', []):
        m = x.get('message') or {}
        c = m.get('chat') or {}
        if c.get('type') == 'private':
            seen[c['id']] = (c.get('first_name', '') + ' ' + c.get('last_name', '')).strip() + ' @' + (c.get('username') or '')
    print('Bot:', '@' + (tg('getMe').get('result') or {}).get('username', '?'))
    print('TG_ADMIN not set. Private chats that messaged the bot:')
    for k, v in seen.items(): print(' ', k, v)
    if not seen: print('  (none — send "Hi" to the bot in Telegram and run again)')
    sys.exit(0)

sa = json.loads(os.environ['SA'])
cred = service_account.Credentials.from_service_account_info(sa, scopes=['https://www.googleapis.com/auth/datastore'])
cred.refresh(Request())
proj = sa['project_id']
since = datetime.datetime.utcnow() - datetime.timedelta(days=DAYS)
q = {'structuredQuery': {'from': [{'collectionId': 'reports'}],
     'where': {'fieldFilter': {'field': {'fieldPath': 'ts'}, 'op': 'GREATER_THAN_OR_EQUAL',
               'value': {'timestampValue': since.strftime('%Y-%m-%dT%H:%M:%SZ')}}},
     'orderBy': [{'field': {'fieldPath': 'ts'}}], 'limit': 500}}
r = requests.post(f'https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents:runQuery',
                  headers={'Authorization': 'Bearer ' + cred.token}, json=q, timeout=60)
r.raise_for_status()
def val(v):
    if not v: return None
    for k in ('stringValue', 'integerValue', 'doubleValue', 'timestampValue', 'booleanValue'):
        if k in v: return v[k]
    return None
reps = []
for row in r.json():
    d = row.get('document')
    if not d: continue
    f = {k: val(v) for k, v in d.get('fields', {}).items()}
    f['_id'] = d['name'].split('/')[-1]
    reps.append(f)
print(len(reps), 'reports since', since)

# question text from the bank (bundled files + live patch)
Q = {}
for fn in sorted(glob.glob('q-*.json')):
    try:
        for x in json.load(open(fn, encoding='utf-8')):
            if x.get('id'): Q[x['id']] = x
    except Exception as e: print('skip', fn, e)
try:
    for x in json.load(open('live/qpatch.json', encoding='utf-8')).get('upd', []):
        if x.get('id'): Q[x['id']] = x
except Exception as e: print('qpatch', e)

by = {}
for x in reps: by.setdefault(x.get('qid'), []).append(x)
out = []
for qid, L in sorted(by.items(), key=lambda kv: -len(kv[1])):
    qq = Q.get(qid) or {}
    out.append({'qid': qid, 'n': len(L), 'types': [x.get('type') for x in L], 'notes': [x.get('note') for x in L if x.get('note')],
                'paper': L[0].get('paper') or '', 'q': qq.get('q', ''), 'opts': qq.get('opts', []), 'ans': qq.get('ans'), 'sub': qq.get('sub', '')})
json.dump({'since': since.isoformat() + 'Z', 'reports': out}, open('reports.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
today = (datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)).strftime('%d-%m-%Y')
if not out:
    tg('sendMessage', chat_id=ADMIN, text=f'✅ {today}: पिछले 24 घंटे में कोई गलती-रिपोर्ट नहीं आई।', disable_notification=True)
    sys.exit(0)
msgs, cur = [], f'🚩 <b>गलती-रिपोर्ट • {today}</b>\n{len(reps)} रिपोर्ट, {len(out)} प्रश्न\n'
for i, x in enumerate(out, 1):
    ans = x['opts'][x['ans']] if isinstance(x['ans'], int) and x['ans'] < len(x['opts']) else '?'
    t = ', '.join(sorted({TYPES.get(y, y or '?') for y in x['types']}))
    blk = f"\n<b>{i}. [{esc(x['qid'])}]</b> {'👥 ' + str(x['n']) + ' • ' if x['n'] > 1 else ''}{esc(t)}\n{esc(x['q'][:300]) or '(प्रश्न बैंक में नहीं मिला)'}\n✔ {esc(ans)}"
    if x['paper']: blk += f"\n📄 {esc(x['paper'])}"
    for n in x['notes'][:3]: blk += f"\n💬 {esc(n[:200])}"
    blk += '\n'
    if len(cur) + len(blk) > 3800: msgs.append(cur); cur = ''
    cur += blk
msgs.append(cur + '\nसुधार के लिए Claude को बताएँ: "रिपोर्ट वाले प्रश्न ठीक करो"')
for m in msgs:
    res = tg('sendMessage', chat_id=ADMIN, text=m, parse_mode='HTML', disable_web_page_preview=True)
    if not res.get('ok'): print('telegram error', res); sys.exit(1)
    time.sleep(1)
print('sent', len(msgs), 'message(s)')
