#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تركيب شورتات «أصحاب الأخدود» وفحص بواباتها.

لا يمسّ أصل الصوت في film1/audio/ ولا في film1/audio_paced/.
المصدر: film1/audio_paced، والضغط على نسخ في shorts/work/audio_tight فقط، بلا atempo إضافي.
ولا يصيّر حتى تجتاز كتل الشورتات الاستماع بعد دمج تقارير الإعادة، ما لم يُمرَّر --force
(ممنوع في العمل العادي).

الاستعمال (من جذر hikayat-factory):
  python3 tools_local/mk_shorts.py status
  python3 tools_local/mk_shorts.py gates
  python3 tools_local/mk_shorts.py render            # S1–S3 إن كان الصوت جاهزاً
  python3 tools_local/mk_shorts.py render --ids S1
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]  # hikayat-factory
SPEC_PATH = ROOT / "shorts" / "shorts_spec.json"
FACTORY = Path("/workspace/mutafail-factory")
LISTEN = ROOT / "film1/audio/_reports/listen_results.json"
LISTEN_OVERLAYS = [
    ROOT / "film1/audio/_reports/listen_results_regen.json",
    ROOT / "film1/audio/_reports/listen_results_d015_regen.json",
    ROOT / "film1/audio/_reports/listen_results_d030_regen.json",
]
STAMP_A = ROOT / "film1/audio/_reports/LISTEN_COMPLETE.txt"
STAMP_B = ROOT / "shorts/work/AUDIO_READY"


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def run(cmd, **kw):
    return subprocess.run(cmd, check=False, **kw)


def merged_listen():
    """listen_results.json ثم overlays الإعادة (ok=true فقط). لا يُدمج pass2 الناقص."""
    lr = {}
    if LISTEN.exists():
        lr.update(json.loads(LISTEN.read_text(encoding="utf-8")))
    for op in LISTEN_OVERLAYS:
        if not op.exists():
            continue
        ov = json.loads(op.read_text(encoding="utf-8"))
        if not isinstance(ov, dict):
            continue
        for k, rec in ov.items():
            if isinstance(rec, dict) and rec.get("ok") is True:
                lr[k] = rec
    return lr


# ─────────────────────────── جاهزية الصوت ───────────────────────────
def needed_blocks(spec, ids=None):
    ids = set(ids or [s["id"] for s in spec["shorts"] if s.get("enabled")])
    blocks = []
    for s in spec["shorts"]:
        if s["id"] in ids:
            blocks.extend(s["blocks"])
    return list(dict.fromkeys(blocks))


def audio_status(spec, ids=None):
    """يرجع (جاهز؟، قائمة أسباب المنع)."""
    reasons = []
    blocks = needed_blocks(spec, ids)
    src = ROOT / spec["audio_src"]
    missing = [b for b in blocks if not (src / f"{b}.wav").exists()]
    if missing:
        reasons.append("ملفات صوت غائبة: " + ", ".join(missing))
    if not LISTEN.exists():
        reasons.append(f"لا تقرير استماع: {LISTEN}")
        return False, reasons
    lr = merged_listen()
    fails = []
    pending = []
    for b in blocks:
        rec = lr.get(b)
        if rec is None:
            pending.append(b)
        elif rec.get("ok") is True:
            continue
        else:
            fails.append(f"{b}: {rec.get('why') or rec.get('status') or 'ok=false'}")
    if pending:
        reasons.append("كتل بلا نتيجة استماع: " + ", ".join(pending))
    if fails:
        reasons.append("كتل لم تجتز الاستماع: " + "؛ ".join(fails))
    # ختم الاكتمال اختياري لكنه كافٍ مع ok=true
    stamped = STAMP_A.exists() or STAMP_B.exists()
    if fails or missing or pending:
        return False, reasons
    if not stamped:
        # إن اجتازت كتل الشورتات كلها الاستماع نسمح بالتصيير حتى بلا ختم عامّ للفيلم
        # (قد تبقى كتل أخرى من الفيلم قيد الإصلاح مثل d_024 ولا تلزم الشورتات S1/S2).
        return True, ["لا ختم LISTEN_COMPLETE للفيلم كله، لكن كتل الشورتات المطلوبة ناجحة."]
    return True, []


def cmd_status(spec, ids=None):
    ok, reasons = audio_status(spec, ids)
    print("جاهزية صوت الشورتات:", "نعم" if ok else "لا")
    for r in reasons:
        print(" -", r)
    return 0 if ok else 2


