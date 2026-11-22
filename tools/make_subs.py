# -*- coding: utf-8 -*-
"""يولّد ترجمة عربية من السيناريو — أمر المالك 2026-11-23.

الاستعمال: python tools/make_subs.py <مجلد_المشروع>
يكتب ترجمة.ar.vtt وترجمة.ar.srt من كتل الفيلم. إن وُجدت ملفات الصوت استُعملت
مددها (كالفصول)، وإلا تقدير الكلمات. الترجمة من النص المنطوق لا من تلخيص.
"""
from __future__ import annotations

import json
import os
import subprocess as sp
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from thrill_gate import SEC_PER_WORD, words
except ImportError:
    SEC_PER_WORD = 0.46

    def words(t: str) -> int:
        return len((t or "").split())

GAP = 0.30
TEMPO = 1.05
VTT_NAME = "ترجمة.ar.vtt"
SRT_NAME = "ترجمة.ar.srt"


def ffprobe() -> str:
    try:
        from envpaths import FP
        return FP
    except Exception:
        return "ffprobe"


def audio_dur(path: str) -> float | None:
    if not os.path.exists(path):
        return None
    o = sp.run(
        [ffprobe(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(o.stdout.strip())
    except ValueError:
        return None


def film_blocks(proj: str) -> list[dict]:
    blocks_p = os.path.join(proj, "blocks.json")
    if os.path.exists(blocks_p):
        with open(blocks_p, encoding="utf-8") as f:
            blocks = json.load(f)
        return [b for b in blocks if not b.get("reel_only") and (b.get("text") or "").strip()]
    # من السيناريو إن لم تُبنَ الكتل بعد
    script = os.path.join(proj, "script.md")
    if not os.path.exists(script):
        return []
    import re
    out = []
    for raw in open(script, encoding="utf-8"):
        m = re.match(r"^(d_\d{3}|m_\d{3})\|(\w)\|(.+)$", raw.rstrip("\n"))
        if m:
            out.append({"id": m.group(1), "role": m.group(2), "text": m.group(3).strip()})
    return out


def cues(proj: str, blocks: list[dict]) -> list[tuple[float, float, str]]:
    rows, t = [], 0.0
    used_audio = False
    for b in blocks:
        text = (b.get("text") or "").strip()
        wav = os.path.join(proj, "audio", b["id"] + ".wav")
        dur = audio_dur(wav)
        if dur is not None:
            used_audio = True
            span = (dur + GAP) / TEMPO
        else:
            span = max(words(text) * SEC_PER_WORD, 0.8)
        start, end = t, t + span
        rows.append((start, end, text))
        t = end
    if used_audio:
        # عندما تُقاس المدد من الصوت نستخدم التوقيت كما في الفصول
        pass
    return rows


def fmt_vtt(s: float) -> str:
    if s < 0:
        s = 0.0
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s - h * 3600 - m * 60
    return "%02d:%02d:%06.3f" % (h, m, sec)


def fmt_srt(s: float) -> str:
    return fmt_vtt(s).replace(".", ",")


def vtt_body(rows: list[tuple[float, float, str]]) -> str:
    lines = ["WEBVTT", "Kind: captions", "Language: ar", ""]
    for i, (a, b, text) in enumerate(rows, 1):
        lines.append(str(i))
        lines.append("%s --> %s" % (fmt_vtt(a), fmt_vtt(b)))
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def srt_body(rows: list[tuple[float, float, str]]) -> str:
    lines = []
    for i, (a, b, text) in enumerate(rows, 1):
        lines.append(str(i))
        lines.append("%s --> %s" % (fmt_srt(a), fmt_srt(b)))
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def generate(proj: str) -> tuple[str, str]:
    blocks = film_blocks(proj)
    if not blocks:
        raise ValueError("لا كتل ولا سيناريو لتوليد الترجمة")
    rows = cues(proj, blocks)
    # لا نعيد فحص التشكيل هنا: النص من سيناريو اجتاز text_gate. نمنع الأسطر الفارغة فقط.
    vtt, srt = vtt_body(rows), srt_body(rows)
    vtt_path = os.path.join(proj, VTT_NAME)
    srt_path = os.path.join(proj, SRT_NAME)
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt)
    return vtt_path, srt_path


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    proj = os.path.abspath(argv[0])
    try:
        vtt, srt = generate(proj)
    except ValueError as exc:
        print("⛔", exc)
        return 1
    print("✅", vtt)
    print("✅", srt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
