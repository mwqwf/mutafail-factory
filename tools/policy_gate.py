# -*- coding: utf-8 -*-
"""بوّابة المخالفات — لا فيلم ولا ريلز ولا مصغّرة فيها ما قد يعدّه يوتيوب مخالفة.

⛔⛔ أمر المالك 2026-10-25 بعد أن أزال يوتيوب ريلز الفيل بتحذير «أذى الحيوان» ورُفض الاعتراض:
   «يجب أن لا يتكرّر هذا تحت أيّ طائل سواء حيوان أو إنسان أو غيره. ادرس كلّ ما قد يعتبرونه مخالفة دورياً
    ثم تأكّد من أنّ أيّ فلم لن يكون فيه مخالفة».
   الدراسة والقواعد في ops/policy/README.md، والمعجم في ops/policy/lexicon.json (يُحدَّث في المراجعة الدورية).

طبقتان:
  text   — بلا شبكة ولا كلفة: السيناريو (script.md وimages-extra.md)، وأوامر كوديكس (codex_job.json)، وحركات اللقطات
           (shots.json)، ونصوص البطاقات (cards.json)، وعناوين الريلزات وأوصافها (reels.json)، وعنوان الفيلم ووصفه ووسومه
           (publish.json). يُشغَّل من precheck.py قبل الختم، ومن شوط النشر، ومن guard على طابور كوديكس.
  media  — يشاهد جيميناي الفيلم النهائيّ كلَّه (إطارٌ كلّ ثانيتين في لوحاتٍ مرقّمة بالزمن) والريلزات والمصغّرة بمعيار
           السياسات، ويحكم: block (إزالة أو إنذار محتمل) / restrict (تقييد عمريّ محتمل) / warn. ويُشغَّل في شوط النشر قبل الرفع،
           وفي policy-check.yml على أيّ إصدار.

⛔ البوّابة لا تُخفَّف لتمرير شوط: ما تمسكه يُحذف من المصدر أو يُكنّى عنه، لا يُعاد صوغه بالتفصيل نفسه.
⛔ التعذّر ليس نجاحاً: إن لم يُشرَّح الفيلم (حصّةٌ أو خطأ) خرجت بـ2 فلا يُنشر.

الاستعمال:
  python tools/policy_gate.py text  <مجلد_الحمولة> [--codex <codex_job.json>] [--out /tmp/policy_text.json]
  python tools/policy_gate.py media <مجلد_فيه film.mp4 وreels/ وthumb-a.jpg> --keys /tmp/keys.json [--out /tmp/policy_media.json]
خروج 0 = تجتاز · 1 = مخالفة مانعة · 2 = تعذّر التشريح (media)."""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
LEX = os.path.join(ROOT, 'ops', 'policy', 'lexicon.json')

DIAC = 'ًٌٍَُِّْٰ'
# تعابير واقية في أوامر الصور لا تُعدّ ذكراً للمحظور
NEG_EN = re.compile(r'\b(no|without|never|not)\s+(blood|bloody|wounds?|corpses?|gore|dead bodies|injur\w+|crosses|icons|text|letters|women|nudity|violence|visible wounds?|suffering)\b[^.;,]*', re.I)
NEG_AR = re.compile(r'(بلا|بدون|لا|دون)\s+(دم|دماء|جراح|جرح|جثث|اشلاء|أشلاء|عنف|اذى|أذى)\w*')


def norm_ar(s: str) -> str:
    s = ''.join(c for c in s if c not in DIAC).replace('ـ', '')
    s = re.sub('[أإآٱ]', 'ا', s).replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    return NEG_AR.sub(' ', s)


def norm_en(s: str) -> str:
    return NEG_EN.sub(' ', s)


def load_lex(path: str = LEX) -> dict:
    return json.load(io.open(path, encoding='utf-8'))


# ─────────────────────────── الطبقة النصّية ───────────────────────────

def script_lines(path: str):
    """كتل السيناريو: (المعرّف، النصّ). سطور IMG: أوصاف صورٍ بالإنجليزية."""
    for raw in io.open(path, encoding='utf-8'):
        raw = raw.rstrip('\n')
        if raw.startswith('IMG:'):
            name, _, txt = raw[4:].partition('|')
            yield 'IMG:' + name.strip(), txt
        elif raw.count('|') >= 2:
            bid, _, txt = raw.split('|', 2)
            yield bid.strip(), txt


