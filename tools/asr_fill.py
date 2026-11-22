# -*- coding: utf-8 -*-
"""إكمال الإصغاء بتفريغ محلي حين تنفد مفاتيح جيميناي — أمر المالك 2026-11-22.

درس أجنادين: 21 كتلة `unchecked` بسبب `nokeys`، وراية `d_052` كانت إيجابية كاذبة أزالها
faster-whisper لاحقاً. هذه الأداة تملأ listen_results.json للكتل غير المفحوصة بسبب نفاد
المفاتيح (nokeys وما شابه)، إن وُجد faster-whisper، ثم تُعيد كتابة listen_report.json.

الاستعمال: python tools/asr_fill.py <مجلد_المشروع>
لا تستدعي شبكة. إن غاب النموذج تُطبع تنبيه وتُترك الكتل كما هي (خروج 0).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import listen_report  # noqa: E402

DIAC = re.compile(r"[\u064B-\u0652ٰـ]")
NOKEY = re.compile(r"nokeys|لا مفاتيح|نفدت|quota|resource.?exhausted", re.I)


def _plain(s: str) -> str:
    return DIAC.sub("", s or "")


def needed(proj: str) -> bool:
    path = os.path.join(proj, "listen_report.json")
    if os.path.exists(path):
        try:
            r = json.load(open(path, encoding="utf-8"))
        except ValueError:
            r = listen_report.report(proj)
    else:
        if not os.path.exists(os.path.join(proj, "listen_results.json")):
            return False
        r = listen_report.report(proj)
    why = r.get("why_unchecked") or {}
    return any(NOKEY.search(str(w) or "") or str(w) == "nokeys" for w in why.values())


def _model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
    except Exception as e:
        # محاولة بيئة /workspace/asr إن وُجدت
        vpy = "/workspace/asr/bin/python"
        if os.path.exists(vpy) and sys.executable != vpy:
            raise RuntimeError("استخدم %s -m asr_fill أو ثبّت faster-whisper: %s" % (vpy, e))
        raise


def _transcribe(model, path: str) -> str:
    segs, _ = model.transcribe(
        path, language="ar", beam_size=5, word_timestamps=False, vad_filter=False,
        condition_on_previous_text=False, temperature=0.0,
    )
    return " ".join((s.text or "").strip() for s in segs).strip()


def _close(a: str, b: str) -> bool:
    """مقارنة مخفّفة بعد نزع التشكيل والترقيم."""
    def norm(s):
        s = _plain(s)
        s = re.sub(r"[^\u0621-\u064A\s]", " ", s)
        return " ".join(s.split())
    x, y = norm(a), norm(b)
    if not x or not y:
        return False
    if x == y:
        return True
    # نسبة التغطية بالكلمات
    sx, sy = set(x.split()), set(y.split())
    if not sy:
        return False
    return len(sx & sy) / len(sy) >= 0.85 and abs(len(x) - len(y)) <= max(12, int(0.2 * len(y)))


def fill(proj: str) -> int:
    proj = os.path.abspath(proj)
    if not needed(proj):
        print("asr_fill: لا كتل معلّقة بسبب نفاد المفاتيح")
        return 0
    r0 = listen_report.report(proj)
    why = r0.get("why_unchecked") or {}
    ids = [k for k, w in why.items() if NOKEY.search(str(w) or "") or str(w) == "nokeys"]
    if not ids:
        print("asr_fill: لا كتل nokeys")
        return 0
    try:
        model = _model()
    except Exception as e:
        print("⚠ asr_fill: faster-whisper غير متاح — تُترك %d كتلة بلا فحص (%s)" % (len(ids), e))
        return 0
    res_path = os.path.join(proj, "listen_results.json")
    try:
        res = json.load(open(res_path, encoding="utf-8"))
    except (OSError, ValueError):
        res = {}
    blocks = {b["id"]: b for b in json.load(open(os.path.join(proj, "blocks.json"), encoding="utf-8"))}
    filled = 0
    for k in ids:
        wav = os.path.join(proj, "audio", k + ".wav")
        if not os.path.exists(wav) or k not in blocks:
            continue
        text = blocks[k]["text"]
        digest = hashlib.sha256(text.encode("utf-8") + b"\0" + open(wav, "rb").read()).hexdigest()
        heard = _transcribe(model, wav)
        ok = _close(heard, text)
        res[k] = {
            "id": k,
            "ok": bool(ok),
            "why": "" if ok else "التفريغ المحلي لا يطابق النص",
            "written": heard,
            "input_sha256": digest,
            "reviewer": "asr-fill:faster-whisper",
        }
        filled += 1
        print("  %s: %s · «%s»" % (k, "موافق" if ok else "راية", heard[:80]))
    json.dump(res, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    r = listen_report.report(proj)
    json.dump(r, open(os.path.join(proj, "listen_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("asr_fill: مُلئت %d كتلة بـfaster-whisper · رايات %d · لم يُفحص %d" % (
        filled, len(r["flags"]), len(r["unchecked"])))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    return fill(argv[0])


if __name__ == "__main__":
    sys.exit(main())
