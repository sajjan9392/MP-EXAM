# -*- coding: utf-8 -*-
"""
Excel question banks -> questions.json (merged with built-in bank)

Usage:  python3 convert_xlsx.py            (reads every .xlsx in ./questions/)
Runs automatically in GitHub Actions before the APK build.

Recognised columns (case-insensitive, partial match, Hindi or English):
  Question (Hindi) / प्रश्न      -> q
  Option A..D (Hindi)             -> opts
  Correct Option (A/B/C/D or 1-4) -> ans
  Explanation (Hindi) / व्याख्या  -> exp
  Subject / Topic / Sub-Topic     -> tag + subject bucket
  Difficulty                      -> d (Very Easy..Very Hard -> 1..5)
  Year / Asked In Exam            -> year (shows under Previous Year Papers)
"""
import glob, json, os, re, sys
try:
    import openpyxl
except ImportError:
    print("openpyxl missing: pip install openpyxl"); sys.exit(1)

def _num(s):
    s=str(s).strip(); return re.sub(r"^(-?\d+)\.0$", r"\1", s)

ROMAN_TAG={'prachin itihas':'प्राचीन इतिहास','madhyakalin itihas':'मध्यकालीन इतिहास','adhunik itihas':'आधुनिक इतिहास','bhugol':'भूगोल','samvidhan':'भारतीय संविधान','arthvyavastha':'अर्थव्यवस्था','vigyan':'विज्ञान','paryavaran':'पर्यावरण'}

HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = os.path.join(HERE, 'questions.json')
XLSX_DIR = os.path.join(HERE, 'questions')
OUT = os.path.join(HERE, 'questions.json')

DIFF = {'very easy':1,'easy':2,'medium':3,'hard':4,'very hard':5,
        'अति सरल':1,'सरल':2,'मध्यम':3,'कठिन':4,'अति कठिन':5}

# subject bucket keywords (same buckets the app uses)
BUCKETS = [
  ('mp',     ['mp ','म.प्र','मध्य प्रदेश','madhya','जनजाति','tribe','janjati']),
  ('hist',   ['इतिहास','history','संस्कृति','culture','itihas','prachin','madhyakal','adhunik','sanskriti']),
  ('geo',    ['भूगोल','geograph','जलवायु','नदी','climate','resource','संसाधन','bhugol']),
  ('polity', ['संविधान','राजनीति','राजव्यवस्था','polity','constitution','शासन','governance','samvidhan','rajvyavastha','rajniti']),
  ('eco',    ['अर्थ','econom','बैंक','bank','योजना','scheme','budget','बजट','arthvyavastha','arth ','yojana']),
  ('env',    ['पर्यावरण','environment','जैव','biodiversity','ecology','पारिस्थितिक','paryavaran']),
  ('sci',    ['विज्ञान','science','physics','chemistry','biology','भौतिक','रसायन','जीव','अंतरिक्ष','space','स्वास्थ्य','health','vigyan']),
  ('comp',   ['computer','कंप्यूटर',' it ',' ai ','a.i.','cyber','साइबर','digital']),
  ('reason', ['तर्क','reason','मानसिक','mental','aptitude','निर्णय','decision','tark']),
  ('math',   ['गणित','math','quant','data','डेटा','संख्या','ganit']),
  ('hindi',  ['हिंदी','hindi','व्याकरण','grammar','vyakaran']),
  ('eng',    ['english','अंग्रेजी']),
  ('agri',   ['कृषि','agri','soil','मृदा','horticult']),
  ('ca',     ['करंट','current affairs','समसामयिक']),
]
def bucket(*texts):
    t=' '+' '.join(x for x in texts if x).lower()+' '
    for key,kws in BUCKETS:
        if any(k in t for k in kws): return key
    return 'gk'

def find_col(headers, *needles, exclude=()):
    for i,h in enumerate(headers):
        hl=(h or '').strip().lower()
        if any(n in hl for n in needles) and not any(e in hl for e in exclude):
            return i
    return None

