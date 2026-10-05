# -*- coding: utf-8 -*-
"""بوّابة الافتتاحية قبل النشر — خطّة مؤتة §١٢ (ops/research/mutah/00-retention-plan.md)، وحكم المالك 2026-10-05:
«تُلغى طقوس الافتتاحية القديمة دائماً» (السلام في الثانية الأولى، «نسافر بكم عبر الزمن»، الاشتراك قبل القصّة).

بوّابة التشويق (tools/thrill_gate.py) تقيس النصّ قبل الصوت. وهذه تقيس الفيلم النهائيّ نفسه بعد المونتاج: يشاهد جيميناي
أوّل أربع دقائق منه بالمعيار الذي شُرّحت به افتتاحياتنا وافتتاحيات المنافسين (tools/openings.py)، ولا يُعرَّف بالقناة.
- **مانعٌ للنشر:**
  - القصّة أقلّ من ثلث أوّل 150 ث.
  - منهجٌ أو مصادر، أو طلبُ اشتراكٍ أو إعجاب، أو تعريفٌ بالقناة، قبل الدقيقة الرابعة.
  - تحيّةٌ قبل الثانية 25 (الافتتاح البارد).
- **تنبيه:** أوّل حدثٍ قصصيٍّ بعد الثانية 30، وأقلّ من 12 لقطةً في أوّل 30 ث، وأكثر من رقمٍ في أوّل 30 ث،
  ولا سؤال معلّقاً قبل الدقيقة، وأداءٌ صوتيٌّ على وتيرةٍ واحدة، وخطّافٌ دون 7 من 10.
- **التعذّر ليس نجاحاً:** إن لم يُشرَّح الفيلم (حصّةٌ أو خطأ) خرجت البوّابة بـ2 فلا يُنشر، ويُعاد بعد تجدّد الحصّة.

⛔ الفيلم لم يُنشر بعد: يُرسل نسخةً صغيرة (320 عرضاً، إطاران في الثانية، أوّل 240 ث) في الطلب نفسه، فلا رفع ولا تخزين.
   والتقرير (وفيه تفريغ ما لم يُنشر) إلى ملفٍّ مؤقّت في العدّاء وحده، والسجلّ العامّ يطبع الأرقام والأسباب لا النصوص.

الاستعمال: python tools/opening_gate.py <مجلد_الحمولة> --keys /tmp/keys.json [--out /tmp/opening_gate.json]
خروج 0 = تجتاز أو لا فيلم في الحمولة · 1 = لا تجتاز · 2 = تعذّر التشريح."""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openings  # noqa: E402

END_S = 240            # الدقيقة الرابعة: لا منهج ولا طلب قبلها
STORY_S = 150          # نافذة نسبة القصّة: بالمعيار الذي شُرّحت به الافتتاحيات
STORY_MIN = 1 / 3
COLD_S = 25            # الافتتاح البارد: لا تحيّة قبلها
STORY_ROLES = ('story_scene', 'hook')      # الخطّاف عندنا مشهدٌ من المعركة لا إعلان
CUTS_MIN, SCENE_MAX, NUMBERS_MAX, HOOK_MIN, QUESTION_BY = 12, 30, 1, 7, 60
BANNED = {'method_or_sources': 'منهجٌ أو مصادر', 'engagement_ask': 'طلبُ اشتراكٍ أو إعجاب',
          'channel_intro': 'تعريفٌ بالقناة أو السلسلة'}

# المعيار نفسه، ونافذةٌ أطول: يُعدَّل وصف المدّة وحده
PROMPT = (openings.PROMPT.replace('أوّلُ ١٥٠ ثانيةً', 'أوّلُ ٢٤٠ ثانيةً').replace('من ٣٠ إلى ١٥٠ ثانية', 'من ٣٠ إلى ٢٤٠ ثانية')
          .replace('تقسيمُ الـ١٥٠ ثانية', 'تقسيمُ الـ٢٤٠ ثانية'))


def clip_proxy(path: str, end: int = END_S) -> str:
    """أوّل end ثانيةً بنسخةٍ صغيرة: 320 عرضاً، وإطاران في الثانية (ليُرى الإيقاع: 12 لقطةً في 30 ث)، وصوتٌ أحاديّ."""
    out = os.path.splitext(path)[0] + '.gate.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-t', str(end), '-i', path, '-vf', 'scale=320:-2,fps=2',
                    '-c:v', 'libx264', '-crf', '32', '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '32k', '-ac', '1', out],
                   check=True)
    return out


def body(data: bytes, light: bool) -> bytes:
    part = {'inlineData': {'mimeType': 'video/mp4', 'data': base64.b64encode(data).decode('ascii')}, 'videoMetadata': {'fps': 2}}
    cfg = {'temperature': 0.1, 'responseMimeType': 'application/json'}
    if not light:
        cfg.update(responseSchema=openings.SCHEMA, mediaResolution='MEDIA_RESOLUTION_LOW')
    return json.dumps({'contents': [{'parts': [part, {'text': PROMPT}]}], 'generationConfig': cfg}).encode('utf-8')