def gather(proj: str, codex: str | None) -> list[tuple[str, str, str]]:
    """(المصدر، المعرّف، النصّ) من كلّ ما يصل إلى الشاشة أو السمع أو الواجهة. النطاق: body أو metadata أو description."""
    items: list[tuple[str, str, str]] = []
    J = lambda n: json.load(io.open(os.path.join(proj, n), encoding='utf-8'))
    for f in ('script.md', 'images-extra.md'):
        p = os.path.join(proj, f)
        if os.path.exists(p):
            items += [('body:' + f, bid, txt) for bid, txt in script_lines(p)]
    p = os.path.join(proj, 'shots.json')
    if os.path.exists(p):
        for s in J('shots.json'):
            if s.get('move'):
                items.append(('body:shots.json', s.get('id', '?'), str(s['move'])))
    p = os.path.join(proj, 'images.json')
    if os.path.exists(p):
        for im in J('images.json'):
            if isinstance(im, dict) and im.get('prompt'):
                items.append(('body:images.json', im.get('id', '?'), str(im['prompt'])))
    p = os.path.join(proj, 'cards.json')
    if os.path.exists(p):
        c = J('cards.json')
        for k, v in (c.items() if isinstance(c, dict) else enumerate(c)):
            if isinstance(v, dict):
                items.append(('metadata:cards.json', str(k), ' '.join(str(v.get(x) or '') for x in ('text', 'sub'))))
    p = os.path.join(proj, 'reels.json')
    if os.path.exists(p):
        for r in J('reels.json'):
            items.append(('metadata:reels.json', r.get('id', '?'), ' '.join(str(r.get(x) or '') for x in ('title', 'hook', 'end_q'))))
            if r.get('description'):
                items.append(('description:reels.json', r.get('id', '?'), str(r['description'])))
    p = os.path.join(proj, 'publish.json')
    if os.path.exists(p):
        m = J('publish.json')
        film = m.get('film') or {}
        items.append(('metadata:publish.json', 'film.title', str(film.get('title') or m.get('title') or '')))
        items.append(('metadata:publish.json', 'film.tags', ' '.join(film.get('tags') or m.get('tags') or [])))
        items.append(('description:publish.json', 'film.description', str(film.get('description') or m.get('description') or '')))
        for r in m.get('reels') or []:
            items.append(('metadata:publish.json', r.get('file', '?'), str(r.get('title') or '')))
            items.append(('description:publish.json', r.get('file', '?'), str(r.get('description') or '')))
        for t in m.get('thumb_texts') or []:
            items.append(('metadata:publish.json', 'thumb', str(t)))
    if codex and os.path.exists(codex):
        job = json.load(io.open(codex, encoding='utf-8'))
        for it in job.get('items') or []:
            items.append(('body:codex_job.json', str(it.get('file', '?')), str(it.get('prompt') or '') + ' ' + str(it.get('text') or '')))
    return items


AR_L = '\u0621-\u064A'
AR_PRE = '(?:وال|فال|بال|كال|ولل|فلل|ال|لل|و|ف|ب|ل|ك|س)?'


def ar_rx(pat: str):
    """كلمةٌ أو عبارةٌ عربيّة بحدودها: سابقةٌ صرفيّة اختيارية، ولاحقةٌ حتى ثلاثة أحرف (ضمائر وجموع)، ولا حرفَ قبلها.
    فـ«دم» لا تُمسك في «قدم»، و«خول» لا تُمسك في «دخول»، و«ضرب» تُمسك «ضربوا» و«فضربوه»."""
    core = r'\s+'.join(re.escape(w) for w in norm_ar(pat).split())
    # النمط المختوم بمسافةٍ في المعجم («كس »، «زب ») كلمةٌ تامّة بلا لاحقة: كانت اللاحقة تُمسك «كسرى» و«كسره» (2026-10-28)
    tail = '' if pat.endswith(' ') else '[%s]{0,3}' % AR_L
    return re.compile('(?<![%s])%s%s%s(?![%s])' % (AR_L, AR_PRE, core, tail, AR_L))


_RX: dict = {}


def ar_hit(pat: str, ar: str) -> bool:
    rx = _RX.get(pat)
    if rx is None:
        rx = _RX[pat] = ar_rx(pat)
    return bool(rx.search(ar))


