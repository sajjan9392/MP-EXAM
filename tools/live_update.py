#!/usr/bin/env python3
"""Build live/ (online updates) for Pariksha Sarthi.

Baseline = the files in the repo root (what the last APK bundles: qindex.json + q-*.json,
ca-index.json + ca-YYYY-MM.json). Latest = a folder with the newest bank (e.g. the bank
artifact's files downloaded into BANK/).

    python3 tools/live_update.py <repo_dir> <latest_dir>

Writes <repo_dir>/live/{ca-index.json, ca-YYYY-MM.json (only changed months), qpatch.json,
manifest.json}. qpatch = questions that are new or changed vs the baseline, plus ids that
disappeared (never PYQ ids starting with P). Explanation-only edits are left for the next APK. Prints a short summary.
"""
import hashlib, json, os, sys, glob

def jload(p, d=None):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception: return d

def bank(d):
    idx = jload(os.path.join(d, 'qindex.json'), {}) or {}
    out = {}
    for f in idx.get('files', []):
        for q in jload(os.path.join(d, f), []) or []:
            if q.get('id'): out[q['id']] = q
    return out

def canon(o): return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def h(s): return hashlib.sha1(s.encode('utf-8')).hexdigest()[:12]

def main(repo, latest):
    live = os.path.join(repo, 'live'); os.makedirs(live, exist_ok=True)
    base, new = bank(repo), bank(latest)
    if not new: sys.exit('latest bank empty — abort')
    # only what changes the test itself: new questions, or a changed question/options/answer.
    # Explanation-only edits (hourly enrichment) wait for the next APK — keeps downloads small.
    KEY = ('q', 'qe', 'opts', 'optse', 'ans')
    def core(q): return canon({k: q.get(k) for k in KEY})
    upd = [q for i, q in new.items() if i not in base or core(base[i]) != core(q)]
    dele = sorted(i for i in base if i not in new and not i.startswith('P'))
    files = {}
    def put(name, obj):
        s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        with open(os.path.join(live, name), 'w', encoding='utf-8') as f: f.write(s)
        files[name] = h(s)
    put('qpatch.json', {'upd': sorted(upd, key=lambda q: q['id']), 'del': dele})
    # current affairs: send months that are new or changed vs the bundled files
    ci_new = jload(os.path.join(latest, 'ca-index.json'), {}) or {}
    months = []
    for x in ci_new.get('months', []):
        m = x['m']; a = jload(os.path.join(latest, f'ca-{m}.json')); b = jload(os.path.join(repo, f'ca-{m}.json'))
        if a is not None and (b is None or canon(a) != canon(b)):
            put(f'ca-{m}.json', a); months.append(x)
    for f in glob.glob(os.path.join(live, 'ca-20*.json')):   # drop stale month files
        if os.path.basename(f) not in files: os.remove(f)
    if months: put('ca-index.json', {'updated': ci_new.get('updated'), 'months': months})
    elif os.path.exists(os.path.join(live, 'ca-index.json')): os.remove(os.path.join(live, 'ca-index.json'))
    man = {'updated': ci_new.get('updated') or '', 'files': files}
    with open(os.path.join(live, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print(json.dumps({'qpatch_upd': len(upd), 'qpatch_del': len(dele), 'ca_months': [x['m'] for x in months],
                      'bytes': sum(os.path.getsize(os.path.join(live, n)) for n in files)}, ensure_ascii=False))

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
