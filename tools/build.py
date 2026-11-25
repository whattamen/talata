#!/usr/bin/env python3
"""
Talata build: gumagawa ng mga static na pahina para sa malilinis na URL,
share preview (Open Graph), sitemap, RSS feed, ePub at site-data.json.

Patakbuhin pagkatapos baguhin ang index.html (halimbawa kapag nagdagdag ng kabanata):
    python3 tools/build.py

Kailangan: Python 3, Pillow (hindi na), at Playwright (para mabasa ang WORKS).
Ang index.html ang pinagmulan. Huwag baguhin ng kamay ang mga nabuong pahina
(w/, read/, c/, a/, epub/, learn/, submit/, about/, privacy/, terms/, 404.html).
"""
import base64, datetime, html, json, os, re, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://talata-studio.com'
os.chdir(ROOT)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto('file://' + os.path.join(ROOT, 'index.html'))
    pg.wait_for_timeout(300)
    DATA = pg.evaluate("({works:WORKS, cats:CATS, pen:PEN, authors:AUTHORS})")
    b.close()

WORKS, CATS, AUTHORS = DATA['works'], DATA['cats'], DATA['authors']
esc = lambda s: html.escape(str(s), quote=True)
em = lambda s: re.sub(r'\*([^*]+)\*', r'<em>\1</em>', esc(s))   # *italics* -> <em>

# ---------- template (may marker para sa SEO at noscript) ----------
tpl = open('index.html', encoding='utf-8').read()
tpl = re.sub(r'<!--SEO-->.*?<!--/SEO-->', '<!--SEO--><!--/SEO-->', tpl, flags=re.S)
tpl = re.sub(r'<!--NS-->.*?<!--/NS-->', '<!--NS--><!--/NS-->', tpl, flags=re.S)
assert '<!--SEO--><!--/SEO-->' in tpl and '<!--NS--><!--/NS-->' in tpl, 'walang markers sa index.html'

# ---------- mga larawan ng cover ----------
os.makedirs('img', exist_ok=True)
covers = {}
for w in WORKS:
    c = w.get('coverImg') or ''
    if c.startswith('/') and os.path.exists(c.lstrip('/')):
        covers[w['id']] = c
        continue
    m = re.match(r'data:image/(\w+);base64,(.*)', c, re.S)
    if m:
        ext = 'jpg' if m.group(1) in ('jpeg', 'jpg') else m.group(1)
        fn = f'img/{w["id"]}.{ext}'
        open(fn, 'wb').write(base64.b64decode(m.group(2)))
        covers[w['id']] = '/' + fn

# ---------- petsa ng mga kabanata (nananatili sa site-data.json) ----------
today = datetime.date.today().isoformat()
old = {}
if os.path.exists('site-data.json'):
    try:
        old = json.load(open('site-data.json', encoding='utf-8')).get('dates', {})
    except Exception:
        old = {}
dates = {}
for w in WORKS:
    for i, c in enumerate(w['chapters'], 1):
        if c.get('soon'):
            continue
        k = f'{w["id"]}/{i}'
        dates[k] = old.get(k, today)

def snip(t, n=180):
    t = re.sub(r'\s+', ' ', (t or '').replace('*', '')).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(' ', 1)[0] + '…'

def work_desc(w):
    return snip(w.get('lead') or ' '.join(w.get('synopsis') or []) or w['title'], 200)

# ---------- mga pahina ----------
pages = []   # (path, title, desc, image, kind, body_html)
home_desc = "Novels, kids' short stories, alamat, and tula in Tagalog and English, on Talata."
home_list = ''.join(f'<li><a href="/w/{w["id"]}/">{esc(w["title"])}</a></li>' for w in WORKS)
pages.append(('', 'Talata — Novels, Kids Stories, Alamat at Tula', home_desc, '/og-default.jpg', 'website',
              f'<h1>Talata</h1><p>{esc(home_desc)}</p><ul>{home_list}</ul>'))

for k, c in CATS.items():
    items = ''.join(f'<li><a href="/w/{w["id"]}/">{esc(w["title"])}</a></li>' for w in WORKS if w['cat'] == k)
    pages.append((f'c/{k}', f'{c["name"]} — Talata', f'{c["name"]} sa Talata.', '/og-default.jpg', 'website',
                  f'<h1>{esc(c["name"])}</h1><ul>{items}</ul>'))

