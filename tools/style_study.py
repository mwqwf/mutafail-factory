# -*- coding: utf-8 -*-
"""دراسةُ الأسلوب — أمر المالك 2026-10-05: «اعرف المشكلة بالضبط، ثم اعرف أسلوب من نجحوا وطبّقه أو طبّق أسلوباً أفضل منه
— الافتتاحية والريلزات والحماسة والأكشن… كلَّ مرّةٍ أشدّد عليها وفي كلّ مرّةٍ النتائج متقاربة».

تشريح أوّل 150 ث (tools/openings.py) لا يكفي لمعرفة كيف يُمسَك المشاهد إلى النهاية، ولا لتعلّم كتابة الأكشن من نصوص
الناجحين أنفسهم. فهذه الأداة تجمع في السحابة (يوتيوب محجوبٌ عن جلسة Claude) أربعة أشياء لكلّ ما في ops/stats/style.json:
1) الأفلام: جيميناي يشاهد الفيلم كاملاً من رابطه (إطارٌ كلّ خمس ثوانٍ أو عشر، مع الصوت كلّه) فيكتب تحليلاً بنيوياً
   (الفصول وشدّتها، وإعادة الشدّ، ومشاهد الأكشن، وتقنيات التحميس، والحوار، والخاتمة، ومواضع المغادرة المرجّحة)
   ثم التفريغ الحرفيّ بتوقيته. ثم نافذةُ الأكشن الأشدّ (90 ث بإطارٍ كلّ ثانية): اللقطات والحركة والمؤثّرات وجُمل الراوي.
2) الريلزات: الريلز كاملاً بإطارٍ كلّ ثانية: الثانية الأولى والثلاث الأولى، والنصّ على الشاشة، والإيقاع، والخاتمة والإحالة.
3) المصغّرات: صورة كلّ مصغّرة من i.ytimg.com مع عنوانها ومشاهداتها: النصّ والتكوين والوجوه واللون وفجوة الفضول.
4) صفحة الفيديو عبر yt-dlp إن أتاحها يوتيوب للعدّاء (أفضل جهد): خريطة «الأكثر إعادة» والفصول والترجمة الآلية.

⛔ تفريغ أفلام المنافسين نصٌّ محميّ، وتحليلات قناتنا خاصّة ⇒ التقرير إلى الإصدار المسوّد الخاصّ channel-stats وحده.
⛔ المفاتيح من سرّ GEMINI_KEYS_JSON في ملفٍّ مؤقّت، ولا يُطبع رابط نداءٍ فيه مفتاح.
الاستعمال: python tools/style_study.py <out.json> --keys /tmp/keys.json [--resume <prev.json>] [--only films,reels,thumbs,page]"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openings import Gem, MAX_TRIES, json_out  # noqa: E402
from voice_lab import keys_from  # noqa: E402

YT = 'https://www.youtube.com/watch?v='
MARK = '===TRANSCRIPT==='
ACTION_S = 90

FILM_PROMPT = """أنت محلّلُ أسلوبٍ وبقاءٍ لمشاهدي يوتيوب. أمامك فيلمٌ وثائقيٌّ تاريخيٌّ كامل (إطارٌ كلّ بضع ثوانٍ مع الصوت كلّه).
حلّل ما تسمعه وتراه فعلاً لا ما تتوقّعه، والأوقات بالثواني من بداية الفيلم.
اكتب أوّلاً كائنَ JSON واحداً بالمفاتيح الآتية، ثم سطراً فيه ===TRANSCRIPT=== وحده، ثم التفريغ.

مفاتيح JSON:
- duration_s: مدّة الفيلم.
- chapters: الفيلم كلّه مقاطعَ متتالية (من ٢٠ ثانيةً إلى ثلاث دقائق): from، to، role، intensity (١–١٠: شدّة التشويق
  والحماسة كما يحسّها المشاهد)، what (سطرٌ بالعربية). وrole واحدةٌ من: hook، greeting، channel_intro، method_or_sources،
  engagement_ask، context، story_scene، battle_action، dialogue، poetry، faith_reflection، analysis_or_lesson،
  map_or_strategy، teaser، recap، outro، next_episode.
- rehooks: كلُّ لحظةٍ يُفتح فيها سؤالٌ أو وعدٌ أو تعليقٌ يشدّ إلى ما بعده: s، kind (question|promise|cliffhanger|reveal|
  countdown|contrast|threat)، text (حرفيّاً).
