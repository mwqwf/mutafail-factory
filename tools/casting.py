# -*- coding: utf-8 -*-
"""اختيار الأصوات لكلّ سيناريو (casting) — أمر المالك 2026-11-27 (دائم لكلّ فيلم):
الصوت يُختار لكلّ سيناريو بعد قراءته: الراوي بنبرةٍ وسنٍّ وإيقاعٍ تناسب القصّة (ملحمة معركة أم تأمّل)، ولكلّ شخصيةٍ متكلّمة
صوتٌ مستقلّ مناسب (خالد، عمرو بن العاص، قادة العدوّ…) ثابتٌ في السلسلة كلّها، ولا صوت امرأة أبداً، ويُسجَّل في
`casting.md` لكلّ فيلم بأسبابه، وتُجرَّب عيّنات قبل التوليد الكامل.

ما كان (أجنادين): الراوي يتناوب Orus وCharon كتلةً كتلة، وصوت الاقتباس الواحد لشخصياتٍ متعدّدة.

`<proj>/casting.json`:
    {"series": "sayf-allah",
     "narrator": {"voice": "Algenib", "style": "epic", "pos_styles": {"medina": "reverent"}, "reason": "…"},
     "characters": {"khalid": {"name": "خالد بن الوليد", "voice": "Algieba", "style": "quote", "reason": "…"}},
     "blocks": {"d_008": "khalid"},                # كلّ كتلة Q/P ⇒ شخصيتها
     "samples": {"status": "pending|approved", "notes": "…"}}
وثبات السلسلة في `ops/series/voice_casting.json` ({"sayf-allah": {"narrator": …, "characters": {"khalid": …}}}).

    python3 tools/casting.py check  <proj> [--render]   # --render: يشترط عيّنات مُجازة قبل التوليد الكامل
    python3 tools/casting.py md     <proj>              # يكتب casting.md من casting.json
    python3 tools/casting.py apply  <proj>              # يكتب voice/speaker في blocks.json (بعد check --render)
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES = os.path.join(ROOT, 'ops', 'series', 'voice_casting.json')
# أصوات Gemini TTS الرجالية (ما جرّبه مختبر الأصوات منها مُعلَّم في VOICE_NOTES) — وكلّ ما سواها مرفوض
MALE = {'Algenib', 'Algieba', 'Alnilam', 'Achird', 'Charon', 'Enceladus', 'Fenrir', 'Iapetus', 'Orus', 'Puck',
        'Rasalgethi', 'Sadachbia', 'Sadaltager', 'Schedar', 'Umbriel', 'Zubenelgenubi'}
FEMALE = {'Achernar', 'Aoede', 'Autonoe', 'Callirrhoe', 'Despina', 'Erinome', 'Gacrux', 'Kore', 'Laomedeia', 'Leda',
          'Pulcherrima', 'Sulafat', 'Vindemiatrix', 'Zephyr'}
SPOKEN = ('Q', 'P')


def load(p: str):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def check(cast: dict, blocks: list[dict], series: dict | None = None, render: bool = False) -> list[str]:
    errs = []
    nar = cast.get('narrator') or {}
    chars = cast.get('characters') or {}
    every = [('narrator', nar)] + list(chars.items())
    for k, c in every:
        v = c.get('voice')
        if v in FEMALE:
            errs.append('%s: صوت امرأة «%s» — ممنوع منعاً باتّاً' % (k, v))
        elif v not in MALE:
            errs.append('%s: صوت غير معروف «%s» (الرجالية: %s)' % (k, v, ' '.join(sorted(MALE))))
        if len((c.get('reason') or '').strip()) < 10:
            errs.append('%s: بلا سبب اختيار (reason) — الصوت يُختار للقصّة لا بالعادة' % k)
    for k, c in chars.items():
        if c.get('voice') == nar.get('voice'):
            errs.append('%s: صوته صوت الراوي نفسه — كلّ شخصية بصوتٍ مستقلّ' % k)
    used = {}
    for k, c in chars.items():
        used.setdefault(c.get('voice'), []).append(k)
    for v, ks in used.items():
        if len(ks) > 1:
            errs.append('صوت %s لشخصياتٍ متعدّدة: %s' % (v, ' '.join(ks)))
    bmap = cast.get('blocks') or {}
    for b in blocks:
        if b.get('role') in SPOKEN:
            who = bmap.get(b['id'])
            if not who:
                errs.append('%s: كلامٌ منقول بلا شخصية مسمّاة في casting' % b['id'])
            elif who not in chars:
                errs.append('%s: الشخصية «%s» غير معرّفة في characters' % (b['id'], who))
    ser = (series or {}).get(cast.get('series') or '') or {}
    if ser:
        sn = (ser.get('narrator') or {}).get('voice')
        if sn and sn != nar.get('voice') and not nar.get('override_reason'):
            errs.append('الراوي %s يخالف راوي السلسلة %s (override_reason للعدول المسوَّغ)' % (nar.get('voice'), sn))
        for k, c in chars.items():
            sv = ((ser.get('characters') or {}).get(k) or {}).get('voice')
            if sv and sv != c.get('voice') and not c.get('override_reason'):
                errs.append('%s: %s يخالف صوته في السلسلة %s' % (k, c.get('voice'), sv))
    if render and (cast.get('samples') or {}).get('status') != 'approved':
        errs.append('العيّنات لم تُجَز بعد — لا توليد كامل قبل سماع عيّنة لكلّ صوت (voice_lab)')
    return errs


def md(cast: dict, blocks: list[dict]) -> str:
    by = {b['id']: b for b in blocks}
    nar = cast['narrator']
    out = ['# اختيار الأصوات (casting) — %s' % cast.get('title', cast.get('series', '')), '',
           '> أمر المالك 2026-11-27: الصوت يُختار لكلّ سيناريو، ولكلّ شخصية صوتٌ مستقلّ ثابت في السلسلة، ولا صوت امرأة، '
           'وعيّنات قبل التوليد الكامل. مولَّد من `casting.json` بـ`tools/casting.py md`.', '',
           '| الدور | الصوت | الأسلوب | السبب |', '|---|---|---|---|',
           '| الراوي | %s | %s%s | %s |' % (nar['voice'], nar.get('style', ''),
                                         ''.join(' · %s@%s' % (v, k) for k, v in (nar.get('pos_styles') or {}).items()),
                                         nar.get('reason', ''))]
    for k, c in (cast.get('characters') or {}).items():
        lines = [i for i, w in (cast.get('blocks') or {}).items() if w == k]
        out.append('| %s (%s) | %s | %s | %s — الكتل: %s |' % (c.get('name', k), k, c['voice'], c.get('style', ''),
                                                            c.get('reason', ''), ' '.join(sorted(lines))))
    alts = cast.get('alternates') or {}
    if alts:
        out += ['', '## بدائل تُجرَّب في العيّنات', ''] + ['- %s: %s' % (k, ' · '.join(v)) for k, v in alts.items()]
    s = cast.get('samples') or {}
    out += ['', '## العيّنات', '', '- الحالة: **%s**' % s.get('status', 'pending'), '- %s' % s.get('notes', '')]
    return '\n'.join(out) + '\n'


def apply(cast: dict, blocks: list[dict]) -> list[dict]:
    chars, bmap, nar = cast.get('characters') or {}, cast.get('blocks') or {}, cast['narrator']
    for b in blocks:
        if b.get('role') in SPOKEN and bmap.get(b['id']) in chars:
            c = chars[bmap[b['id']]]
            b['speaker'], b['voice'] = bmap[b['id']], c['voice']
        elif b.get('role') in (None, 'N'):
            b['voice'] = nar['voice']
    return blocks


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2:
        print(__doc__); return 2
    cmd, proj = a[0], a[1]
    cast = load(os.path.join(proj, 'casting.json'))
    bp = os.path.join(proj, 'blocks.json')
    blocks = load(bp) if os.path.exists(bp) else []
    series = load(SERIES) if os.path.exists(SERIES) else {}
    if cmd == 'md':
        with open(os.path.join(proj, 'casting.md'), 'w', encoding='utf-8') as f:
            f.write(md(cast, blocks))
        print('✓ casting.md'); return 0
    errs = check(cast, blocks, series, render=(cmd == 'apply' or '--render' in a))
    for e in errs:
        print('⛔', e)
    if errs:
        return 1
    if cmd == 'apply':
        with open(bp, 'w', encoding='utf-8') as f:
            json.dump(apply(cast, blocks), f, ensure_ascii=False, indent=1)
    print('✓ الأصوات سليمة: راوٍ + %d شخصية' % len(cast.get('characters') or {}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
