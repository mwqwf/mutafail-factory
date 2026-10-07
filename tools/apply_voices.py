# -*- coding: utf-8 -*-
"""يطبّق نتيجة مختبر الأصوات على كتل مشروعٍ قبل ختمه (مؤتة 2026-10-06).

لكلّ كتلةٍ حقل «role»: N الراوي · Q صوت الاقتباس (كلمات الصحابة المأثورة نثراً) · P الملقي (الشعر والرجز، وبه يحكم
audio_checks بمدّة البيت). ولكتل الراوي حقلٌ اختياريّ «pos» (موضعها: medina…) يختار للصوت نفسه أسلوباً آخر من
«pos_styles» في مواصفة الراوي (المدينة هادئةٌ موقّرة بلا انفعال: حكمٌ معنويّ لا ذوقيّ).
- الصوت وملاحظات المخرج (director) من فائز كلّ دور. وصوت الاقتباس والملقي غيرُ صوت الراوي (حكم المالك 2026-10-05:
  «بصوتٍ مستقلّ»): إن فاز صوت الراوي في دورٍ آخر أُخذ التالي في ترتيب ذلك الدور المحكَّم.
- سلسلة المعالجة (publish.json: voice_filter) من فائز الراوي إن حُكّمت، وإلا يبقى الافتراض في mont_hybrid.
- ⛔ دورٌ تحتاجه الكتل بلا فائزٍ محكَّم ⇒ لا يُكتب شيء ويُخرج بـ1: لا صوتَ فيلمٍ بلا حكمٍ فعليّ (درس مؤتة 2026-10-05).

الاستعمال:
  python tools/apply_voices.py <مجلد_المشروع> ops/voice-lab/results/<slug>-results.json [ops/voice-lab/results/<slug>-voices-results.json]
  python tools/apply_voices.py --check <مجلد_المشروع>    # في weekly-film قبل التوليد
"""
from __future__ import annotations

import io
import json
import os
import sys

ROLES = {'N': 'narrator', 'Q': 'quote', 'P': 'poetry'}


def load(path: str):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path: str, obj) -> None:
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=1) + '\n')


def role_results(results: list[dict]) -> tuple[dict, dict, dict]:
    """{الدور: نتيجته مع أساليب مواصفتها}، وأساليب مواضع الراوي من ملفّ النتيجة الذي فيه الراوي."""
    roles, pos_styles = {}, {}
    for res in results:
        rr = res.get('roles') or ({'narrator': res} if res.get('winner') or res.get('final') else {})
        for name, r in rr.items():
            roles[name] = dict(r, styles=res.get('styles') or {})
        if 'narrator' in rr:
            pos_styles = res.get('pos_styles') or {}
    return roles, (roles.get('narrator') or {}).get('styles') or {}, pos_styles


def plan(blocks: list[dict], results: list[dict]) -> tuple[list[dict], str | None, dict]:
    """الكتل بأصواتها وملاحظاتها، وسلسلة المعالجة، وتقريرٌ موجز. ValueError بكلّ الموانع معاً."""
    roles, styles, pos_styles = role_results(results)
    need = sorted({ROLES.get(b.get('role')) for b in blocks if b.get('role')} - {None})
    unknown = sorted({b['role'] for b in blocks if b.get('role') and b['role'] not in ROLES})
    errs = ['دورٌ غير معروف: %s' % ' '.join(unknown)] if unknown else []
    for r in need:
        if not (roles.get(r) or {}).get('winner'):
            errs.append('لا فائز محكَّماً لدور %s: %s' % (r, (roles.get(r) or {}).get('error', 'لا نتيجة')))
    if errs:
        raise ValueError(errs)
    narr = roles.get('narrator', {}).get('winner')
    pick = {}
    for r in need:
        w = roles[r]['winner']
        if r != 'narrator' and narr:
            alt = [lab for lab in w.get('order') or ['%s·%s' % (w['voice'], w['style'])] if lab.split('·')[0] != narr['voice']]
            if not alt:
                errs.append('دور %s: لا صوتَ محكَّماً غيرُ صوت الراوي %s' % (r, narr['voice']))
                continue
            if alt[0].split('·')[0] != w['voice']:
                v, s = alt[0].split('·')
                w = dict(w, voice=v, style=s, director=roles[r]['styles'].get(s) or w['director'])
        pick[r] = w
    for p in sorted({b['pos'] for b in blocks if b.get('pos') and ROLES.get(b.get('role')) == 'narrator'}):
        if p not in pos_styles or pos_styles[p] not in styles:
            errs.append('موضعٌ بلا أسلوبٍ في مواصفة الراوي: %s' % p)
    if errs:
        raise ValueError(errs)
    out, rep = [], {}
    for b in blocks:
        b = dict(b)
        r = ROLES.get(b.get('role'))
        if r:
            w = pick[r]
            d = w['director']
            if r == 'narrator' and b.get('pos'):
                d = styles[pos_styles[b['pos']]]
            b['voice'], b['director'] = w['voice'], d
            b.pop('style', None)                     # «style» الخام يُرسل قبل النصّ في gen25: لا يبقى مع director
            key = '%s %s·%s%s' % (r, w['voice'], w['style'], ' @' + b['pos'] if r == 'narrator' and b.get('pos') else '')
            rep[key] = rep.get(key, 0) + 1
        out.append(b)
    return out, (narr or {}).get('filter'), rep


def check(blocks: list[dict]) -> list[str]:
    """ما يمنع التوليد: كتلةٌ لها دورٌ بلا director (لم يُطبَّق المختبر)، أو بقي فيها «style» خام."""
    return ['%s: %s' % (b['id'], 'بلا director' if not b.get('director') else 'style خام «%s»' % b['style'])
            for b in blocks if b.get('role') and (not b.get('director') or b.get('style'))]


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == '--check':
        bad = check(load(os.path.join(argv[1], 'blocks.json')))
        if bad:
            print('⛔ أصوات المختبر لم تُطبَّق على %d كتلة (tools/apply_voices.py قبل الختم): %s' % (len(bad), ' · '.join(bad[:6])))
            return 1
        return 0
    proj, paths = argv[0], argv[1:]
    blocks = load(os.path.join(proj, 'blocks.json'))
    try:
        new, flt, rep = plan(blocks, [load(p) for p in paths])
    except ValueError as e:
        for m in e.args[0]:
            print('⛔', m)
        print('⛔ لم يُكتب شيء: يُعاد المختبر بعد تجدّد الحصّة')
        return 1
    save(os.path.join(proj, 'blocks.json'), new)
    if flt:
        pub = load(os.path.join(proj, 'publish.json'))
        pub['voice_filter'] = flt
        save(os.path.join(proj, 'publish.json'), pub)
    for k, n in sorted(rep.items()):
        print('✅ %s: %d كتلة' % (k, n))
    print('المعالجة:', flt or 'الافتراضية (لم تُحكَّم سلاسل المعالجة)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
