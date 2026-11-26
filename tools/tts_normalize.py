# -*- coding: utf-8 -*-
"""Ihanda ang tekstong Tagalog bago basahin ng boses (TTS).
Ginagamit ng tools/make_audio.py. Ang bersyong JS (para sa browser) ay nasa index.html (ttsNorm).
"""
import re

ABBR = [  # (pattern, palit) — may tuldok ang mga ito kaya hiwalay sa mga salita
    (r'\bGng\.', 'Ginang'), (r'\bBb\.', 'Binibini'), (r'\bG\.(?=\s+[A-ZÑ])', 'Ginoo'),
    (r'\bDra\.', 'Doktora'), (r'\bDr\.', 'Doktor'), (r'\bAtty\.', 'Abogado'),
    (r'\bEng\.', 'Inhinyero'), (r'\bGen\.', 'Heneral'), (r'\bKgg\.', 'Kagalang-galang'),
    (r'\bSr\.', 'Senior'), (r'\bJr\.', 'Junior'), (r'\bBro\.', 'Brod'), (r'\bSis\.', 'Sis'),
    (r'\bBlg\.', 'Bilang'), (r'\bTel\.', 'Telepono'), (r'\batbp\.', 'at iba pa'), (r'\bhal\.', 'halimbawa'),
    (r'\bSt\.', 'Santo'), (r'\bNo\.\s*(?=\d)', 'Bilang '),
]
# Bigkas ng mga salitang banyaga o pangalan na maaaring mali ang basa. Dagdagan ayon sa pangangailangan.
PRON = {
    'Archivo': 'Arkibo', 'Wi-Fi': 'wayfay', 'WiFi': 'wayfay', 'YouTube': 'yutyub', 'Intramuros': 'Intramuros',
    'Tala': 'Tala', 'Baybayin': 'Baybayin', 'Tikbalang': 'Tikbalang', 'Mateo': 'Mateyo',
    'Salvador': 'Salbador', 'internship': 'intern-ship', 'intern': 'intern', 'OK': 'okey', 'okay': 'okey',
    'Facebook': 'feysbuk', 'TikTok': 'tiktok', 'Google': 'gugol',
}
MONTHS = 'Enero Pebrero Marso Abril Mayo Hunyo Hulyo Agosto Setyembre Oktubre Nobyembre Disyembre'.split()

U = ['', 'isa', 'dalawa', 'tatlo', 'apat', 'lima', 'anim', 'pito', 'walo', 'siyam']
TEENS = ['sampu', 'labing-isa', 'labindalawa', 'labintatlo', 'labing-apat', 'labinlima', 'labing-anim',
         'labimpito', 'labingwalo', 'labinsiyam']
TENS = ['', '', 'dalawampu', 'tatlumpu', 'apatnapu', 'limampu', 'animnapu', 'pitumpu', 'walumpu', 'siyamnapu']
# pang-angkop (-ng / na) pagkatapos ng bilang
LINK = {'isa': 'isang', 'dalawa': 'dalawang', 'tatlo': 'tatlong', 'apat': 'apat na', 'lima': 'limang',
        'anim': 'anim na', 'pito': 'pitong', 'walo': 'walong', 'siyam': 'siyam na'}


def _below100(n):
    if n < 10: return U[n]
    if n < 20: return TEENS[n - 10]
    t, u = divmod(n, 10)
    return TENS[t] if u == 0 else f"{TENS[t]}'t {U[u]}"


def _below1000(n):
    h, r = divmod(n, 100)
    if h == 0: return _below100(r)
    head = f"{LINK[U[h]]} daan"
    if r == 0: return head
    return f"{head} at {_below100(r)}"


def tagalog_number(n):
    """0..999999 sa salitang Tagalog."""
    if n == 0: return 'sero'
    if n >= 1_000_000: return ' '.join(tagalog_number(int(d)) for d in str(n))  # basahin bawat digit
    th, r = divmod(n, 1000)
    parts = []
    if th:
        parts.append(f"{_link_for(th)} libo")
    if r:
        parts.append(('at ' if th and r < 100 else '') + _below1000(r))
    return ' '.join(parts)


def link(w):
    """Idagdag ang pang-angkop: -ng kapag patinig ang dulo, 'na' kapag katinig."""
    return w + 'ng' if re.search(r'[aeiou]$', w) else w + ' na'


def _link_for(n):
    return link(_below1000(n))


NO_LINK = {'at', 'ay', 'ng', 'sa', 'na', 'pa', 'ang', 'kay', 'o', 'ni', 'nang', 'din', 'rin', 'lang', 'lamang', 'ba', 'po', 'ho'}


def _num_sub(m):
    ws = m.group(0)[len(m.group(0).rstrip()):]
    return _num_core(m) + ws


def _num_core(m):
    s = m.group(1).replace(',', '')
    if '.' in s:
        a, b = s.split('.', 1)
        w = f"{tagalog_number(int(a))} punto {' '.join(tagalog_number(int(d)) for d in b)}"
    else:
        w = tagalog_number(int(s))
    suffix = m.group(2) or ''
    unit = {'%': 'porsiyento'}.get(suffix.strip())
    nxt = (m.group(3) or '').strip().lower()
    if unit:
        return link(w) + ' ' + unit
    if nxt and nxt not in NO_LINK:
        return link(w)
    return w


def normalize(text):
    t = text
    # markdown at palamuti
    t = re.sub(r'\*+', '', t)
    t = t.replace('_', ' ')
    for pat, rep in ABBR: t = re.sub(pat, rep, t)
    for k, v in PRON.items(): t = re.sub(r'\b' + re.escape(k) + r'\b', v, t)
    # oras: 3:30 -> alas tres y medya ay mahirap; basahin bilang bilang
    t = re.sub(r'(\d{1,2}):(\d{2})', lambda m: f"{tagalog_number(int(m.group(1)))} {tagalog_number(int(m.group(2)))}" if m.group(2) != '00' else tagalog_number(int(m.group(1))), t)
    t = re.sub(r'[\u20b1P](\d[\d,]*(?:\.\d+)?)', lambda m: tagalog_number(int(m.group(1).replace(',', '').split('.')[0])) + ' piso', t)
    t = re.sub(r'(\d[\d,]*(?:\.\d+)?)(\s*%)?(?:\s+(?=([A-Za-z\u00d1\u00f1]+)))?', _num_sub, t)
    # bantas para sa natural na paghinto
    t = t.replace('—', ', ').replace('–', ', ').replace(' - ', ', ')
    t = re.sub(r'\.{3,}|…', ', ', t)           # ... -> maikling hinto
    t = t.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\s+([,.!?])', r'\1', t)
    t = re.sub(r',\s*,', ',', t)
    if t and t[-1] not in '.!?"\'': t += '.'
    return t


if __name__ == '__main__':
    tests = ['Sabi ni Gng. Cruz at Dr. Santos, 16 taong gulang si Mateo noong 2026.',
             'Mahigit 519 na taon... at 30% ng 1,250 aklat — sa Archivo!', 'Bb. Reyes, alas 3:30, ₱1,500.']
    for x in tests: print(normalize(x))
    for n in (1, 11, 12, 16, 21, 100, 101, 519, 600, 1000, 1250, 2026, 20000): print(n, tagalog_number(n))
