#!/usr/bin/env python3
"""🧾 طابور كوديكس — أمرٌ ثابتٌ واحد بدل أوامر تُلصق لكل فيلم (أمر المالك 2026-10-01).

**لماذا؟** كانت كلّ حلقة تُنتج 3–6 أوامر طويلة يلصقها المالك بيده في كوديكس. والمالك يريد ألّا
يتدخّل إلا باختيار الموضوع. فصارت الجلسة تكتب **ملفّ مهمّة** في مستودع الصور الدائم
`mwqwf/yarmouk-media` (‏`<المجلد>/codex_job.json`)، وكوديكس يُعطى أمراً ثابتاً لا يتغيّر:

    نفّذ الطابور                ← مهمّةٌ واحدة تولّد كلّ الناقص
    نفّذ الطابور، الجزء 2 من 3  ← ثلاث مهامّ متوازية، كلٌّ يملك ثلث items الثابت ويولّد ناقصه

وبروتوكولُه مكتوبٌ في `AGENTS.md` بجذر مستودع الصور، فيقرؤه كوديكس وحده. وإن أتاح كوديكس
جدولةَ مهمّةٍ متكرّرة فهذا الأمر نفسُه يُجدوَل مرّةً واحدة، ولا يعود المالك إليه.

    python3 tools/codex_queue.py write  <مستودع_الصور> <المجلد> <prompts.json> [--rules ملف] [--size 1920x1080]
    python3 tools/codex_queue.py status <مستودع_الصور> <المجلد>     # خروج 0 = اكتمل · 3 = ناقص (غائب أو تالف أو بمقاسٍ آخر)
    python3 tools/codex_queue.py shard  <مستودع_الصور> <المجلد> <k> <n>   # ما يخصّ الجزء k من n (للفحص)

`prompts.json` إمّا قاموس `{"F001": "وصف…"}` (يُحفظ `images/F001.jpg`) أو قائمة
`[{"file": "thumbs/x-A.png", "prompt": "…", "size": [1280, 720]}]`.

الفحص الكامل يحتاج Pillow: `python -m pip install Pillow`.
النجاح يعني سلامة البنية وفكّ الصورة بالمقاس المطلوب؛ الاعتماد البصري يبقى على الجلسة.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path, PurePosixPath

JOB = "codex_job.json"


def load_items(prompts: Path, size: list[int]) -> list[dict]:
    data = json.loads(prompts.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [{"file": f"images/{k}.jpg", "prompt": v, "size": size} for k, v in sorted(data.items())]
    items = []
    for it in data:
        if not it.get("file") or not it.get("prompt"):
            sys.exit(f"⛔ عنصرٌ بلا file أو prompt: {it}")
        items.append({"file": it["file"], "prompt": it["prompt"], "size": it.get("size", size)})
    for it in items:   # المسارُ داخل مجلّد الفيلم وحده (تدقيق كوديكس MF-10)
        pp = PurePosixPath(it["file"])
        if pp.is_absolute() or ".." in pp.parts or "\\" in it["file"]:
            sys.exit(f"⛔ مسارٌ خارج مجلّد الفيلم: {it['file']}")
    return items


def dims(path: Path) -> tuple[int, int] | None:
    """أبعاد JPG/PNG بعد التحقّق من بنية الملف وفكّ كل بكسلاته، لا من الترويسة وحدها."""
    try:
        from PIL import Image, ImageFile
    except ImportError:
        sys.exit("⛔ فحص الصور الكامل يحتاج Pillow؛ ثبّتها بالأمر: python -m pip install Pillow")

    # لا نرث تساهل برنامج آخر مع الصور المبتورة عند استيراد هذه الأداة.
    allow_truncated = ImageFile.LOAD_TRUNCATED_IMAGES
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format not in {"JPEG", "PNG"}:
                    return None
                image.verify()
            # verify يفحص البنية؛ إعادة الفتح ثم load تفحص بيانات الصورة نفسها.
            with Image.open(path) as image:
                image.load()
                return image.size
    except (OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        return None
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = allow_truncated


def done(base: Path, it: dict) -> bool:
    """منجزٌ = صورةٌ تُفتح وتُفكّ كاملةً بالمقاس المطلوب، لا مجرّد ترويسة سليمة.
    ⛔ هذا اكتمالٌ تقنيّ لا اعتمادٌ بصريّ: الفحص بالعين يبقى على الجلسة."""
    f = base / it["file"]
    d = dims(f)
    return d is not None and list(d) == list(it.get("size") or d)


def missing(media: Path, folder: str, job: dict) -> list[dict]:
    base = media / folder
    return [it for it in job["items"] if not done(base, it)]


def shard(items: list[dict], k: int, n: int) -> list[dict]:
    """⛔ يُقسَّم ترتيبُ `items` الثابت في المهمّة، لا قائمةُ الناقص المتغيّرة (تدقيق كوديكس MF-09):
    جزءٌ بدأ بعد أن أنجز غيرُه صورةً كان يرى قائمةً أقصر فيأخذ نصيبَ غيره ويكرّره ويُسقط آخر."""
    if not (1 <= k <= n):
        sys.exit(f"⛔ الجزء {k} من {n} خارج المدى")
    return [it for i, it in enumerate(items) if i % n == k - 1]


def cmd_write(a) -> int:
    media, folder = Path(a.media), a.folder
    w, h = (int(x) for x in a.size.lower().split("x"))
    items = load_items(Path(a.prompts), [w, h])
    files = [it["file"] for it in items]
    dup = {f for f in files if files.count(f) > 1}
    if dup:
        sys.exit(f"⛔ أسماء مكرّرة: {sorted(dup)}")
    job = {
        "folder": folder,
        "status": "pending",
        "created": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "rules": Path(a.rules).read_text(encoding="utf-8") if a.rules else "",
        "items": items,
    }
    out = media / folder / JOB
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(job, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✅ {out}: {len(items)} صورة، الناقص منها {len(missing(media, folder, job))}")
    return 0


def read_job(media: Path, folder: str) -> dict:
    p = media / folder / JOB
    if not p.exists():
        sys.exit(f"⛔ لا مهمّة في {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_status(a) -> int:
    job = read_job(Path(a.media), a.folder)
    miss = missing(Path(a.media), a.folder, job)
    total = len(job["items"])
    print(f"{a.folder}: {total - len(miss)}/{total} · الحالة في الملف: {job.get('status')}")
    base = Path(a.media) / a.folder
    for it in miss[:20]:
        f = base / it["file"]
        why = "غائب" if not f.exists() else f"تالف أو بمقاسٍ غير {it.get('size')}: {dims(f)}"
        print("  ناقص:", it["file"], "—", why)
    return 0 if not miss else 3


def cmd_shard(a) -> int:
    job = read_job(Path(a.media), a.folder)
    base = Path(a.media) / a.folder
    for it in shard(job["items"], a.k, a.n):
        if not done(base, it):
            print(it["file"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("media"); w.add_argument("folder"); w.add_argument("prompts")
    w.add_argument("--rules"); w.add_argument("--size", default="1920x1080")
    s = sub.add_parser("status"); s.add_argument("media"); s.add_argument("folder")
    h = sub.add_parser("shard"); h.add_argument("media"); h.add_argument("folder")
    h.add_argument("k", type=int); h.add_argument("n", type=int)
    a = ap.parse_args()
    return {"write": cmd_write, "status": cmd_status, "shard": cmd_shard}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

