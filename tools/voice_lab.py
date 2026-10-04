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

    python3 tools/voice_lab.py ops/voice-lab/<slug>.json --keys /tmp/keys.json --out out

المخرج: out/<slug>-results.json (الترتيب والقياسات والملاحظات) وmp3 لكلّ تركيبة وللفائز بكلّ معالجة.
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
def generate(vdir: Path, blocks: list[dict], keys_file: str) -> dict[str, str]:
    """يولّد الكتل في مجلّد تركيبةٍ واحدة بأداة الفيلم نفسها (gen25.js) ويعيد {المعرّف: المسار}."""
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / 'blocks.json').write_text(json.dumps(blocks, ensure_ascii=False), encoding='utf-8')
    for _ in range(3):
        sp.run(['node', str(ROOT / 'gen25.js'), str(vdir), '4', '--keys', keys_file, '--model', 'gemini-3.8-flash-tts'],
               stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if all((vdir / 'audio' / (b['id'] + '.wav')).exists() for b in blocks):
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
    """دوري مقارنات: مجموعاتٌ صغيرة يصعد من كلّ منها الأوائل، حتى ترتيبٍ نهائيّ لثمانيةٍ على الأكثر."""
    pool = list(clips)
    random.shuffle(pool)
    info: dict = {'rounds': [], 'leaked': set(), 'notes': {}}
    while len(pool) > 8:
        nxt = []
        for i in range(0, len(pool), group):
            g = pool[i:i + group]
            order, inf = judge.rank([(lab, clips[lab]) for lab in g], text, purpose)
            info['rounds'].append(order)
            info['leaked'].update(inf.get('leaked', []))
            info['notes'].update(inf.get('notes', {}))
            nxt += [lab for lab in order if lab not in info['leaked']][:keep]
        pool = nxt
    order, inf = judge.rank([(lab, clips[lab]) for lab in pool], text, purpose)
    info['leaked'].update(inf.get('leaked', []))
    info['notes'].update(inf.get('notes', {}))
    info['final'] = order
    info['leaked'] = sorted(info['leaked'])
    return [lab for lab in order if lab not in info['leaked']], info


# ═════════════ التشغيل ═════════════
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('spec')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--out', default='out')
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding='utf-8'))
    slug = spec['slug']
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    work = Path('lab_work'); work.mkdir(exist_ok=True)
    judge = Judge(keys_from(a.keys))
    styles = spec['styles']                       # {"plain": null, "epic": "<ملاحظات المخرج>", …}
    lines = spec['lines']                         # [{"id": "L1", "text": "…", "purpose": "…"}, …]
    first = [ln for ln in lines if ln['id'] in spec.get('stage1_lines', ['L1', 'L2'])]
    combos = [(v, s) for v in spec['voices'] for s in styles]
    res: dict = {'slug': slug, 'stage1': {}, 'metrics': {}, 'generated': 0}

    # ١) التوليد والقياس
    clips: dict[str, dict[str, str]] = {ln['id']: {} for ln in lines}
    for v, s in combos:
        lab = f'{v}·{s}'
        blocks = [{'id': ln['id'], 'voice': v, 'text': ln['text'], **({'director': styles[s]} if styles[s] else {})} for ln in first]
        got = generate(work / lab.replace('·', '_'), blocks, a.keys)
        for lid, f in got.items():
            clips[lid][lab] = f
            res['metrics'].setdefault(lab, {})[lid] = measure(f, next(ln['text'] for ln in lines if ln['id'] == lid))
        res['generated'] += len(got)
        log('توليد', lab, len(got), '/', len(first))

    # كشف نطق التوجيه بالمدّة: أطول من نسخة الصوت نفسه بلا توجيه بنسبةٍ كبيرة ⇒ مستبعد
    suspect = set()
    for lab, m in res['metrics'].items():
        v, s = lab.split('·')
        if styles.get(s) and f'{v}·plain' in res['metrics']:
            for lid, mm in m.items():
                base = res['metrics'][f'{v}·plain'].get(lid)
                if base and mm['dur'] > base['dur'] * 1.6 + 0.8:
                    suspect.add(lab)
    res['suspect_duration'] = sorted(suspect)

    # ٢) الحَكَم: دوريٌّ لكلّ جملة من جملتي المرحلة الأولى، ثم جمعٌ بنقاط بوردا
    score: dict[str, float] = {}
    leaked_all: set = set(suspect)
    for ln in first:
        pool = {lab: f for lab, f in clips[ln['id']].items() if lab not in suspect}
        order, info = tournament(judge, pool, ln['text'], ln.get('purpose', 'افتتاحية فيلمٍ وثائقيّ ملحميّ'))
        res['stage1'][ln['id']] = {'order': order, 'leaked': info['leaked'], 'notes': info['notes']}
        leaked_all.update(info['leaked'])
        for rnk, lab in enumerate(order):
            score[lab] = score.get(lab, 0) + (len(order) - rnk)
        log('ترتيب', ln['id'], order[:5])
    top = [lab for lab, _ in sorted(score.items(), key=lambda kv: -kv[1]) if lab not in leaked_all][:spec.get('finalists', 4)]
    res['finalists'] = top
    res['leaked'] = sorted(leaked_all)

    # ٣) الأوائل بكلّ الجمل ثمّ ترتيبٌ نهائيّ على مقطعٍ متّصل
    joined: dict[str, str] = {}
    for lab in top:
        v, s = lab.split('·')
        blocks = [{'id': ln['id'], 'voice': v, 'text': ln['text'], **({'director': styles[s]} if styles[s] else {})} for ln in lines]
        got = generate(work / lab.replace('·', '_'), blocks, a.keys)
        if len(got) < len(lines):
            continue
        lst = work / (lab.replace('·', '_') + '_list.txt')
        sil = work / 'sil.wav'
        if not sil.exists():
            sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '0.45', str(sil)], check=True)
        lst.write_text(''.join("file '%s'\nfile '%s'\n" % (os.path.abspath(got[ln['id']]), os.path.abspath(sil)) for ln in lines), encoding='utf-8')
        j = work / (lab.replace('·', '_') + '_all.wav')
        sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-ar', '24000', '-ac', '1', str(j)], check=True)
        joined[lab] = str(j)
        sp.run([FF, '-v', 'error', '-y', '-i', str(j), '-b:a', '128k', str(out / f"{slug}-{lab.replace('·', '-')}.mp3")], check=True)
        res['metrics'].setdefault(lab, {})['ALL'] = measure(str(j), ' '.join(ln['text'] for ln in lines))
    if joined:
        order, inf = judge.rank(list(joined.items()), ' / '.join(ln['text'] for ln in lines),
                                'راوي فيلمٍ وثائقيّ ملحميّ كاملٍ عن معركة: الافتتاحية والسرد والمعركة والخاتمة')
        res['final'] = {'order': order, **inf}
        win = order[0]
        # ٤) سلاسل المعالجة على الفائز
        chains = {}
        for name, flt in CHAINS.items():
            o = work / f'chain_{name}.wav'
            sp.run([FF, '-v', 'error', '-y', '-i', joined[win], '-af', flt, '-ar', '48000', '-ac', '1', str(o)], check=True)
            chains[name] = str(o)
            sp.run([FF, '-v', 'error', '-y', '-i', str(o), '-b:a', '160k', str(out / f'{slug}-winner-{name}.mp3')], check=True)
            res['metrics'].setdefault('chain_' + name, {})['ALL'] = measure(str(o), ' '.join(ln['text'] for ln in lines))
        corder, cinf = judge.rank(list(chains.items()), ' / '.join(ln['text'] for ln in lines),
                                  'المعالجة الصوتية الأفضل للصوت نفسه: أقوى وأوضح وأنقى دون أن يبدو مضغوطاً أو مصطنعاً')
        res['chains'] = {'order': corder, **cinf, 'filters': CHAINS}
        res['winner'] = {'voice': win.split('·')[0], 'style': win.split('·')[1],
                         'director': styles[win.split('·')[1]], 'chain': corder[0], 'filter': CHAINS[corder[0]]}
    res['judge_calls'] = judge.calls
    (out / f'{slug}-results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    log('الفائز:', json.dumps(res.get('winner'), ensure_ascii=False))
    return 0 if res.get('winner') else 1


if __name__ == '__main__':
    sys.exit(main())
