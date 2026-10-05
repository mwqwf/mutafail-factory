# -*- coding: utf-8 -*-
"""تشريحُ الافتتاحيات — لماذا يبقى مشاهدُ غيرنا ويغادر مشاهدُنا؟ (سؤال المالك 2026-10-05:
«لماذا قنواتٌ أخرى لا تقدّم الجودة التي نقدّمها يحتفظون بالمشاهد أكثر؟»).

نصفُ مشاهدينا الطبيعيّين يغادرون في أوّل ثلاثين ثانية (منحنى البقاء الطبيعيّ في channel_stats)، فالمقارنة هنا
على أوّل دقيقتين ونصف وحدها: يُعطى جيميناي رابطَ كلّ فيلمٍ على يوتيوب (يجلبه بنفسه من خوادم غوغل، فلا حجبَ ولا تنزيل)
مقصوراً على [0، 150 ث]، ويُسأل **بالمعيار نفسه لكلّ الأفلام** — ولا يُقال له أيُّها لنا — عن: التفريغ الحرفيّ، وأوّل
حدثٍ قصصيّ، والتحيّة والتعريف بالقناة والمنهج، والسؤال المعلّق، والشخصيّة، وكثافة الأسماء، واللقطات، والصوت ونبرته،
والأسلوب البصريّ وجودته، وسبب البقاء وسبب المغادرة.

القائمة في ops/stats/openings.json: {"الأفلام":[{"id","الجهة":"نحن"|"منافس","الوسم"}]} — والوسم والجهة لا يُرسلان.
الاستعمال: python tools/openings.py <out.json> --keys /tmp/keys.json [--workers 4]
⛔ المفاتيح من سرّ GEMINI_KEYS_JSON في الملفّ المؤقّت وحده؛ والتقرير إلى الإصدار المسوّد الخاصّ channel-stats."""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import io
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_lab import keys_from  # noqa: E402

MODELS = ['gemini-3.5-flash', 'gemini-flash-latest', 'gemini-3.8-flash', 'gemini-3.5-pro', 'gemini-pro-latest',
          # ⛔ الشوط 37313830497: نفدت حصّة اليوم للنماذج الخمسة بعد 13 فيلماً ⇒ الخفيفان آخراً، ولكلٍّ حصّته المستقلّة
          'gemini-3.5-flash-lite', 'gemini-flash-lite-latest']
MAX_TRIES = 3          # محاولات الاستئناف القصوى للفيلم الواحد عبر الأشواط (فيديو خاصٌّ أو محجوب لا يُطارَد للأبد)
END_S = 150

PROMPT = """أنت محلّلُ بقاءٍ لمشاهدي يوتيوب. أمامك أوّلُ ١٥٠ ثانيةً من فيلمٍ وثائقيٍّ تاريخيّ طويل.
حلّل ما تسمعه وتراه فعلاً، لا ما تتوقّعه. والأرقامُ بالثواني من بداية المقطع. أجب بـJSON وحده بهذه المفاتيح:
- t30: الكلامُ المنطوق حرفيّاً في أوّل ٣٠ ثانية بلغته كما قيل (عربيّاً أو إنجليزيّاً).
- t150: الكلامُ المنطوق حرفيّاً من ٣٠ إلى ١٥٠ ثانية.
- segments: تقسيمُ الـ١٥٠ ثانية إلى مقاطع متتالية: from وto وwhat (ما يحدث بالعربية) وrole، وrole واحدةٌ من:
  hook، greeting، channel_intro، method_or_sources، engagement_ask، context، story_scene، teaser، title_card.
- first_scene_s: الثانيةُ التي يبدأ فيها أوّلُ حدثٍ قصصيٍّ ملموس (شخصٌ يفعل شيئاً في مكانٍ وزمان) — لا تمهيدٌ عامّ.
- greeting / channel_intro / method_or_sources / engagement_ask: لكلٍّ {present، s، text}: هل وُجدت تحيّةٌ أو ترحيب،
  أو تعريفٌ بالقناة أو السلسلة، أو ذكرٌ للمصادر والمنهج، أو طلبُ اشتراكٍ وإعجاب — وثانيتُها ونصُّها.
- open_question: {text، s}: السؤالُ أو الوعدُ الذي يجعل المشاهدَ ينتظر الجواب، وثانيةُ طرحه (فارغٌ إن لم يوجد).
- character: {name، s، personal}: الشخصيّةُ المحوريّة، وثانيةُ ظهورها، وهل يُقدَّم لها بُعدٌ شخصيٌّ أو عاطفيّ.
- names_30 وnumbers_30: عددُ أسماء الأعلام، وعددُ التواريخ والأرقام، المنطوقة في أوّل ٣٠ ثانية.
- cuts_30: عددُ اللقطات المختلفة (القطعات البصرية) في أوّل ٣٠ ثانية.
- voice: {kind: human|synthetic|unsure، gender، emotion: ١–٥، pace: slow|medium|fast، varies: هل يتغيّر الأداءُ مع المعنى
  (همسٌ وشدّةٌ ووقفات) أم يبقى على وتيرةٍ واحدة}.
- music، sfx، character_dialogue: هل توجد موسيقى، ومؤثّراتٌ صوتية، وحوارٌ بأصوات الشخصيات.
- on_screen_text: ما يُكتب على الشاشة إن وُجد.
- visual: واحدٌ من: ai_stills_camera_move، ai_animated، cartoon_or_anime، live_action، presenter، mixed.
- image_quality: من ١ إلى ٥ (الإتقان التقنيّ للصورة وحده).
- stay_reasons: ما يجعل المشاهدَ يكمل بعد الدقيقة الأولى (حتى ثلاثة، بالعربية).
- leave_reasons: ما قد يجعله يغادر في أوّل ٣٠ ثانية (حتى ثلاثة، بالعربية).
- hook: {score: ١–١٠، why: العلّة في سطرٍ بالعربية}.
"""