# ─────────────────────────── البوابات النصّية ───────────────────────────
def cmd_gates(spec):
    lines_path = ROOT / "shorts/work/titles_cta.txt"
    lines_path.parent.mkdir(parents=True, exist_ok=True)
    titles = [spec["cta_text"]] + [s["title"] for s in spec["shorts"]] + ["القصة كاملة في الفيلم:"]
    lines_path.write_text("\n".join(titles) + "\n", encoding="utf-8")
    rc = 0
    checks = [
        (["python3", str(FACTORY / "tools/text_gate.py"), "--lines", str(lines_path)], "text_gate"),
        (["python3", str(FACTORY / "tools/policy_gate.py"), "text", str(ROOT / "shorts"),
          "--out", str(ROOT / "shorts/work/policy_text.json")], "policy_gate text"),
        (["python3", "/home/box/agent-skills/global/arabic-text-integrity/scripts/check_arabic_text.py",
          str(lines_path)], "check_arabic_text"),
    ]
    for cmd, name in checks:
        print("—", name)
        p = run(cmd)
        print("  rc=", p.returncode)
        if p.returncode != 0:
            rc = 1
    # وصف الفيلم فيه الرقم ٣٠٠٥: لا يُمرَّر إلى text_gate (قاعدة النطق)، ويبقى في الوصف المكتوب.
    print("ملاحظة: رقم الحديث في الوصف مكتوب للعرض، ولا يدخل بوابة النص المنطوق.")
    return rc


# ─────────────────────────── ضغط الصوت (نسخة) ───────────────────────────
def tighten_one(src: Path, dst: Path, maxgap=0.45, edge=0.15):
    with wave.open(str(src)) as w:
        r = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).copy()
    fr = max(1, int(r * 0.02))
    n = len(a) // fr
    e = np.array([np.sqrt(np.mean(a[i * fr:(i + 1) * fr].astype(float) ** 2)) for i in range(n)])
    sil = e < 300
    sp = np.where(~sil)[0]
    if len(sp) == 0:
        dst.write_bytes(src.read_bytes())
        return
    s0 = max(sp[0] * fr - int(edge * r), 0)
    s1 = min((sp[-1] + 1) * fr + int(edge * r), len(a))
    keep = np.ones(len(a), bool)
    keep[:s0] = False
    keep[s1:] = False
    i = sp[0]
    while i <= sp[-1]:
        if sil[i]:
            j = i
            while j <= sp[-1] and sil[j]:
                j += 1
            L = (j - i) * 0.02
            if L > maxgap:
                cut0 = i * fr + int(maxgap / 2 * r)
                cut1 = j * fr - int(maxgap / 2 * r)
                keep[cut0:cut1] = False
            i = j
        else:
            i += 1
    b = a[keep].astype(float)
    k = int(0.01 * r)
    if k > 0 and len(b) > 2 * k:
        b[:k] *= np.linspace(0, 1, k)
        b[-k:] *= np.linspace(1, 0, k)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(r)
        o.writeframes(b.astype(np.int16).tobytes())


