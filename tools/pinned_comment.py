# -*- coding: utf-8 -*-
"""يولّد التعليق المثبت لسلسلة «سيف الله» — أمر المالك 2026-11-23.

الاستعمال: python tools/pinned_comment.py <مجلد_المشروع>
يكتب <المشروع>/تعليق-مثبت.txt من القالب والكتالوج، بعد فحص الإملاء.
"""
from __future__ import annotations

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(ROOT, "ops", "series", "sayf-allah-episodes.json")
sys.path.insert(0, HERE)
import text_gate  # noqa: E402

OUT_NAME = "تعليق-مثبت.txt"
SERIES_NAMES = {"سيف الله", "خالد", "خالد بن الوليد"}


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def catalog() -> dict:
    return load_json(CATALOG)


def is_khalid_series(pub: dict, meta: dict) -> bool:
    series = pub.get("series") or pub.get("السلسلة") or meta.get("السلسلة") or meta.get("series") or ""
    return any(name in str(series) for name in SERIES_NAMES) or bool(slug_in_catalog(pub, meta))


def slug_of(pub: dict, meta: dict) -> str:
    return (meta.get("slug") or pub.get("slug") or pub.get("film_slug") or "").strip()


def slug_in_catalog(pub: dict, meta: dict) -> str:
    slug = slug_of(pub, meta)
    if not slug:
        return ""
    for ep in catalog().get("episodes") or []:
        if ep.get("slug") == slug:
            return slug
    return ""


def find_episode(cat: dict, slug: str) -> tuple[int, dict | None]:
    eps = cat.get("episodes") or []
    for i, ep in enumerate(eps):
        if ep.get("slug") == slug:
            return i, ep
    return -1, None


def override_neighbor(pub: dict, key: str) -> dict | None:
    raw = pub.get(key)
    if not isinstance(raw, dict):
        return None
    title = (raw.get("title") or raw.get("العنوان") or "").strip()
    vid = (raw.get("id") or raw.get("video_id") or raw.get("معرّف") or "").strip() or None
    if not title and not vid:
        return None
    return {"title": title, "video_id": vid}


def neighbor_from_ep(ep: dict | None) -> dict | None:
    if not ep:
        return None
    return {"title": ep.get("title") or "", "video_id": ep.get("video_id") or None, "n": ep.get("n")}


def link_block(label: str, item: dict | None, missing_line: str) -> str:
    if not item:
        return missing_line
    title = (item.get("title") or "").strip()
    vid = (item.get("video_id") or "").strip() if item.get("video_id") else ""
    if vid and title:
        return "%s\n\n«%s»\nhttps://youtu.be/%s" % (label, title, vid)
    if vid:
        return "%s\n\nhttps://youtu.be/%s" % (label, vid)
    if title:
        if "السابقة" in label:
            return "إن أعجبتك هذه الحلقة، فالحلقة السابقة هي: «%s»." % title
        # لا وعد بنشر حلقة مقبلة (أمر المالك 2026-11-27)
        return ""
    return missing_line


def render(pub: dict, meta: dict, cat: dict | None = None) -> str:
    cat = cat or catalog()
    slug = slug_of(pub, meta)
    idx, current = find_episode(cat, slug)
    question = (
        (pub.get("pinned_question") or "").strip()
        or (current or {}).get("question")
        or cat.get("default_question")
        or "أيُّ موقفٍ في هذه الحلقة شدَّك أكثر، ولماذا؟"
    )
    prev = override_neighbor(pub, "prev_episode")
    nxt = override_neighbor(pub, "next_episode")
    eps = cat.get("episodes") or []
    if prev is None and idx > 0:
        prev = neighbor_from_ep(eps[idx - 1])
    if nxt is None and 0 <= idx < len(eps) - 1:
        nxt = neighbor_from_ep(eps[idx + 1])

    parts = []
    if idx == 0:
        parts.append("هذه أولى حلقات قصة خالد بن الوليد.")
        if nxt and nxt.get("video_id"):
            parts.append(link_block("والحلقة التالية هنا:", nxt, ""))
        # وإلا: لا وعد بحلقة لم تُنشر بعد (أمر المالك 2026-11-27)
    else:
        if prev and (prev.get("video_id") or prev.get("title")):
            if prev.get("video_id"):
                parts.append(link_block("إن أعجبتك هذه الحلقة، فالحلقة السابقة هنا:", prev, ""))
            else:
                parts.append("إن أعجبتك هذه الحلقة، فالحلقة السابقة هي: «%s»." % (prev.get("title") or "").strip())
        else:
            parts.append("إن أعجبتك هذه الحلقة، فشارك ما شدّك منها في تعليق.")
        if nxt and nxt.get("video_id"):
            parts.append(link_block("والحلقة التالية هنا:", nxt, ""))
        # وإلا: لا وعد بحلقة لم تُنشر بعد (أمر المالك 2026-11-27)

    parts.append("سؤال للتعليق: %s" % question)
    text = "\n\n".join(p for p in parts if p).strip() + "\n"
    return text


def write_proj(proj: str, text: str) -> str:
    out = os.path.join(proj, OUT_NAME)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(text)
    return out


def generate(proj: str) -> tuple[str, str]:
    """يكتب التعليق ويعيد (المسار، النص). يرفع إن فشل فحص الإملاء."""
    pub = load_json(os.path.join(proj, "publish.json"))
    meta = load_json(os.path.join(proj, "meta.json"))
    if not is_khalid_series(pub, meta):
        raise ValueError("ليست حلقة من سلسلة سيف الله — لا يُولَّد تعليق مثبت إلزامي")
    if not slug_of(pub, meta):
        raise ValueError("لا slug في publish.json أو meta.json لتحديد الحلقة السابقة والتالية")
    text = render(pub, meta)
    if text_gate.check_lines([(OUT_NAME, text)], require_tashkeel=False):
        raise ValueError("بوّابة النصّ رفضت التعليق المثبت")
    return write_proj(proj, text), text


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    proj = os.path.abspath(argv[0])
    try:
        path, _ = generate(proj)
    except ValueError as exc:
        print("⛔", exc)
        return 1
    print("✅", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