for w in WORKS:
    img = covers.get(w['id'], '/og-default.jpg')
    syn = ''.join(f'<p>{esc(x)}</p>' for x in (w.get('synopsis') or []))
    chl = ''.join(f'<li><a href="/read/{w["id"]}/{i}/">{esc(c["label"])}: {esc(c.get("title",""))}</a></li>'
                  for i, c in enumerate(w['chapters'], 1) if not c.get('soon'))
    pages.append((f'w/{w["id"]}', f'{w.get("subtitle") or w["title"]} — Talata', work_desc(w), img, 'book',
                  f'<h1>{esc(w["title"])}</h1>{syn}<ol>{chl}</ol>'))
    for i, c in enumerate(w['chapters'], 1):
        if c.get('soon'):
            continue
        paras = ''.join(f'<p>{em(x)}</p>' for x in c.get('paras', []))
        first = (c.get('paras') or [w['title']])[0]
        pages.append((f'read/{w["id"]}/{i}', f'{c["label"]} — {w["title"]}', snip(first, 160), img, 'article',
                      f'<h1>{esc(w["title"])}</h1><h2>{esc(c["label"])}: {esc(c.get("title",""))}</h2>{paras}'))

for slug, a in AUTHORS.items():
    mine = [w for w in WORKS if (w.get('writer') if w.get('writer') in AUTHORS else 'ang-manunulat') == slug]
    items = ''.join(f'<li><a href="/w/{w["id"]}/">{esc(w["title"])}</a></li>' for w in mine)
    pages.append((f'a/{slug}', f'{a["name"]} — Talata', snip(a.get('bio', ''), 160), '/og-default.jpg', 'profile',
                  f'<h1>{esc(a["name"])}</h1><p>{esc(a.get("bio",""))}</p><ul>{items}</ul>'))

for path, title, desc in [
    ('learn', 'Learning — Talata', 'Mga gabay, kasaysayan ng sinaunang panulat sa Pilipinas, at mga aktibidad.'),
    ('learn/laro', 'Laro — Talata', 'Mga laro sa Talata: Heneral, Salitaan, Bituin at iba pa.'),
    ('learn/info', 'Materials at Info — Talata', 'Mga materyales, sinaunang panulat, gabay sa komento, at pagsusumite.'),
    ('submit', 'Magsumite ng Akda — Talata', 'Bukas ang Talata sa mga malayang manunulat. Alamin kung paano magsumite.'),
    ('about', 'About — Talata', 'Tungkol sa may-akda at sa Talata.'),
    ('privacy', 'Privacy — Talata', 'Paano ginagamit ng Talata ang impormasyon ng mga bisita.'),
    ('terms', 'Mga Tuntunin — Talata', 'Mga tuntunin sa karapatan, pagsusumite, at komento.'),
]:
    pages.append((path, title, desc, '/og-default.jpg', 'website', f'<h1>{esc(title)}</h1><p>{esc(desc)}</p>'))

def make(path, title, desc, image, kind, body):
    url = f'{BASE}/{path + "/" if path else ""}'
    seo = (f'<link rel="canonical" href="{url}">'
           f'<meta property="og:site_name" content="Talata"><meta property="og:type" content="{kind if kind in ("article","website") else "website"}">'
           f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
           f'<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}{image}">'
           f'<meta name="twitter:card" content="{"summary_large_image" if image.endswith("og-default.jpg") else "summary"}">'
           f'<meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}">'
           f'<meta name="twitter:image" content="{BASE}{image}">')
    out = tpl.replace('<!--SEO--><!--/SEO-->', f'<!--SEO-->{seo}<!--/SEO-->')
    out = out.replace('<!--NS--><!--/NS-->', f'<!--NS--><noscript><main>{body}</main></noscript><!--/NS-->')
    out = re.sub(r'<title>.*?</title>', lambda m: f'<title>{esc(title)}</title>', out, count=1, flags=re.S)
    out = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{esc(desc)}">', out, count=1)
    return out

# linisin ang mga lumang nabuong folder
for d in ['w', 'read', 'c', 'a', 'learn', 'submit', 'about', 'privacy', 'terms']:
    shutil.rmtree(d, ignore_errors=True)

for path, title, desc, image, kind, body in pages:
    out = make(path, title, desc, image, kind, body)
    if path == '':
        open('index.html', 'w', encoding='utf-8').write(out)
        open('404.html', 'w', encoding='utf-8').write(out)
    else:
        os.makedirs(path, exist_ok=True)
        open(os.path.join(path, 'index.html'), 'w', encoding='utf-8').write(out)

