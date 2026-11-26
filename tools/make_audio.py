#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gumawa ng mp3 na narasyon (Tagalog, fil-PH) bawat kabanata.
  python3 tools/make_audio.py --work huling-tagapag-ingat --chapter 1
  python3 tools/make_audio.py --all            (lahat ng wala pang mp3)
Provider:
  azure (opisyal, may libreng tier): kailangan ang AZURE_SPEECH_KEY at AZURE_SPEECH_REGION
  edge  (libre, di-opisyal):         pip install edge-tts
Awtomatikong pipili: azure kung may key, kung wala ay edge.
Boses: fil-PH-BlessicaNeural (babae) o fil-PH-AngeloNeural (lalaki).
"""
import argparse, asyncio, html, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from tts_normalize import normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chunks(paras, limit=2800):
    cur, n = [], 0
    for p in paras:
        if cur and n + len(p) > limit:
            yield cur; cur, n = [], 0
        cur.append(p); n += len(p)
    if cur: yield cur


def azure(paras, voice, rate):
    key, region = os.environ['AZURE_SPEECH_KEY'], os.environ['AZURE_SPEECH_REGION']
    out = b''
    for grp in chunks(paras):
        body = '<break time="650ms"/>'.join(html.escape(p) for p in grp)
        ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fil-PH">'
                f'<voice name="{voice}"><prosody rate="{rate}">{body}</prosody></voice></speak>')
        req = urllib.request.Request(f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
            data=ssml.encode('utf-8'), headers={'Ocp-Apim-Subscription-Key': key,
            'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
            'User-Agent': 'talata'})
        out += urllib.request.urlopen(req, timeout=120).read()
    return out


def edge(paras, voice, rate):
    import edge_tts
    async def run():
        out = b''
        for grp in chunks(paras):
            com = edge_tts.Communicate('\n\n'.join(grp), voice, rate=rate)
            async for m in com.stream():
                if m['type'] == 'audio': out += m['data']
        return out
    return asyncio.run(run())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work'); ap.add_argument('--chapter', type=int); ap.add_argument('--all', action='store_true')
    ap.add_argument('--provider', choices=['azure', 'edge']); ap.add_argument('--voice', default='fil-PH-BlessicaNeural')
    ap.add_argument('--rate', default='-5%'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    prov = a.provider or ('azure' if os.environ.get('AZURE_SPEECH_KEY') else 'edge')
    works = json.load(open(os.path.join(ROOT, 'tools', 'works.json'), encoding='utf-8'))
    todo = []
    for w in works:
        if a.work and w['id'] != a.work: continue
        for i, c in enumerate(w['chapters'], 1):
            if c.get('soon') or not c.get('paras'): continue
            if a.chapter and i != a.chapter: continue
            if not (a.all or a.work): continue
            todo.append((w, i, c))
    if not todo: sys.exit('Walang gagawin. Gamitin ang --work <id> --chapter <n> o --all')
    for w, i, c in todo:
        path = os.path.join(ROOT, 'audio', w['id'], f'{i}.mp3')
        if os.path.exists(path) and not a.force: print('nariyan na:', w['id'], i); continue
        paras = [normalize(c.get('title') or w['title'])] + [normalize(p) for p in c['paras']]
        paras = [p for p in paras if p]
        print(f'{prov}: {w["id"]} kabanata {i} ({sum(map(len, paras))} titik)...', flush=True)
        data = azure(paras, a.voice, a.rate) if prov == 'azure' else edge(paras, a.voice, a.rate)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data); print('  ->', path, len(data) // 1024, 'KB')
        refresh_site_data()


def refresh_site_data():
    f = os.path.join(ROOT, 'site-data.json'); d = json.load(open(f, encoding='utf-8'))
    ad = os.path.join(ROOT, 'audio')
    d['audio'] = sorted(f'{x}/{y[:-4]}' for x in os.listdir(ad) if os.path.isdir(os.path.join(ad, x))
                        for y in os.listdir(os.path.join(ad, x)) if y.endswith('.mp3'))
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
