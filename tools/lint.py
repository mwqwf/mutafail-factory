# -*- coding: utf-8 -*-
"""فاحص لغوي وقائي — يُشغَّل على script.md قبل أي توليد صوت (بلا رصيد).
الاستعمال:  python ~/.claude/skills/video-factory/lint.py <path>/script.md
يمسك أنماط الخطأ التي أثبت القياس أنها تُنتج رايات."""
import io, re, sys

TANWEEN = 'ًٌٍ'
DIAC = 'ًٌٍَُِّْ'
# أعلام أعجمية شائعة في أفلامنا — تحتاج مضافًا عربيًّا قبلها وسكونًا في آخرها
# القائمة مقصورة على ما أثبت القياس أنه يُنتج رايات فعلًا
# (الأعلام المستعرَبة القديمة كبجاية وغرناطة وصقلية تُنطق سليمة فلا تُدرَج)
FOREIGN = ['تُونُس','تِلِمْسَان','فَرَنْسَا','أُورُوبَّا','لُوِيس','قَشْتَالَة','سِرَقُوسَة',
           'السِّنِغَال','الْفَايْكِنْج','مَلِيلِيَّة','وَرْجِلَان','بَطَلْيَوْس','سَرَقُسْطَة']
MUDAF = ['مَدِينَةِ','بِلَادِ','جَزِيرَةِ','مَلِكُ','مَلِكِ','سَاحِلِ','نَهْرِ','قَبَائِلِ','وَادِي','جَبَلِ','أَهْلِ','قَصْرِ']

def strip_d(s): return ''.join(c for c in s if c not in DIAC)

def check(path):
    bad = []
    for ln, raw in enumerate(io.open(path, encoding='utf-8'), 1):
        # `r_###` كتلُ الريلزات — تُفحص لغويًّا كغيرها ولا تدخل الفيلم
        m = re.match(r'^(d_\d{3}|m_\d{3}|r_\d{3})\|(\w)\|(.+)$', raw.rstrip('\n'))
        if not m: continue
        bid, txt = m.group(1), m.group(3).strip()

        # ١) تنوين في آخر الكتلة
        tail = txt.rstrip().rstrip('.؟!»…')
        if tail and tail[-1] in TANWEEN:
            bad.append((bid, 'تنوين في آخر الكتلة', tail[-6:]))

        # ٢) «ابن» بين علمين بدل «بْن»
        if re.search(r'(?<!\S)ابْنِ?\s', txt) and not txt.strip().startswith('ابْن'):
            bad.append((bid, 'استعمل «بْن» الساكنة بين العلمين', 'ابن'))

        # ٣) أرقام داخل النصّ
        if re.search(r'[0-9٠-٩]', txt):
            bad.append((bid, 'رقم داخل النصّ — اكتب العدد بالحروف', re.search(r'[0-9٠-٩]+', txt).group()))

        # ٤) علم أعجمي بلا مضاف عربي قبله وبلا سكون في آخره
        plain = strip_d(txt)
        for f in FOREIGN:
            pf = strip_d(f)
            for mm in re.finditer(re.escape(pf), plain):
                before = plain[:mm.start()].split()
                prev = before[-1] if before else ''
                if strip_d(prev) in [strip_d(x) for x in MUDAF]: continue
                seg = txt[max(0, mm.start()-2):]
                idx = plain.find(pf, mm.start()) + len(pf)
                nxt = plain[idx:idx+1]
                if nxt and nxt not in ' ،.؛:':
                    continue
                bad.append((bid, 'علم أعجمي بلا مضاف عربي قبله', f))
                break

        # ٥) همزات وإملاء شائع الخطأ
        for w, fix in [('إنشاء الله','إن شاء الله'), ('لاكن','لكن'), ('هاذا','هذا')]:
            if w in plain: bad.append((bid, 'إملاء', w+' ← '+fix))
    return bad

if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 'script.md'
    bad = check(p)
    if not bad:
        print('✅ لا ملاحظات لغوية وقائية — يجوز التوليد')
        sys.exit(0)
    print('⚠ %d ملاحظة وقائية (استشارية — حكِّمها ولا تتبعها عمياء):' % len(bad))
    for bid, why, what in bad:
        print('  %s | %s | %s' % (bid, why, what))
    print('')
    print('القاعدة: أصلحها في النصّ قبل التوليد؛ فكل واحدة تُترك قد تكلّف أربع توليدات إصلاح.')
    sys.exit(0)
