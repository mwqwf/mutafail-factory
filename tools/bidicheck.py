# -*- coding: utf-8 -*-
"""⛔ حارسُ اتّجاه العربية — يمنع عودةَ «العناوين المقلوبة».

الاستعمال: python tools/bidicheck.py        (لا يحتاج شبكةً ولا رصيدًا)

الحكَم: على بيئةٍ فيها RAQM، رسمُ النصّ **المنطقيّ** بمحرّك RAQM هو الصوابُ
المرجعيّ. فنقارن به ما تُخرجه أدواتُنا (قلبٌ يدويّ + محرّك BASIC):
  • تطابقٌ تقريبيّ ⇒ الاتجاه سليم.
  • اختلافٌ كبير  ⇒ قلبٌ مزدوجٌ أو مفقود ⇒ سقوطُ الفحص.
وإن غاب RAQM (وندوز) اكتفى الفحصُ بالتحقّق من أن الأدوات لا تستدعي
ImageFont.truetype مباشرةً — فذلك بابُ العطب.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
CARD_TOOLS = ("mkreel3d.py", "mkthumb.py")
SAMPLE = "عشرون تمثالاً واقفاً ثم لا واحد"
fails = []

# ١) لا استدعاءَ مباشرًا لـtruetype في أدوات البطاقات
for t in CARD_TOOLS:
    src = open(os.path.join(HERE, t), encoding="utf-8").read()
    if re.search(r"ImageFont\.truetype\(", src):
        fails.append(f"⛔ {t}: استدعاءٌ مباشرٌ لـImageFont.truetype — استعمل envpaths.arfont")
    if re.search(r"get_display\(", src):
        fails.append(f"⛔ {t}: قلبٌ يدويٌّ مكرّر — استعمل envpaths.ar وحده")

# ٢) مقارنةُ الرسم بالمرجع حين يتوفّر RAQM
if features.check("raqm"):
    FB = envpaths.font(bold=True)
    W, H = 1400, 200

    def draw(text, f):
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).text((20, 40), text, font=f, fill=255)
        return im

    ours = draw(envpaths.ar(SAMPLE), envpaths.arfont(64, path=FB))
    ref = draw(SAMPLE, ImageFont.truetype(FB, 64,
                                          layout_engine=ImageFont.Layout.RAQM))
    a, b = ours.tobytes(), ref.tobytes()
    diff = sum(1 for x, y in zip(a, b) if abs(x - y) > 48) / float(len(a))
    print(f"فرقُ البكسلات عن المرجع: {diff:.4f}")
    if diff > 0.02:
        fails.append("⛔ اتّجاهُ النصّ يخالف المرجع — قلبٌ مزدوجٌ أو مفقود "
                     "(راجع محرّكَ التخطيط في envpaths.arfont)")
else:
    print("⚠️ لا RAQM في هذه البيئة — اكتُفي بالفحص الساكن")

if fails:
    print("\n".join(fails)); sys.exit(1)
print("✅ اتّجاهُ العربية سليمٌ في أدوات البطاقات")