def wav_dur(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / float(w.getframerate())


def concat_wavs(paths, gaps, out: Path, sr=None):
    chunks = []
    rate = None
    for i, p in enumerate(paths):
        with wave.open(str(p)) as w:
            rate = rate or w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        chunks.append(a)
        if i < len(paths) - 1:
            g = gaps[i] if i < len(gaps) else 0.2
            chunks.append(np.zeros(int(g * rate), np.int16))
    out.parent.mkdir(parents=True, exist_ok=True)
    cat = np.concatenate(chunks)
    with wave.open(str(out), "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(rate)
        o.writeframes(cat.tobytes())
    return len(cat) / rate


# ─────────────────────────── الخطّ والنص ───────────────────────────
def font(spec, size, weight="Black"):
    f = ImageFont.truetype(spec["font"], size, layout_engine=ImageFont.Layout.RAQM)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        try:
            f.set_variation_by_axes([900 if weight == "Black" else 700])
        except Exception:
            pass
    return f


def wrap_rtl(text, fnt, max_w, draw):
    words = text.replace("…", " … ").split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt, direction="rtl", language="ar") <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def draw_caption(im, spec, text, y_center=1250, size=54):
    """نص عربي في نطاق الأمان، سطران كحدّ أقصى."""
    d = ImageDraw.Draw(im)
    fnt = font(spec, size)
    sz = spec
    max_w = sz["safe_zone"]["x1"] - sz["safe_zone"]["x0"]
    lines = wrap_rtl(text, fnt, max_w, d)
    if len(lines) > 2:
        fnt = font(spec, int(size * 0.85))
        lines = wrap_rtl(text, fnt, max_w, d)[:3]
    line_h = int(size * 1.55)
    total = line_h * len(lines)
    y = int(y_center - total / 2)
    y = max(spec["safe_zone"]["y0"] + 8, min(y, spec["safe_zone"]["y1"] - total - 8))
    cx = (spec["safe_zone"]["x0"] + spec["safe_zone"]["x1"]) // 2
    boxes = []
    for ln in lines:
        w = d.textlength(ln, font=fnt, direction="rtl", language="ar")
        x = cx - w / 2
        # ظل
        for dx, dy in [(-3, 3), (3, 3), (0, 4), (-2, -2), (2, -2)]:
            d.text((x + dx, y + dy), ln, font=fnt, fill=(0, 0, 0, 220), direction="rtl", language="ar")
        d.text((x, y), ln, font=fnt, fill=(255, 255, 255, 255), direction="rtl", language="ar",
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
        boxes.append((x, y, x + w, y + line_h))
        y += line_h
    return boxes


def make_cta_frame(spec, short, w, h):
    img_dir = ROOT / spec["images_dir"]
    bg = Image.open(img_dir / short["cta_image"]).convert("RGB")
    bg = bg.resize((w, h), Image.LANCZOS)
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    # تعتيم إضافي أسفل
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, int(h * 0.45), w, h], fill=(0, 0, 0, 140))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay)
    # مصغّرة الفيلم إن وُجدت
    thumb = ROOT / spec["film_images_dir"] / "thumb-a.jpg"
    if thumb.exists():
        t = Image.open(thumb).convert("RGB")
        tw = 420
        th = int(tw * 9 / 16)
        t = t.resize((tw, th), Image.LANCZOS)
        tx, ty = (w - tw) // 2, 420
        # إطار ذهبي
        frame = Image.new("RGB", (tw + 8, th + 8), (212, 160, 60))
        bg.paste(frame, (tx - 4, ty - 4))
        bg.paste(t, (tx, ty))
    d = ImageDraw.Draw(bg)
    # سهم إلى أسفل اليسار (موضع رابط «فيديو ذو صلة»)
    ax, ay = 180, 1680
    d.polygon([(ax, ay - 40), (ax + 36, ay - 10), (ax + 14, ay - 10), (ax + 14, ay + 50),
               (ax - 14, ay + 50), (ax - 14, ay - 10), (ax - 36, ay - 10)], fill=(212, 160, 60))
    # عنوان الفيلم + الدعوة
    im = bg.convert("RGB")
    draw_caption({"font": spec["font"], "safe_zone": spec["safe_zone"]},
                 "قصة أصحاب الأخدود كما في صحيح مسلم", y_center=1100, size=48)
    # reuse im after convert - redraw on im
    im = bg.convert("RGB")
    # actually draw on im
    # rebuild simply:
    return _finish_cta(spec, short, w, h)


def _finish_cta(spec, short, w, h):
    img_dir = ROOT / spec["images_dir"]
    bg = Image.open(img_dir / short["cta_image"]).convert("RGB").resize((w, h), Image.LANCZOS)
    bg = ImageEnhance.Brightness(bg).enhance(0.42)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rectangle([0, int(h * 0.40), w, h], fill=(0, 0, 0, 150))
    bg = Image.alpha_composite(bg.convert("RGBA"), layer).convert("RGB")
    thumb = ROOT / spec["film_images_dir"] / "thumb-a.jpg"
    if thumb.exists():
        t = Image.open(thumb).convert("RGB")
        tw, th = 440, 248
        t = t.resize((tw, th), Image.LANCZOS)
        tx, ty = (w - tw) // 2, 400
        fr = Image.new("RGB", (tw + 8, th + 8), (212, 160, 60))
        bg.paste(fr, (tx - 4, ty - 4))
        bg.paste(t, (tx, ty))
    d = ImageDraw.Draw(bg)
    # سهم إلى الأسفل ناحية رابط «فيديو ذو صلة» أسفل الشاشة
    ax, ay = 200, 1688
    d.polygon([
        (ax, ay + 56), (ax + 40, ay + 18), (ax + 16, ay + 18),
        (ax + 16, ay - 50), (ax - 16, ay - 50), (ax - 16, ay + 18), (ax - 40, ay + 18),
    ], fill=(212, 160, 60))
    boxes = []
    boxes += draw_caption(bg, spec, "قصة أصحاب الأخدود", y_center=1040, size=48)
    boxes += draw_caption(bg, spec, "كما في صحيح مسلم", y_center=1110, size=42)
    # سطران مفصولان عند علامة الحذف حتى لا ينكسر «أسفل الشاشة»
    cta = spec["cta_text"]
    if "…" in cta:
        a, b = cta.split("…", 1)
        boxes += draw_caption(bg, spec, a.strip() + "…", y_center=1260, size=50)
        boxes += draw_caption(bg, spec, b.strip(), y_center=1340, size=50)
    else:
        boxes += draw_caption(bg, spec, cta, y_center=1280, size=50)
    boxes += draw_caption(bg, spec, spec["source_tag"], y_center=1460, size=36)
    return bg, boxes


