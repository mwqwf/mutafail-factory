# -*- coding: utf-8 -*-
"""عيّنةٌ قصيرة من الفيلم قبل اكتمال صوته — أمر المالك 2026-10-04 (فيلم «الأرك»): «أرسل لي عيّنةً عمّا سيكون عليه الفيلم،
مقطعاً قصيراً حتى أراه».

يبني مشروعاً مصغّراً <out> من <proj>: اللقطات من أوّل الفيلم بترتيبها ما دام صوتُ كلّ كتلها موجوداً، وحتى --max ثانيةً،
ويربط بملفّات المشروع نفسها (images img cards audio clips anim) فلا يُنسخ شيء — ثم يُمنتَج بـmont_hybrid.py كما يُمنتَج الفيلم
تماماً: الصوت نفسه، والمقاطع الحيّة، والمشاهد المجسّمة، والبطاقات، والانتقالات.
الاستعمال: python tools/sample_cut.py <proj> <out> [--max 90]
         python tools/sample_cut.py <proj> <out> --shots S01,S07a,K21,…   (لقطاتٌ مختارة بترتيب الفيلم: عيّنةٌ تمثّل الفيلم كلّه،
         ويلزم صوتٌ لكلّ كتلها — حقيقيٌّ أو مؤقّتٌ يُكتم في المزج بـMONT_MUTE_VOICE=1)"""
from __future__ import annotations

import json
import os
import sys
import wave

LINKS = ('images', 'img', 'cards', 'map', 'audio', 'clips', 'anim')   # map: أصول خريطة المعركة الحيّة


def wav_seconds(f: str) -> float:
    with wave.open(f, 'rb') as w:
        return w.getnframes() / float(w.getframerate())


def cut(proj: str, out: str, max_s: float = 90.0, pick: list | None = None) -> list:
    """يعيد معرّفات اللقطات المأخوذة. لا يأخذ لقطةً ينقص صوتُ إحدى كتلها، ويقف عندها (العيّنة متّصلةٌ من أوّل الفيلم)."""
    P = lambda *a: os.path.join(proj, *a)
    blocks = json.load(open(P('blocks.json'), encoding='utf-8'))
    shots = json.load(open(P('shots.json'), encoding='utf-8'))
    secs = json.load(open(P('sections.json'), encoding='utf-8')) if os.path.exists(P('sections.json')) else []
    has = lambda b: os.path.exists(P('audio', b + '.wav')) and os.path.getsize(P('audio', b + '.wav')) > 8000
    keep, t = [], 0.0
    if pick:
        want = set(pick)
        keep = [s for s in shots if s['id'] in want]
        miss = [b for s in keep for b in (s.get('blocks') or []) if not has(b)]
        if len(keep) != len(want) or miss:
            raise SystemExit('⛔ لقطاتٌ غير موجودة %s أو كتلٌ بلا صوت %s' % (sorted(want - {s['id'] for s in keep}), miss))
        t = sum(float(s['hold']) if not s.get('blocks') else sum(wav_seconds(P('audio', b + '.wav')) for b in s['blocks']) / 1.05
                for s in keep)
    for s in ([] if pick else shots):
        bl = s.get('blocks') or []
        if not bl and not s.get('hold'):
            continue
        if not all(has(b) for b in bl):
            break
        d = float(s['hold']) if not bl else sum(wav_seconds(P('audio', b + '.wav')) for b in bl) / 1.05
        if keep and t + d > max_s:
            break
        keep.append(s); t += d
    if not keep:
        raise SystemExit('⛔ لا لقطة في أوّل الفيلم اكتمل صوتها — لا عيّنة')
    ids = {b for s in keep for b in (s.get('blocks') or [])}
    os.makedirs(out, exist_ok=True)
    dump = lambda name, obj: json.dump(obj, open(os.path.join(out, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    dump('blocks.json', [b for b in blocks if b['id'] in ids and not b.get('reel_only')])
    dump('shots.json', keep)
    dump('sections.json', [x for x in secs if x['id'] in ids])
    dump('reels.json', [])
    for name in ('publish.json', 'cards.json'):
        if os.path.exists(P(name)):
            dump(name, json.load(open(P(name), encoding='utf-8')))
    for d in LINKS:
        src, dst = os.path.abspath(P(d)), os.path.join(out, d)
        if os.path.isdir(src) and not os.path.lexists(dst):
            os.symlink(src, dst)
    print('العيّنة: %d لقطة · %d كتلة · ≈%.0f ث (من %s إلى %s)' % (len(keep), len(ids), t, keep[0]['id'], keep[-1]['id']))
    return [s['id'] for s in keep]


if __name__ == '__main__':
    args = sys.argv[1:]
    mx, pick = 90.0, None
    if '--max' in args:
        i = args.index('--max'); mx = float(args[i + 1]); del args[i:i + 2]
    if '--shots' in args:
        i = args.index('--shots'); pick = [x for x in args[i + 1].split(',') if x]; del args[i:i + 2]
    cut(os.path.abspath(args[0]), os.path.abspath(args[1]), mx, pick)