def scan_text(items: list[tuple[str, str, str]], lex: dict) -> list[dict]:
    hits = []
    lists = {k: v for k, v in lex.items() if k.endswith('_ar')}
    for rule in lex['القواعد']:
        scope = rule.get('النطاق', 'body')
        for src, bid, txt in items:
            s_scope = src.split(':')[0]
            if scope == 'body' and s_scope != 'body':
                continue
            if scope in ('metadata', 'description') and s_scope != scope:
                continue
            ar, en = norm_ar(txt), norm_en(txt)
            found = []
            kind = rule['النوع']
            if kind == 'ar':
                found = [p for p in rule['أنماط'] if ar_hit(p, ar)]
            elif kind == 'en':
                found = [m.group(0) for p in rule['أنماط'] for m in re.finditer(p, en, re.I)]
            elif kind == 'تلازم':
                a = [w for w in lists[rule['أ']] if ar_hit(w, ar)]
                b = [w for w in lists[rule['ب']] if ar_hit(w, ar)]
                if a and b:
                    found = ['%s + %s' % (a[0], b[0])]
            elif kind == 'غياب':
                if not any(ar_hit(p, ar) or p in txt for p in rule['أنماط']):
                    found = ['غياب الإفصاح']
            if found:
                hits.append({'الفئة': rule['الفئة'], 'الشدة': rule['الشدة'], 'المصدر': src, 'الكتلة': bid,
                             'ما وُجد': found[:3], 'النصّ': txt[:160], 'لماذا': rule['لماذا']})
    return hits


def run_text(a) -> int:
    lex = load_lex(a.lexicon)
    items = gather(a.proj, a.codex)
    hits = scan_text(items, lex)
    blocks = [h for h in hits if h['الشدة'] == 'block']
    warns = [h for h in hits if h['الشدة'] != 'block']
    if a.out:
        json.dump({'فُحص': len(items), 'موانع': blocks, 'تنبيهات': warns}, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('بوّابة المخالفات (نصّ): فُحص %d عنصراً' % len(items))
    for h in warns:
        print('⚠️ [%s] %s %s: %s — «%s»' % (h['الفئة'], h['المصدر'], h['الكتلة'], ', '.join(h['ما وُجد']), h['النصّ'][:90]))
    for h in blocks:
        print('⛔ [%s] %s %s: %s — «%s»\n   ↳ %s' % (h['الفئة'], h['المصدر'], h['الكتلة'], ', '.join(h['ما وُجد']), h['النصّ'][:90], h['لماذا'][:200]))
    print('✅ لا مخالفة نصّية' if not blocks else '⛔ %d مخالفةً مانعة — لا توليد ولا نشر حتى تُحذف من المصدر' % len(blocks))
    return 1 if blocks else 0


# ─────────────────────────── الطبقة البصرية ───────────────────────────

SHEET_COLS, SHEET_ROWS, TILE_W, TILE_H = 6, 5, 320, 180
SHEETS_PER_CALL = 6

PROMPT = """أنت مراجع سياسات يوتيوب (إرشادات المنتدى وسياسة المصغّرات والإرشادات الملائمة للمعلنين). أمامك لوحاتٌ من إطارات فيلمٍ وثائقيٍّ تاريخيٍّ عربيّ بصورٍ واقعيّة مولَّدة بالذكاء الاصطناعيّ (ليست تصويراً حقيقياً)، كلُّ إطارٍ فوقه ملصقٌ بالزمن (ث) أو باسم الملف.
افحص كلّ إطارٍ على حدة وأبلغ عن كلّ ما قد يؤدّي إلى إزالةٍ أو إنذارٍ (block) أو تقييدٍ عمريّ (restrict) أو يستحقّ مراجعةً بشرية (warn):
١) أذى حيوان: إنسانٌ يضرب أو يطعن أو يجلد أو يدفع بمحاجن أو يرمي أو يدوس حيواناً (فيل، جمل، خيل…)، أو حيوانٌ جريح أو ينزف أو يتألّم بفعل إنسان. حتى بلا دم. (block)
٢) عنف صادم: دم ظاهر، جراح مفتوحة، أشلاء، رؤوس أو أطراف مقطوعة، جثث بإصابات شديدة أو منتفخة، تعذيب، صلب، حرق إنسانٍ حيّاً، خوزقة، تمثيلٌ بجثّة. (block)؛ لحظة قتلٍ أو موتٍ عنيف لإنسانٍ واقعيّ المظهر في لقطةٍ قريبة أو مطوَّلة، أو جثثٌ كثيرة محور الإطار. (restrict)
٣) طفلٌ أو قاصر في مشهد عنفٍ أو خطرٍ أو قربه. (block)
٤) عريٌ أو إيحاءٌ جنسيّ أو امرأة ظاهرة. (block)
٥) نصٌّ على الشاشة بذيءٌ أو يقصد الصدم والاشمئزاز (مثل: مقزّز، دموي، 18+). (block)
٦) رموز دينيّة تُدنَّس، أو شعارات جماعاتٍ عنيفة، أو إيماءات كراهية. (block)
٧) إيذاء النفس أو انتحار مصوَّر. (block)
٨) أيّ شيءٍ آخر قد يراه المراجع «بقصد الصدم»، أو مصغّرةٌ محورها دمٌ أو عنف، أو تضليل. (restrict/warn)
لا تبلغ عن: جيوشٍ تتقدّم، سيوفٍ مرفوعة، قتالٍ عامٍّ بلا دمٍ ولا جراح، فيلٍ بارك أو يمشي بلا أذى، غبارٍ ونيران مخيّمات، خرائط ورايات، وجوهٍ غاضبة. تلك لا تخالف.
كن حازماً فيما يخالف وصريحاً فيما لا يخالف. أجب بـJSON فقط بهذا الشكل:
{"findings":[{"severity":"block|restrict|warn","category":"animal|graphic|minor|sexual|text|hate|selfharm|other","where":"ملصق الإطار كما هو مكتوب","what":"ما رأيته بدقّة بالعربية","why":"السياسة"}],"summary":"سطر بالعربية"}
إن لم تجد شيئاً: {"findings":[],"summary":"..."}"""

SCHEMA = {'type': 'OBJECT', 'properties': {
    'findings': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'severity': {'type': 'STRING'}, 'category': {'type': 'STRING'}, 'where': {'type': 'STRING'},
        'what': {'type': 'STRING'}, 'why': {'type': 'STRING'}}, 'required': ['severity', 'category', 'where', 'what']}},
    'summary': {'type': 'STRING'}}, 'required': ['findings', 'summary']}


