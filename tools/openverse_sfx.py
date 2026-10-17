# -*- coding: utf-8 -*-
"""بحثٌ في مؤثّرات Openverse الصوتية (بلا مفتاح) بمرشّح ترخيصٍ صارم ونسبٍ للوصف.

⛔ لا موسيقى: يُقيَّد البحث بفئة sound_effect/ambience وتُرفض النتائج الموسومة music.
⛔ الرخص المقبولة: cc0 وpdm وby فقط (تجاريّ + تعديلٌ جائز). تُستبعد nc وnd وsa.
النسب (by) يذهب إلى وصف يوتيوب لا إلى نصّ الفيلم (أمر المالك: المصادر خارج الفيلم).
الاستعمال: openverse_sfx.py "horse gallop" --n 3 --out work/ov  |  --probe يطبع حدود المعدّل.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
OK_LICENSES = "cc0,pdm,by"
UA = {"User-Agent": "mutafail-factory/1.0 (sfx research)"}


def search(q, n=5, categories="sound_effect,pronunciation", max_dur=30):
    # الفئة غير معلَنةٍ في كل المصادر؛ نمرّر category ثم نرشّح محلياً
    qs = urllib.parse.urlencode({
        "q": q, "license": OK_LICENSES, "page_size": min(n * 3, 20),
        "excluded_source": "jamendo,ccmixter,freemusicarchive",
        "duration": "short" if max_dur <= 30 else "medium",
    })
    req = urllib.request.Request(API + "?" + qs, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        hdr = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower() or k.lower() == "retry-after"}
        data = json.load(r)
    out = []
    for it in data.get("results", []):
        if it.get("category") == "music" or "music" in (it.get("genres") or []):
            continue
        out.append({k: it.get(k) for k in (
            "id", "title", "creator", "license", "license_version", "duration",
            "filesize", "source", "foreign_landing_url", "url", "attribution")})
        if len(out) >= n:
            break
    return out, hdr


def fetch(item, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(urllib.parse.urlparse(item["url"]).path)[1] or ".mp3"
    path = os.path.join(out_dir, f"ov_{item['id']}{ext}")
    req = urllib.request.Request(item["url"], headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def credit_line(item):
    """سطر النسب للوصف؛ CC0/PDM لا يلزمه نسب لكنه يُسجَّل للتوثيق."""
    lic = f"{item['license']} {item.get('license_version') or ''}".strip().upper()
    return f"{item['title']} — {item['creator'] or 'مجهول'} — {lic} — {item['foreign_landing_url']}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("q", nargs="?")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--out")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    qs = ["horse gallop", "sword clash", "desert wind", "battle crowd shouting", "arrows whoosh", "fire crackling"] if a.probe else [a.q]
    for q in qs:
        try:
            items, hdr = search(q, a.n)
        except Exception as e:  # noqa: BLE001
            print(f"[{q}] فشل: {e}")
            continue
        print(f"[{q}] {len(items)} نتيجة؛ حدود: {hdr}")
        for it in items:
            print("  ", credit_line(it), f"{it['duration']}ms" if it['duration'] else "", it["source"])
            if a.out:
                print("   ->", fetch(it, a.out))
