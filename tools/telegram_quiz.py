#!/usr/bin/env python3
"""Pariksha Sarthi — roz Telegram channel par 5 Current Affairs quiz.

Sabse naye din ke CA (live/ca-YYYY-MM.json) se jude prashn (live/qpatch.json + q-ca.json) uthakar
Telegram "Quiz" poll ke roop me channel par bhejta hai, aur ant me app ka link.
Agar kal/aaj ka naya CA nahi mila to purane CA se 5 "Revision" prashn bhejta hai (roz alag).

Env:  TG_TOKEN (bot token, GitHub secret TELEGRAM_BOT_TOKEN)   TG_CHAT (jaise @channelusername)
      DRY_RUN=1  -> kuch nahi bhejta, sirf dikhata hai
"""
import datetime, glob, json, os, random, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LINK = 'https://play.google.com/store/apps/details?id=in.mpexam.app'
N = 5
MONTHS = ['जनवरी', 'फरवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर']


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def entry_dates():
    """CA entry id -> date. live/ ke mahine bundled mahino ke upar."""
    dates = {}
    for pat in ('ca-20*.json', os.path.join('live', 'ca-20*.json')):
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            for e in load(p, {}).get('entries', []):
                if e.get('id') and e.get('date'):
                    dates[e['id']] = e['date']
    return dates


def ca_questions():
    qs = {}
    for q in load(os.path.join(ROOT, 'q-ca.json'), []):
        qs[q['id']] = q
    patch = load(os.path.join(ROOT, 'live', 'qpatch.json'), {})
    for q in patch.get('upd', []):
        if q.get('sub') == 'ca':
            qs[q['id']] = q
    for i in patch.get('del', []):
        qs.pop(i, None)
    hidden = load(os.path.join(ROOT, 'live', 'hide.json'), {})
    hid = set(hidden.get('ids', [])) if isinstance(hidden, dict) else set()
    out = []
    for q in qs.values():
        opts = q.get('opts') or []
        if q['id'] in hid or q.get('paper') or q.get('img') or q.get('fig'):
            continue  # PYQ / figure wale nahi
        if not (isinstance(q.get('ans'), int) and 2 <= len(opts) <= 10 and 0 <= q['ans'] < len(opts)):
            continue
        if len(q.get('q', '')) > 300 or not q.get('q') or any((not o) or len(o) > 100 for o in opts):
            continue  # Telegram ki seema
        out.append(q)
    return out


def pick(qs, dates, today):
    link = lambda q: q.get('ca') or q.get('caid')
    by_date = {}
    for q in qs:
        d = dates.get(link(q))
        if d:
            by_date.setdefault(d, []).append(q)
    latest = max(by_date) if by_date else None
    fresh = latest and (today - datetime.date.fromisoformat(latest)).days <= 1
    if fresh:
        groups = {}
        for q in sorted(by_date[latest], key=lambda q: q['id']):
            groups.setdefault(link(q), []).append(q)
        order = sorted(groups, key=lambda k: (0 if '-M' in k else 1 if '-N' in k else 2, k))  # MP pehle
        chosen = []
        while len(chosen) < N and any(groups.values()):
            for k in order:
                if groups[k] and len(chosen) < N:
                    chosen.append(groups[k].pop(0))
        return latest, chosen
    recent = sorted(d for d in by_date if (today - datetime.date.fromisoformat(d)).days <= 120)
    pool = [q for d in recent for q in by_date[d]] or qs
    rnd = random.Random(today.isoformat())
    return None, rnd.sample(sorted(pool, key=lambda q: q['id']), min(N, len(pool)))


def explanation(q):
    lines = [l.strip() for l in (q.get('exp') or '').split('\n') if l.strip() and not l.strip().startswith('✖')]
    text = ' '.join(lines[:2])
    return text if len(text) <= 200 else text[:197].rstrip() + '…'


def api(method, payload):
    token = os.environ['TG_TOKEN']
    req = urllib.request.Request('https://api.telegram.org/bot%s/%s' % (token, method),
                                 data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        raise SystemExit('Telegram error (%s): %s' % (method, body))


def main():
    dry = os.environ.get('DRY_RUN') == '1'
    chat = os.environ.get('TG_CHAT', '')
    if not dry and not (os.environ.get('TG_TOKEN') and chat):
        print('::warning::TELEGRAM_BOT_TOKEN secret ya channel nahi mila — quiz skip')
        return
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()
    date, chosen = pick(ca_questions(), entry_dates(), today)
    if not chosen:
        print('::warning::koi CA prashn nahi mila — quiz skip')
        return
    if date:
        d = datetime.date.fromisoformat(date)
        head = '📰 <b>आज का Current Affairs Quiz</b>\n%d %s %d की ख़बरों से %d सवाल 👇' % (d.day, MONTHS[d.month - 1], d.year, len(chosen))
    else:
        head = '🔁 <b>Current Affairs Revision Quiz</b>\nपिछले महीनों की ख़बरों से %d सवाल 👇' % len(chosen)
    foot = ('✅ ऐसे ही रोज़ नए Current Affairs, पुराने पेपर (PYQ) और Test — <b>Pariksha Sarthi</b> App में, बिल्कुल FREE\n\n'
            '📲 Download: ' + APP_LINK)
    if dry:
        print(head)
        for i, q in enumerate(chosen, 1):
            print('\nQ%d [%s] %s' % (i, q['id'], q['q']))
            for j, o in enumerate(q['opts']):
                print('   %s %s' % ('✅' if j == q['ans'] else '  ', o))
            print('   exp:', explanation(q))
        print('\n' + foot)
        return
    api('sendMessage', {'chat_id': chat, 'text': head, 'parse_mode': 'HTML'})
    for i, q in enumerate(chosen, 1):
        time.sleep(2)
        p = {'chat_id': chat, 'question': 'Q%d. %s' % (i, q['q']) if len(q['q']) <= 294 else q['q'],
             'options': q['opts'], 'type': 'quiz', 'correct_option_id': q['ans'], 'is_anonymous': True}
        exp = explanation(q)
        if exp:
            p['explanation'] = exp
        api('sendPoll', p)
    time.sleep(2)
    api('sendMessage', {'chat_id': chat, 'text': foot, 'parse_mode': 'HTML'})
    print('Bheja: %d quiz (%s) -> %s' % (len(chosen), date or 'revision', chat))


if __name__ == '__main__':
    main()