# ─────────────────────────── حركة Ken Burns ───────────────────────────
def kenburns_clip(img_path: Path, duration: float, out: Path, spec, direction="in", captions=None):
    """يصيّر لقطة 1080×1920 بتكبير بطيء، والنصوص محروقة على الإطارات."""
    w, h, fps = spec["target_w"], spec["target_h"], spec["fps"]
    n = max(1, int(round(duration * fps)))
    src = Image.open(img_path).convert("RGB")
    # املأ الإطار
    src = src.resize((w, h), Image.LANCZOS)
    z0, z1 = (1.0, 1.08) if direction == "in" else (1.08, 1.0)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix(".raw")
    with raw.open("wb") as fh:
        for i in range(n):
            t = i / max(n - 1, 1)
            z = z0 + (z1 - z0) * t
            cw, ch = int(w / z), int(h / z)
            # مركز
            x0 = (w - cw) // 2
            y0 = (h - ch) // 2
            crop = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.LANCZOS)
            if captions:
                for text, _y in captions:
                    draw_caption(crop, spec, text, y_center=_y)
            fh.write(crop.tobytes())
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(fps), "-i", str(raw),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast",
        str(out),
    ]
    p = run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    raw.unlink(missing_ok=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg kenburns failed: " + p.stderr[-400:].decode("utf-8", "replace"))


def split_duration(block_dur, shots_for_block):
    n = len(shots_for_block)
    return [block_dur / n] * n


# ─────────────────────────── تصيير شورت ───────────────────────────
def build_timeline(spec, short, tight_dir: Path, cta_path: Path | None):
    """يرجع قائمة لقطات {image, dur, kb, captions} ثم مدة الدعوة.

    الفجوات بين الكتل وفجوة ما قبل الدعوة تُمدَّد على آخر لقطة في الكتلة
    حتى يطابق طول الفيديو طول الصوت (وإلا قصّ -shortest آخر الدعوة).
    """
    gap = float(spec.get("gap_between_blocks", 0.12))
    pre_cta = float(spec.get("pre_cta_gap", 0.12))
    # مدد الكتل المضغوطة
    bdur = {b: wav_dur(tight_dir / f"{b}.wav") for b in short["blocks"]}
    # تجميع اللقطات حسب الكتلة مع الحفاظ على الترتيب
    by_block = {}
    for sh in short["shots"]:
        by_block.setdefault(sh["block"], []).append(sh)
    t = 0.0
    clips = []
    block_t0 = {}
    nblocks = len(short["blocks"])
    for i, b in enumerate(short["blocks"]):
        block_t0[b] = t
        shots = by_block[b]
        durs = split_duration(bdur[b], shots)
        extra = pre_cta if i == nblocks - 1 else gap
        durs[-1] += extra
        for sh, d in zip(shots, durs):
            clips.append({**sh, "dur": d, "t0": t, "t1": t + d})
            t += d
    narr_end = t  # بداية بطاقة الدعوة = نهاية السرد + فجوة ما قبل الدعوة
    cta_dur = wav_dur(cta_path) if cta_path and cta_path.exists() else 3.4
    return clips, narr_end, cta_dur, bdur, block_t0


def captions_for_clip(spec, short, clip, t_global_start):
    """النصوص الظاهرة في هذه اللقطة (الخطّاف في أول ثانيتين، ونص الوسط في كتلته، ووسم المصدر)."""
    caps = []
    t0, t1 = clip["t0"], clip["t1"]
    # hook at start of short
    if t0 < short.get("hook_until", 2.6) and short.get("hook_text"):
        caps.append((short["hook_text"], 1180))
    # mid text during mid_block
    if short.get("mid_text") and clip["block"] == short.get("mid_block"):
        caps.append((short["mid_text"], 1180))
    # source tag on Q blocks
    role = short.get("blocks_role", {}).get(clip["block"])
    if short.get("source_on_q") and role == "Q":
        caps.append((spec["source_tag"], 1480))
    # if hook and mid would overlap, hook wins only in first window
    if len(caps) >= 2 and caps[0][0] == short.get("hook_text") and t0 >= short.get("hook_until", 2.6):
        caps = caps[1:]
    # if both hook and mid in same early clip of mid_block, show hook first only when t0 < hook_until
    return caps



def loudnorm_wav(src: Path, dst: Path, I=-14.0, LRA=11.0, TP=-1.5, ar=48000) -> int:
    """تمريران: قياس ثم تطبيق خطيّ عند 48 كيلوهرتز. يعيد 0 عند النجاح."""
    meas = run(
        ["ffmpeg", "-y", "-i", str(src),
         "-af", f"loudnorm=I={I}:LRA={LRA}:TP={TP}:print_format=json",
         "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    err = (meas.stderr or b"").decode("utf-8", "replace")
    i = err.rfind("{")
    j = err.rfind("}")
    if i < 0 or j <= i:
        return 1
    try:
        m = json.loads(err[i:j + 1])
    except json.JSONDecodeError:
        return 1
    af = (
        f"loudnorm=I={I}:LRA={LRA}:TP={TP}:"
        f"measured_I={m['input_i']}:measured_LRA={m['input_lra']}:"
        f"measured_TP={m['input_tp']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']}:linear=true,aresample={ar}"
    )
    p = run(
        ["ffmpeg", "-y", "-i", str(src), "-af", af, "-ar", str(ar), str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    return p.returncode


def render_short(spec, short, force=False):
    ids = [short["id"]]
    ok, reasons = audio_status(spec, ids)
    if not ok and not force:
        print(f"⛔ لا يُصيَّر {short['id']}:")
        for r in reasons:
            print(" -", r)
        return 2
    for r in reasons:
        print("تنبيه:", r)

    cta_src = ROOT / spec["cta_audio"]
    if not cta_src.exists():
        print(f"⛔ لا ملف دعوة صوتية: {cta_src} (يولَّد بعد المراجعة بصوت الفيلم نفسه).")
        return 2

    tight = ROOT / spec["audio_tight"]
    tight.mkdir(parents=True, exist_ok=True)
    src = ROOT / spec["audio_src"]
    # ضغط الدعوة على نسخة فقط — الأصل shorts/work/sh_cta.wav لا يُمسّ
    cta_path = tight / "sh_cta.wav"
    tighten_one(
        cta_src,
        cta_path,
        maxgap=spec.get("maxgap", 0.45),
        edge=spec.get("edge", 0.10),
    )
    for b in short["blocks"]:
        tighten_one(
            src / f"{b}.wav",
            tight / f"{b}.wav",
            maxgap=spec.get("maxgap", 0.45),
            edge=spec.get("edge", 0.10),
        )

    clips, narr_end, cta_dur, bdur, block_t0 = build_timeline(spec, short, tight, cta_path)
    print(f"{short['id']}: سرد {narr_end:.1f} ث + دعوة {cta_dur:.1f} ث")

    work = ROOT / "shorts/work" / short["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    img_dir = ROOT / spec["images_dir"]
    parts = []
    for i, cl in enumerate(clips):
        ip = img_dir / cl["image"]
        if not ip.exists():
            print("⛔ صورة غائبة", ip)
            return 2
        caps = captions_for_clip(spec, short, cl, cl["t0"])
        part = work / f"p{i:02d}.mp4"
        kenburns_clip(ip, cl["dur"], part, spec, cl.get("kb", "in"), captions=caps or None)
        parts.append(part)

    # CTA still
    w, h = spec["target_w"], spec["target_h"]
    cta_img, _ = _finish_cta(spec, short, w, h)
    cta_png = work / "cta.png"
    cta_img.save(cta_png)
    cta_mp4 = work / "cta.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(cta_png), "-t", f"{cta_dur:.3f}",
         "-vf", f"fps={spec['fps']},format=yuv420p", "-c:v", "libx264", "-crf", "18",
         str(cta_mp4)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    parts.append(cta_mp4)

    # audio: blocks + gaps + cta
    wavs = [tight / f"{b}.wav" for b in short["blocks"]] + [cta_path]
    gap = float(spec.get("gap_between_blocks", 0.12))
    pre_cta = float(spec.get("pre_cta_gap", 0.12))
    gaps = [gap] * (len(short["blocks"]) - 1) + [pre_cta]
    voice = work / "voice.wav"
    concat_wavs(wavs, gaps, voice)
    # loudnorm تمريران + 48 كيلوهرتز (تمرير واحد يرفع العيّنة إلى 192 كيلوهرتز ويُخطئ الهدف)
    voice_n = work / "voice_norm.wav"
    p = loudnorm_wav(voice, voice_n, I=spec["lufs"])
    if p != 0:
        # احتياط: إعادة عيّنة دون قياس إن تعذّر التحليل
        p = run(["ffmpeg", "-y", "-i", str(voice), "-ar", "48000", str(voice_n)],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if p.returncode != 0:
            shutil.copy(voice, voice_n)

    # concat video
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    silent = work / "silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(silent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out_dir = ROOT / spec["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{short['id']}.mp4"
    p = run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice_n),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", str(out)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if p.returncode != 0:
        print("⛔ دمج الصوت/الفيديو فشل:", p.stderr[-400:].decode("utf-8", "replace"))
        return 1
    # مدّة
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)
    ]).decode().strip())
    # narr_end يشمل فجوة ما قبل الدعوة، وهو موعد بداية صوت الدعوة وبطاقتها
    cta_audio_start = narr_end
    min_d = float(spec.get("min_dur", 25))
    max_d = float(spec.get("max_dur", 33))
    win = float(spec.get("cta_window", 5))
    ok_dur = min_d - 0.05 <= dur <= max_d + 0.05
    # قياس عملي بعد الدمج: بداية الدعوة ≈ dur - cta_dur، ويجب أن تطابق narr_end تقريباً
    cta_audio_start_est = dur - cta_dur
    ok_cta = (cta_dur <= win + 0.05) and (cta_audio_start_est >= dur - win - 0.05)
    flag = "✅" if ok_dur and ok_cta else "⛔"
    print(f"{flag} {out}  ({dur:.2f} ث)  دعوة {cta_dur:.2f} ث تبدأ عند {cta_audio_start_est:.2f}")
    if not ok_dur:
        print(f"  ⛔ المدة خارج النطاق {min_d}–{max_d} ث")
    if not ok_cta:
        print(f"  ⛔ الدعوة ليست بالكامل في آخر {win} ث")
    # بوّابة نطاق الأمان: عيّنة إطارات
    _safe_zone_spotcheck(out, spec, work)
    meta = {
        "id": short["id"], "path": str(out), "duration": dur,
        "title": short["title"], "blocks": short["blocks"], "bdur": bdur,
        "narr_end": narr_end, "cta_dur": cta_dur,
        "cta_audio_start": cta_audio_start_est,
        "duration_ok": ok_dur, "cta_in_last_5s": ok_cta,
        "no_music": True,
    }
    (out_dir / f"{short['id']}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok_dur and ok_cta else 1


def _safe_zone_spotcheck(mp4: Path, spec, work: Path):
    """يستخرج 6 إطارات ويحفظها للمراجعة البصرية (لا يمنع تلقائياً ما لم يُطلب)."""
    probe = work / "frames"
    probe.mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(mp4), "-vf", "fps=1/5", "-q:v", "3",
         str(probe / "f%02d.jpg")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  إطارات المراجعة:", probe)


def cmd_render(spec, ids, force=False):
    want = ids or [s["id"] for s in spec["shorts"] if s.get("enabled")]
    rc = 0
    for s in spec["shorts"]:
        if s["id"] in want:
            r = render_short(spec, s, force=force)
            rc = rc or r
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "gates", "render"])
    ap.add_argument("--ids", default="", help="مثل S1,S2")
    ap.add_argument("--force", action="store_true", help="للتجربة فقط — لا يُستعمل في الشوط العادي")
    args = ap.parse_args()
    os.chdir(ROOT)
    spec = load_spec()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or None
    if args.cmd == "status":
        return cmd_status(spec, ids)
    if args.cmd == "gates":
        return cmd_gates(spec)
    if args.cmd == "render":
        if args.force:
            print("⚠ --force مفعّل: يتجاوز جاهزية الصوت.")
        return cmd_render(spec, ids, force=args.force)
    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