def story_share(a: dict, window: float = STORY_S) -> float:
    """نصيب المشاهد القصصيّة من أوّل window ثانية (المقاطع المتداخلة لا تُعدّ مرّتين)."""
    spans = sorted((max(0.0, float(s.get('from') or 0)), min(window, float(s.get('to') or 0)))
                   for s in a.get('segments') or [] if s.get('role') in STORY_ROLES)
    total, end = 0.0, 0.0
    for x, y in spans:
        x = max(x, end)
        if y > x:
            total, end = total + (y - x), y
    return round(total / window, 3)


def verdict(a: dict) -> tuple[list[str], list[str], dict]:
    errs, warns = [], []
    share = story_share(a)
    if share < STORY_MIN:
        errs.append('القصّة %d٪ من أوّل %d ث (< الثلث): المشهد قبل الإعلان' % (round(share * 100), STORY_S))
    for k, label in BANNED.items():
        f = a.get(k) or {}
        if f.get('present') and float(f.get('s') or 0) < END_S:
            errs.append('%s عند الثانية %d (قبل الدقيقة الرابعة)' % (label, round(float(f.get('s') or 0))))
    g = a.get('greeting') or {}
    if g.get('present') and float(g.get('s') or 0) < COLD_S:
        errs.append('تحيّةٌ عند الثانية %d (قبل %d): الافتتاح البارد مشهدٌ متّصل' % (round(float(g.get('s') or 0)), COLD_S))
    scene = a.get('first_scene_s')
    if scene is None or float(scene) > SCENE_MAX:
        warns.append('أوّل حدثٍ قصصيٍّ عند %s ث (> %d)' % (scene, SCENE_MAX))
    if (a.get('cuts_30') or 0) < CUTS_MIN:
        warns.append('%s لقطةً في أوّل 30 ث (< %d) كما رآها جيميناي' % (a.get('cuts_30'), CUTS_MIN))
    if (a.get('numbers_30') or 0) > NUMBERS_MAX:
        warns.append('%s أرقامٍ أو تواريخ في أوّل 30 ث (> %d)' % (a.get('numbers_30'), NUMBERS_MAX))
    q = a.get('open_question') or {}
    if not (q.get('text') and q.get('s') is not None and float(q['s']) <= QUESTION_BY):
        warns.append('لا سؤال معلّقاً قبل الثانية %d' % QUESTION_BY)
    if (a.get('voice') or {}).get('varies') is False:
        warns.append('الأداء الصوتيّ على وتيرةٍ واحدة')
    hook = (a.get('hook') or {}).get('score')
    if hook is not None and hook < HOOK_MIN:
        warns.append('الخطّاف %s من 10 (< %d)' % (hook, HOOK_MIN))
    facts = {'نسبة_القصّة': share, 'أوّل_مشهد': scene, 'لقطات_30': a.get('cuts_30'), 'أرقام_30': a.get('numbers_30'),
             'أسماء_30': a.get('names_30'), 'الخطّاف': hook, 'السؤال_عند': q.get('s'),
             'الأدوار': [(round(float(s.get('from') or 0)), s.get('role')) for s in a.get('segments') or []]}
    return errs, warns, facts


def already_up(proj: str, state: str = os.path.join('ops', 'state', 'last_publish.json')) -> str:
    """معرّف فيلم هذه الحمولة إن رُفع في شوطٍ سابق (استئناف): FILM_VIDEO_ID، أو حالة النشر من master بالمعرّف نفسه."""
    vid = os.environ.get('FILM_VIDEO_ID', '').strip()
    if vid:
        return vid
    try:
        slug = json.load(io.open(os.path.join(proj, 'publish.json'), encoding='utf-8')).get('slug')
        last = json.load(io.open(state, encoding='utf-8'))
    except (OSError, ValueError):
        return ''
    return ((last.get('film') or {}).get('id') or '') if slug and last.get('slug') == slug else ''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('proj')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--out', default='/tmp/opening_gate.json')
    a = ap.parse_args(argv)
    film = os.path.join(a.proj, 'film.mp4')
    if not os.path.exists(film):
        print('لا فيلم في الحمولة (ريلزاتٌ وحدها): لا بوّابة افتتاحية'); return 0
    if already_up(a.proj):
        print('↻ الفيلم مرفوعٌ سلفاً (استئناف): اجتاز البوّابة قبل رفعه'); return 0
    keys = openings.keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي: الحالة المجهولة ليست نجاحاً'); return 2
    data = io.open(clip_proxy(film), 'rb').read()
    r = openings.Gem(keys).call(lambda light: body(data, light), 'opening-gate', budget_s=900)
    if 'error' in r:
        print('⛔ تعذّر تشريح الافتتاحية: %s — لا يُنشر، ويُعاد بعد تجدّد الحصّة' % str(r['error'])[:160]); return 2
    errs, warns, facts = verdict(r)
    json.dump({'التشريح': r, 'الأرقام': facts, 'موانع': errs, 'تنبيهات': warns},
              io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('الأرقام:', json.dumps({k: v for k, v in facts.items() if k != 'الأدوار'}, ensure_ascii=False))
    print('الأدوار:', facts['الأدوار'])
    for w in warns:
        print('⚠️', w)
    for e in errs:
        print('✗', e)
    print('✅ تجتاز بوّابة الافتتاحية' if not errs else '⛔ %d مانعاً في الافتتاحية — لا يُنشر' % len(errs))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
