#!/usr/bin/env python3
"""🔍 معاينة المصغّرات بالحجم الذي يراها به المشاهد فعلاً — قبل اعتمادها (أمر المالك 2026-10-03:
«المصغّرات لا تزال ضعيفة ولا تحمل تشويقاً»).

المصغّرةُ تُصمَّم على 1280×720 وتُرى في الجوال نحو 168×94 بكسلاً في «التالي» و≈360×202 في الصفحة
الرئيسية. ما لا يُقرأ ولا يُفهم في الصغير لا يُنقَر. فهذه الأداة **تحجّم** صور كوديكس فقط (لا ترسم ولا تولّد
شيئاً — الحظر الدائم على صناعة Claude للصور قائم) وتضعها في لوحةٍ واحدة بثلاثة أحجام، على خلفيّةٍ
فاتحةٍ وداكنة، لتُعاين بالعين: هل يُقرأ النصّ؟ هل يُرى الصراعُ والوجه؟ هل تختلف الثلاث عن بعضها؟

    python3 tools/thumb_preview.py out.jpg thumbs/x-A.png thumbs/x-B.png thumbs/x-C.png
"""
import sys

from PIL import Image

SIZES = [(360, 202), (246, 138), (168, 94)]   # الرئيسية · الاقتراحات على الحاسوب · «التالي» على الجوال
BG = [(255, 255, 255), (15, 15, 15)]           # وضعا يوتيوب الفاتح والداكن
PAD = 16


def sheet(files):
    ims = [Image.open(f).convert("RGB") for f in files]
    col = sum(w for w, _ in SIZES) + PAD * (len(SIZES) + 1)
    row = max(h for _, h in SIZES) + PAD
    out = Image.new("RGB", (col * len(BG), row * len(ims) + PAD), BG[0])
    for b, bg in enumerate(BG):
        out.paste(Image.new("RGB", (col, out.height), bg), (b * col, 0))
        for r, im in enumerate(ims):
            x = b * col + PAD
            for w, h in SIZES:
                out.paste(im.resize((w, h), Image.LANCZOS), (x, PAD + r * row))
                x += w + PAD
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sheet(sys.argv[2:]).save(sys.argv[1], quality=90)
    print("✅", sys.argv[1])
