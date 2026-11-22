# -*- coding: utf-8 -*-
"""بوّابة النصّ قبل أي توليد — أمر المالك 2026-11-22: الوقاية من الأخطاء الإملائية خير من العلاج.

تُفحص النصوص (السيناريو المشكول، والعناوين، والوصف، والبطاقات، والمصغّرات) قبل توليد الصوت أو
رسم كتابة على صورة. الفحص آليّ مجّاني: أنماط lint، وقائمة أخطاء متكرّرة، واتساق الأعلام،
ونسبة التشكيل في السرد، وhunspell-ar إن وُجد. والخروج 1 يمنع التوليد.

الاستعمال:
  python tools/text_gate.py <مجلد_المشروع>          # سيناريو/كتل (تشكيل مطلوب)
  python tools/text_gate.py --lines text.txt        # أسطر حرّة بلا إلزام تشكيل (عناوين)
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint  # noqa: E402

DIAC = "ًٌٍَُِّْٰـ"
AR_LETTER = re.compile(r"[\u0621-\u064A]")
WORD_RX = re.compile(r"[\u0621-\u064A]+(?:[\u064B-\u0652ٰـ]*[\u0621-\u064A]+)*")
MISTAKES_PATH = os.path.join(HERE, "data", "text_gate_mistakes.json")
TASHKEEL_MIN = 0.55  # نسبة الحروف العربية المتبوعة بحركة في السرد المشكول

# أسماء لا يُحكم عليها hunspell (أعلام ومصطلحات تاريخية شائعة في أفلام القناة)
ALLOW = {
    "خالد", "الوليد", "هرقل", "ضرار", "هشام", "العاص", "عمرو", "وردان", "تليب", "طليب",
    "أجنادين", "اليرموك", "القادسية", "مؤتة", "اليمامة", "الأرك", "ملاذكرد",
    "البلقاء", "حمص", "الشام", "الروم", "المسلمون", "المسلمين", "سيف", "الله",
}


def strip_d(s: str) -> str:
    return "".join(c for c in (s or "") if c not in DIAC)


def load_mistakes() -> dict:
    try:
        return json.load(io.open(MISTAKES_PATH, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def parse_script(path: str) -> list[tuple[str, str, str]]:
    """(id, role, text) من script.md بصيغة الكتلة|الدور|النص."""
    out = []
    for raw in io.open(path, encoding="utf-8"):
        m = re.match(r"^(d_\d{3}|m_\d{3}|r_\d{3})\|(\w)\|(.+)$", raw.rstrip("\n"))
        if m:
            out.append((m.group(1), m.group(2), m.group(3).strip()))
    return out


def items_from_proj(proj: str) -> list[tuple[str, str, str]]:
    """بنود الفحص: من script.md إن وُجد، وإلا من blocks.json."""
    script = os.path.join(proj, "script.md")
    if os.path.exists(script):
        items = parse_script(script)
        if items:
            return items
    blocks_p = os.path.join(proj, "blocks.json")
    if os.path.exists(blocks_p):
        blocks = json.load(io.open(blocks_p, encoding="utf-8"))
        return [(b["id"], b.get("role") or "N", b.get("text") or "") for b in blocks if b.get("text")]
    return []


def tashkeel_ratio(text: str) -> float:
    letters = 0
    marked = 0
    for i, ch in enumerate(text):
        if not AR_LETTER.match(ch):
            continue
        letters += 1
        if i + 1 < len(text) and text[i + 1] in DIAC:
            marked += 1
    return (marked / letters) if letters else 1.0


def hunspell_bin() -> str | None:
    return shutil.which("hunspell")


def hunspell_words(words: list[str]) -> list[str]:
    """كلمات يرفضها hunspell-ar (بعد نزع التشكيل). قائمة تحذيرية فقط."""
    exe = hunspell_bin()
    if not exe or not words:
        return []
    dic = "/usr/share/hunspell/ar"
    if not os.path.exists(dic + ".dic"):
        return []
    uniq, seen = [], set()
    for w in words:
        p = strip_d(w)
        if len(p) < 3 or p in ALLOW or p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    if not uniq:
        return []
    try:
        r = subprocess.run(
            [exe, "-d", dic, "-l"],
            input="\n".join(uniq) + "\n",
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def check_items(items: list[tuple[str, str, str]], require_tashkeel: bool = True) -> tuple[list[str], list[str]]:
    """يرجع (موانع، تحذيرات)."""
    errs, warns = [], []
    lex = load_mistakes()
    substitutes = {strip_d(k): v for k, v in (lex.get("بدائل") or {}).items()}
    risky = {strip_d(k): v for k, v in (lex.get("ملتبسة_النطق") or {}).items()}

    # lint على ملف مؤقت بصيغة السيناريو إن كانت البنود على شكل كتل
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".md", text=True)
        os.close(fd)
        with io.open(tmp, "w", encoding="utf-8") as f:
            for bid, role, text in items:
                role = role if role in ("N", "Q", "P") else "N"
                bid_s = bid if re.match(r"^(d|m|r)_\d{3}$", bid) else "d_000"
                f.write("%s|%s|%s\n" % (bid_s, role, text))
        for bid, msg, ev in lint.check(tmp):
            errs.append("%s: %s «%s»" % (bid, msg, ev))
        for bid, w in lint.naqs(tmp):
            errs.append("%s: تنقّص ممنوع «%s»" % (bid, w))
        # صيغ التمريض: lint يرفضها في الراوي كلّه؛ هنا تُنقل كما هي (السياسة القائمة)
        for bid, w in lint.hedge(tmp):
            errs.append("%s: صيغة تمريض في كلام الراوي «%s»" % (bid, w))
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

    names: dict[str, set[str]] = {}
    hunspell_pool = []
    for bid, role, text in items:
        plain = strip_d(text)
        for typo, fix in substitutes.items():
            if typo and typo in plain.replace("ـ", ""):
                errs.append("%s: إملاء «%s» ← %s" % (bid, typo, fix))
        if require_tashkeel and role in ("N", "Q", "P", "") and len(AR_LETTER.findall(text)) >= 12:
            ratio = tashkeel_ratio(text)
            if ratio < TASHKEEL_MIN:
                errs.append("%s: التشكيل ناقص (%.0f%% من الحروف مشكولة، المطلوب ≥ %.0f%%)" % (
                    bid, ratio * 100, TASHKEEL_MIN * 100))
        # اتساق «ابن/بن» سجّله lint؛ اتساق كتابة العلم نفسه بأشكال مختلفة في الملف
        for m in re.finditer(r"(خالد|ضرار|هشام|عمرو|هرقل|وردان)\s+(?:بْنُ?\s+|ابن\s+)([\u0621-\u064A]+)", text):
            key = strip_d(m.group(1))
            names.setdefault(key, set()).add(strip_d(m.group(0)))
        hunspell_pool.extend(WORD_RX.findall(plain))

    for key, variants in names.items():
        if len(variants) > 1:
            warns.append("كتابة غير موحّدة للاسم «%s»: %s" % (key, "، ".join(sorted(variants))))

    unknown = hunspell_words(hunspell_pool)
    if unknown:
        # تحذير فقط: المعجم الحديث يرفض كثيراً من فصحى الأعلام والتاريخ
        sample = "، ".join(unknown[:12])
        warns.append("hunspell لم يعرف %d كلمة (للمراجعة اليدوية، ليست مانعاً): %s" % (len(unknown), sample))
    elif require_tashkeel and hunspell_bin() is None:
        warns.append("hunspell-ar غير متاح في هذه البيئة — أُنجزت الفحوص الأخرى")

    return errs, warns


def checklist() -> str:
    return (
        "مراجعة يدوية إلزامية قبل التوليد: اقرأ السيناريو المشكول كاملاً، وتحقق من همزات الأعلام، "
        "ومن أن التشكيل يطابق المعنى (لا وجهين في كلمة ملتبسة)، ومن أن العناوين والبطاقات والمصغّرات "
        "مطابقة حرفاً لحرف لما في السيناريو، بلا مصدر ولا اسم سلسلة في أول أربع دقائق."
    )


def check_proj(proj: str, require_tashkeel: bool = True) -> int:
    items = items_from_proj(proj)
    # عناوين ووصف النشر إن وُجدت
    extras: list[tuple[str, str, str]] = []
    for name in ("publish.json", "thumbs_titles.md", "description.md"):
        p = os.path.join(proj, name)
        if not os.path.exists(p):
            continue
        if name.endswith(".json"):
            try:
                pub = json.load(io.open(p, encoding="utf-8"))
            except ValueError:
                continue
            title = ((pub.get("film") or {}).get("title") or pub.get("title") or "")
            desc = ((pub.get("film") or {}).get("description") or pub.get("description") or "")
            if title:
                extras.append(("publish.title", "T", title))
            if desc:
                extras.append(("publish.description", "T", desc[:2000]))
        else:
            extras.append((name, "T", io.open(p, encoding="utf-8").read()[:4000]))
    errs, warns = check_items(items, require_tashkeel=require_tashkeel)
    e2, w2 = check_items(extras, require_tashkeel=False) if extras else ([], [])
    errs, warns = errs + e2, warns + w2
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    print("📋", checklist())
    if errs:
        print("⛔ بوّابة النصّ: %d مانعاً — يُصلح قبل أي توليد" % len(errs))
        return 1
    print("✅ بوّابة النصّ: لا موانع (%d بنداً)" % len(items))
    return 0


def check_lines(pairs: list[tuple[str, str]], require_tashkeel: bool = False) -> int:
    items = [(k, "T", v) for k, v in pairs if (v or "").strip()]
    errs, warns = check_items(items, require_tashkeel=require_tashkeel)
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    if errs:
        print("⛔ بوّابة النصّ: %d مانعاً في العناوين/الكتابة" % len(errs))
        return 1
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--lines":
        path = argv[1]
        lines = [ln.rstrip("\n") for ln in io.open(path, encoding="utf-8") if ln.strip()]
        return check_lines([(f"L{i}", ln) for i, ln in enumerate(lines, 1)], require_tashkeel=False)
    return check_proj(argv[0], require_tashkeel=True)


if __name__ == "__main__":
    sys.exit(main())
