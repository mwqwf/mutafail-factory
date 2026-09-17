#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس المحظورات — يُشغَّل إلزامًا على script.md قبل توليد أي صورة أو صوت.
   الاستعمال:  python guard.py <path/to/script.md>
   يعود بـ exit code 1 عند أي مخالفة، فيوقف خطّ الإنتاج."""
import io, re, sys, os

# ⛔ محظورات صاحب القناة — لا تُخفَّف ولا يُستثنى منها شيء
BANNED_IMG = {
    'نساء': r'\b(woman|women|girl|girls|female|lady|ladies|mother|wife|bride|feminine)\b',
    'آلات موسيقية': r'\b(lute|oud|guitar|instrument|instruments|musician|musicians|tidinit|ardin|drum|drums|flute|string\s+instrument|playing\s+music|band|orchestra)\b',
    'موسيقى': r'\b(music|musical|singing|singer|song|dancing|dancer|dance)\b',
    'كتابة في الصورة': r'\b(text|letters|caption|inscription|calligraphy|signboard|banner\s+with|written)\b(?!.*\bNo\b)',
}
# الجملة الواقية الإلزامية في آخر كل وصف صورة
REQUIRED_TAIL = 'No text, no letters, no captions, no watermark.'

def main(path):
    if not os.path.exists(path):
        print(f'✗ لا يوجد ملف: {path}'); return 1
    # ⛔⛔ ثغرةٌ أُغلقت 2026-09-14: الحارسُ كان يفحص `script.md` وحدَه، و`images-extra.md`
    #    فيه أوصافُ صورٍ تُولَّد وتدخل الفيلم كغيرها — فكانت تمرّ بلا فحصٍ البتّة.
    files = [path]
    extra = os.path.join(os.path.dirname(os.path.abspath(path)), 'images-extra.md')
    if os.path.basename(path) == 'script.md' and os.path.exists(extra):
        files.append(extra)

    problems = []
    imgs = 0
    for f in files:
        lines = io.open(f, encoding='utf-8').read().split('\n')
        for n, l in enumerate(lines, 1):
            if not l.startswith('IMG:'):
                continue
            imgs += 1
            body = l.split('|', 2)[-1]
            low = body.lower()
            for label, pat in BANNED_IMG.items():
                m = re.search(pat, low, re.I)
                if m:
                    problems.append((f'{os.path.basename(f)}:{n}', label, m.group(0), l[:90]))
            if REQUIRED_TAIL.lower() not in low:
                problems.append((f'{os.path.basename(f)}:{n}', 'الجملة الواقية ناقصة', REQUIRED_TAIL, l[:90]))

    print(f'فُحص {imgs} وصف صورة في {" و".join(os.path.basename(f) for f in files)}')
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
