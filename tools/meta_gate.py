# -*- coding: utf-8 -*-
"""بوّابة بيانات البحث ومواعيد النشر — أمر المالك 2026-11-23.

العنوان على صيغة المفارقة/الفضول مع لفظ يُبحث به (خالد بن الوليد / اسم معركة / قصة / معركة).
السطران الأوّلان من الوصف يتضمنان عبارة قابلة للبحث. قائمة المصادر تبقى في الوصف.
موعد العلن الافتراضي 17:30–21:00 بتوقيت الجزائر، والشورتات في اليوم التالي.

الاستعمال: python tools/meta_gate.py <مجلد_المشروع>
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import cta_gate

ALGIER = ZoneInfo("Africa/Algiers")
SLOT_START = time(17, 30)
SLOT_END = time(21, 0)

# ألفاظ وعناوين يُبحث بها: الثوابت العامة + أسماء الوقائع الشائعة في أفلام القناة
SEARCH = [
    "خالد بن الوليد",
    "قصة",
    "معركة",
    "غزوة",
    "مؤتة",
    "اليمامة",
    "حديقة الموت",
    "الولجة",
    "أُلّيس",
    "أليس",
    "الأنبار",
    "الفراض",
    "ذات العيون",
    "اليرموك",
    "أجنادين",
    "ذات السلاسل",
    "المفازة",
    "دومة الجندل",
    "أكيدر",
    "جَرَجة",
    "جرجة",
    "الكنانة",
    "القادسية",
    "بدر",
    "أحد",
    "حطين",
    "عين جالوت",
    "الأرك",
    "الزلاقة",
    "ملاذكرد",
    "العقاب",
    "نهاوند",
]

HARAKAT = re.compile(r"[\u064B-\u0652ٰـ]")


def plain(t: str) -> str:
    return HARAKAT.sub("", t or "")


def has_search_term(text: str) -> list[str]:
    t = plain(text)
    found = []
    for term in SEARCH:
        if plain(term) and plain(term) in t:
            found.append(term)
    return found


def first_two_lines(desc: str) -> str:
    lines = [ln.strip() for ln in (desc or "").replace("\r\n", "\n").split("\n") if ln.strip()]
    return "\n".join(lines[:2])


def has_sources(desc: str) -> bool:
    t = plain(desc)
    return bool(re.search(r"المصادر|قائمة المصادر|المصادر والاعتماد", t))


def parse_when(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ALGIER)


def in_slot(dt: datetime) -> bool:
    return SLOT_START <= dt.time() <= SLOT_END


def load_pub(proj: str) -> dict:
    p = os.path.join(proj, "publish.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)



def metadata_texts(pub: dict) -> list[tuple[str, str]]:
    """نصوص بيانات النشر التي يُفحص فيها الوعد بفيلم مقبل."""
    film = pub.get("film") or {}
    pairs = [
        ("العنوان", film.get("title") or pub.get("title") or ""),
        ("الوصف", film.get("description") or pub.get("description") or ""),
        ("التعليق المثبت", pub.get("pinned_comment") or film.get("pinned_comment") or ""),
        ("سؤال التعليق", pub.get("pinned_question") or film.get("pinned_question") or ""),
    ]
    return [(label, text) for label, text in pairs if text]


def end_screen_plan(pub: dict):
    film = pub.get("film") or {}
    for key in ("end_screen", "endscreen", "endScreen"):
        if key in pub:
            return pub[key]
        if key in film:
            return film[key]
    return None


def _end_screen_has_subscribe(plan) -> bool:
    if plan is None or plan is False:
        return False
    if isinstance(plan, str):
        if re.search(r"(no[_-]?subscribe|بدون اشتراك|بلا (?:عنصر )?اشتراك)", plan, re.I):
            return False
        return bool(re.search(r"subscribe|اشتراك", plan, re.I))
    if isinstance(plan, dict):
        for k, v in plan.items():
            kl = str(k).lower()
            if kl in ("subscribe", "subscription", "اشتراك") and v not in (False, None, 0, "false", "no", "off"):
                return True
            if kl in ("type", "kind", "element") and isinstance(v, str) and re.search(r"subscribe|اشتراك", v, re.I):
                return True
            if _end_screen_has_subscribe(v):
                return True
        return False
    if isinstance(plan, (list, tuple)):
        return any(_end_screen_has_subscribe(x) for x in plan)
    return False


def check_pub(pub: dict) -> tuple[list[str], list[str]]:

    errs, warns = [], []
    film = pub.get("film") or {}
    title = film.get("title") or pub.get("title") or ""
    desc = film.get("description") or pub.get("description") or ""

    for label, text in metadata_texts(pub):
        if cta_gate.FUTURE_PROMISE.search(cta_gate.plain(text)):
            errs.append(
                "وعد بفيلم أو حلقة قادمة في %s (أمر المالك 2026-11-27): "
                "لا يُوعَد بفيلم مقبل إلا إن استوفى شروط النجاح وأذن المالك به صراحة"
                % label
            )
    plan = end_screen_plan(pub)
    if plan is not None and _end_screen_has_subscribe(plan):
        errs.append(
            "خطّة شاشة النهاية تتضمن عنصر اشتراك (تشخيص 2026-11-27): "
            "الشاشة فيديوهات فقط (الأفضل للمشاهد وقائمة السلسلة) بلا عنصر اشتراك"
        )

    if title and not has_search_term(title):
        errs.append(
            "العنوان بلا لفظ يُبحث به (أمر المالك 2026-11-23): أدرج «خالد بن الوليد» أو اسم المعركة أو «قصة» أو «معركة»"
        )
    if desc:
        head = first_two_lines(desc)
        if not has_search_term(head):
            errs.append(
                "السطران الأوّلان من الوصف بلا عبارة قابلة للبحث (خالد بن الوليد / اسم معركة / قصة / معركة)"
            )
        if not has_sources(desc):
            errs.append("الوصف بلا قائمة مصادر — المصادر تبقى في الوصف (أمر المالك 2026-11-23)")
        if "{CHAPTERS}" not in desc:
            # يفحصها precheck أيضاً؛ هنا تنبيه لا مانع إضافي إن غاب في استدعاء منفرد
            warns.append("الوصف بلا موضع {CHAPTERS} للفصول")

    when = parse_when(pub.get("publishAt") or film.get("publishAt"))
    if when:
        if not in_slot(when):
            errs.append(
                "موعد علن الفيلم %s خارج الفترة الافتراضية 17:30–21:00 بتوقيت الجزائر"
                % when.strftime("%Y-%m-%d %H:%M")
            )
        film_day = when.date()
        for i, reel in enumerate(pub.get("reels") or [], 1):
            raw = reel.get("publishAt") or reel.get("publish_at")
            if not raw:
                warns.append("شورت %s بلا موعد نشر — الافتراضي اليوم التالي للفيلم" % (reel.get("file") or i))
                continue
            rd = parse_when(raw)
            if not rd:
                errs.append("موعد شورت %s غير قابل للقراءة: %s" % (reel.get("file") or i, raw))
                continue
            delta = (rd.date() - film_day).days
            if delta < 1:
                errs.append(
                    "شورت %s في %s يجب أن يُنشر في اليوم التالي ليوم الفيلم (%s) لا في يومه أو قبله"
                    % ((reel.get("file") or i), rd.strftime("%Y-%m-%d %H:%M"), film_day.isoformat())
                )
            elif delta > 2:
                warns.append(
                    "شورت %s بعد %d أيام من الفيلم — الافتراضي اليوم التالي مباشرة"
                    % (reel.get("file") or i, delta)
                )
    elif pub.get("publicNow"):
        warns.append("علن فوري بلا publishAt — الفترة الافتراضية 17:30–21:00 بتوقيت الجزائر إن أمكن الجدولة")
    return errs, warns


def check_proj(proj: str) -> tuple[list[str], list[str]]:
    return check_pub(load_pub(proj))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    errs, warns = check_proj(argv[0])
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    if errs:
        print("⛔ بوّابة البيانات والمواعيد: %d مانع" % len(errs))
        return 1
    print("✅ بوّابة البيانات والمواعيد: تجتاز")
    return 0


if __name__ == "__main__":
    sys.exit(main())
