#!/usr/bin/env python3
"""Pariksha Sarthi — roz Telegram channel par 3 Current Affairs "news card" (photo album).

Sabse naye din ke CA (live/ca-YYYY-MM.json) se 3 khabren (MP, rashtriya, antarrashtriya) chunkar
peele poster-style ke 3 card (1080x1350 PNG, neeche app ki jankari) + app ka 1 card banata hai aur channel par album ke roop me bhejta hai.
Kal/aaj ka naya CA na ho to kuch nahi bhejta.

Env:  TG_TOKEN, TG_CHAT   |   DRY_RUN=1 -> sirf card banata hai (CARD_DIR me), bhejta nahi
"""
import datetime, glob, io, json, os, sys, urllib.error, urllib.request, uuid
from PIL import Image, ImageDraw, ImageFont, features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'tools', 'fonts')
APP_LINK = 'https://play.google.com/store/apps/details?id=in.mpexam.app'
MONTHS = ['जनवरी', 'फरवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर']
CATS = {'mp': ('मध्यप्रदेश', '#12843c'), 'national': ('राष्ट्रीय', '#e11d2e'), 'international': ('अंतरराष्ट्रीय', '#1d4ed8')}
W, H, PAD = 1080, 1350, 56
YELLOW, BLACK, WHITE = '#ffd60a', '#111111', '#ffffff'
FOOT = 196
APP_LINE1 = 'पुराने पेपर (PYQ) • Test • रोज़ Current Affairs • बिना Login'
APP_LINE2 = 'Play Store: Pariksha Sarthi: MP Exam Prep'
APP_CARD = os.path.join(ROOT, 'tools', 'assets', 'app_card.png')


def font(size, weight='800'):
    return ImageFont.truetype(os.path.join(FONTS, 'Mukta-%s.ttf' % weight), size, layout_engine=ImageFont.Layout.RAQM)


def wrap(text, f, width):
    lines, cur = [], ''
    for word in text.split():
        t = (cur + ' ' + word).strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(text, width, max_h, sizes, weight, lead=1.28):
    """Sabse bada font jo diye gaye dibbe me aa jaye."""
    for s in sizes:
        f = font(s, weight)
        lines = wrap(text, f, width)
        if len(lines) * s * lead <= max_h:
            return f, lines, s * lead
    return f, lines, s * lead


def box(d, xy, fill, shadow=10, radius=28, outline=BLACK, width=6):
    x0, y0, x1, y1 = xy
    if shadow:
        d.rounded_rectangle((x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow), radius, fill=BLACK)
    d.rounded_rectangle(xy, radius, fill=fill, outline=outline, width=width)