# ---------- sitemap + robots ----------
urls = [f'{BASE}/{p + "/" if p else ""}' for p, *_ in pages] + [f'{BASE}/laro.html', f'{BASE}/bigkas.html']
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
     ''.join(f'<url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n'
open('sitemap.xml', 'w', encoding='utf-8').write(sm)
open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')

# ---------- RSS ----------
def rfc822(d):
    return datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d %b %Y 08:00:00 +0000')
items = []
for k, d in sorted(dates.items(), key=lambda kv: kv[1], reverse=True)[:30]:
    wid, n = k.split('/')
    w = next(x for x in WORKS if x['id'] == wid); c = w['chapters'][int(n) - 1]
    link = f'{BASE}/read/{wid}/{n}/'
    first = snip((c.get('paras') or [''])[0], 280)
    items.append(f'<item><title>{esc(w.get("subtitle") or w["title"])} — {esc(c["label"])}'
                 f'{": " + esc(c["title"]) if c.get("title") and c["title"] != c["label"] else ""}</title>'
                 f'<link>{link}</link><guid>{link}</guid><pubDate>{rfc822(d)}</pubDate>'
                 f'<description>{esc(first)}</description></item>')
rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Talata</title>'
       f'<link>{BASE}/</link><description>Mga bagong kabanata at akda sa Talata</description><language>tl</language>'
       + ''.join(items) + '</channel></rss>\n')
open('feed.xml', 'w', encoding='utf-8').write(rss)

# ---------- ePub ----------
os.makedirs('epub', exist_ok=True)
for fn in os.listdir('epub'):
    if fn.endswith('.epub'):
        os.remove(os.path.join('epub', fn))
epub_ids = []
def zi(n):
    return zipfile.ZipInfo(n, (2026, 1, 1, 0, 0, 0))   # pirmeng petsa para hindi nagbabago ang file kapag walang pagbabago
XH = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="tl" lang="tl"><head><meta charset="utf-8"/><title>{t}</title><style>body{{font-family:serif;line-height:1.6}}p{{text-indent:1.2em;margin:.3em 0}}h1,h2{{text-align:center}}</style></head><body>{b}</body></html>'
for w in WORKS:
    chs = [(i, c) for i, c in enumerate(w['chapters'], 1) if not c.get('soon') and c.get('paras')]
    if not chs:
        continue
    author = (AUTHORS.get(w.get('writer')) or AUTHORS['ang-manunulat'])['name'] if not w.get('author') else w['author']
    files = []
    manifest = ''
    spine = ''
    navli = ''
    for j, (i, c) in enumerate(chs, 1):
        name = f'ch{j}.xhtml'
        t = f'{c["label"]}: {c.get("title","")}' if c.get('title') and c['title'] != c['label'] else c['label']
        body = f'<h2>{esc(t)}</h2>' + ''.join(f'<p>{em(x)}</p>' for x in c['paras'])
        files.append((f'OEBPS/{name}', XH.format(t=esc(t), b=body)))
        manifest += f'<item id="c{j}" href="{name}" media-type="application/xhtml+xml"/>'
        spine += f'<itemref idref="c{j}"/>'
        navli += f'<li><a href="{name}">{esc(t)}</a></li>'
    title = w.get('subtitle') or w['title']
    cover_item = ''
    cover_file = None
    if w['id'] in covers:
        cp = covers[w['id']].lstrip('/')
        ext = cp.rsplit('.', 1)[1]
        mt = 'image/jpeg' if ext == 'jpg' else f'image/{ext}'
        cover_item = f'<item id="cover" href="cover.{ext}" media-type="{mt}" properties="cover-image"/>'
        cover_file = (f'OEBPS/cover.{ext}', open(cp, 'rb').read())
    opf = ('<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="id">talata-{w["id"]}</dc:identifier><dc:title>{esc(title)}</dc:title>'
           f'<dc:creator>{esc(author)}</dc:creator><dc:language>tl</dc:language>'
           f'<meta property="dcterms:modified">{today}T00:00:00Z</meta></metadata><manifest>'
           f'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{cover_item}{manifest}</manifest>'
           f'<spine>{spine}</spine></package>')
    nav = XH.format(t='Nilalaman', b=f'<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><h1>Nilalaman</h1><ol>{navli}</ol></nav>')
    fn = f'epub/{w["id"]}.epub'
    with zipfile.ZipFile(fn, 'w') as z:
        z.writestr(zi('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr(zi('META-INF/container.xml'), '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>', compress_type=zipfile.ZIP_DEFLATED)
        z.writestr(zi('OEBPS/content.opf'), opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr(zi('OEBPS/nav.xhtml'), nav, compress_type=zipfile.ZIP_DEFLATED)
        for name, data in files:
            z.writestr(zi(name), data, compress_type=zipfile.ZIP_DEFLATED)
        if cover_file:
            z.writestr(zi(cover_file[0]), cover_file[1], compress_type=zipfile.ZIP_DEFLATED)
    epub_ids.append(w['id'])

json.dump({'dates': dates, 'epub': epub_ids, 'built': today}, open('site-data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'OK: {len(pages)} pahina, {len(epub_ids)} ePub, {len(dates)} kabanata')
