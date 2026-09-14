# -*- coding: utf-8 -*-
"""المونتاج بالتحريك المجسَّم: صوت الكتل + لقطات parallax + خلفية رياح → الفيلم.

الاستعمال: python mont3d.py <projectDir> [GAP]
نسخة `mont.py` نفسها، إلا أن الخطوة ③ تصيّر لكل لقطة **مقطعًا مجسَّمًا بمدّة كتلها
الصوتية بالضبط** بدل تكرار صورة ثابتة.

⛔ شرط مسبق: `python kb3d.py depth <projectDir>` (خرائط العمق).
   وإن غابت خريطةُ صورةٍ، تراجعت الأداة إلى تدرّجٍ رأسيّ (كين-بيرنز محسَّن) ولم تتعطّل.
"""
import json, os, sys, subprocess as sp

PROJ = os.path.abspath(sys.argv[1])
MEDIA = os.path.join(os.path.expanduser("~"), "Desktop", "claude-media")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MEDIA)
import kb3d                                     # ← أداة التحريك المجسَّم
from envpaths import FF, FP

GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
WORK = os.path.join(PROJ, "work"); os.makedirs(WORK, exist_ok=True)

blocks = json.load(open(os.path.join(PROJ, "blocks.json"), encoding="utf-8"))
blocks = [b for b in blocks if not b.get("reel_only")]      # ⛔ كتل الريلزات لا تدخل الفيلم
shots  = json.load(open(os.path.join(PROJ, "shots.json"), encoding="utf-8"))


def dur(f):
    o = sp.run([FP, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", f], capture_output=True, text=True)
    return float(o.stdout.strip())


# ١. سلسلة الصوت مع فواصل
print("① بناء الصوت…", flush=True)
concat = os.path.join(WORK, "alist.txt")
sil = os.path.join(WORK, "sil.wav")
sp.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", str(GAP), sil], check=True)
durs = {}
with open(concat, "w", encoding="utf-8") as fh:
    for b in blocks:
        a = os.path.join(PROJ, "audio", b["id"] + ".wav")
        if not os.path.exists(a):
            print("  ⚠ ناقص:", b["id"]); continue
        durs[b["id"]] = dur(a)
        fh.write(f"file '{a.replace(chr(92),'/')}'\n")
        fh.write(f"file '{sil.replace(chr(92),'/')}'\n")

voice = os.path.join(WORK, "voice.wav")
sp.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", concat,
        "-filter:a", "atempo=1.05,dynaudnorm", "-ar", "48000", voice], check=True)
VD = dur(voice); print(f"  مدّة الصوت: {VD/60:.2f} دقيقة", flush=True)

# ٢. خلفية الرياح (⛔ لا موسيقى إطلاقًا)
print("② خلفية الرياح…", flush=True)
mixed = os.path.join(WORK, "audio_final.m4a")
sp.run([FF, "-v", "error", "-y", "-i", voice, "-f", "lavfi", "-t", str(VD),
        "-i", "anoisesrc=c=pink:r=48000",
        "-filter_complex",
        "[1:a]lowpass=520,highpass=60,volume=0.15[w];[0:a][w]amix=inputs=2:duration=first[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", mixed], check=True)

# ٣. اللقطات — ⭐ تحريك مجسَّم بمدّة كل لقطة بالضبط
print("③ اللقطات المجسَّمة…", flush=True)
ids = [b["id"] for b in blocks]


def span(s):
    i0, i1 = ids.index(s["from"]), ids.index(s["to"])
    return sum(durs.get(ids[i], 0) + GAP for i in range(i0, i1 + 1)) / 1.05


seg_dir = os.path.join(WORK, "seg"); os.makedirs(seg_dir, exist_ok=True)
segs = []
for n, s in enumerate(shots):
    img = os.path.join(PROJ, "img", s["img"] + ".jpg")
    if not os.path.exists(img):
        print("  ⚠ صورة ناقصة:", s["img"]); continue
    out = os.path.join(seg_dir, f"s{n:03d}.mp4")
    sec = span(s)
    if not (os.path.exists(out) and os.path.getsize(out) > 20000
            and abs(dur(out) - sec) < 0.05):
        mv = kb3d.render(img, out, sec, n)
        print(f"  [{n+1}/{len(shots)}] {s['img']} · {mv} · {sec:.1f} ث", flush=True)
    segs.append(out)

vlist = os.path.join(WORK, "vlist.txt")
with open(vlist, "w", encoding="utf-8") as fh:
    for s in segs:
        fh.write(f"file '{s.replace(chr(92),'/')}'\n")
silent = os.path.join(WORK, "video_silent.mp4")
sp.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", vlist,
        "-c", "copy", silent], check=True)

# ٤. الدمج — ⛔ بلا shell=True
print("④ الدمج…", flush=True)
final = os.path.join(PROJ, "film.mp4")
sp.run([FF, "-v", "error", "-y", "-i", silent, "-i", mixed,
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", "-shortest", final], check=True)
print(f"✅ {final}  |  {dur(final)/60:.2f} دقيقة", flush=True)
