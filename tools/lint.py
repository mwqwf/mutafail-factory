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

# ⛔⛔ أمر المالك 2026-10-01 (درس المرابطين وصلاح الدين): الواقعة تُذكر كما وقعت، بلا أيّ تعليقٍ قد يُفهم منه
#    — ولو بشكلٍ غير مباشر — تنقّصٌ من مسلمٍ أو من تاريخ المسلمين، أو قد يولّد سوء فهم.
#    هذا خطأٌ يوقف التوليد (لا ملاحظة استشارية)؛ ويُصلَح بحذف التعليق لا بإعادة صياغته.
NAQS = ['التاريخ لا يعمل', 'التاريخ لا يرحم', 'لم يكن كله', 'لم تكن كلها', 'لم يكن فتحا', 'لم يكن فتحًا',
        'للأسف', 'مع الأسف', 'أخطأ', 'خطأ كبير', 'خطأ فادح', 'وصمة', 'نقطة سوداء', 'صفحة سوداء', 'سقطة', 'زلة',
        'تجاوزات', 'لا يخلو من', 'ليسوا دقيقين', 'ليس بريئا', 'ليست بريئة', 'على حساب', 'الوجه الآخر', 'الجانب المظلم']

def naqs(path):
    hits = []
    for raw in io.open(path, encoding='utf-8'):
        if '|' not in raw or raw.startswith('IMG:'): continue
        bid, _, txt = raw.rstrip('\n').split('|', 2) if raw.count('|') >= 2 else (raw.split('|')[0], '', '')
        plain = strip_d(txt).replace('ـ', '')
        for w in NAQS:
            if w in plain: hits.append((bid, w))
    return hits

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

        # ٦) ⛔ أفعالٌ وأسماءٌ ملتبسة نطقها المحرّك خطأً في «اليرموك» (سمعها المالك):
        #    «رَدُّوا» نُطقت «رُدُّوا» (مبنيّاً للمجهول) · «المال» بحركةٍ غير المكتوبة.
        #    ⇒ استبدل بمرادفٍ لا يحتمل وجهين، أو أنهِ الجملة بالكلمة ساكنة.
        RISKY = {'ردوا': 'أَعَادُوا', 'رد': 'أَعَادَ', 'يرد': 'يُعِيدُ', 'فيرد': 'فَيُعِيدُ', 'المال': 'الْأَمْوَالَ (أو سكّنها آخرَ الجملة)',
                 'قتل': 'استُشهد/صُرع بصيغة لا تلتبس', 'حكم': 'تولّى الحكم',
                 'سماها': 'وَصَفَهَا (بدر 2026-10-01: «سمّاها» نُطقت بلا شدّة — سمعها المالك)', 'سماه': 'وَصَفَهُ'}
        for w in plain.replace('،', ' ').replace('.', ' ').split():
            if w in RISKY:
                bad.append((bid, 'كلمة ملتبسة النطق — ' + w + ' ← ' + RISKY[w], w))

        # ٥) همزات وإملاء شائع الخطأ
        for w, fix in [('إنشاء الله','إن شاء الله'), ('لاكن','لكن'), ('هاذا','هذا')]:
            if w in plain: bad.append((bid, 'إملاء', w+' ← '+fix))
    return bad

if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 'script.md'
    hits = naqs(p)
    if hits:
        print('⛔ %d تعليقاً قد يُفهم منه تنقّصٌ من مسلمٍ أو من تاريخ المسلمين — احذف التعليق واذكر الواقعة مجرّدة:' % len(hits))
        for bid, w in hits: print('  %s | «%s»' % (bid, w))
        print('')
    bad = check(p)
    if hits and not bad:
        sys.exit(1)
    if not bad:
        print('✅ لا ملاحظات لغوية وقائية — يجوز التوليد')
        sys.exit(0)
    print('⚠ %d ملاحظة وقائية (استشارية — حكِّمها ولا تتبعها عمياء):' % len(bad))
    for bid, why, what in bad:
        print('  %s | %s | %s' % (bid, why, what))
    print('')
    print('القاعدة: أصلحها في النصّ قبل التوليد؛ فكل واحدة تُترك قد تكلّف أربع توليدات إصلاح.')
    sys.exit(1 if hits else 0)
