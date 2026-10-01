#!/usr/bin/env python3
"""🧾 طابور كوديكس — أمرٌ ثابتٌ واحد بدل أوامر تُلصق لكل فيلم (أمر المالك 2026-10-01).

**لماذا؟** كانت كلّ حلقة تُنتج 3–6 أوامر طويلة يلصقها المالك بيده في كوديكس. والمالك يريد ألّا
يتدخّل إلا باختيار الموضوع. فصارت الجلسة تكتب **ملفّ مهمّة** في مستودع الصور الدائم
`mwqwf/yarmouk-media` (‏`<المجلد>/codex_job.json`)، وكوديكس يُعطى أمراً ثابتاً لا يتغيّر:

    نفّذ الطابور                ← مهمّةٌ واحدة تولّد كلّ الناقص
    نفّذ الطابور، الجزء 2 من 3  ← ثلاث مهامّ متوازية، كلٌّ يأخذ ثلث الناقص

وبروتوكولُه مكتوبٌ في `AGENTS.md` بجذر مستودع الصور، فيقرؤه كوديكس وحده. وإن أتاح كوديكس
جدولةَ مهمّةٍ متكرّرة فهذا الأمر نفسُه يُجدوَل مرّةً واحدة، ولا يعود المالك إليه.

    python3 tools/codex_queue.py write  <مستودع_الصور> <المجلد> <prompts.json> [--rules ملف] [--size 1920x1080]
    python3 tools/codex_queue.py status <مستودع_الصور> <المجلد>     # خروج 0 = اكتمل · 3 = ناقص
    python3 tools/codex_queue.py shard  <مستودع_الصور> <المجلد> <k> <n>   # ما يخصّ الجزء k من n (للفحص)

`prompts.json` إمّا قاموس `{"F001": "وصف…"}` (يُحفظ `images/F001.jpg`) أو قائمة
`[{"file": "thumbs/x-A.png", "prompt": "…", "size": [1280, 720]}]`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

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
    return items


def missing(media: Path, folder: str, job: dict) -> list[dict]:
    base = media / folder
    return [it for it in job["items"] if not (base / it["file"]).exists()]


def shard(items: list[dict], k: int, n: int) -> list[dict]:
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
    for it in miss[:20]:
        print("  ناقص:", it["file"])
    return 0 if not miss else 3


def cmd_shard(a) -> int:
    job = read_job(Path(a.media), a.folder)
    for it in shard(missing(Path(a.media), a.folder, job), a.k, a.n):
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
