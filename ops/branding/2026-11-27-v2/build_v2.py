"""هوية المتفائل v2 — تركيب الأيقونتين والغلافين من أصلين مولَّدين بلا نص."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
SRC, V1, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CH = {"battles": dict(src="battles_emblem_source.jpg", scale=0.89, v1="history"),
      "hikayat": dict(src="hikayat_emblem_source.jpg", scale=0.85, v1="hikayat")}

def icon(src, scale):
    im = Image.open(src).convert("RGB").resize((800, 800), Image.LANCZOS)
    # خلفية ممتدة من حواف الأصل نفسه (لا خط فاصل)
    bg = im.resize((24, 24), Image.BOX).resize((800, 800), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
    s = int(800 * scale); sm = im.resize((s, s), Image.LANCZOS)
    m = Image.new("L", (s, s), 0); d = ImageDraw.Draw(m)
    d.ellipse((0, 0, s, s), fill=255)  # قناع دائري واسع مخفّف الحواف
    m = m.filter(ImageFilter.GaussianBlur(s * 0.06))
    bg.paste(sm, ((800 - s) // 2, (800 - s) // 2), m)
    # عمق: تظليل حواف خفيف + حدّة
    yy, xx = np.mgrid[0:800, 0:800]; r = np.hypot(xx - 400, yy - 400) / 400
    v = np.clip(1 - 0.28 * np.clip(r - 0.55, 0, 1) ** 1.4, 0, 1)[..., None]
    a = (np.asarray(bg).astype(float) * v).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(a).filter(ImageFilter.UnsharpMask(1.2, 60, 2))
    return ImageEnhance.Contrast(out).enhance(1.04)

def circ(im, s, edge=None):
    ss = 4; big = im.resize((s * ss, s * ss), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", big.size, 0); d = ImageDraw.Draw(m); d.ellipse((0, 0, s * ss - 1, s * ss - 1), fill=255)
    big.putalpha(m)
    if edge:
        e = Image.new("RGBA", big.size, (0, 0, 0, 0)); de = ImageDraw.Draw(e)
        w = edge * ss
        de.ellipse((w // 2, w // 2, s * ss - w // 2 - 1, s * ss - w // 2 - 1), outline=(226, 184, 92, 255), width=w)
        big = Image.alpha_composite(big, e)
    return big.resize((s, s), Image.LANCZOS)

def banner(name, ic, v1dir, outdir):
    L = os.path.join(v1dir, "layers"); lay = json.load(open(os.path.join(L, "layout.json")))
    base = Image.open(os.path.join(L, "L0_background_2560x1440.jpg")).convert("RGBA")
    base = Image.alpha_composite(base, Image.open(os.path.join(L, "L1_scrim.png")).convert("RGBA"))
    mk = lay["mark"]; s = mk["size"]
    mark = circ(ic, s, edge=4)
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sm = Image.new("L", (s, s), 0); ImageDraw.Draw(sm).ellipse((0, 0, s, s), fill=170)
    sh.paste((0, 0, 0, 255), (mk["x"] + 6, mk["y"] + 12), sm)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    base = Image.alpha_composite(base, sh)
    L2 = Image.new("RGBA", base.size, (0, 0, 0, 0)); L2.paste(mark, (mk["x"], mk["y"]), mark)
    base = Image.alpha_composite(base, L2)
    base = Image.alpha_composite(base, Image.open(os.path.join(L, "L3_text.png")).convert("RGBA"))
    p = os.path.join(outdir, f"{name}_banner_2560x1440.jpg")
    base.convert("RGB").save(p, quality=92, optimize=True, progressive=True)
    sa = lay["safe_area"]; base.convert("RGB").crop(tuple(sa)).save(os.path.join(outdir, f"{name}_banner_mobile_safe_crop.jpg"), quality=90)
    os.makedirs(os.path.join(outdir, "layers"), exist_ok=True)
    L2.save(os.path.join(outdir, "layers", "L2_mark_v2.png"), optimize=True)
    return p

for name, c in CH.items():
    od = os.path.join(OUT, name); os.makedirs(od, exist_ok=True)
    ic = icon(os.path.join(SRC, c["src"]), c["scale"])
    ic.save(os.path.join(od, f"{name}_youtube_icon_800x800.png"), optimize=True)
    ic.resize((512, 512), Image.LANCZOS).save(os.path.join(od, f"{name}_bot_avatar_512x512.png"), optimize=True)
    circ(ic, 150).save(os.path.join(od, f"{name}_watermark_150x150.png"), optimize=True)
    circ(ic, 800).save(os.path.join(od, f"{name}_mark_transparent_800.png"), optimize=True)
    print(name, banner(name, ic, os.path.join(V1, c["v1"]), od))
