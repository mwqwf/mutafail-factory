# -*- coding: utf-8 -*-
"""حارسُ سلامة النصّ القرآنيّ — مانعٌ داخل precheck.py، ولا يحتاج شبكة.

الاستعمال:  python3 quranverify.py <path/to/script.md> [ملفّات أخرى…]

القاعدة (أمر المالك 2026-09-24: «تأكّد ألّا تحرّف الآيات القرآنية»):
١) كلُّ نصٍّ قرآنيٍّ في السيناريو يُكتب بين القوسين ﴿ ﴾ — وما بينهما يجب أن يطابق
   حروفُه آيةً أو آياتٍ متتاليةً من المصحف المحلّيّ `assets/quran/` كلمةً كلمة.
   التشكيلُ ورسمُ الهمزة وألفُ الوصل لا تُعدّ فرقاً (نطقٌ لا حرف)؛ أمّا حرفٌ زائدٌ أو ناقص
   أو كلمةٌ مبدَّلة أو مقدَّمةٌ أو مؤخَّرة فتحريفٌ مانع.
٢) وكلُّ سبعِ كلماتٍ متتاليةٍ فأكثر تطابق المصحفَ خارج القوسين تُمنع كذلك: قرآنٌ لم يُوسَم،
   فلا يُعرف أنّه قرآن ولا يُفحص نطقُه بما يليق.
⛔ لا يُخفَّف هذا الحارس ولا يُتجاوز؛ ويحرسه tools/test_quranverify.py.

المصدر: نسختان مستقلّتان تطابقتا حرفاً حرفاً في 6236 آية (انظر assets/quran/README.md).
"""
import io
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(os.path.dirname(HERE), "assets", "quran")
UNMARKED_RUN = 7


def norm_word(w):
    w = unicodedata.normalize("NFKC", w)
    w = "".join(c for c in w if not unicodedata.category(c).startswith("M"))
    w = re.sub("[ٱإأآ]", "ا", w)
    w = re.sub("[ىی]", "ي", w)
    w = w.replace("ـ", "").replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    w = w.replace("ء", "")
    return re.sub(r"[^ء-ي]", "", w)


def words(text):
    return [x for x in (norm_word(w) for w in text.split()) if x]


def load_mushaf():
    """يعيد لكلّ نسخةٍ قائمةَ كلماتِ كلِّ سورةٍ متّصلةً، مع موضع كلّ كلمة."""
    out = []
    for name in ("simple", "uthmani"):
        d = json.load(io.open(os.path.join(QDIR, "quran-%s.json" % name), encoding="utf-8"))
        surahs = {}
        for key, text in d.items():
            s, v = map(int, key.split(":"))
            surahs.setdefault(s, []).append((v, text))
        seqs = []
        for s in sorted(surahs):
            ws, refs = [], []
            for v, text in sorted(surahs[s]):
                for w in words(text):
                    ws.append(w)
                    refs.append("%d:%d" % (s, v))
            seqs.append((ws, refs))
        out.append(seqs)
    return out


def find(seq_words, mushaf):
    """يبحث عن الكلمات متّصلةً في أيٍّ من النسختين؛ يعيد (سورة:آية الأولى، الأخيرة) أو None."""
    n = len(seq_words)
    if not n:
        return None
    first = seq_words[0]
    for seqs in mushaf:
        for ws, refs in seqs:
            for i in range(len(ws) - n + 1):
                if ws[i] == first and ws[i:i + n] == seq_words:
                    return refs[i], refs[i + n - 1]
    return None


def build_index(mushaf, k):
    idx = set()
    for seqs in mushaf:
        for ws, _ in seqs:
            for i in range(len(ws) - k + 1):
                idx.add(tuple(ws[i:i + k]))
    return idx


def audit_text(label, text, mushaf, kgrams):
    problems = []
    for m in re.finditer(r"﴿([^﴾]*)﴾", text):
        q = words(m.group(1))
        if not q:
            problems.append("%s: قوسا آيةٍ فارغان" % label)
            continue
        if not find(q, mushaf):
            problems.append("%s: ⛔ نصٌّ بين ﴿ ﴾ لا يطابق المصحف حرفيّاً — «%s»"
                            % (label, m.group(1).strip()[:80]))
    if "﴿" in text.replace("﴾", "") and text.count("﴿") != text.count("﴾"):
        problems.append("%s: قوسُ آيةٍ مفتوحٌ بلا إغلاق" % label)
    outside = re.sub(r"﴿[^﴾]*﴾", " | ", text)
    for chunk in outside.split("|"):
        ws = words(chunk)
        for i in range(len(ws) - UNMARKED_RUN + 1):
            if tuple(ws[i:i + UNMARKED_RUN]) in kgrams:
                problems.append("%s: ⛔ %d كلماتٍ من المصحف بلا قوسَي ﴿ ﴾ — «%s»"
                                % (label, UNMARKED_RUN, " ".join(chunk.split()[i:i + UNMARKED_RUN])))
                break
    return problems


def audit_files(paths, mushaf=None):
    mushaf = mushaf or load_mushaf()
    kgrams = build_index(mushaf, UNMARKED_RUN)
    problems, quoted = [], 0
    for p in paths:
        with io.open(p, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        for n, line in enumerate(lines, 1):
            line = line.rstrip("\n")
            if line.startswith("IMG:"):
                if "﴿" in line or any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in line):
                    problems.append("%s:%d: ⛔ نصٌّ عربيٌّ/قرآنيٌّ في وصف صورة" % (os.path.basename(p), n))
                continue
            quoted += line.count("﴿")
            problems += audit_text("%s:%d" % (os.path.basename(p), n), line, mushaf, kgrams)
    return problems, quoted


def main(argv):
    paths = argv[1:] or ["script.md"]
    problems, quoted = audit_files(paths)
    print("حارسُ النصّ القرآنيّ: فُحص %d اقتباساً بين ﴿ ﴾" % quoted)
    if problems:
        print("⛔ %d مانع:" % len(problems))
        for p in problems:
            print("  · " + p)
        return 1
    print("✅ كلُّ آيةٍ مطابقةٌ للمصحف حرفيّاً، ولا قرآنَ بلا وسم")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
