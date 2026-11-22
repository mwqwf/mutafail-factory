# -*- coding: utf-8 -*-
"""فحص بصري مبكر لمقاطع التحريك قبل المونتاج — أمر المالك 2026-11-22.

درس أجنادين: 5 إعادات لظهور وجوه أو انفجارات، و5 حالات حدّية اكتُشفت بعد التوليد.
هذه الأداة تفحص clips/*.mp4 قبل mont_hybrid: سلامة الملف، بلا مسار صوت (المقاطع بجروك صامتة)،
والأبعاد، والمدة، وكاشف وجوه اختياري (OpenCV Haar) للقطات التي يُشترط فيها إخفاء الوجه.

الاستعمال: python tools/clip_policy.py <مجلد_المشروع>
خروج 1 عند مانع. لا يستدعي جيميناي ولا ينفق.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HIDDEN_FACE = re.compile(
    r"from behind|hidden face|faces fully hidden|silhouette|behind, in silhouette|"
    r"من الخلف|وجه(?:ه|ها)? (?:مخفي|مغطى)|لا تظهر.*وجه",
    re.I,
)


def _probe(path: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout or "{}")


def _frame(path: str, t: float, out: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % t, "-i", path,
         "-frames:v", "1", "-q:v", "3", out],
        capture_output=True,
    )
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 100


def _faces(img_path: str) -> int:
    try:
        import cv2
    except ImportError:
        return 0
    cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not os.path.exists(cascade):
        return 0
    im = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return 0
    det = cv2.CascadeClassifier(cascade)
    h, w = im.shape[:2]
    found = det.detectMultiScale(im, scaleFactor=1.1, minNeighbors=5, minSize=(int(min(h, w) * 0.08),) * 2)
    # وجه كبير نسبياً فقط (لا نقاط بعيدة)
    big = [r for r in found if r[2] * r[3] >= 0.015 * w * h]
    return len(big)


def _prompt_of(shot: dict) -> str:
    return " ".join(str(shot.get(k) or "") for k in ("move", "prompt", "desc", "tag"))


def check(proj: str) -> tuple[list[str], list[str]]:
    proj = os.path.abspath(proj)
    clips = os.path.join(proj, "clips")
    shots_p = os.path.join(proj, "shots.json")
    if not os.path.isdir(clips) or not os.path.exists(shots_p):
        return [], ["لا مجلد clips أو shots.json — تُتخطّى بوّابة المقاطع"]
    shots = json.load(open(shots_p, encoding="utf-8"))
    live = [s for s in shots if (s.get("tag") == "live" or s.get("kind") == "حيّة") and not s.get("still")]
    if not live:
        return [], []
    errs, warns = [], []
    tmp = os.path.join(proj, "work", "clip_policy")
    os.makedirs(tmp, exist_ok=True)
    for s in live:
        sid = s["id"]
        path = os.path.join(clips, sid + ".mp4")
        need = float(s.get("est_dur") or s.get("duration") or s.get("hold") or 0)
        if not os.path.exists(path):
            errs.append("%s: لا مقطع في clips/" % sid)
            continue
        try:
            info = _probe(path)
        except (OSError, subprocess.CalledProcessError, ValueError) as e:
            errs.append("%s: تعذّر فحص الملف (%s)" % (sid, e))
            continue
        streams = info.get("streams") or []
        v = next((x for x in streams if x.get("codec_type") == "video"), None)
        a = [x for x in streams if x.get("codec_type") == "audio"]
        if not v:
            errs.append("%s: بلا مسار صورة" % sid)
            continue
        w, h = int(v.get("width") or 0), int(v.get("height") or 0)
        dur = float((info.get("format") or {}).get("duration") or v.get("duration") or 0)
        if w < 1280 or h < 720:
            errs.append("%s: دقة ضعيفة %dx%d" % (sid, w, h))
        if need and dur + 0.15 < need:
            errs.append("%s: المدة %.2f ث أقصر من المطلوب %.2f ث" % (sid, dur, need))
        if a:
            warns.append("%s: فيه مسار صوت — المقاطع بجروك تُحفظ صامتة؛ يُفحص إن كان موسيقى" % sid)
        # عيّنة إطارات وكشف وجوه إن اشترط الوصف إخفاء الوجه
        ts = [0.4, max(0.4, dur * 0.5), max(0.4, dur - 0.4)] if dur > 0.8 else [0.1]
        faces = 0
        for i, t in enumerate(ts):
            fp = os.path.join(tmp, "%s_%d.jpg" % (sid, i))
            if _frame(path, min(t, max(0, dur - 0.05)), fp):
                faces += _faces(fp)
        prompt = _prompt_of(s)
        if faces and HIDDEN_FACE.search(prompt):
            errs.append("%s: كاشف الوجوه وجد ملامح في لقطة يُشترط إخفاء الوجه فيها (%d إطاراً)" % (sid, faces))
        elif faces >= 2:
            warns.append("%s: وجوه محتملة في %d إطار — تُراجع بالعين قبل المونتاج" % (sid, faces))
    return errs, warns


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    errs, warns = check(argv[0])
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    if errs:
        print("⛔ بوّابة المقاطع: %d مانعاً — لا يُبدأ المونتاج" % len(errs))
        return 1
    print("✅ بوّابة المقاطع: لا موانع")
    return 0


if __name__ == "__main__":
    sys.exit(main())
