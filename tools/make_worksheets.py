#!/usr/bin/env python3
"""
Gumagawa ng mga printable na PDF para sa mga guro: kuwento + worksheet + susi sa pagwawasto.
Pinagmulan: tools/worksheets.json (mga tanong) at tools/works.json (teksto, gawa ng build.py).
Patakbuhin pagkatapos ng build:  python3 tools/make_worksheets.py
Lalabas sa guro/<id>.pdf
"""
import html, json, os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
esc = lambda s: html.escape(str(s))
WS = json.load(open('tools/worksheets.json', encoding='utf-8'))
WORKS = {w['id']: w for w in json.load(open('tools/works.json', encoding='utf-8'))}
os.makedirs('guro', exist_ok=True)

CSS = """
@page{size:A4;margin:18mm 18mm 16mm}
*{box-sizing:border-box}
body{font-family:'Lora','Cardo',Georgia,serif;font-size:12pt;line-height:1.55;color:#1d1a14;margin:0}
.page{page-break-after:always}
.page:last-child{page-break-after:auto}
.top{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #C9A45C;padding-bottom:6px;margin-bottom:14px;font-family:'Inter','DejaVu Sans',sans-serif;font-size:9.5pt;color:#6b5a35}
.top b{font-family:'Cardo',Georgia,serif;font-size:15pt;letter-spacing:.18em;color:#8f650c}
h1{font-family:'Cardo',Georgia,serif;font-size:24pt;margin:4px 0 2px}
.meta{font-family:'Inter','DejaVu Sans',sans-serif;font-size:9.5pt;color:#6b5a35;margin-bottom:12px}
h2{font-family:'Inter','DejaVu Sans',sans-serif;font-size:11.5pt;text-transform:uppercase;letter-spacing:.06em;color:#8f650c;margin:16px 0 6px}
p{margin:0 0 8px;text-align:justify}
.fields{display:flex;gap:16px;font-family:'Inter','DejaVu Sans',sans-serif;font-size:10.5pt;margin-bottom:6px}
.fields span{flex:1;border-bottom:1px solid #999;padding-bottom:2px}
table{width:100%;border-collapse:collapse;font-size:11pt}
td{border:1px solid #cdbf9c;padding:6px 8px;vertical-align:top}
td.w{width:28%;font-weight:600}
ol{margin:0;padding-left:20px}
li{margin-bottom:6px}
.line{border-bottom:1px solid #bbb;height:20px;margin:2px 0 6px}
.foot{margin-top:14px;font-family:'Inter','DejaVu Sans',sans-serif;font-size:8.5pt;color:#7d6c47;text-align:center}
.key li{margin-bottom:8px}
.ws{font-size:11pt;line-height:1.45}
.ws .line{height:19px;margin:1px 0 4px}
.ws table{font-size:10.5pt}
.ws td{padding:4px 8px}
.ws .foot{margin-top:6px}
.ws h2{margin:12px 0 5px}
"""

def top(label):
    return f'<div class="top"><b>TALATA</b><span>{esc(label)}</span></div>'

FOOT = '<p class="foot">Libreng materyales mula sa Talata · talata-studio.com · Malayang i-print at gamitin sa klase.</p>'

def build(ws):
    w = WORKS[ws['id']]
    c = w['chapters'][0]
    url = f'talata-studio.com/read/{ws["id"]}/1/'
    story = ''.join(f'<p>{esc(p).replace("*", "")}</p>' for p in (c.get('paras') or []))
    p1 = (f'<div class="page">{top("Kuwento")}<h1>{esc(ws["title"])}</h1>'
          f'<div class="meta">{esc(ws["type"])} · Mungkahing antas: {esc(ws["level"])} · Basahin at pakinggan online: {url}</div>'
          f'{story}{FOOT}</div>')
    vocab = ''.join(f'<tr><td class="w">{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in ws['words'])
    qs = ''.join(f'<li>{esc(q)}<div class="line"></div></li>' for q in ws['questions'])
    th = ''.join(f'<li>{esc(q)}<div class="line"></div><div class="line"></div></li>' for q in ws['think'])
    p2 = (f'<div class="page ws">{top("Worksheet")}<div class="fields"><span>Pangalan:</span><span>Baitang at Seksiyon:</span><span>Petsa:</span></div>'
          f'<h1>{esc(ws["title"])}</h1>'
          f'<h2>A. Talasalitaan</h2><table>{vocab}</table>'
          f'<h2>B. Pag-unawa sa Binasa</h2><ol>{qs}</ol>'
          f'<h2>C. Pag-isipan</h2><ol>{th}</ol>'
          f'<h2>D. Gawain</h2><p>{esc(ws["activity"])}</p>{FOOT}</div>')
    ans = ''.join(f'<li>{esc(a)}</li>' for a in ws['answers'])
    p3 = (f'<div class="page">{top("Para sa Guro")}<h1>Susi sa Pagwawasto</h1>'
          f'<div class="meta">{esc(ws["title"])} · Bahagi B: Pag-unawa sa Binasa</div><ol class="key">{ans}</ol>'
          '<h2>Mungkahi sa Pagtuturo</h2><p>Para sa Bahagi C at D, tanggapin ang anumang makatwirang sagot na may paliwanag. '
          'Puwedeng iparinig muna sa klase ang audio ng kuwento sa website bago ito basahin nang tahimik.</p>'
          f'<p>Mababasa at mapapakinggan ang buong kuwento nang libre sa {url}</p>{FOOT}</div>')
    return f'<!DOCTYPE html><html lang="fil"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{p1}{p2}{p3}</body></html>'

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    for ws in WS:
        pg.set_content(build(ws), wait_until='load')
        pg.pdf(path=f'guro/{ws["id"]}.pdf', format='A4', print_background=True)
        print('guro/' + ws['id'] + '.pdf')
    b.close()