def card(entry, idx, total, date):
    im = Image.new('RGB', (W, H), YELLOW)
    d = ImageDraw.Draw(im)
    for y in range(22, H, 44):
        for x in range(22, W, 44):
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill='#e8c309')
    # upar ki patti
    d.rectangle((0, 0, W, 150), fill=BLACK)
    d.text((PAD, 75), 'आज का Current Affairs', font=font(58), fill=WHITE, anchor='lm')
    dt = '%d %s %d' % (date.day, MONTHS[date.month - 1], date.year)
    f = font(40)
    tw = f.getlength(dt)
    d.rounded_rectangle((W - PAD - tw - 44, 40, W - PAD, 110), 35, fill=YELLOW)
    d.text((W - PAD - 22 - tw / 2, 75), dt, font=f, fill=BLACK, anchor='mm')
    # shreni ka tag
    name, col = CATS.get(entry.get('cat'), ('Current Affairs', BLACK))
    f = font(44)
    tw = f.getlength(name)
    box(d, (PAD, 196, PAD + tw + 64, 196 + 78), col, shadow=7, radius=18, width=5)
    d.text((PAD + 32 + tw / 2, 196 + 39), name, font=f, fill=WHITE, anchor='mm')
    d.text((W - PAD, 196 + 39), '%d/%d' % (idx, total), font=font(44), fill=BLACK, anchor='rm')
    # sheershak
    tf, tl, tlh = fit(entry['title'], W - 2 * PAD - 72, 300, (66, 60, 54, 50, 46, 42), '800', 1.26)
    th = int(len(tl) * tlh) + 64
    ty = 316
    box(d, (PAD, ty, W - PAD, ty + th), BLACK, shadow=12, radius=30, outline=BLACK)
    d.rounded_rectangle((PAD + 12, ty + 12, W - PAD + 12, ty + th + 12), 30, fill='#e11d2e')
    d.rounded_rectangle((PAD, ty, W - PAD, ty + th), 30, fill=BLACK)
    y = ty + 32
    for l in tl:
        d.text((PAD + 36, y + tlh / 2), l, font=tf, fill=WHITE, anchor='lm')
        y += tlh
    # mukhya tathya
    top = ty + th + 50
    bottom = H - FOOT - 34
    facts = [x for x in (entry.get('facts') or []) if x and len(x) <= 110][:4]
    if not facts:
        facts = [entry.get('body', '')[:220]]
    avail = bottom - top
    for size in (52, 48, 44, 40, 36, 32):
        f = font(size, '700')
        lh = size * 1.3
        blocks = [wrap(x, f, W - 2 * PAD - 150) for x in facts]
        hs = [int(len(b) * lh) + 40 for b in blocks]
        gap = 22
        while len(blocks) > 2 and sum(hs) + gap * (len(hs) - 1) > avail and size == 32:
            blocks.pop(); hs.pop()
        if sum(hs) + gap * (len(hs) - 1) <= avail:
            break
    y = top
    for b, hh in zip(blocks, hs):
        box(d, (PAD, y, W - PAD, y + hh), WHITE, shadow=8, radius=22, width=5)
        d.rounded_rectangle((PAD + 26, y + hh / 2 - 15, PAD + 56, y + hh / 2 + 15), 7, fill=col)
        yy = y + 20
        for l in b:
            d.text((PAD + 86, yy + lh / 2), l, font=f, fill=BLACK, anchor='lm')
            yy += lh
        y += hh + gap
    # neeche ki patti: app ki jankari
    d.rectangle((0, H - FOOT, W, H), fill=BLACK)
    try:
        ic = Image.open(os.path.join(ROOT, 'icon-512.png')).convert('RGB').resize((136, 136), Image.LANCZOS)
        mask = Image.new('L', (136, 136), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 135, 135), 30, fill=255)
        im.paste(ic, (PAD, H - FOOT + 30), mask)
        d.rounded_rectangle((PAD - 2, H - FOOT + 28, PAD + 137, H - FOOT + 167), 30, outline=YELLOW, width=4)
        tx = PAD + 164
    except Exception:
        tx = PAD
    d.text((tx, H - FOOT + 58), 'Pariksha Sarthi', font=font(58), fill=YELLOW, anchor='lm')
    f = font(34)
    tw = f.getlength('FREE App')
    d.rounded_rectangle((W - PAD - tw - 44, H - FOOT + 26, W - PAD, H - FOOT + 90), 16, fill='#12843c')
    d.text((W - PAD - 22 - tw / 2, H - FOOT + 58), 'FREE App', font=f, fill=WHITE, anchor='mm')
    for size in (34, 32, 30, 28, 26):
        f = font(size, '700')
        if f.getlength(APP_LINE1) <= W - PAD - tx:
            break
    d.text((tx, H - FOOT + 112), APP_LINE1, font=f, fill=WHITE, anchor='lm')
    for size in (32, 30, 28, 26, 24):
        f = font(size, '700')
        if f.getlength(APP_LINE2) <= W - PAD - tx:
            break
    d.text((tx, H - FOOT + 156), APP_LINE2, font=f, fill='#ffe98a', anchor='lm')
    return im


