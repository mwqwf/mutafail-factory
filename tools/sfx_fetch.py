# -*- coding: utf-8 -*-
"""توسيع مكتبة المؤثّرات بأصواتٍ حرّة الرخصة فقط (CC0) — أمر المالك 2026-11-27 («جودة الإنتاج»).

يقرأ `assets/sfx/curation.json` (قائمة منتقاة يدوياً: معرّف Freesound، الصنف، اسم الملف، بداية المقطع ومدّته)،
ولكلّ ملفٍّ غائب: يفتح صفحة الصوت ويتحقّق أنّ الرخصة **CC0** (`publicdomain/zero`) — وإلا يرفضه —، ثم ينزّل
المعاينة العامّة عالية الجودة ويحوّلها إلى ogg opus أحادي 48kHz ويضيف سطرها إلى `LICENSES.md`.
⛔ لا موسيقى ولا آلات ولا صوت امرأة: كلّ ملفّ جديد يمرّ بـ`tonal_gate` ثم يُقاس في `sfx_library.py`.
لا مفتاح ولا حساب ولا إنفاق (الصفحات والمعاينات عامّة).

    python3 tools/sfx_fetch.py            # ينزّل الغائب فقط
    python3 tools/sfx_fetch.py --dry      # يطبع ما سيُنزَّل
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, 'assets', 'sfx')
UA = {'User-Agent': 'Mozilla/5.0 (mutafail-factory sfx curation)'}
CC0 = re.compile(r'creativecommons\.org/publicdomain/zero/1\.0', re.I)


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def page_info(sid: int) -> dict:
    t = get('https://freesound.org/s/%d/' % sid).decode('utf-8', 'ignore')
    m = re.search(r'og:title" content="([^"]+) by ([^"]+)"', t)
    pv = re.search(r'(https://cdn\.freesound\.org/previews/\d+/%d_\d+-hq\.mp3)' % sid, t)
    page = re.search(r'href="(/people/[^"/]+/sounds/%d/)"' % sid, t)
    return {'cc0': bool(CC0.search(t)), 'title': html.unescape(m.group(1)) if m else '?',
            'author': html.unescape(m.group(2)) if m else '?', 'preview': pv.group(1) if pv else None,
            'url': 'https://freesound.org' + page.group(1) if page else 'https://freesound.org/s/%d/' % sid}


def license_row(e: dict, info: dict, dur: float) -> str:
    return '| %s | %s | %.1f | %s | %s | %s | CC0 1.0 Universal (Public Domain Dedication) |' % (
        e['file'], e['category'], dur, info['title'].replace('|', '/'), info['author'], info['url'])


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = '--dry' in argv
    cur = json.load(open(os.path.join(SFX, 'curation.json'), encoding='utf-8'))
    lic_path = os.path.join(SFX, 'LICENSES.md')
    lic = open(lic_path, encoding='utf-8').read()
    rc = 0
    for e in cur['items']:
        dst = os.path.join(SFX, e['file'])
        if os.path.exists(dst) and e['file'] in lic:
            continue
        if dry:
            print('سيُنزَّل', e['file'], e['id']); continue
        info = page_info(int(e['id']))
        if not info['cc0'] or not info['preview']:
            print('⛔ مرفوض (ليس CC0 أو لا معاينة):', e['id'], e['file']); rc = 1; continue
        with tempfile.TemporaryDirectory() as td:
            mp3 = os.path.join(td, 'p.mp3')
            open(mp3, 'wb').write(get(info['preview']))
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(e.get('start', 0)), '-i', mp3,
                            '-t', str(min(30.0, float(e.get('dur', 30)))), '-ac', '1', '-ar', '48000',
                            '-c:a', 'libopus', '-b:a', '96k', dst], check=True)
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst],
                                 capture_output=True, text=True).stdout.strip() or 0)
        if e['file'] not in lic:                  # يُكتب فوراً: انقطاع الشوط لا يترك ملفاً بلا سطر رخصته
            lic = lic.rstrip('\n') + '\n' + license_row(e, info, d) + '\n'
            open(lic_path, 'w', encoding='utf-8').write(lic)
        print('✓', e['file'], '%.1f ث' % d, info['title'], '—', info['author'])
    return rc


if __name__ == '__main__':
    sys.exit(main())