def frames(path: str, every: float, outdir: str, prefix: str) -> list[tuple[str, str]]:
    """إطارٌ كلّ every ثانية؛ الأفقيّ بعرض TILE_W والعموديّ (ريلز) بارتفاع 2×TILE_H. يعيد (ملف، ملصق الزمن)."""
    pat = os.path.join(outdir, prefix + '_%05d.jpg')
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path],
                        capture_output=True, text=True).stdout.strip().split(',')
    vert = len(pr) == 2 and pr[0].isdigit() and pr[1].isdigit() and int(pr[1]) > int(pr[0])
    scale = 'scale=-2:%d' % (2 * TILE_H) if vert else 'scale=%d:-2' % TILE_W
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-vf', 'fps=1/%s,%s' % (every, scale), '-q:v', '5', pat], check=True)
    return [(f, '%s %ds' % (prefix, round(i * every))) for i, f in enumerate(sorted(glob.glob(os.path.join(outdir, prefix + '_*.jpg'))))]


def sheets(tiles: list[tuple[str, str]], outdir: str, tag: str) -> list[tuple[str, str]]:
    """لوحاتٌ بملصق زمنٍ على كلّ إطار: الأفقيّ 6×5 بخانة 320×180، والعموديّ 10×3 بخانة 180×360. تعيد (ملف اللوحة، وصف مداها)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    except Exception:
        font = ImageFont.load_default()
    groups: dict[bool, list] = {False: [], True: []}
    for f, label in tiles:
        with Image.open(f) as im:
            groups[im.height > im.width].append((f, label))
    out = []
    for vert, items in groups.items():
        cols, rows, tw, th = (10, 3, TILE_H, 2 * TILE_H) if vert else (SHEET_COLS, SHEET_ROWS, TILE_W, TILE_H)
        per = cols * rows
        for n in range(0, len(items), per):
            chunk = items[n:n + per]
            sh = Image.new('RGB', (cols * tw, rows * th), (20, 20, 20))
            d = ImageDraw.Draw(sh)
            for i, (f, label) in enumerate(chunk):
                im = Image.open(f).convert('RGB')
                im.thumbnail((tw, th))
                x, y = (i % cols) * tw, (i // cols) * th
                sh.paste(im, (x, y))
                d.rectangle([x, y, x + 8 + 9 * len(label), y + 20], fill=(0, 0, 0))
                d.text((x + 4, y + 2), label, fill=(255, 230, 0), font=font)
            p = os.path.join(outdir, '%s_%s_%02d.jpg' % (tag, 'v' if vert else 'h', n // per + 1))
            sh.save(p, quality=82)
            out.append((p, '%s → %s' % (chunk[0][1], chunk[-1][1])))
    return out


def body(images: list[bytes], light: bool) -> bytes:
    parts = [{'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(b).decode('ascii')}} for b in images]
    parts.append({'text': PROMPT})
    cfg = {'temperature': 0.1, 'responseMimeType': 'application/json'}
    if not light:
        cfg['responseSchema'] = SCHEMA
    return json.dumps({'contents': [{'parts': parts}], 'generationConfig': cfg}).encode('utf-8')


def run_media(a) -> int:
    import openings  # noqa: E402  (Gem وkeys_from)
    keys = openings.keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي: الحالة المجهولة ليست نجاحاً'); return 2
    tmp = tempfile.mkdtemp(prefix='policy_')
    tiles: list[tuple[str, str]] = []
    film = next((p for p in (os.path.join(a.proj, 'film.mp4'), os.path.join(a.proj, 'preview480.mp4')) if os.path.exists(p)), None)
    if film:
        tiles += frames(film, a.every, tmp, 'film')
    reels = sorted(glob.glob(os.path.join(a.proj, 'reels', '*.mp4')) + glob.glob(os.path.join(a.proj, 'r[0-9].mp4')))
    for r in reels:
        tiles += frames(r, max(1.0, a.every / 2), tmp, os.path.splitext(os.path.basename(r))[0])
    thumbs = sorted(glob.glob(os.path.join(a.proj, 'thumb*.jpg')) + glob.glob(os.path.join(a.proj, 'thumb*.png')) + glob.glob(os.path.join(a.proj, 'thumbs', '*')))
    for t in thumbs:
        tiles.append((t, 'thumb ' + os.path.basename(t)))
    if not tiles:
        print('لا فيلم ولا ريلز ولا مصغّرة في المجلّد: لا بوّابة بصرية'); return 0
    shs = sheets(tiles, tmp, 'sheets')
    print('بوّابة المخالفات (صور): %d إطاراً في %d لوحة (فيلم %s، ريلزات %d، مصغّرات %d)' % (len(tiles), len(shs), 'نعم' if film else 'لا', len(reels), len(thumbs)), flush=True)
    g = openings.Gem(keys)
    findings, calls, failed = [], 0, []
    for n in range(0, len(shs), SHEETS_PER_CALL):
        chunk = shs[n:n + SHEETS_PER_CALL]
        data = [io.open(p, 'rb').read() for p, _ in chunk]
        r = g.call(lambda light, d=data: body(d, light), 'policy-%d' % (n // SHEETS_PER_CALL + 1), budget_s=a.budget)
        calls += 1
        if 'error' in r:
            failed.append(chunk[0][1] + ' … ' + chunk[-1][1]); print('   ↻ تعذّر: %s' % str(r['error'])[:160], flush=True); continue
        for f in r.get('findings') or []:
            f['sheets'] = '%s … %s' % (chunk[0][1], chunk[-1][1])
            findings.append(f)
        print('   لوحات %d–%d: %s' % (n + 1, n + len(chunk), str(r.get('summary', ''))[:140]), flush=True)
    for f in findings:
        mark = {'block': '⛔', 'restrict': '🔞', 'warn': '⚠️'}.get(f.get('severity'), '•')
        print('%s [%s] %s — %s (%s)' % (mark, f.get('category'), f.get('where'), f.get('what'), f.get('why', '')[:120]))
    blocks = [f for f in findings if f.get('severity') == 'block']
    restricts = [f for f in findings if f.get('severity') == 'restrict']
    if a.out:
        json.dump({'لوحات': len(shs), 'نداءات': calls, 'تعذّر': failed, 'نتائج': findings}, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if failed:
        print('⛔ لم تُشرَّح %d دفعة من اللوحات — الحالة المجهولة ليست نجاحاً، يُعاد بعد تجدّد الحصّة' % len(failed)); return 2
    if blocks:
        print('⛔ %d مخالفةً بصريّة مانعة — لا يُنشر حتى تُستبدل اللقطات' % len(blocks)); return 1
    if restricts and a.strict:
        print('⛔ %d لقطةً قد تُقيَّد عمرياً — بالوضع الصارم لا يُنشر' % len(restricts)); return 1
    print('✅ تجتاز بوّابة المخالفات البصرية' + (' (مع %d تنبيهاً يُراجَع بالعين)' % (len(findings)) if findings else ''))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='mode', required=True)
    t = sub.add_parser('text'); t.add_argument('proj'); t.add_argument('--codex'); t.add_argument('--out'); t.add_argument('--lexicon', default=LEX)
    m = sub.add_parser('media'); m.add_argument('proj'); m.add_argument('--keys', required=True); m.add_argument('--out')
    m.add_argument('--every', type=float, default=2.0); m.add_argument('--budget', type=int, default=600); m.add_argument('--strict', action='store_true')
    a = ap.parse_args(argv)
    return run_text(a) if a.mode == 'text' else run_media(a)


if __name__ == '__main__':
    sys.exit(main())