S, I, B, N = {'type': 'STRING'}, {'type': 'INTEGER'}, {'type': 'BOOLEAN'}, {'type': 'NUMBER'}
FLAG = {'type': 'OBJECT', 'required': ['present'], 'properties': {'present': B, 's': N, 'text': S}}
SCHEMA = {'type': 'OBJECT', 'required': ['t30', 'segments', 'first_scene_s', 'greeting', 'channel_intro', 'method_or_sources',
                                        'voice', 'visual', 'hook'],
          'properties': {
              't30': S, 't150': S,
              'segments': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'required': ['from', 'to', 'role'],
                                                      'properties': {'from': N, 'to': N, 'what': S, 'role': S}}},
              'first_scene_s': N, 'greeting': FLAG, 'channel_intro': FLAG, 'method_or_sources': FLAG, 'engagement_ask': FLAG,
              'open_question': {'type': 'OBJECT', 'properties': {'text': S, 's': N}},
              'character': {'type': 'OBJECT', 'properties': {'name': S, 's': N, 'personal': B}},
              'names_30': I, 'numbers_30': I, 'cuts_30': I,
              'voice': {'type': 'OBJECT', 'required': ['kind'], 'properties': {
                  'kind': S, 'gender': S, 'emotion': I, 'pace': S, 'varies': B}},
              'music': B, 'sfx': B, 'character_dialogue': B, 'on_screen_text': S,
              'visual': S, 'image_quality': I,
              'stay_reasons': {'type': 'ARRAY', 'items': S}, 'leave_reasons': {'type': 'ARRAY', 'items': S},
              'hook': {'type': 'OBJECT', 'required': ['score'], 'properties': {'score': I, 'why': S}}}}


def body(vid: str, light: bool) -> bytes:
    """light: بلا مخطّطٍ صارم ولا دقّة وسائط — لنموذجٍ يرفض أحدهما (400). ومعدّل الإطارات الافتراضيّ (إطارٌ في الثانية):
    ⛔ الشوط 37313830497 طال جداً، و fps=2 تضاعف الرموز فتقرب من حدّ الرموز في الدقيقة للطبقة المجّانية."""
    part = {'fileData': {'fileUri': 'https://www.youtube.com/watch?v=' + vid},
            'videoMetadata': {'startOffset': '0s', 'endOffset': '%ds' % END_S}}
    cfg = {'temperature': 0.1, 'responseMimeType': 'application/json'}
    if not light:
        cfg.update(responseSchema=SCHEMA, mediaResolution='MEDIA_RESOLUTION_LOW')
    return json.dumps({'contents': [{'parts': [part, {'text': PROMPT}]}], 'generationConfig': cfg}).encode('utf-8')


def json_out(txt: str) -> dict:
    return json.loads(re.search(r'\{.*\}', txt, re.S).group(0))


