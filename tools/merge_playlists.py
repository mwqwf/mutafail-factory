# -*- coding: utf-8 -*-
"""يدمج playlists.json الذي كتبه الشوطُ في نسخة master دمجاً لا استبدالاً.

⛔ الدرسُ المقيس (2026-09-23): استبدالُ الملفّ كاملاً من نسخة الشوط محا قائمةَ
«كائنات غيّرت التاريخ» (PLJSofb55AafA) التي سجّلها نشرٌ سابقٌ في master.
⇒ القوائمُ اتّحادٌ لا استبدال: لا تُحذف قائمةٌ عرفها أيُّ طرف، ويغلب الشوطُ فيما كتبه هو.
الاستعمال: merge_playlists.py <ملفّ master الهدف> <ملفّ الشوط>
"""
import io, json, sys


def merge(base, run):
    out = dict(base)
    for key in ("القوائم", "السلاسل"):
        merged = dict(base.get(key) or {})
        merged.update(run.get(key) or {})
        out[key] = merged
    for key, value in run.items():
        if key not in ("القوائم", "السلاسل"):
            out[key] = value
    return out


def main(target, run_file):
    base = json.load(io.open(target, encoding="utf-8"))
    run = json.load(io.open(run_file, encoding="utf-8"))
    io.open(target, "w", encoding="utf-8").write(
        json.dumps(merge(base, run), ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
