# -*- coding: utf-8 -*-
"""المؤثّرات بإشاراتٍ من السيناريو لا بالحشو — أمر المالك 2026-11-27:
«المؤثّرات الحالية غير كافية وأحياناً مزعجة في بعض الأماكن، فكلّ مؤثّر يجب أن يكون له مكانه المناسب لا أن يوضع عشوائياً».

ما كان (تدقيق أجنادين، `ops/PRODUCTION_QUALITY_2026-11-27.md`): مؤثّرٌ لكلّ لقطة (146 من 146) يُشتقّ بكلمةٍ جزئية،
يُختار ملفّه بالبذرة من 2–3 ملفّات فيتكرّر أوّله نفسه، ويُشغَّل بمستوى ثابت مهما كانت جهارته، وحفيفٌ على كلّ انتقال.

ما صار: ورقة إشارات `<proj>/sfx_cues.json` يكتبها كاتب السيناريو/المونتير، كلّ إشارةٍ فيها حدثٌ مسمّى من EVENTS
مربوطٌ بكلمةٍ في نصّ الكتلة (anchor) أو بوصفٍ بصريّ صريح (visual)، ومعها سببها (why). لا شيء خارج الورقة يُسمع.

    {"key_blocks": ["d_046"],                       # جملٌ مفتاحية: لا مؤثّر فوقها (غير silence)
     "cues": [{"id": "c01", "block": "d_001", "event": "wind", "anchor": "خيل", "dur": 9,
               "why": "الافتتاح على كثيب مكشوف", "level": -24}]}

البوّابة (`lint` على الورقة قبل المونتاج، و`mix_gate` على المسار المصيَّر بعده) تفشل عند:
  • حدثٍ مجهول أو بلا سبب، أو مرساةٍ ليست في نصّ الكتلة ولا وصف بصريّ (غير مُسوَّغ).
  • مؤثّرٍ فوق جملةٍ مفتاحية (حديث نبويّ، شهادة، ذروة) — الصمت وحده يُسمح فيها.
  • كثافةٍ فوق DENSITY_SPOT نقطةً في أيّ دقيقة، أو أكثر من BEDS_MAX فرشٍ متزامن، أو نقطتين أقرب من SPOT_GAP ث.
  • تكرار: الحدث النقطيّ نفسه أكثر من REPEAT_MAX مرّات في دقيقة، أو الملفّ نفسه قبل REUSE_S ثانية.
  • مستوى تحت الكلام أعلى من −18 dB نسبةً للصوت (الفرش ≤ −22)، أو مستوى بين الجمل أعلى من −8.
  • بعد التصيير: نافذةُ كلامٍ يعلو فيها المسار عن −12 dB نسبةً للصوت، أو وسيطٌ أعلى من −18، أو ذروةٌ فوق −6 dBFS،
    أو حدّةٌ (2–6 كيلوهرتز) فوق 0.45 في النوافذ المسموعة، أو مؤثّرٌ مسموعٌ فوق جملةٍ مفتاحية.
⛔ لا موسيقى ولا آلات ولا طبول: الأحداث كلّها أصواتٌ طبيعية من `assets/sfx` (CC0) وتمرّ بـ`tonal_gate`.

    python3 tools/sfx_cues.py lint   <proj>                 # فحص الورقة
    python3 tools/sfx_cues.py draft  <proj>                 # مسودّة إشاراتٍ من الكلمات (اقتراحٌ يُراجَع، لا يُستعمل كما هو)
    python3 tools/sfx_cues.py render <proj> <voice.wav> <out.wav>   # يصيّر المسار المدكوك تحت الكلام
    python3 tools/sfx_cues.py gate   <proj> <voice.wav> <sfx.wav>   # فحص المسار المصيَّر
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SFX_DIR = os.path.join(os.path.dirname(HERE), 'assets', 'sfx')
SR = 48000
SEC_PER_WORD = 0.5627            # معايرة أجنادين (حين لا يوجد صوتٌ مولَّد بعد)
HARAKAT = re.compile(r'[\u064b-\u0652\u0670\u0640]')

# الحدث ⇒ (صنف المكتبة، النوع، المستوى الافتراضيّ تحت الكلام dB نسبةً للصوت)
# spot = نقطة قصيرة لحظة الفعل · bed = فرشُ مكانٍ متّصل بتلاشٍ طويل · silence = إسكاتُ كلّ المؤثّرات
EVENTS = {
    'hooves': ('hooves', 'spot', -20), 'gallop': ('horses', 'bed', -22), 'horse_snort': ('horsesnort', 'spot', -20),
    'sword_clash': ('swords', 'spot', -19), 'battle': ('battle', 'bed', -22), 'sword_draw': ('sworddraw', 'spot', -19),
    'arrows': ('arrows', 'spot', -20), 'wind': ('wind', 'bed', -24), 'crowd': ('crowd', 'bed', -23),
    'footsteps': ('footsteps', 'spot', -21), 'marching': ('marching', 'bed', -23), 'camels': ('camels', 'spot', -21),
    'fire': ('fire', 'bed', -23), 'night': ('night', 'bed', -26), 'sea': ('sea', 'bed', -24),
    'banner': ('banner', 'bed', -24), 'tent': ('tent', 'bed', -24), 'leather': ('leather', 'spot', -22),
    'breath': ('breath', 'spot', -22), 'silence': (None, 'silence', None),
}
UNDER_MAX = -18.0       # أعلى مستوى لأيّ مؤثّر تحت الكلام (نسبةً للصوت)
BED_UNDER_MAX = -22.0   # أعلى مستوى للفرش تحت الكلام
GAP_MAX = -8.0          # أعلى مستوى بين الجمل
DENSITY_SPOT = 6        # أقصى نقاط في أيّ 60 ث
BEDS_MAX = 2            # أقصى فرشٍ متزامن
SPOT_GAP = 3.0          # أدنى فاصل بين نقطتين (ث)
REPEAT_MAX = 2          # أقصى تكرارٍ للحدث النقطيّ نفسه في 60 ث
REUSE_S = 60.0          # لا يُعاد الملفّ نفسه قبل هذه المدّة
CEIL_UNDER = -15.0      # سقف المسار تحت الكلام لحظةً بلحظة (dB نسبةً لغلاف الكلام)
GAP_CEIL_DBFS = -12.0   # سقفه بين الجمل
WIN_FAIL = -12.0        # بعد التصيير: نافذة كلامٍ يعلو فيها المسار فوق هذا (نسبةً للصوت) ⇒ فشل
MEDIAN_FAIL = -18.0
PEAK_FAIL = -6.0        # dBFS للمسار
HARSH_FAIL = 0.45
KEY_FAIL = -35.0        # فوق الجمل المفتاحية: المسار تحت هذا (نسبةً للصوت)
# كلام النبي ﷺ المنقول (قال/يقول قبل ذكره، أو «:»/قال بعده قريباً)، والشهادة — لا مجرّد ذكره في السرد
KEY_AUTO = re.compile(r'((قال|فقال|يقول|ويقول)( له| لهم| لاصحابه)? (النبي|رسول الله)|(النبي|رسول الله) صلى الله عليه وسلم[^.!؟]{0,30}'
                      r'(قال|يقول|:)|اشهد ان لا اله الا الله|يجب ما كان قبله)')


def plain(t: str) -> str:
    return HARAKAT.sub('', t or '').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')


def words(t: str) -> list[str]:
    return [w for w in re.split(r'[\s،؛:.!؟?«»…\-]+', plain(t)) if w]


# ── الأزمنة ──────────────────────────────────────────────────────────────────────────────────────
def wav_dur(p: str) -> float:
    with wave.open(p, 'rb') as w:
        return w.getnframes() / float(w.getframerate())


def block_times(proj: str, blocks: list[dict], gap: float = 0.25) -> dict:
    """{id: (بداية، نهاية)} من times.json إن وُجد، وإلا من ملفّات الصوت، وإلا تقديراً بعدد الكلمات."""
    tj = os.path.join(proj, 'times.json')
    if os.path.exists(tj):
        t = json.load(open(tj, encoding='utf-8'))
        if isinstance(t, dict) and all(isinstance(v, (list, tuple)) and len(v) >= 2 for v in t.values()):
            return {k: (float(v[0]), float(v[1])) for k, v in t.items()}
    out, t0 = {}, 0.0
    for b in blocks:
        a = os.path.join(proj, 'audio', b['id'] + '.wav')
        d = wav_dur(a) if os.path.exists(a) else max(1.0, len(words(b['text'])) * SEC_PER_WORD)
        out[b['id']] = (t0, t0 + d)
        t0 += d + gap
    return out


def key_blocks(sheet: dict, blocks: list[dict]) -> set:
    ks = set(sheet.get('key_blocks') or [])
    for b in blocks:
        if b.get('key') or KEY_AUTO.search(plain(b['text'])):
            ks.add(b['id'])
    return ks


def cue_window(c: dict, bt: dict, by: dict) -> tuple[float, float]:
    a, b = bt[c['block']]
    st = a
    if c.get('at') is not None:
        st = a + float(c['at'])
    elif c.get('anchor'):
        ws = words(by[c['block']]['text'])
        an = words(c['anchor'])
        idx = next((i for i in range(len(ws)) if ws[i:i + len(an)] == an or (an and ws[i].endswith(an[0]))), 0)
        st = a + (b - a) * idx / max(1, len(ws))
    st += float(c.get('offset', 0.0))
    kind = EVENTS.get(c.get('event'), (None, 'spot', 0))[1]
    d = float(c.get('dur') or (1.6 if kind == 'spot' else 6.0))
    return st, st + d


# ── فحص الورقة ───────────────────────────────────────────────────────────────────────────────────
def lint(sheet: dict, blocks: list[dict], bt: dict, sfx_dir: str = SFX_DIR) -> list[str]:
    errs = []
    by = {b['id']: b for b in blocks}
    keys = key_blocks(sheet, blocks)
    cues = sheet.get('cues') or []
    if not cues:
        return ['ورقة الإشارات فارغة — طبقة المحيط إلزامية (أمر 2026-11-22) لكن بمواضع مسمّاة']
    spans = []
    for c in cues:
        cid = c.get('id', '?')
        ev = c.get('event')
        if ev not in EVENTS:
            errs.append('%s: حدث مجهول «%s» (المسموح: %s)' % (cid, ev, ' '.join(sorted(EVENTS)))); continue
        if c.get('block') not in by:
            errs.append('%s: كتلة غير موجودة %s' % (cid, c.get('block'))); continue
        if len((c.get('why') or '').strip()) < 6:
            errs.append('%s: بلا سبب (why) — المؤثّر بلا دافعٍ في القصة حشو' % cid)
        anc, vis = (c.get('anchor') or '').strip(), (c.get('visual') or '').strip()
        if anc:
            if not all(w in words(by[c['block']]['text']) or any(x.endswith(w) for x in words(by[c['block']]['text']))
                       for w in words(anc)):
                errs.append('%s: المرساة «%s» ليست في نصّ %s — غير مُسوَّغ' % (cid, anc, c['block']))
        elif len(vis) < 10 and c.get('at') is None:
            errs.append('%s: لا مرساة في النصّ ولا وصف بصريّ (visual) — المؤثّر بلا مكانٍ مسمّى' % cid)
        cat, kind, lvl0 = EVENTS[ev]
        if kind != 'silence':
            if cat and not glob.glob(os.path.join(sfx_dir, '%s_*.ogg' % cat)):
                errs.append('%s: لا ملفّ للصنف %s في المكتبة' % (cid, cat))
            lvl = float(c.get('level', lvl0))
            cap = BED_UNDER_MAX if kind == 'bed' else UNDER_MAX
            if lvl > cap:
                errs.append('%s: المستوى تحت الكلام %+.0f dB أعلى من الحدّ %+.0f' % (cid, lvl, cap))
            gl = float(c.get('gap_level', min(lvl + 8, GAP_MAX)))
            if gl > GAP_MAX:
                errs.append('%s: المستوى بين الجمل %+.0f dB أعلى من %+.0f' % (cid, gl, GAP_MAX))
        st, en = cue_window(c, bt, by)
        spans.append((st, en, kind, ev, cid))
        if kind != 'silence':
            for k in keys:
                if k in bt and st < bt[k][1] - 0.05 and en > bt[k][0] + 0.05:
                    errs.append('%s: %s فوق جملةٍ مفتاحية %s — لا مؤثّر فوقها إلا الصمت' % (cid, ev, k))
    spots = sorted(s for s in spans if s[2] == 'spot')
    for i, s in enumerate(spots):
        win = [x for x in spots if s[0] <= x[0] < s[0] + 60]
        if len(win) > DENSITY_SPOT:
            errs.append('كثافة: %d نقطة في الدقيقة من %.0f ث (الحدّ %d)' % (len(win), s[0], DENSITY_SPOT)); break
    for a, b in zip(spots, spots[1:]):
        if b[0] - a[0] < SPOT_GAP:
            errs.append('%s و%s: نقطتان متقاربتان (%.1f ث < %.0f)' % (a[4], b[4], b[0] - a[0], SPOT_GAP))
    for s in spots:
        same = [x for x in spots if x[3] == s[3] and s[0] <= x[0] < s[0] + 60]
        if len(same) > REPEAT_MAX:
            errs.append('تكرار: %s %d مرّات في دقيقة من %.0f ث (الحدّ %d)' % (s[3], len(same), s[0], REPEAT_MAX)); break
    beds = [s for s in spans if s[2] == 'bed']
    for s in beds:
        live = sum(1 for x in beds if x[0] <= s[0] < x[1])
        if live > BEDS_MAX:
            errs.append('%s: %d فرشٍ متزامن (الحدّ %d)' % (s[4], live, BEDS_MAX)); break
    return errs


# ── الاختيار والتصيير ────────────────────────────────────────────────────────────────────────────
def manifest() -> dict:
    p = os.path.join(SFX_DIR, 'manifest.json')
    return json.load(open(p, encoding='utf-8'))['files'] if os.path.exists(p) else {}


def pick_files(cues: list[dict], spans: list, sfx_dir: str = SFX_DIR, man: dict | None = None) -> list:
    """لكلّ إشارةٍ (ملفّ، بداية داخل الملفّ): تناوبٌ يتجنّب الملفّ نفسه قبل REUSE_S، وبدايةٌ مختلفة كلّ مرّة."""
    man = manifest() if man is None else man
    last, used_off, out = {}, {}, []
    for c, (st, en, kind, ev, cid) in zip(cues, spans):
        cat = EVENTS[ev][0]
        if kind == 'silence' or not cat:
            out.append((None, 0.0)); continue
        fs = [f for f in sorted(glob.glob(os.path.join(sfx_dir, '%s_*.ogg' % cat)))
              if (man.get(os.path.basename(f)) or {}).get('status') != 'reject']
        if c.get('file') and os.path.exists(os.path.join(sfx_dir, c['file'])):
            fs = [os.path.join(sfx_dir, c['file'])] + [f for f in fs if not f.endswith(c['file'])]
        fs.sort(key=lambda f: last.get(f, -1e9))          # الأقدم استعمالاً أوّلاً
        f = fs[0] if fs else None
        if f:
            last[f] = st
            n = used_off.get(f, 0); used_off[f] = n + 1
            try:
                fd = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                          capture_output=True, text=True).stdout.strip())
            except ValueError:
                fd = 0.0
            room = max(0.0, fd - (en - st))
            off = 0.0 if kind == 'spot' and n == 0 else (room * ((n * 0.37) % 1.0) if room > 0 else 0.0)
            out.append((f, round(off, 2)))
        else:
            out.append((None, 0.0))
    return out


def reuse_errors(spans: list, files: list) -> list[str]:
    errs, seen = [], {}
    for (st, en, kind, ev, cid), (f, off) in zip(spans, files):
        if not f:
            continue
        k = (f, off)
        if f in seen and st - seen[f][0] < REUSE_S and seen[f][1] == off:
            errs.append('%s: الملفّ %s نفسه وبالبداية نفسها بعد %.0f ث فقط' % (cid, os.path.basename(f), st - seen[f][0]))
        seen[f] = (st, off)
    return errs


def _load(f: str, off: float, dur: float, eq: str | None) -> np.ndarray:
    af = ['aresample=%d' % SR] + ([eq] if eq else [])
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(off), '-t', '%.3f' % dur, '-i', f, '-ac', '1',
                          '-af', ','.join(af), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def _env(x: np.ndarray, att: float, rel: float, hop: int = 480) -> np.ndarray:
    """غلاف RMS بهجومٍ وتحرّرٍ (لكلّ 10 مللي ث) ثم يُمدّ إلى طول الإشارة."""
    n = len(x) // hop + 1
    r = np.sqrt(np.array([np.mean(x[i * hop:(i + 1) * hop] ** 2) if i * hop < len(x) else 0.0 for i in range(n)]) + 1e-12)
    a, b = np.exp(-hop / (att * SR)), np.exp(-hop / (rel * SR))
    e = np.empty_like(r); s = 0.0
    for i, v in enumerate(r):
        k = a if v > s else b
        s = k * s + (1 - k) * v
        e[i] = s
    return np.repeat(e, hop)[:len(x)]


def max_harsh(y: np.ndarray, win_s: float = 0.4) -> float:
    """أعلى حصّة 2–6 كيلوهرتز في نوافذ المقطع المسموعة (في حدود 20 dB من ذروته)."""
    import sfx_library
    W = int(win_s * SR)
    if len(y) < W:
        return sfx_library.harsh_share(y)
    top = max(rms_db(y[i:i + W]) for i in range(0, len(y) - W + 1, W))
    hs = [sfx_library.harsh_share(y[i:i + W]) for i in range(0, len(y) - W + 1, W) if rms_db(y[i:i + W]) > top - 20]
    return max(hs) if hs else 0.0


def active_db(x: np.ndarray, floor: float, win_s: float = 0.4) -> float:
    """RMS بالديسيبل على النوافذ المسموعة فقط (فوق floor) — لا يخفضه الصمت بين الجمل."""
    W = max(1, int(win_s * SR))
    ws = [x[i:i + W] for i in range(0, max(1, len(x) - W + 1), W)] or [x]
    act = [w for w in ws if rms_db(w) > floor]
    return rms_db(np.concatenate(act)) if act else rms_db(x)


def rms_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-9))


def render(sheet: dict, blocks: list[dict], bt: dict, voice: np.ndarray, out: str | None = None,
           sfx_dir: str = SFX_DIR, man: dict | None = None) -> np.ndarray:
    """مسار المؤثّرات وحده: كلّ إشارة بكسبها المقيس إلى REF ثم مستواها النسبيّ للصوت، وتلاشٍ دخولاً وخروجاً،
    ودكٌّ يقوده الكلام نفسه: تحت الكلام = level، وبين الجمل = gap_level، وصمتٌ تامّ فوق الجمل المفتاحية والصمت."""
    man = manifest() if man is None else man
    by = {b['id']: b for b in blocks}
    cues = sheet.get('cues') or []
    spans = [cue_window(c, bt, by) + (EVENTS[c['event']][1], c['event'], c.get('id', '?')) for c in cues]
    files = pick_files(cues, spans, sfx_dir, man)
    n = len(voice)
    under = np.zeros(n, np.float32); gaps = np.zeros(n, np.float32)
    v_ref = active_db(voice, -35.0)                      # جهارة الكلام في نوافذه المسموعة وحدها
    mute = np.ones(n, np.float32)
    keys = key_blocks(sheet, blocks)
    for k in keys:
        if k in bt:
            i, j = int(max(0, bt[k][0] - 0.2) * SR), int(min(n / SR, bt[k][1] + 0.2) * SR)
            mute[i:j] = 0.0
    for c, (st, en, kind, ev, cid), (f, off) in zip(cues, spans, files):
        i, j = int(max(0, st) * SR), int(min(n / SR, en) * SR)
        if kind == 'silence':
            mute[i:j] = 0.0; continue
        if not f or j <= i:
            continue
        m = man.get(os.path.basename(f)) or {}
        y = _load(f, off, (j - i) / SR, m.get('eq'))
        if not len(y):
            continue
        import sfx_library
        if not m.get('eq') and max_harsh(y) > 0.40:                     # مقطعٌ حادّ ولو في لحظة ⇒ يُروَّض قبل الدخول
            y = _load(f, off, (j - i) / SR, sfx_library.TAME)
        y = y / (10 ** (active_db(y, -60.0) / 20))          # المؤثّر بجهارته الفعلية = 0 dB، ثم مستواه النسبيّ للكلام
        y = y * 10 ** (v_ref / 20)
        fi = int((0.02 if kind == 'spot' else 0.8) * SR); fo = int((0.3 if kind == 'spot' else 1.2) * SR)
        fi, fo = min(fi, len(y) // 3), min(fo, len(y) // 2)
        if fi: y[:fi] *= np.linspace(0, 1, fi)
        if fo: y[-fo:] *= np.linspace(1, 0, fo)
        lv = float(c.get('level', EVENTS[ev][2])); gl = float(c.get('gap_level', min(lv + 8, GAP_MAX)))
        seg = slice(i, i + len(y))
        under[seg] += y * 10 ** (lv / 20)
        gaps[seg] += y * 10 ** (gl / 20)
    env = _env(voice, 0.06, 0.45)
    thr = 10 ** ((v_ref - 14) / 20)
    w = np.clip(env / thr, 0, 1).astype(np.float32)         # 1 = كلام، 0 = بين الجمل
    mute_s = np.convolve(mute, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode='same').astype(np.float32)
    y = (w * under + (1 - w) * gaps) * mute_s
    # سقفٌ يقوده الكلام: لا يعلو المسار فوق الكلام الحاضر بأكثر من CEIL_UNDER (يمنع ضربةً تطغى على كلمةٍ خافتة)
    venv = _env(voice, 0.005, 0.25)
    senv = _env(y, 0.002, 0.15)
    ceil_ = np.where(w > 0.5, venv * 10 ** (CEIL_UNDER / 20), 10 ** (GAP_CEIL_DBFS / 20)).astype(np.float32)
    g = np.minimum(1.0, ceil_ / (senv + 1e-9))
    k = int(0.01 * SR)
    g = np.convolve(g, np.ones(k) / k, mode='same').astype(np.float32)
    y = y * g
    pk = float(np.abs(y).max()) if len(y) else 0.0
    lim = 10 ** (PEAK_FAIL / 20) * 0.9
    if pk > lim:
        y *= lim / pk
    if out:
        with wave.open(out, 'wb') as wv:
            wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
            wv.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
    return y


# ── فحص المسار المصيَّر ──────────────────────────────────────────────────────────────────────────
def mix_gate(voice: np.ndarray, stem: np.ndarray, key_spans: list | None = None, win_s: float = 0.4) -> list[str]:
    errs = []
    n = min(len(voice), len(stem)); voice, stem = voice[:n], stem[:n]
    pk = 20 * np.log10(float(np.abs(stem).max()) + 1e-9) if n else -120
    if pk > PEAK_FAIL:
        errs.append('ذروة مسار المؤثّرات %.1f dBFS فوق %.0f' % (pk, PEAK_FAIL))
    W = int(win_s * SR); rel, harsh_bad = [], 0
    speech = active_db(voice, -35.0) - 8.0          # نافذة كلامٍ = كلامٌ حاضرٌ بجهارته لا طرفُ كلمةٍ عند الصمت
    for i in range(0, n - W, W):
        v, s = voice[i:i + W], stem[i:i + W]
        vd, sd = rms_db(v), rms_db(s)
        if vd > speech:
            rel.append(sd - vd)
            if sd - vd > WIN_FAIL:
                errs.append('عند %.1f ث: المؤثّر %+.1f dB نسبةً للكلام (الحدّ %+.0f)' % (i / SR, sd - vd, WIN_FAIL))
        if sd > speech - 16:                        # الحدّة تُحكم حيث يُسمع المؤثّر فعلاً
            S = np.abs(np.fft.rfft(s * np.hanning(W))) ** 2; f = np.fft.rfftfreq(W, 1 / SR)
            share = S[(f >= 2000) & (f < 6000)].sum() / (S.sum() + 1e-12)
            # حادٌّ = حصّةٌ عالية **و**طاقة الحزمة نفسها في حدود 20 dB من الكلام (الخطوة الخافتة على الرمل ليست حدّة)
            if share > HARSH_FAIL and sd + 10 * np.log10(share + 1e-12) > speech + 8 - 20:
                harsh_bad += 1
                if harsh_bad <= 3:
                    errs.append('عند %.1f ث: حدّة 2–6 كيلوهرتز (%.2f) مسموعة' % (i / SR, share))
    if rel and float(np.median(rel)) > MEDIAN_FAIL:
        errs.append('وسيط المؤثّرات تحت الكلام %+.1f dB أعلى من %+.0f' % (float(np.median(rel)), MEDIAN_FAIL))
    for a, b in key_spans or []:
        i, j = int(a * SR), int(b * SR)
        if j > i and rms_db(voice[i:j]) > -40 and rms_db(stem[i:j]) - rms_db(voice[i:j]) > KEY_FAIL:
            errs.append('مؤثّرٌ مسموع فوق جملةٍ مفتاحية (%.1f–%.1f ث)' % (a, b))
    return errs


# ── مسودّة من الكلمات (اقتراح يُراجَع) ────────────────────────────────────────────────────────────
DRAFT_MAP = {'hooves': 'hooves', 'horses': 'gallop', 'swords': 'sword_clash', 'battle': 'battle', 'armor': 'leather',
             'bowstring': 'arrows', 'arrows': 'arrows', 'crowd': 'crowd', 'footsteps': 'footsteps', 'marching': 'marching',
             'night': 'night', 'fire': 'fire', 'wind': 'wind', 'shout': 'crowd', 'breath': 'breath', 'elephants': None}


def draft(blocks: list[dict]) -> dict:
    import sfx_auto
    cues = []
    for b in blocks:
        t = sfx_auto.plain(b['text'])
        for cat, rx, _ in sfx_auto.RULES:
            m = rx.search(t)
            if m and DRAFT_MAP.get(cat):
                cues.append({'id': 'c%02d' % (len(cues) + 1), 'block': b['id'], 'event': DRAFT_MAP[cat],
                             'anchor': m.group(0).strip(), 'why': 'TODO: سبب سرديّ — احذف الإشارة إن لم يكن لها سبب'})
                break
    return {'key_blocks': [], 'cues': cues}


def _pcm(p: str) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2:
        print(__doc__); return 2
    cmd, proj = a[0], a[1]
    if cmd in ('render', 'gate') and len(a) < 4:
        print('الاستعمال: sfx_cues.py %s <proj> <voice.wav> <sfx_stem.wav>' % cmd); return 2
    blocks = json.load(open(os.path.join(proj, 'blocks.json'), encoding='utf-8'))
    if cmd == 'draft':
        print(json.dumps(draft(blocks), ensure_ascii=False, indent=1)); return 0
    sheet = json.load(open(os.path.join(proj, 'sfx_cues.json'), encoding='utf-8'))
    bt = block_times(proj, blocks)
    errs = lint(sheet, blocks, bt)
    if cmd in ('render', 'gate') and not errs:
        by = {b['id']: b for b in blocks}
        cues = sheet.get('cues') or []
        spans = [cue_window(c, bt, by) + (EVENTS[c['event']][1], c['event'], c.get('id', '?')) for c in cues]
        errs += reuse_errors(spans, pick_files(cues, spans))
    if cmd == 'render' and not errs:
        render(sheet, blocks, bt, _pcm(a[2]), a[3])
    if cmd == 'gate':
        keys = key_blocks(sheet, blocks)
        errs += mix_gate(_pcm(a[2]), _pcm(a[3]), [bt[k] for k in keys if k in bt])
    for e in errs:
        print('⛔', e)
    if not errs:
        print('✓ ورقة الإشارات%s سليمة: %d إشارة' % (' والمسار' if cmd == 'gate' else '', len(sheet.get('cues') or [])))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