- action_scenes: مشاهد القتال والحركة: from، to، intensity، narration (كيف تُروى: طول الجمل، والزمن، والضمير، والأفعال)،
  visual (اللقطات والحركة والمؤثّرات)، sound (المؤثّرات والأصوات والموسيقى).
- hype: تقنيات التحميس والتشويق المستعملة فعلاً: s، technique (بالعربية)، example (حرفيّاً).
- dialogue: الجمل التي تقولها الشخصيّات بأصواتها لا الراوي: s، speaker، text.
- ending: {from: بداية الخاتمة، what، outro_s: بداية ما بعد القصّة (شكرٌ أو طلبٌ أو تعريف) أو null، next_episode: هل يمهّد
  لحلقةٍ تالية، last_line: آخر جملةٍ حرفيّاً}.
- narrator: {on_screen: هل يظهر راوٍ أو مقدّم، persona: وصفه في سطر، voice_range: low|medium|high (مدى تلوّن الأداء)،
  pace_wpm: كلماتٌ في الدقيقة تقديراً}.
- sound: {music: هل توجد موسيقى، music_kind، sfx: none|low|medium|high، silence_use: هل يُستعمل الصمت للتأثير}.
- visual: {kind: ai_stills_camera_move|ai_animated|cartoon_or_anime|live_action|presenter|mixed، shots_per_min: تقديراً،
  maps: هل تُستعمل خرائط، on_screen_text: none|low|medium|high}.
- drop_risks: حتى ستّ لحظاتٍ يُرجَّح أن يغادر فيها المشاهد: s، why.
- strengths: حتى ستّة أسبابٍ تجعل المشاهد يكمل إلى النهاية (بالعربية).