def latest_entries(today):
    files = sorted(glob.glob(os.path.join(ROOT, 'live', 'ca-20*.json'))) or sorted(glob.glob(os.path.join(ROOT, 'ca-20*.json')))
    entries = []
    for p in files[-2:]:
        try:
            entries += json.load(open(p, encoding='utf-8')).get('entries', [])
        except Exception:
            pass
    entries = [e for e in entries if e.get('date') and e.get('title')]
    if not entries:
        return None, []
    latest = max(e['date'] for e in entries)
    date = datetime.date.fromisoformat(latest)
    if (today - date).days > 1:
        return date, []
    day = sorted((e for e in entries if e['date'] == latest), key=lambda e: e['id'])
    chosen = []
    for cat in ('mp', 'national', 'international'):
        for e in day:
            if e.get('cat') == cat:
                chosen.append(e)
                break
    for e in day:  # 3 poore karne ke liye
        if len(chosen) >= 3:
            break
        if e not in chosen:
            chosen.append(e)
    return date, chosen[:3]


def send_album(chat, images, caption):
    boundary = uuid.uuid4().hex
    media = [{'type': 'photo', 'media': 'attach://p%d' % i} for i in range(len(images))]
    media[0].update(caption=caption, parse_mode='HTML')
    parts = []
    def field(name, value):
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode('utf-8'))
    field('chat_id', chat)
    field('media', json.dumps(media, ensure_ascii=False))
    for i, im in enumerate(images):
        buf = io.BytesIO()
        im.save(buf, 'PNG', optimize=True)
        parts.append(('--%s\r\nContent-Disposition: form-data; name="p%d"; filename="card%d.png"\r\nContent-Type: image/png\r\n\r\n' % (boundary, i, i + 1)).encode('utf-8') + buf.getvalue() + b'\r\n')
    parts.append(('--%s--\r\n' % boundary).encode('utf-8'))
    req = urllib.request.Request('https://api.telegram.org/bot%s/sendMediaGroup' % os.environ['TG_TOKEN'], data=b''.join(parts),
                                 headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit('Telegram error (sendMediaGroup): ' + e.read().decode('utf-8', 'replace'))


def main():
    dry = os.environ.get('DRY_RUN') == '1'
    chat = os.environ.get('TG_CHAT', '')
    if not dry and not (os.environ.get('TG_TOKEN') and chat):
        print('::warning::TELEGRAM_BOT_TOKEN secret ya channel nahi mila — news card skip')
        return
    if not features.check('raqm'):
        raise SystemExit('Pillow me raqm nahi hai — Hindi akshar galat banenge, isliye card nahi bheje')
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()
    date, chosen = latest_entries(today)
    if not chosen:
        print('::warning::kal/aaj ka naya CA nahi mila — news card skip')
        return
    images = [card(e, i + 1, len(chosen), date) for i, e in enumerate(chosen)]
    if os.path.exists(APP_CARD):  # aakhri card: app ki poori jankari
        images.append(Image.open(APP_CARD).convert('RGB'))
    caption = ('📰 <b>आज का Current Affairs</b> — %d %s %d\n%d ज़रूरी ख़बरें, परीक्षा के लिए 👆\n\n'
               'पूरी ख़बरें और इन पर सवाल <b>Pariksha Sarthi</b> App में, बिल्कुल FREE\n📲 %s') % (
        date.day, MONTHS[date.month - 1], date.year, len(chosen), APP_LINK)
    if dry:
        out = os.environ.get('CARD_DIR', '/tmp')
        for i, im in enumerate(images):
            im.save(os.path.join(out, 'card%d.png' % (i + 1)))
        print(caption)
        print('\n'.join('%s | %s' % (e['id'], e['title']) for e in chosen))
        return
    send_album(chat, images, caption)
    print('Bheja: %d news card (%s) -> %s' % (len(images), date.isoformat(), chat))


if __name__ == '__main__':
    main()