class Gem:
    def __init__(self, keys: list[str]):
        self.keys, self.dead = keys, {}

    def video(self, vid: str, budget_s: int = 420) -> dict:
        return self.call(lambda light: body(vid, light), vid, budget_s)

    def call(self, mk, tag: str, budget_s: int = 420, parse=json_out, cap_s: int = 240) -> dict:
        """mk(light) يبني جسم النداء، وparse(النصّ) يستخرج الجواب (وإخفاقُه يجرّب نموذجاً آخر) — تستعمله دراسة الأسلوب أيضاً.
        موعدٌ نهائيّ لكلّ طلب (لا تكرار بلا نهاية)، وكلُّ إخفاقٍ يُطبع مختصراً — بلا رابط النداء لأنّ فيه المفتاح."""
        vid = tag
        last, refused, t_end, seen = '', set(), time.time() + budget_s, set()
        while time.time() < t_end:
            tried = False
            for light in (False, True):
                for model in MODELS:
                    if (model, light) in refused or time.time() >= t_end:
                        continue
                    ks = [k for k in self.keys if k not in self.dead.setdefault(model, set())]
                    if not ks:
                        continue
                    tried, key = True, random.choice(ks)
                    req = urllib.request.Request(
                        'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, key),
                        data=mk(light), headers={'content-type': 'application/json'})
                    try:
                        with urllib.request.urlopen(req, timeout=max(30, min(cap_s, t_end - time.time()))) as r:
                            j = json.loads(r.read().decode('utf-8'))
                        cand = j['candidates'][0]
                        txt = ''.join(p.get('text', '') for p in cand['content']['parts'] if not p.get('thought'))
                        out = parse(txt)
                        out['_model'], out['_light'] = model, light
                        out['_tokens'] = j.get('usageMetadata', {}).get('totalTokenCount')
                        if cand.get('finishReason') not in (None, 'STOP'):
                            out['_finish'] = cand.get('finishReason')
                        return out
                    except urllib.error.HTTPError as e:
                        msg = e.read().decode('utf-8', 'ignore')
                        last = '%s %s: %s' % (model, e.code, re.sub(r'\s+', ' ', msg)[:200])
                        if 'model' in msg.lower() and (e.code == 404 or 'not found' in msg.lower()):
                            self.dead[model] = set(self.keys)      # النموذج غير موجود: يسقط فوراً بلا كلفة
                        elif e.code == 429 and 'PerDay' in msg:
                            self.dead[model].add(key)
                        elif e.code == 403:
                            self.dead[model].add(key)
                        elif e.code == 400:
                            refused.add((model, light))
                        time.sleep(3 if e.code != 429 else 15)
                    except Exception as e:
                        last = '%s: %s' % (model, str(e)[:200])
                        time.sleep(3)
                    sig = last[:60]
                    if sig not in seen:              # كلُّ نوعِ إخفاقٍ مرّةً واحدة لكلّ فيلم: سجلٌّ عامّ لا يُغرق
                        seen.add(sig)
                        print('   ↻ %s %s' % (vid, last[:160]), flush=True)
            if not tried or len(refused) >= 2 * len(MODELS):
                break                       # لا نموذج ولا مفتاح صالح، أو رفضه الكلّ بالصيغتين: الفيديو نفسه
        return {'error': last or 'لا مفاتيح صالحة'}


def report(films: list, res: dict) -> dict:
    ok = sum('error' not in v for v in res.values())
    return {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'المقطع_ث': END_S, 'نجح': ok, 'المطلوب': len(films),
            'الأفلام': [res[f['id']] | {'id': f['id']} for f in films if f['id'] in res]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--resume', help='تقريرٌ سابق: يُبقى ما نجح فيه، ويُعاد ما فشل (حتى MAX_TRIES) وما لم يُحلَّل')
    a = ap.parse_args()
    keys = keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي'); return 1
    films = json.load(io.open(os.path.join('ops', 'stats', 'openings.json'), encoding='utf-8'))['الأفلام']
    res, prev = {}, {}
    if a.resume and os.path.exists(a.resume):
        prev = {f['id']: f for f in json.load(io.open(a.resume, encoding='utf-8')).get('الأفلام', [])}
        res = {i: f for i, f in prev.items() if 'error' not in f and i in {x['id'] for x in films}}
    todo = [f for f in films if f['id'] not in res and prev.get(f['id'], {}).get('_tries', 1 if f['id'] in prev else 0) < MAX_TRIES]
    g = Gem(keys)
    print('مفاتيح: %d | أفلام: %d | محفوظٌ من قبل: %d | للتحليل: %d | المقطع: 0–%d ث' % (
        len(keys), len(films), len(res), len(todo), END_S), flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(g.video, f['id']): f for f in todo}
        for fu in cf.as_completed(futs):
            f = futs[fu]
            r = fu.result()
            if 'error' in r:
                r['_tries'] = prev.get(f['id'], {}).get('_tries', 1 if f['id'] in prev else 0) + 1
            res[f['id']] = {'الجهة': f['الجهة'], 'الوسم': f['الوسم'], **r}
            # ⛔ الشوط 37313830497 تجاوز عشرين دقيقة: يُكتب التقرير بعد كلّ فيلم، فإن انقضت مهلة الخطوة رُفع ما اكتمل
            json.dump(report(films, res), io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('%s [%3d ث] %-12s %-40s خطاف=%s مشهد=%s %s' % (
                '✅' if 'error' not in r else '⛔', time.time() - t0, f['id'], f['الوسم'][:40],
                (r.get('hook') or {}).get('score'), r.get('first_scene_s'), r.get('error', '')[:120]), flush=True)
    json.dump(report(films, res), io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum('error' not in v for v in res.values())
    print('نجح %d من %d' % (ok, len(films)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