التفريغ: سطرٌ لكلّ جملةٍ منطوقة بالصيغة: [الثانية] (المتكلّم) النصّ — حرفيّاً بلغته كما قيل،
والمتكلّم: راوٍ، أو اسم الشخصيّة، أو منشد. ولا تلخّص ولا تحذف شيئاً من الكلام."""

ACTION_PROMPT = """أمامك مقطعُ أكشن من فيلمٍ تاريخيّ (إطارٌ كلّ ثانية مع الصوت). صفه وصفاً دقيقاً قابلاً للتقليد. JSON وحده:
- shots: عدد اللقطات المختلفة، وshot_s: متوسّط طول اللقطة بالثواني.
- camera: حركات الكاميرا المستعملة (قائمة بالعربية).
- effects: المؤثّرات البصريّة (اهتزاز، وميض، إبطاء، تسريع، جسيمات، غبار، نار، نصّ، خريطة…) (قائمة).
- sound_layers: طبقات الصوت (سيوف، خيل، صيحات، تنفّس، نبض، صمت، موسيقى…) (قائمة).
- narration: كلام الراوي في المقطع حرفيّاً.
- sentence_words: متوسّط عدد كلمات الجملة المنطوقة.
- animated: true إن كانت الشخصيّات تتحرّك فعلاً، وfalse إن كانت صوراً ثابتةً تتحرّك عليها الكاميرا.
- techniques: ما الذي يجعل المقطع حماسيّاً (حتى خمسة، بالعربية، محدّدةً قابلةً للتطبيق)."""

REEL_PROMPT = """أمامك ريلز (فيديو قصير) عن التاريخ. حلّل ما تسمعه وتراه فعلاً. JSON وحده:
- first_1s: ما يُرى ويُسمع في الثانية الأولى.
- first_3s: ما يُقال ويُكتب في أوّل ثلاث ثوانٍ حرفيّاً.
- hook_kind: question|shock_claim|action_shot|mystery|number|quote|direct_address|other.
- transcript: الكلام كلّه حرفيّاً.
- on_screen_text: النصّ المكتوب على الشاشة (قائمة: s وtext).
- shots: عدد اللقطات، وcuts_per_10s.
- arc: هل يروي قصّةً كاملة أم مقطعاً منها، وpeak_s: ثانية الذروة.
- ending: {last_line، loop: هل تعود النهاية إلى البداية، cta: طلبٌ أو إحالةٌ إلى فيلمٍ أو جزءٍ تالٍ (نصّه أو فارغ)}.
- voice: {kind: human|synthetic|unsure، emotion: ١–٥، pace: slow|medium|fast}.
- music، sfx: true/false.
- visual: ai_stills_camera_move|ai_animated|cartoon_or_anime|live_action|presenter|mixed.
- why_viral: لماذا انتشر (حتى ثلاثة، بالعربية)."""

THUMB_PROMPT = """أمامك مصغّراتُ أفلامٍ يوتيوب عن التاريخ، وقبل كلّ صورةٍ رقمُها وعنوانها ومشاهداتها.
أجب بقائمة JSON وحدها، عنصرٌ لكلّ مصغّرةٍ بترتيبها بهذه المفاتيح:
- i: رقمها.
- text: النصّ المكتوب على الصورة حرفيّاً (فارغ إن لم يوجد)، وwords: عدد كلماته.
- focal: العنصر المحوريّ (شخص، سلاح، جيش، مبنى، خريطة، وجهٌ غاضب…).
- face: هل يظهر وجهٌ بشريٌّ واضح، وface_emotion.
- revered_face: هل يظهر وجهُ صحابيٍّ أو قائدٍ مسلمٍ معظّم، وكيف: shown|veiled|from_behind|silhouette|light|none.
- colors: الألوان الغالبة، وcontrast: ١–٥.
- composition: التكوين في سطر.
- curiosity: فجوة الفضول بين الصورة والعنوان في سطر.
- style: ai_realistic|anime|painting|photo|graphic.
- clutter: ١–٥.
- readable_small: هل تُقرأ وتُفهم على شاشة هاتفٍ صغيرة."""


def film_body(vid: str, light: bool, dur_s: float) -> bytes:
    """إطارٌ كلّ خمس ثوانٍ (وكلّ عشرٍ لما جاوز نصف الساعة) بدقّةٍ منخفضة، والصوت كلّه: نحو 45 رمزاً في الثانية بدل 98.
    light: بلا دقّة وسائط — لنموذجٍ يرفضها (400). ويبقى معدّل الإطارات: بدونه يقارب فيلمُ ساعةٍ حدَّ المليون رمز."""
    part = {'fileData': {'fileUri': YT + vid}, 'videoMetadata': {'fps': 0.2 if dur_s <= 1800 else 0.1}}
    cfg = {'temperature': 0.1, 'maxOutputTokens': 60000}
    if not light:
        cfg['mediaResolution'] = 'MEDIA_RESOLUTION_LOW'
    return json.dumps({'contents': [{'parts': [part, {'text': FILM_PROMPT}]}], 'generationConfig': cfg}).encode('utf-8')


def clip_body(vid: str, light: bool, prompt: str, a: float | None = None, b: float | None = None) -> bytes:
    part = {'fileData': {'fileUri': YT + vid}}
    if a is not None:
        part['videoMetadata'] = {'startOffset': '%ds' % a, 'endOffset': '%ds' % b}
    cfg = {'temperature': 0.1, 'responseMimeType': 'application/json'}
    if not light:
        cfg['mediaResolution'] = 'MEDIA_RESOLUTION_LOW'
    return json.dumps({'contents': [{'parts': [part, {'text': prompt}]}], 'generationConfig': cfg}).encode('utf-8')


def parse_film(txt: str) -> dict:
    """JSON التحليل أوّلاً ثم التفريغ: إن قُطع الجواب في التفريغ بقي التحليل وما وصل من التفريغ."""
    head, _, tail = txt.partition(MARK)
    out = json_out(head)
    out['transcript'] = tail.strip()
    out['_lines'] = len(re.findall(r'^\s*\[\d', out['transcript'], re.M))
    return out


def parse_list(txt: str) -> dict:
    return {'items': json.loads(re.search(r'\[.*\]', txt, re.S).group(0))}


def strongest_action(a: dict, dur_s: float) -> tuple[float, float] | None:
    """أشدّ مشهد أكشن (ثم أشدّ فصل battle_action) ⇒ نافذةٌ من 90 ث تبدأ عنده."""
    cands = [(x.get('intensity') or 0, x.get('from')) for x in a.get('action_scenes') or [] if x.get('from') is not None]
    cands += [(x.get('intensity') or 0, x.get('from')) for x in a.get('chapters') or []
              if x.get('role') == 'battle_action' and x.get('from') is not None]
    if not cands:
        return None
    s = float(max(cands)[1])
    end = dur_s or a.get('duration_s') or s + ACTION_S
    s = max(0.0, min(s, float(end) - ACTION_S))
    return s, s + ACTION_S


def page(vid: str) -> dict:
    """صفحة الفيديو عبر yt-dlp: خريطة الأكثر إعادة والفصول والترجمة الآلية العربية — أفضل جهد (قد يطلب يوتيوب تحقّقاً)."""
    try:
        p = subprocess.run(['yt-dlp', '-J', '--skip-download', '--no-warnings', '--no-playlist', YT + vid],
                           capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)[:200]}
    if p.returncode != 0:
        return {'error': re.sub(r'\s+', ' ', p.stderr)[-240:]}
    j = json.loads(p.stdout)
    out = {k: j.get(k) for k in ('duration', 'view_count', 'like_count', 'comment_count', 'channel_follower_count',
                                 'upload_date', 'chapters', 'heatmap', 'title')}
    out['description'] = (j.get('description') or '')[:3000]
    for src in ('subtitles', 'automatic_captions'):
        fmts = (j.get(src) or {}).get('ar') or (j.get(src) or {}).get('ar-orig') or []
        url = next((f['url'] for f in fmts if f.get('ext') == 'json3'), None)
        if not url:
            continue
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                ev = json.loads(r.read().decode('utf-8')).get('events') or []
            out['captions_' + src] = [[round(e.get('tStartMs', 0) / 1000, 1), ''.join(s.get('utf8', '') for s in e['segs'])]
                                      for e in ev if e.get('segs')]
            break
        except Exception as e:  # noqa: BLE001
            out['captions_error'] = str(e)[:200]
    return out


def thumb(vid: str) -> bytes | None:
    for name in ('maxresdefault', 'hqdefault'):
        try:
            with urllib.request.urlopen('https://i.ytimg.com/vi/%s/%s.jpg' % (vid, name), timeout=30) as r:
                b = r.read()
            if len(b) > 5000:
                return b
        except Exception:  # noqa: BLE001
            continue
    return None


def thumbs_body(batch: list, light: bool) -> bytes:
    parts = []
    for i, (f, img) in enumerate(batch, 1):
        parts.append({'text': '%d) %s — %s مشاهدة' % (i, f.get('العنوان', ''), f.get('المشاهدات', '?'))})
        parts.append({'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(img).decode('ascii')}})
    parts.append({'text': THUMB_PROMPT})
    cfg = {'temperature': 0.1, 'responseMimeType': 'application/json'}
    return json.dumps({'contents': [{'parts': parts}], 'generationConfig': cfg}).encode('utf-8')


class Study:
    def __init__(self, req: dict, prev: dict, out: str, g):
        self.req, self.prev, self.out, self.g = req, prev, out, g
        self.res = {k: dict() for k in ('الأفلام', 'الريلزات', 'المصغّرات')}
        self.lock = threading.Lock()
        for k in self.res:
            want = {f['id'] for f in req.get(k) or []}
            self.res[k] = {i: f for i, f in (prev.get(k) or {}).items() if i in want and 'error' not in f}

    def todo(self, k: str) -> list:
        pk = self.prev.get(k) or {}
        return [f for f in self.req.get(k) or [] if f['id'] not in self.res[k]
                and pk.get(f['id'], {}).get('_tries', 1 if f['id'] in pk else 0) < MAX_TRIES]

    def put(self, k: str, f: dict, r: dict) -> None:
        if 'error' in r:
            pk = self.prev.get(k) or {}
            r['_tries'] = pk.get(f['id'], {}).get('_tries', 1 if f['id'] in pk else 0) + 1
        with self.lock:
            self.res[k][f['id']] = {kk: v for kk, v in f.items()} | r
            self.save()

    def save(self) -> None:
        rep = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
               'نجح': {k: sum('error' not in v for v in self.res[k].values()) for k in self.res},
               'المطلوب': {k: len(self.req.get(k) or []) for k in self.res}}
        for k in self.res:
            rep[k] = [self.res[k][f['id']] for f in self.req.get(k) or [] if f['id'] in self.res[k]]
        tmp = self.out + '.tmp'
        json.dump(rep, io.open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(tmp, self.out)

    # ———— المهامّ ————
    def film(self, f: dict, with_page: bool) -> dict:
        dur = float(f.get('الطول_ث') or 60 * float(f.get('الطول_د') or 0) or 1500)
        r = self.g.call(lambda light: film_body(f['id'], light, dur), f['id'], budget_s=1200, parse=parse_film, cap_s=900)
        if 'error' not in r:
            win = strongest_action(r, dur)
            if win:
                a = self.g.call(lambda light: clip_body(f['id'], light, ACTION_PROMPT, *win), f['id'] + '#أكشن', budget_s=300)
                r['action'] = a | {'from': win[0], 'to': win[1]}
        if with_page:
            r['page'] = page(f['id'])
        return r

    def reel(self, f: dict) -> dict:
        return self.g.call(lambda light: clip_body(f['id'], light, REEL_PROMPT), f['id'], budget_s=300)

    def run(self, only: set, workers: int) -> None:
        t0 = time.time()
        jobs = []
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            if 'films' in only:
                for f in self.todo('الأفلام'):
                    jobs.append((ex.submit(self.film, f, 'page' in only), 'الأفلام', f))
            if 'reels' in only:
                for f in self.todo('الريلزات'):
                    jobs.append((ex.submit(self.reel, f), 'الريلزات', f))
            if 'thumbs' in only:
                todo = self.todo('المصغّرات')
                imgs = [(f, thumb(f['id'])) for f in todo]
                for f, img in imgs:
                    if img is None:
                        self.put('المصغّرات', f, {'error': 'لم تُجلب الصورة'})
                ok = [(f, img) for f, img in imgs if img is not None]
                for i in range(0, len(ok), 6):
                    batch = ok[i:i + 6]
                    jobs.append((ex.submit(self.g.call, lambda light, b=batch: thumbs_body(b, light),
                                           'مصغّرات%d' % i, 300, parse_list), 'المصغّرات', batch))
            for fu in cf.as_completed([j[0] for j in jobs]):
                fu_, k, f = next(j for j in jobs if j[0] is fu)
                try:
                    r = fu.result()
                except Exception as e:  # noqa: BLE001
                    r = {'error': str(e)[:200]}
                if k == 'المصغّرات':
                    items = {int(x.get('i', 0)): x for x in r.get('items') or [] if isinstance(x, dict)}
                    for n, (ff, _) in enumerate(f, 1):
                        self.put(k, ff, items.get(n) or {'error': r.get('error') or 'لا جواب لهذه الصورة'})
                    print('%s [%4d ث] مصغّرات %d' % ('✅' if items else '⛔', time.time() - t0, len(f)), flush=True)
                    continue
                self.put(k, f, r)
                print('%s [%4d ث] %-9s %-12s %-38s %s' % (
                    '✅' if 'error' not in r else '⛔', time.time() - t0, k, f['id'], f.get('الوسم', '')[:38],
                    r.get('error', '')[:110] or ('سطور=%s أكشن=%s صفحة=%s' % (
                        r.get('_lines'), 'action' in r and 'error' not in r['action'],
                        'page' in r and 'error' not in r['page']) if k == 'الأفلام' else r.get('_model'))), flush=True)
        self.save()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--resume', help='تقريرٌ سابق: يُبقى ما نجح، ويُعاد ما فشل (حتى MAX_TRIES) وما لم يُدرس')
    ap.add_argument('--only', default='films,reels,thumbs,page')
    a = ap.parse_args()
    keys = keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي'); return 1
    req = json.load(io.open(os.path.join('ops', 'stats', 'style.json'), encoding='utf-8'))
    prev = {}
    if a.resume and os.path.exists(a.resume):
        p = json.load(io.open(a.resume, encoding='utf-8'))
        prev = {k: {f['id']: f for f in p.get(k) or []} for k in ('الأفلام', 'الريلزات', 'المصغّرات')}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    st = Study(req, prev, a.out, Gem(keys))
    print('مفاتيح: %d | للدراسة: أفلام %d، ريلزات %d، مصغّرات %d | محفوظ: %s' % (
        len(keys), len(st.todo('الأفلام')), len(st.todo('الريلزات')), len(st.todo('المصغّرات')),
        {k: len(v) for k, v in st.res.items()}), flush=True)
    st.run(set(a.only.split(',')), a.workers)
    ok = sum(sum('error' not in v for v in st.res[k].values()) for k in st.res)
    print('نجح %d' % ok)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
