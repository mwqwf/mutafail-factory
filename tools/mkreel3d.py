# -*- coding: utf-8 -*-
"""ريلز عمودي 1080×1920 ⭐بالتحريك المجسَّم (parallax)⭐ + عنوان أعلى + شعار.
الاستعمال: python mkreel3d.py <projectDir> <reelId>
⛔ شرط مسبق: python kb3d.py depth <projectDir>
يقرأ <proj>/reels.json = [{"id":"r1","title":"...","blocks":["c003","c004"],"imgs":["b02","b03"]}]
"""
import json, os, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "Desktop", "claude-media"))
import kb3d
import envpaths
from PIL import Image, ImageDraw, ImageFont, ImageFilter
# ⛔ التهيئةُ والقلبُ وإلزامُ محرّك BASIC — كلُّها في envpaths، ولا تُكرَّر هنا
# (القلبُ المزدوج مع RAQM على لينكس كان يعكس العناوين — انظر envpaths.py).
from envpaths import ar

PROJ, RID = os.path.abspath(sys.argv[1]), sys.argv[2]
FF, FP = envpaths.FF, envpaths.FP
FB = envpaths.font(bold=True)
LOGO = envpaths.logo()
W, H = 1080, 1920

reels = {r["id"]: r for r in json.load(open(os.path.join(PROJ, "reels.json"), encoding="utf-8"))}
R = reels[RID]
WORK = os.path.join(PROJ, "reelwork", RID); os.makedirs(WORK, exist_ok=True)
OUTD = os.path.join(PROJ, "reels"); os.makedirs(OUTD, exist_ok=True)

def dur(f):
    o = sp.run([FP, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", f], capture_output=True, text=True)
    return float(o.stdout.strip())

# صوت الريلز
alist = os.path.join(WORK, "a.txt")
sil = os.path.join(WORK, "sil.wav")
sp.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "0.28", sil], check=True)
with open(alist, "w", encoding="utf-8") as fh:
    for b in R["blocks"]:
        a = os.path.join(PROJ, "audio", b + ".wav")
        fh.write(f"file '{a.replace(chr(92),'/')}'\n")
        fh.write(f"file '{sil.replace(chr(92),'/')}'\n")
voice = os.path.join(WORK, "v.wav")
sp.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", alist,
        "-filter:a", "atempo=1.05,dynaudnorm", "-ar", "48000", voice], check=True)
VD = dur(voice)
aud = os.path.join(WORK, "a.m4a")
sp.run([FF, "-v", "error", "-y", "-i", voice, "-f", "lavfi", "-t", str(VD),
        "-i", "anoisesrc=c=pink:r=48000",
        "-filter_complex", "[1:a]lowpass=520,highpass=60,volume=0.13[w];[0:a][w]amix=inputs=2:duration=first[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", aud], check=True)

# العنوان طبقةً شفافة
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
d.rectangle([0, 0, W, 300], fill=(6, 8, 14, 205))
d.rectangle([0, H - 190, W, H], fill=(6, 8, 14, 190))
words = R["title"].split()
lines, cur = [], ""
size = 74
f = envpaths.arfont(size, path=FB)
for w in words:
    t = (cur + " " + w).strip()
    if d.textlength(ar(t), font=f) > W - 90 and cur:
        lines.append(cur); cur = w
    else: cur = t
if cur: lines.append(cur)
y = 60
for i, ln in enumerate(lines[:3]):
    t = ar(ln); tw = d.textlength(t, font=f)
    col = (247, 199, 74, 255) if i == len(lines[:3]) - 1 else (255, 255, 255, 255)
    for dx, dy in ((-3,0),(3,0),(0,-3),(0,3)):
        d.text(((W - tw) / 2 + dx, y + dy), t, font=f, fill=(0, 0, 0, 255))
    d.text(((W - tw) / 2, y), t, font=f, fill=col)
    y += size + 18
# نسخةُ الطبقة قبل الشعار: يستعملها logocheck خطَّ أساسٍ بصرياً، كي يقيس
# إضافةَ الشعار وحدها لا الشريطَ والعنوانَ معاً.
ov_no_logo = os.path.join(WORK, "ov_no_logo.png")
ov.save(ov_no_logo)
# ⛔ لا شرطَ هنا: غيابُ الشعار أسقط الشوطَ في envpaths.logo() قبل أن نصل
lg = Image.open(LOGO).convert("RGBA").resize((118, 118), Image.LANCZOS)
m = Image.new("L", (472, 472), 0)
ImageDraw.Draw(m).ellipse([6, 6, 466, 466], fill=255)
m = m.filter(ImageFilter.GaussianBlur(4)).resize((118, 118), Image.LANCZOS)
ov.paste(lg, ((W - 118) // 2, H - 158), m)
ovp = os.path.join(WORK, "ov.png"); ov.save(ovp)

# ⭐ نداء «اشترك» البصريّ — آخر ثلاث ثوانٍ (أكثر مشاهدة الشورتات بلا صوت)
cta = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dc = ImageDraw.Draw(cta)
fc = envpaths.arfont(86, path=FB)
_t = ar("اشترك في القناة")
_tw = dc.textlength(_t, font=fc)
_bw, _bh = _tw + 140, 170
_bx, _by = (W - _bw) // 2, H - 560
dc.rounded_rectangle([_bx + 8, _by + 10, _bx + _bw + 8, _by + _bh + 10],
                     radius=44, fill=(0, 0, 0, 150))
dc.rounded_rectangle([_bx, _by, _bx + _bw, _by + _bh], radius=44, fill=(200, 32, 34, 245))
dc.text(((W - _tw) / 2, _by + 38), _t, font=fc, fill=(255, 255, 255, 255))
_f2 = envpaths.arfont(52, path=FB)
_s = ar("والفيلم كاملًا في الوصف")
_sw = dc.textlength(_s, font=_f2)
for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
    dc.text(((W - _sw) / 2 + dx, _by + _bh + 26 + dy), _s, font=_f2, fill=(0, 0, 0, 255))
dc.text(((W - _sw) / 2, _by + _bh + 26), _s, font=_f2, fill=(247, 199, 74, 255))
ctap = os.path.join(WORK, "cta.png"); cta.save(ctap)
CTA_AT = max(0.0, VD - 3.0)

# ⭐ لقطات مجسَّمة (parallax) بدل كين-بيرنز المسطّح
imgs = R["imgs"]; per = VD / len(imgs)
segs = []
for n, im in enumerate(imgs):
    src = os.path.join(PROJ, "img", im + ".jpg")
    out = os.path.join(WORK, f"s{n:02d}.mp4")
    mv = kb3d.render(src, out, per, n, (W, H))
    print(f"  لقطة {im} · {mv} · {per:.1f} ث", flush=True)
    segs.append(out)
vl = os.path.join(WORK, "v.txt")
with open(vl, "w", encoding="utf-8") as fh:
    for s in segs: fh.write(f"file '{s.replace(chr(92),'/')}'\n")
vid = os.path.join(WORK, "v.mp4")
sp.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", vl, "-c", "copy", vid], check=True)

final = os.path.join(OUTD, f"{RID}.mp4")
sp.run([FF, "-v", "error", "-y", "-i", vid, "-i", ovp, "-i", ctap, "-i", aud,
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0[v1];[v1][2:v]overlay=0:0:enable='gte(t,{CTA_AT:.2f})'[v]",
        "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-shortest", final], check=True)
print(f"✅ {final} | {dur(final):.1f} ثانية")
