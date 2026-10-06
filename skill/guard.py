#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس المحظورات — يُشغَّل إلزامًا على script.md قبل توليد أي صورة أو صوت.
   الاستعمال:  python guard.py <path/to/script.md>   أو   python guard.py <yarmouk-media/<slug>/codex_job.json>
   يعود بـ exit code 1 عند أي مخالفة، فيوقف خطّ الإنتاج.
   ⛔⛔ ثغرةٌ ثانية أُغلقت 2026-10-05 (مؤتة): صار كوديكس مصدرَ الصور كلّها (أمر المالك 2026-09-29)، وأوامره في
   codex_job.json لا في script.md، فكانت تمرّ بلا فحص ⇒ يُفحص كلّ وصفٍ فيه كسطر IMG. والمصغّرات (thumbs/) وبطاقات الكتابة
   (cards/، tools/cards.py) فيها نصٌّ مقصود، فتُعفى من الجملة الواقية وقاعدة الكتابة وحدهما لا من المحظورات."""
import io, re, sys, os
# طرفية وندوز (cp1252) تُسقط الطباعة العربية والرموز — يُفرض UTF-8 أيّاً كانت البيئة.
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8')
    except Exception: pass

# ⛔ محظورات صاحب القناة — لا تُخفَّف ولا يُستثنى منها شيء
BANNED_IMG = {
    'نساء': r'\b(woman|women|girl|girls|female|lady|ladies|mother|wife|bride|feminine)\b',
    'آلات موسيقية': r'\b(lute|oud|guitar|instrument|instruments|musician|musicians|tidinit|ardin|drum|drums|flute|string\s+instrument|playing\s+music|band|orchestra)\b',
    'موسيقى': r'\b(music|musical|singing|singer|song|dancing|dancer|dance)\b',
    'كتابة في الصورة': r'\b(text|letters|caption|inscription|calligraphy|signboard|banner\s+with|written)\b(?!.*\bNo\b)',
}
# الجملة الواقية الإلزامية في آخر كل وصف صورة
REQUIRED_TAIL = 'No text, no letters, no captions, no watermark.'

def codex_lines(path):
    """أوامر كوديكس سطورَ IMG: (الاسم، السطر، يُعفى من الجملة الواقية؟)."""
    import json
    job = json.load(io.open(path, encoding='utf-8'))
    return [(it.get('file', '?'), 'IMG:%s|%s' % (it.get('file', '?'), it.get('prompt', '').replace('\n', ' ')),
             str(it.get('file', '')).startswith(('thumbs/', 'cards/'))) for it in job.get('items') or []]


def main(path):
    if not os.path.exists(path):
        print(f'✗ لا يوجد ملف: {path}'); return 1
    if path.endswith('.json'):
        return check([(f'{os.path.basename(path)}:{name}', line, thumb) for name, line, thumb in codex_lines(path)],
                     os.path.basename(path))
    # ⛔⛔ ثغرةٌ أُغلقت 2026-09-14: الحارسُ كان يفحص `script.md` وحدَه، و`images-extra.md`
    #    فيه أوصافُ صورٍ تُولَّد وتدخل الفيلم كغيرها — فكانت تمرّ بلا فحصٍ البتّة.
    files = [path]
    extra = os.path.join(os.path.dirname(os.path.abspath(path)), 'images-extra.md')
    if os.path.basename(path) == 'script.md' and os.path.exists(extra):
        files.append(extra)

    rows = []
    for f in files:
        lines = io.open(f, encoding='utf-8').read().split('\n')
        rows += [(f'{os.path.basename(f)}:{n}', l, False) for n, l in enumerate(lines, 1) if l.startswith('IMG:')]
    return check(rows, " و".join(os.path.basename(f) for f in files))


def check(rows, where):
    """rows: (الموضع، سطر IMG، يُعفى من الجملة الواقية؟) — المحظورات على الجميع بلا استثناء."""
    problems = []
    imgs = 0
    for at, l, thumb in rows:
        imgs += 1
        body = l.split('|', 2)[-1]
        low = body.lower()
        for label, pat in BANNED_IMG.items():
            if thumb and label == 'كتابة في الصورة':
                continue                    # نصّ المصغّرة مقصود (والمحظورات الثلاث الأخرى باقية)
            m = re.search(pat, low, re.I)
            if m:
                problems.append((at, label, m.group(0), l[:90]))
        if not thumb and REQUIRED_TAIL.lower() not in low:
            problems.append((at, 'الجملة الواقية ناقصة', REQUIRED_TAIL, l[:90]))

    print(f'فُحص {imgs} وصف صورة في {where}')
    if problems:
        print(f'\n⛔ {len(problems)} مخالفة — التوليد موقوف:\n')
        for n, label, hit, ctx in problems:
            print(f'  {n} · {label} · «{hit}»')
            print(f'    {ctx}…')
        print('\nالبدائل المعتمدة:')
        print('  مشهد نسائي  ← خيمة من الخارج · مجلسٌ خالٍ · أدوات · ظلال · صحراء')
        print('  مشهد موسيقي ← نار المخيّم · مجلس سمر · ليل الصحراء (بلا آلة ولا عازف)')
        return 1
    print('✅ لا مخالفات — يجوز التوليد')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'script.md'))
