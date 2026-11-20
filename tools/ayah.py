# -*- coding: utf-8 -*-
"""الآية نصّاً مركّباً على اللقطة مع صمتٍ تامّ (حكم المالك 2026-11-01: «لا بأس بعرض الآية»، والمرجع الموحّد: production-playbook §التلاوة).

حقل اللقطة:
  "ayah": {"text": "<نصّ الآية من المصحف كما أعاده موصل دلائل get_ayah>", "ref": "الكهف: 97"}
  واللقطة لقطةُ إمساك: "blocks": [] و"hold": ثوانٍ (لا راوي عليها).

⛔ النصّ من المصحف (دلائل) لا من الذاكرة ولا من نموذج صور، ويُرسم هنا بخطّ أميري القرآن (OFL) بالرسم العثمانيّ (textUthmani) بمحرّك raqm الذي يحفظ التشكيل.
⛔ لا تلاوة مولَّدة، ولا جوّ ولا مؤثّر تحت الآية: mont_hybrid يكتم المزج كلّه في نافذتها (silence_expr).
"""
import os, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# أميري القرآن (OFL 1.1، مشروع أميري — assets/fonts/OFL-AmiriQuran.txt): خطٌّ مصمَّمٌ لرسم المصحف بعلامات الضبط والوقف
FONT = os.path.join(_REPO, 'assets', 'fonts', 'AmiriQuran-Regular.ttf')
CREAM, GOLD = (246, 238, 216, 255), (214, 178, 98, 255)


def _font(size):
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)


def _wrap(d, text, f, maxw):
    """يقسم الآية أسطراً لا يتجاوز أحدها maxw، ويوازن الأسطر بدل ترك كلمةٍ يتيمة."""
    words = text.split()
    tw = lambda s: d.textlength(s, font=f, direction='rtl', language='ar')
    n = 1
    while tw(text) / n > maxw and n < 5:
        n += 1
    lines, cur, target = [], [], tw(text) / n
    for w in words:
        if cur and tw(' '.join(cur + [w])) > max(target * 1.12, 1) and len(lines) < n - 1:
            lines.append(' '.join(cur)); cur = [w]
        else:
            cur.append(w)
    lines.append(' '.join(cur))
    return lines


def render(spec: dict, out: str, size: int = 78) -> str:
    """لوحٌ شفّاف 1920×1080: تعتيمٌ ناعم، والآية بين القوسين المزخرفين، ومرجعها تحتها."""
    text = ' '.join(spec['text'].split())
    text = re.sub(r'\s+([\u06D6-\u06DC])', r'\1', text)   # علامات الوقف تلتصق بكلمتها فلا تُرسم يتيمةً بين كلمتين
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dim = Image.new('RGBA', (W, H), (8, 6, 4, 165))
    im = Image.alpha_composite(im, dim)
    d = ImageDraw.Draw(im)
    f = _font(size)
    body = '﴿' + text + '﴾'
    lines = _wrap(d, body, f, 1500)
    while len(lines) > 3 and size > 54:
        size -= 6; f = _font(size); lines = _wrap(d, body, f, 1500)
    lh = size * 2.15   # علامات الوقف فوق السطر تحتاج فسحةً فلا تُقرأ تحت السطر الذي فوقها
    fr = _font(int(size * 0.5))
    block = lh * len(lines) + size * 0.9
    y = (H - block) / 2
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    for ln in lines:
        lw = ld.textlength(ln, font=f, direction='rtl', language='ar')
        ld.text(((W - lw) / 2, y), ln, font=f, fill=CREAM, direction='rtl', language='ar')
        y += lh
    ref = spec.get('ref') or ''
    if ref:
        rw = ld.textlength(ref, font=fr, direction='rtl', language='ar')
        ld.text(((W - rw) / 2, y + size * 0.15), ref, font=fr, fill=GOLD, direction='rtl', language='ar')
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shadow.putalpha(layer.split()[3].point(lambda v: int(v * 0.75)).filter(ImageFilter.GaussianBlur(8)))
    im = Image.alpha_composite(im, shadow)
    im = Image.alpha_composite(im, layer)
    im.save(out)
    return out


def silence_expr(windows, ramp: float = 0.35) -> str:
    """تعبير volume لـffmpeg: 1 خارج نوافذ الآيات، و0 داخلها، بمنحدرٍ قصير على الطرفين."""
    if not windows:
        return '1'
    parts = ['max(0,min(1,max((%.3f-t)/%.2f,(t-%.3f)/%.2f)))' % (a, ramp, b, ramp) for a, b in windows]
    return '*'.join(parts)


if __name__ == '__main__':   # معاينةٌ محلّية: python3 tools/ayah.py out.png "نصّ" "المرجع"
    import sys
    render({'text': sys.argv[2], 'ref': sys.argv[3] if len(sys.argv) > 3 else ''}, sys.argv[1])
    print(sys.argv[1])