def read_sheet(ws):
    rows=list(ws.iter_rows(values_only=True))
    if not rows: return []
    headers=[str(c) if c is not None else '' for c in rows[0]]
    cq  = find_col(headers,'question (hindi)','प्रश्न','question', exclude=('id','type','english'))
    if cq is None: cq = find_col(headers,'question')
    opts=[]
    for L in 'abcd':
        c = find_col(headers,f'option {L} (hindi)',f'option {L}',f'विकल्प {L}', exclude=('english',))
        if c is None: c = find_col(headers,f'option {L}')
        opts.append(c)
    cans = find_col(headers,'correct option','correct','उत्तर','answer', exclude=('hindi','english','answer (','explanation'))
    cexp = find_col(headers,'explanation (hindi)','व्याख्या','explanation', exclude=('english',))
    csub = find_col(headers,'subject','विषय')
    ctop = find_col(headers,'topic','टॉपिक', exclude=('sub-topic','sub topic'))
    cdif = find_col(headers,'difficulty','कठिनाई')
    cyr  = find_col(headers,'year','वर्ष','asked in')
    if cq is None or None in opts or cans is None:
        print(f"  skip sheet '{ws.title}': question/option/answer columns not found"); return []
    # if topics are very granular (avg < 5 questions per topic), tag by Subject instead
    use_subject=False
    if ctop is not None and csub is not None:
        tops=[r[ctop] for r in rows[1:] if r[ctop]]
        if tops and len(set(tops)) > max(3, len(tops)/5): use_subject=True
    out=[]
    for r in rows[1:]:
        q=r[cq]
        if not q or not str(q).strip(): continue
        o=[_num(r[c]) if r[c] is not None else '' for c in opts]
        if any(not x for x in o): continue
        a=str(r[cans]).strip().upper()
        a=a.replace('OPTION','').replace('(','').replace(')','').strip()
        if a in ('A','B','C','D'): ans='ABCD'.index(a)
        elif a in ('1','2','3','4'): ans=int(a)-1
        else:
            # answer given as text -> match option
            try: ans=[x.lower() for x in o].index(a.lower())
            except ValueError: continue
        sub=str(r[csub]) if csub is not None and r[csub] else ''
        top=str(r[ctop]) if ctop is not None and r[ctop] else ''
        dif=str(r[cdif]).strip().lower() if cdif is not None and r[cdif] else ''
        d=DIFF.get(dif,3)
        yr=None
        if cyr is not None and r[cyr]:
            m=re.search(r'20\d\d|19\d\d',str(r[cyr]))
            if m: yr=int(m.group())
        item=dict(sub=bucket(sub,top), tag=re.sub(r'\s*\([^)]*\)\s*$','',((sub if use_subject else top) or sub or top or 'सामान्य ज्ञान')).strip(),
                  q=str(q).strip(), opts=o, ans=ans,
                  exp=str(r[cexp]).strip() if cexp is not None and r[cexp] else '', d=d)
        item['tag']=ROMAN_TAG.get(item['tag'].lower(), item['tag'])
        cqe = find_col(headers,'question (english)')
        if cqe is not None and r[cqe]: item['qe']=str(r[cqe]).strip()
        if yr: item['year']=yr
        out.append(item)
    return out

def main():
    base=json.load(open(BUILTIN,encoding='utf-8')) if os.path.exists(BUILTIN) else []
    base=[x for x in base if x.get('id','')[:1] in ('B','P')]   # keep built-in (B) + PYQ (P), re-merge excel fresh
    added=[]
    for f in sorted(glob.glob(os.path.join(XLSX_DIR,'*.xlsx'))):
        print("reading", os.path.basename(f))
        wb=openpyxl.load_workbook(f, read_only=True, data_only=True)
        for ws in wb.worksheets:
            items=read_sheet(ws); print(f"  {ws.title}: {len(items)} questions"); added+=items
    def norm(s): return re.sub(r'[^\w\u0900-\u097F]+','',str(s or '').lower())
    seen=set()
    for x in base:
        seen.add(norm(x['q']))
        if x.get('qe'): seen.add(norm(x['qe']))
    merged=list(base); n=0; dup=0; near=0
    STOP={'ki','ka','ke','ko','se','mein','me','hai','tha','thi','the','kisne','kis','kaun','kya','kab','kahan','hain','ne','par','aur','or','the','of','in','is','was','which','who','what','when','where','a','an','to','by','the','following','निम्न','में','से','का','की','के','को','है','था','थी','किस','कौन','क्या','कब','कहाँ','हैं','ने','पर','और','निम्नलिखित'}
    def toks(x):
        s=x.get('q','').lower()
        return {w for w in re.findall(r'[\w\u0900-\u097F]+',s) if w not in STOP and len(w)>1}
    by_sub={}
    for x in merged: by_sub.setdefault(x['sub'],[]).append((toks(x),x['ans'],x['opts'][x['ans']].strip().lower()))
    def is_near(x):
        tx=toks(x); ans=x['opts'][x['ans']].strip().lower()
        for ty,_,ay in by_sub.get(x['sub'],[]):
            if ay==ans and tx and ty:
                j=len(tx&ty)/len(tx|ty)
                if j>=0.75: return True
        return False
    for x in added:
        keys={norm(x['q'])} | ({norm(x['qe'])} if x.get('qe') else set())
        if keys & seen: dup+=1; continue
        if is_near(x): near+=1; continue
        seen |= keys; n+=1; x['id']=f"X{n:05d}"; merged.append(x)
        by_sub.setdefault(x['sub'],[]).append((toks(x),x['ans'],x['opts'][x['ans']].strip().lower()))
    print(f"skipped {dup} exact + {near} near duplicates")
    json.dump(merged, open(OUT,'w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
    print(f"built-in {len(base)} + excel {n} = {len(merged)} questions -> questions.json")

if __name__=='__main__': main()
