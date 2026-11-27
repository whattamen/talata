#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gumawa ng mp3 para sa mga sigaw (war cry) sa laro.html, gamit ang parehong boses ng mga aklat.
  python3 tools/make_game_audio.py           (gawin lang ang wala pa)
  python3 tools/make_game_audio.py --force   (gawin lahat muli)
Provider: azure kung may AZURE_SPEECH_KEY at AZURE_SPEECH_REGION, kung wala ay edge-tts.
Output: audio/laro/<key>.mp3 at audio/laro/index.json (teksto -> file).
"""
import argparse, asyncio, html, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'audio', 'laro')
FIL = 'fil-PH-AngeloNeural'
ES = 'es-ES-AlvaroNeural'

# (key, teksto na eksaktong nasa laro.html, boses, rate, pitch)
LINES = [
    ('g5',  'Negosyo o kalayaan? Bayan o sarili? Pumili ka!', FIL, '-6%', '-12Hz'),
    ('g4',  'Para sa bayan, sugod!', FIL, '-2%', '-10Hz'),
    ('g3',  'Walang aatras! Ipagtanggol ang ating lupa!', FIL, '-2%', '-8Hz'),
    ('g2',  'Hukbo, ipakita ang tapang ninyo!', FIL, '+0%', '-8Hz'),
    ('g1',  'Sa ngalan ng kalayaan, lumaban!', FIL, '+0%', '-6Hz'),
    ('col', 'Hindi tayo susuko!', FIL, '+0%', '-4Hz'),
    ('ltc', 'Tumayo kayo! Laban!', FIL, '+0%', '-4Hz'),
    ('maj', 'Sundan ang bandila!', FIL, '+0%', '-2Hz'),
    ('cpt', 'Hanay, sugod!', FIL, '+4%', '+0Hz'),
    ('lt1', 'Ako ang mauuna!', FIL, '+4%', '+0Hz'),
    ('lt2', 'Kaya natin ito!', FIL, '+4%', '+2Hz'),
    ('sgt', 'Bilisan! Sugod, mga kasama!', FIL, '+6%', '+0Hz'),
    ('pvt', 'Handa na ako, Heneral!', FIL, '+6%', '+4Hz'),
    ('spy', 'Hindi mo ako nakita...', FIL, '-12%', '+0Hz'),
    ('flg', 'Ipagtanggol ninyo ako!', FIL, '+0%', '+0Hz'),
    ('h1',  'Haaaa!', FIL, '+0%', '+0Hz'),
    ('h2',  'Sugod!', FIL, '+4%', '+0Hz'),
    ('h3',  'Laban!', FIL, '+4%', '+0Hz'),
    ('h4',  'Hindi ka makakaligtas!', FIL, '+0%', '-2Hz'),
    ('h5',  'Para sa hukbo!', FIL, '+4%', '+0Hz'),
    ('h6',  'Humanda ka!', FIL, '+0%', '-2Hz'),
    ('k1',  'Mabuhay ang Katipunan!', FIL, '+0%', '+0Hz'),
    ('k2',  'Sugod, mga kapatid!', FIL, '+4%', '+0Hz'),
    ('k3',  'Para sa Inang Bayan!', FIL, '+0%', '-2Hz'),
    ('e1',  '¡Adelante!', ES, '+0%', '+0Hz'),
    ('e2',  '¡Por España!', ES, '+0%', '+0Hz'),
    ('e3',  '¡Fuego!', ES, '+0%', '+0Hz'),
    ('e4',  '¡A la carga!', ES, '+0%', '+0Hz'),
    ('e5',  '¡Rendíos, insurrectos!', ES, '+0%', '+0Hz'),
]
# Isinusulat nang mas malapit sa bigkas (hindi binabago ang nakikitang teksto)
SAY = {'Haaaa!': 'Haaa!', 'Hindi mo ako nakita...': 'Hindi mo ako nakita.'}


def azure(text, voice, rate, pitch):
    key, region = os.environ['AZURE_SPEECH_KEY'], os.environ['AZURE_SPEECH_REGION']
    lang = voice[:5]
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
            f'<voice name="{voice}"><prosody rate="{rate}" pitch="{pitch}">{html.escape(text)}</prosody></voice></speak>')
    req = urllib.request.Request(f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml.encode('utf-8'), headers={'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'talata'})
    return urllib.request.urlopen(req, timeout=60).read()


def edge(text, voice, rate, pitch):
    import edge_tts
    async def run():
        out = b''
        async for m in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).stream():
            if m['type'] == 'audio': out += m['data']
        return out
    return asyncio.run(run())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--force', action='store_true'); a = ap.parse_args()
    use = azure if os.environ.get('AZURE_SPEECH_KEY') and os.environ.get('AZURE_SPEECH_REGION') else edge
    os.makedirs(OUT, exist_ok=True)
    index = {}
    for key, text, voice, rate, pitch in LINES:
        path = os.path.join(OUT, key + '.mp3')
        if a.force or not os.path.exists(path):
            data = use(SAY.get(text, text), voice, rate, pitch)
            if not data: sys.exit(f'Walang audio para sa {key}')
            open(path, 'wb').write(data); print('ginawa', key, len(data))
        index[text] = key + '.mp3'
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('tapos:', len(index), 'linya')


if __name__ == '__main__':
    main()
