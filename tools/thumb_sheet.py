# -*- coding: utf-8 -*-
"""لوحة مصغّراتٍ للفحص بالعين — دراسة اختيار الحلقة 2026-10-14.
تُنزَّل مصغّرات يوتيوب المنشورة كما هي (لا توليد صور) وتُرصّ في لوحتين: الأعلى مضاعفاً والأدنى، مع المضاعف تحت كلٍّ.
الاستعمال: python tools/thumb_sheet.py ops/stats/thumbs.json out/"""
import io, json, os, sys, urllib.request
from PIL import Image, ImageDraw

W, H, COLS = 320, 180, 5


def sheet(items, path):
    rows = (len(items) + COLS - 1) // COLS
    im = Image.new('RGB', (COLS * W, rows * (H + 22)), 'white')
    dr = ImageDraw.Draw(im)
    for i, (vid, m) in enumerate(items):
        x, y = (i % COLS) * W, (i // COLS) * (H + 22)
        try:
            b = urllib.request.urlopen(f'https://i.ytimg.com/vi/{vid}/mqdefault.jpg', timeout=20).read()
            im.paste(Image.open(io.BytesIO(b)).convert('RGB').resize((W, H)), (x, y))
        except Exception:
            pass
        dr.text((x + 4, y + H + 4), f'{i + 1}. x{m}  {vid}', fill='black')
    im.save(path, quality=85)


cfg = json.load(open(sys.argv[1], encoding='utf-8'))
os.makedirs(sys.argv[2], exist_ok=True)
sheet(cfg['أعلى'], os.path.join(sys.argv[2], 'thumbs_top.jpg'))
sheet(cfg['أدنى'], os.path.join(sys.argv[2], 'thumbs_low.jpg'))
print('✅ لوحتا المصغّرات')
