#!/usr/bin/env python3
"""🎙️ مختبر الأصوات — يختار أقوى صوتٍ وأجوده آلياً قبل توليد صوت الفيلم (أمر المالك 2026-10-04).

**لماذا؟** لاحظ المالك فرقاً كبيراً في جودة الصوت بين أفلام سلسلة «معارك غيّرت مجرى التاريخ»
وداخل الفيلم الواحد، مع أنّ النموذج واحد، وأمر بأن يبدأ الفيلم (والافتتاحية أوّلاً) بالصوت الأفضل والأقوى.
كانت الأصوات تتناوب بين Charon وOrus كتلةً كتلة، وتُختار بالعادة لا بالقياس. هنا تُقاس.

المراحل (كلّها في CI بحصّة Gemini المجّانية):
  ١) كلّ صوتٍ رجاليّ × كلّ أسلوب أداء × جملتان من الافتتاحية ← توليد بـgemini-3.8-flash-tts.
  ٢) قياسٌ موضوعيّ لكلّ عيّنة: المدّة، والجهارة (LUFS)، ومدى التلوين اللحنيّ (انحراف الطبقة بأنصاف النغمات)،
     وكشف نطق التوجيه (مدّةٌ أطول كثيراً من النسخة بلا توجيه).
  ٣) حَكَمٌ سمعيّ (نموذج Gemini يسمع): دوري مقارنات بين العيّنات للجملة نفسها
     ⇐ ترتيبٌ بالقوة والهيبة والوضوح والفصاحة والطبيعية، ورايةٌ لأيّ نطقٍ لتعليمات إنجليزية.
  ٤) الأربعة الأوائل بأربع جمل، ثم مقارنةُ سلاسل المعالجة الصوتية (الحالية وبدائل أقوى) على الفائز.
  ولكلّ دورٍ فائزُه («roles» في المواصفة: الاقتباس والإلقاء مثلاً)، والراوي دورٌ واحدٌ افتراضاً.
  ⛔ لا فائز بلا حكمٍ فعليّ في كلّ مرحلة وبلا عيّناتٍ كاملة: الناقص أو المتعذّر يُسجَّل في «error» ويخرج الشوط بـ1.

    python3 tools/voice_lab.py ops/voice-lab/<slug>.json --keys /tmp/keys.json --out out

المخرج: out/<slug>-results.json (لكلّ دور: الترتيب والقياسات والملاحظات والفائز) وmp3 لكلّ متأهّل وللفائز بكلّ معالجة،
ثم tools/apply_voices.py يطبّق الفائزين على كتل المشروع قبل ختمه.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import random
import re
import subprocess as sp
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FF, FP = 'ffmpeg', 'ffprobe'
JUDGE_MODELS = ['gemini-3.5-pro', 'gemini-pro-latest', 'gemini-3.5-flash', 'gemini-flash-latest', 'gemini-3.8-flash']
HARAKAT = re.compile('[\u064b-\u0652\u0670\u0640]')

# سلاسل المعالجة: M0 هي الحالية في mont_hybrid، والبقية بدائل أقوى تُقارن بالأذن الآلية
CHAINS = {
    'M0': 'atempo=1.05,adeclick,dynaudnorm',
    'M1': ('atempo=1.05,adeclick,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=8:release=180:makeup=3,'
           'equalizer=f=3000:t=q:w=1.2:g=2.5,equalizer=f=180:t=q:w=1:g=1.5,loudnorm=I=-16:TP=-1.5:LRA=9'),
    'M2': 'atempo=1.05,adeclick,highpass=f=70,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=200:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=11',
}


def log(*a):
    print(*a, flush=True)


def keys_from(path: str | None) -> list[str]:
    out: list[str] = []
    if not path or not os.path.exists(path):
        return out
    t = open(path, encoding='utf-8').read().strip()
    try:
        j = json.loads(t)
        arr = j if isinstance(j, list) else (j.get('keys') if isinstance(j, dict) and isinstance(j.get('keys'), list) else list(j.values()))
        out = [v.strip() for v in arr if isinstance(v, str) and (v.strip().startswith('AIza') or v.strip().startswith('AQ.'))]
    except Exception:
        out = [x for x in re.split(r'[\s,"]+', t) if x.startswith('AIza') or x.startswith('AQ.')]
    return list(dict.fromkeys(out))


def dur(f: str) -> float:
    o = sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True)
    try:
        return float(o.stdout.strip())
    except ValueError:
        return 0.0


# ═════════════ التوليد ═════════════
# ⛔ مؤتة 2026-10-06 (تشخيص الحصّة): كانت مخرجات المولّد مكتومةً، فحاول المختبر مساء 2026-10-05 مئةً وثماني عيّنات
#    بعد نفاد الحصّة ونجح منها 34، ولم يظهر في أيّ سجلٍّ ما صرفه. وكلُّ تركيبةٍ فاشلة طرقت المفاتيح كلّها من جديد.
#    ثم صار المولّد ينتظر عودة المفاتيح حتى 150 دقيقة (443c35c)، فكان المختبر سيعلق ذلك في كلّ تركيبة.
#    ⇒ مهلة المولّد هنا قصيرة، وسطور خلاصته تُطبع، وأوّل «nokeys» (جدار الحصّة) يوقف التوليد في بقيّة المختبر.
#    والنموذج من المواصفة («model»)، والأحدث افتراضاً.
GEN = {'model': 'gemini-3.8-flash-tts', 'wall': False}


def generate(vdir: Path, blocks: list[dict], keys_file: str) -> dict[str, str]:
    """يولّد الكتل في مجلّد تركيبةٍ واحدة بأداة الفيلم نفسها (gen25.js) ويعيد {المعرّف: المسار}."""
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / 'blocks.json').write_text(json.dumps(blocks, ensure_ascii=False), encoding='utf-8')
    env = dict(os.environ, GEN_MAX_MIN=os.environ.get('LAB_GEN_MAX_MIN', '3'), GEN_BLOCK_MS='180000')
    for _ in range(3 if not GEN['wall'] else 0):
        p = sp.run(['node', str(ROOT / 'gen25.js'), str(vdir), '4', '--keys', keys_file, '--model', GEN['model']],
                   capture_output=True, text=True, env=env)
        for ln in (p.stdout + '\n' + p.stderr).splitlines():
            if ln.startswith(('انتهى:', 'حدود 429', 'نتائج النداءات', '⛔')):
                log('   ', ln[:300])
        if all((vdir / 'audio' / (b['id'] + '.wav')).exists() for b in blocks):
            break
        if 'nokeys' in p.stdout:
            GEN['wall'] = True
            log('⛔ جدار الحصّة (nokeys): لا توليد بعد الآن في هذا المختبر — يُعاد بعد تجدّد الحصّة')
            break
    return {b['id']: str(vdir / 'audio' / (b['id'] + '.wav')) for b in blocks if (vdir / 'audio' / (b['id'] + '.wav')).exists()}


# ═════════════ القياس الموضوعيّ ═════════════
def loudness(f: str) -> tuple[float, float]:
    o = sp.run([FF, '-hide_banner', '-nostats', '-i', f, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', o)
    lra = re.findall(r'LRA:\s+([\d.]+) LU', o)
    return (float(i[-1]) if i else float('nan'), float(lra[-1]) if lra else float('nan'))


def pitch_stats(f: str) -> tuple[float, float]:
    """الطبقة الوسيطة (هرتز) وانحرافها بأنصاف النغمات — مقياسٌ للتلوين اللحنيّ (الصوت الرتيب أقلّ)."""
    try:
        import numpy as np
    except ImportError:
        return float('nan'), float('nan')
    raw = sp.run([FF, '-v', 'error', '-i', f, '-f', 's16le', '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if len(x) < 16000 * 0.5:
        return float('nan'), float('nan')
    fr, hop = 640, 160                      # 40 مث بخطوة 10 مث
    lo, hi = 16000 // 300, 16000 // 70      # 70–300 هرتز (أصواتٌ رجالية)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, len(x) - fr, hop)])
    thr = max(0.02, np.percentile(e, 60) * 0.5)
    f0 = []
    for k, i in enumerate(range(0, len(x) - fr, hop)):
        if e[k] < thr:
            continue
        s = x[i:i + fr] - np.mean(x[i:i + fr])
        ac = np.correlate(s, s, 'full')[fr - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        j = int(np.argmax(seg))
        if seg[j] / ac[0] > 0.45:
            f0.append(16000.0 / (lo + j))
    if len(f0) < 10:
        return float('nan'), float('nan')
    f0 = np.array(f0)
    med = float(np.median(f0))
    st = 12 * np.log2(f0 / med)
    return med, float(np.std(st[(st > -12) & (st < 12)]))


def measure(f: str, text: str) -> dict:
    d = dur(f)
    i, lra = loudness(f)
    med, sd = pitch_stats(f)
    letters = len(HARAKAT.sub('', re.sub(r'[^\u0600-\u06FF]', '', text)))
    return {'dur': round(d, 2), 'lufs': round(i, 1), 'lra': round(lra, 1), 'f0': round(med, 1) if med == med else None,
            'pitch_sd_st': round(sd, 2) if sd == sd else None, 'cps': round(letters / d, 1) if d else None}


# ═════════════ الحَكَم السمعيّ ═════════════
class Judge:
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.dead: dict[str, set] = {}
        self.calls = 0

    def ask(self, parts: list[dict], tries: int = 12) -> dict | None:
        body = {'contents': [{'parts': parts}], 'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}}
        data = json.dumps(body).encode('utf-8')
        for _ in range(tries):
            for model in JUDGE_MODELS:
                ks = [k for k in self.keys if k not in self.dead.setdefault(model, set())]
                if not ks:
                    continue
                key = random.choice(ks)
                url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
                req = urllib.request.Request(url, data=data, headers={'content-type': 'application/json'})
                try:
                    with urllib.request.urlopen(req, timeout=300) as r:
                        j = json.loads(r.read().decode('utf-8'))
                    self.calls += 1
                    txt = ''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts'])
                    m = re.search(r'\{.*\}', txt, re.S)
                    if m:
                        out = json.loads(m.group(0)); out['_model'] = model
                        return out
                except urllib.error.HTTPError as e:
                    msg = e.read().decode('utf-8', 'ignore')
                    if e.code == 404 or 'not found' in msg.lower():
                        self.dead[model] = set(self.keys)          # النموذج غير موجود: يسقط فوراً
                    elif e.code == 429 and 'PerDay' in msg:
                        self.dead[model].add(key)
                    elif e.code in (400, 403):
                        self.dead[model].add(key)
                    time.sleep(2)
                except Exception:
                    time.sleep(3)
        return None

    def rank(self, clips: list[tuple[str, str]], text: str, purpose: str) -> tuple[list[str], dict]:
        """يرتّب عيّناتٍ للجملة نفسها (≤ 8 في الطلب). يعيد الترتيب والملاحظات ورايات نطق التوجيه."""
        labels = [c[0] for c in clips]
        tag = {lab: 'S%d' % (i + 1) for i, lab in enumerate(labels)}
        parts = [{'text': (
            'أنت مهندس صوتٍ ومخرجٌ لأفلامٍ وثائقية تاريخية عربية ملحمية. ستسمع عيّناتٍ صوتيّة للجملة العربية المشكولة نفسها:\n'
            f'«{text}»\n'
            f'الغرض: {purpose}\n'
            'رتّب العيّنات من الأفضل إلى الأسوأ بحسب: قوّة الصوت وهيبته وحضوره، ثمّ وضوحه ونقاؤه، ثمّ صحّة النطق الفصيح وفق التشكيل، '
            'ثمّ الطبيعية والإقناع (لا تمثيلٌ مصطنع ولا رتابة)، ثمّ مناسبة الإيقاع للتشويق.\n'
            'وانتبه: إن سمعت في عيّنةٍ كلاماً إنجليزياً أو قراءةً لتعليمات (مثل Say أو Style أو notes) فاجعلها في ذيل الترتيب وضعها في leaked.\n'
            'أجب بـJSON فقط: {"ranking": ["S…", …], "leaked": ["S…"], "notes": {"S…": "ملاحظة قصيرة بالعربية"}}')}]
        for lab, f in clips:
            parts.append({'text': tag[lab] + ':'})
            parts.append({'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(open(f, 'rb').read()).decode()}})
        r = self.ask(parts)
        if not r or not isinstance(r.get('ranking'), list):
            return labels, {'error': 'لا حكم'}
        back = {v: k for k, v in tag.items()}
        order = [back[s] for s in r['ranking'] if s in back]
        order += [lab for lab in labels if lab not in order]
        leaked = [back[s] for s in r.get('leaked', []) if s in back]
        notes = {back[k]: v for k, v in (r.get('notes') or {}).items() if k in back}
        return order, {'leaked': leaked, 'notes': notes, 'model': r.get('_model')}


def tournament(judge: Judge, clips: dict[str, str], text: str, purpose: str, group: int = 6, keep: int = 2) -> tuple[list[str], dict]:
    """دوري مقارنات: مجموعاتٌ صغيرة يصعد من كلّ منها الأوائل، حتى ترتيبٍ نهائيّ لثمانيةٍ على الأكثر.
    ⛔ تعذّرُ حكمٍ واحد يُبطل الجملة كلّها (مؤتة 2026-10-05: كان يعيد الخلط العشوائيّ ترتيباً كأنه حكم)."""
    pool = list(clips)
    random.shuffle(pool)
    info: dict = {'rounds': [], 'leaked': set(), 'notes': {}}

    def done(order: list[str], err: str | None = None) -> tuple[list[str], dict]:
        info['leaked'] = sorted(info['leaked'])
        if err:
            info['error'] = err
            return [], info
        info['final'] = order
        return [lab for lab in order if lab not in info['leaked']], info

    if not pool:
        return done([], 'لا عيّنات')
    while len(pool) > 8:
        nxt = []
        for i in range(0, len(pool), group):
            g = pool[i:i + group]
            order, inf = judge.rank([(lab, clips[lab]) for lab in g], text, purpose)
            if inf.get('error'):
                return done([], inf['error'])
            info['rounds'].append(order)
            info['leaked'].update(inf.get('leaked', []))
            info['notes'].update(inf.get('notes', {}))
            nxt += [lab for lab in order if lab not in info['leaked']][:keep]
        pool = nxt
    order, inf = judge.rank([(lab, clips[lab]) for lab in pool], text, purpose)
    if inf.get('error'):
        return done([], inf['error'])
    info['leaked'].update(inf.get('leaked', []))
    info['notes'].update(inf.get('notes', {}))
    return done(order)


# ═════════════ الأدوار ═════════════
NARRATOR_PURPOSE = 'راوي فيلمٍ وثائقيّ ملحميّ كاملٍ عن معركة: الافتتاحية والسرد والمعركة والخاتمة'
CHAIN_PURPOSE = 'المعالجة الصوتية الأفضل للصوت نفسه: أقوى وأوضح وأنقى دون أن يبدو مضغوطاً أو مصطنعاً'


def roles_of(spec: dict) -> dict:
    """أدوار المختبر، ولكلّ دورٍ فائزه. بلا «roles» دورٌ واحدٌ للراوي بكلّ الأساليب والجمل وسلاسل المعالجة (السلوك الأوّل).
    مثال (مؤتة): {"quote": {"styles": ["quote"], "lines": ["Q1", "Q2"], "stage1_lines": ["Q1"], "finalists": 3, "purpose": "…"},
                  "poetry": {"styles": ["recitation"], "lines": ["P1", "P2", "P3"], …}} — كان صوتا الاقتباس والإلقاء يُحكَّمان
    معاً بغرض الراوي فيخرج فائزٌ واحدٌ للدورين."""
    if spec.get('roles'):
        return spec['roles']
    return {'narrator': {'styles': list(spec['styles']), 'lines': [ln['id'] for ln in spec['lines']],
                         'stage1_lines': spec.get('stage1_lines', ['L1', 'L2']), 'finalists': spec.get('finalists', 4),
                         'purpose': NARRATOR_PURPOSE, 'chains': True}}


def join_lines(files: list[str], out: Path) -> str:
    """الجمل متّصلةً بصمتٍ قصير بينها: مقطعٌ واحدٌ يُحكم عليه كما يُسمع في الفيلم."""
    sil = out.parent / 'sil.wav'
    if not sil.exists():
        sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '0.45', str(sil)], check=True)
    lst = out.with_suffix('.txt')
    lst.write_text(''.join("file '%s'\nfile '%s'\n" % (os.path.abspath(f), os.path.abspath(sil)) for f in files), encoding='utf-8')
    sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-ar', '24000', '-ac', '1', str(out)], check=True)
    return str(out)


def apply_chain(src: str, flt: str, out: Path) -> str:
    sp.run([FF, '-v', 'error', '-y', '-i', src, '-af', flt, '-ar', '48000', '-ac', '1', str(out)], check=True)
    return str(out)


def to_mp3(src: str, dst: Path, rate: str = '128k') -> None:
    sp.run([FF, '-v', 'error', '-y', '-i', src, '-b:a', rate, str(dst)], check=True)


def lab_role(name: str, cfg: dict, spec: dict, judge: Judge, out: Path, work: Path, keys_file: str) -> dict:
    """دورٌ واحد: المرحلة الأولى (كلّ صوتٍ × كلّ أسلوب × جمل المرحلة الأولى) ← دوريٌّ لكلّ جملة ← الأوائل بكلّ الجمل ←
    حكمٌ أخير على مقطعٍ متّصل ← سلاسل المعالجة (للراوي).
    ⛔ لا فائز إلا بحكمٍ فعليّ في كلّ مرحلة وبعيّناتٍ كاملة (مؤتة 2026-10-05: حُكمت جملتان من أربع، وتعذّر الحكم الأخير،
       فسجّلت الأداة أوّل المتأهّلين «فائزاً» وخرجت بنجاح). الناقص أو المتعذّر يُسجَّل في «error» ويُعاد الشوط بعد تجدّد الحصّة."""
    slug = spec['slug']
    styles = {s: spec['styles'][s] for s in cfg['styles']}
    text = {ln['id']: ln['text'] for ln in spec['lines']}
    lines = [ln for ln in spec['lines'] if ln['id'] in cfg['lines']]
    first = [ln for ln in lines if ln['id'] in cfg.get('stage1_lines', [])] or lines[:1]
    combos = [f'{v}·{s}' for v in (cfg.get('voices') or spec['voices']) for s in styles]
    purpose = cfg.get('purpose') or NARRATOR_PURPOSE
    r: dict = {'stage1': {}, 'metrics': {}, 'generated': 0}

    def gen(lab: str, lns: list[dict]) -> dict[str, str]:
        v, s = lab.split('·')
        blocks = [{'id': ln['id'], 'voice': v, 'text': ln['text'], **({'director': styles[s]} if styles[s] else {})} for ln in lns]
        have = set(r['metrics'].get(lab, {}))
        got = generate(work / lab.replace('·', '_'), blocks, keys_file)
        for lid, f in got.items():
            if lid not in have:
                r['metrics'].setdefault(lab, {})[lid] = measure(f, text[lid])
                r['generated'] += 1
        return got

    # ١) المرحلة الأولى: التوليد والقياس — والناقص يمنع الحكم (المقارنة بعيّناتٍ ناقصة تظلم الغائب)
    clips: dict[str, dict[str, str]] = {ln['id']: {} for ln in first}
    missing = []
    for lab in combos:
        got = gen(lab, first)
        for ln in first:
            if ln['id'] in got:
                clips[ln['id']][lab] = got[ln['id']]
            else:
                missing.append(f"{lab}/{ln['id']}")
        log(name, 'توليد', lab, len(got), '/', len(first))
    if missing:
        r['error'] = 'ناقص التوليد (%d): %s' % (len(missing), ' '.join(missing[:8]))
        return r

    # كشف نطق التوجيه بالمدّة: أطول من نسخة الصوت نفسه بلا توجيه بنسبةٍ كبيرة ⇒ مستبعد
    suspect = set()
    for lab, m in r['metrics'].items():
        v, s = lab.split('·')
        if styles.get(s) and f'{v}·plain' in r['metrics']:
            for lid, mm in m.items():
                base = r['metrics'][f'{v}·plain'].get(lid)
                if base and mm['dur'] > base['dur'] * 1.6 + 0.8:
                    suspect.add(lab)
    r['suspect_duration'] = sorted(suspect)

    # ٢) الحَكَم: دوريٌّ لكلّ جملة من جمل المرحلة الأولى، ثم جمعٌ بنقاط بوردا — ولا دوريّ إن لم يزد المرشّحون على الأوائل
    n = cfg.get('finalists', 3)
    leaked = set(suspect)
    pool_all = [lab for lab in combos if lab not in suspect]
    if len(pool_all) <= n:
        top = pool_all
    else:
        score: dict[str, float] = {}
        for ln in first:
            order, info = tournament(judge, {lab: clips[ln['id']][lab] for lab in pool_all}, ln['text'], ln.get('purpose', purpose))
            r['stage1'][ln['id']] = {'order': order, 'leaked': info['leaked'], 'notes': info['notes'],
                                    **({'error': info['error']} if info.get('error') else {})}
            if info.get('error'):
                r['error'] = 'تعذّر حكم المرحلة الأولى على %s: %s' % (ln['id'], info['error'])
                return r
            leaked.update(info['leaked'])
            for rnk, lab in enumerate(order):
                score[lab] = score.get(lab, 0) + (len(order) - rnk)
            log(name, 'ترتيب', ln['id'], order[:5])
        top = [lab for lab, _ in sorted(score.items(), key=lambda kv: -kv[1]) if lab not in leaked][:n]
    r['finalists'] = top
    r['leaked'] = sorted(leaked)
    if not top:
        r['error'] = 'لا متأهّل'
        return r

    # ٣) الأوائل بكلّ الجمل ثمّ ترتيبٌ نهائيّ على مقطعٍ متّصل
    joined: dict[str, str] = {}
    for lab in top:
        got = gen(lab, lines)
        if len(got) < len(lines):
            r['error'] = 'ناقص التوليد في المتأهّل %s (%d/%d)' % (lab, len(got), len(lines))
            return r
        joined[lab] = join_lines([got[ln['id']] for ln in lines], work / (lab.replace('·', '_') + '_all.wav'))
        to_mp3(joined[lab], out / f"{slug}-{lab.replace('·', '-')}.mp3")
        r['metrics'][lab]['ALL'] = measure(joined[lab], ' '.join(ln['text'] for ln in lines))
    alltext = ' / '.join(ln['text'] for ln in lines)
    order, inf = judge.rank(list(joined.items()), alltext, purpose)
    r['final'] = {'order': order, **inf}
    if inf.get('error'):
        r['error'] = 'تعذّر الحكم الأخير: %s' % inf['error']
        return r
    order = [lab for lab in order if lab not in inf.get('leaked', [])]
    if not order:
        r['error'] = 'نطق كلُّ المتأهّلين التوجيه'
        return r
    v, s = order[0].split('·')
    r['winner'] = {'voice': v, 'style': s, 'director': styles[s], 'order': order}

    # ٤) سلاسل المعالجة على الفائز (للراوي) — وتعذّرُ حكمها يُبقي المعالجة الافتراضية لا الأولى في القائمة
    if cfg.get('chains'):
        chains = {}
        for cname, flt in CHAINS.items():
            chains[cname] = apply_chain(joined[order[0]], flt, work / f'chain_{cname}.wav')
            to_mp3(chains[cname], out / f'{slug}-winner-{cname}.mp3', '160k')
            r['metrics'].setdefault('chain_' + cname, {})['ALL'] = measure(chains[cname], ' '.join(ln['text'] for ln in lines))
        corder, cinf = judge.rank(list(chains.items()), alltext, CHAIN_PURPOSE)
        r['chains'] = {'order': corder, **cinf, 'filters': CHAINS}
        best = None if cinf.get('error') else corder[0]
        r['winner'].update(chain=best, filter=CHAINS[best] if best else None)
    return r


# ═════════════ التشغيل ═════════════
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('spec')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--out', default='out')
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text(encoding='utf-8'))
    slug = spec['slug']
    GEN['model'] = spec.get('model', GEN['model'])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    work = Path('lab_work'); work.mkdir(exist_ok=True)
    judge = Judge(keys_from(a.keys))
    res: dict = {'slug': slug, 'model': GEN['model'], 'styles': spec['styles'], 'pos_styles': spec.get('pos_styles', {}), 'roles': {}, 'generated': 0}
    for name, cfg in roles_of(spec).items():
        try:
            rr = lab_role(name, cfg, spec, judge, out, work, a.keys)
        except Exception as e:                      # عطلٌ في دورٍ لا يُسقط نتيجة الأدوار الأخرى ولا ملفّ النتيجة
            rr = {'error': 'استثناء: %s' % str(e)[:300], 'generated': 0}
        res['roles'][name] = rr
        res['generated'] += rr['generated']
        log(name, '— الفائز:', json.dumps(rr.get('winner'), ensure_ascii=False) if rr.get('winner') else 'لا أحد', rr.get('error', ''))
    if list(res['roles']) == ['narrator']:          # الصيغة الأولى للنتيجة (الأرك) محفوظة في الأعلى
        res.update({k: v for k, v in res['roles']['narrator'].items() if k != 'generated'})
    res['judge_calls'] = judge.calls
    res['quota_wall'] = GEN['wall']
    (out / f'{slug}-results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0 if all(rr.get('winner') for rr in res['roles'].values()) else 1


if __name__ == '__main__':
    sys.exit(main())
