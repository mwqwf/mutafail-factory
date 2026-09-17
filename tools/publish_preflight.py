# -*- coding: utf-8 -*-
"""فحصٌ أخيرٌ غير متلف قبل أول طلب رفع إلى يوتيوب.

لا يطبع عناوين أو أوصافاً من الحمولة غير المنشورة؛ يثبت العقد العام فقط.
"""
import io
import json
import os
import sys


def fail(message):
    raise SystemExit("⛔ " + message)


def main(project, expected_slug):
    def read(name):
        with io.open(os.path.join(project, name), encoding="utf-8") as handle:
            return json.load(handle)

    publish = read("publish.json")
    project_meta = read("meta.json")
    if project_meta.get("slug") != expected_slug:
        fail("حمولة النشر لا تطابق أمر الاستئناف")
    if publish.get("publicNow") is not True:
        fail("amal-2 ليس مضبوطاً على publicNow=true")

    series = publish.get("series") or publish.get("السلسلة")
    playlist_ok = bool(publish.get("playlistId"))
    if not playlist_ok and series:
        try:
            state = json.load(io.open("ops/state/playlists.json", encoding="utf-8"))
        except Exception:
            state = {}
        playlist_ok = (series in state.get("السلاسل", {}) or
                       any(series in title for title in state.get("القوائم", {})) or
                       bool(publish.get("playlistNew", {}).get("title")))
    if not playlist_ok:
        fail("لا مسار قائمة تشغيل صالحاً")

    reels = publish.get("reels", [])
    if sorted(item.get("file") for item in reels) != ["r1.mp4", "r2.mp4"]:
        fail("ملفا الريلز ليسا r1.mp4 وr2.mp4 بالضبط")
    if any("{FILM_URL}" not in item.get("description", "") for item in reels):
        fail("وصف ريلز بلا رابط الفيلم")

    required = ["film.mp4", "thumb-a.jpg", "الفصول.txt",
                os.path.join("reels", "r1.mp4"), os.path.join("reels", "r2.mp4")]
    missing = [name for name in required if not os.path.isfile(os.path.join(project, name))]
    if missing:
        fail("ملفات نشر ناقصة: " + ", ".join(missing))
    empty = [name for name in required if os.path.getsize(os.path.join(project, name)) == 0]
    if empty:
        fail("ملفات نشر فارغة: " + ", ".join(empty))

    print("✅ publish-preflight: command-match · publicNow · playlist · film+r1+r2 · رابط الفيلم")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        fail("الاستعمال: publish_preflight.py <project> <expected-slug>")
    main(sys.argv[1], sys.argv[2])
