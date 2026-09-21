# -*- coding: utf-8 -*-
"""فحصُ الحمولة قبل الختمِ والدفع — محليٌّ ومجّانيٌّ بالكامل.

الاستعمال:  python precheck.py <مجلد_الحمولة>

⛔ كلُّ ما يفحصه هنا كان سيسقط الشوطَ بعد ساعاتٍ من التوليد، أو — وهو أسوأ —
   يمرّ صامتاً فيخرج فيلمٌ ناقص. والقاعدة: ما يُمسَك مجّاناً لا يُترك للعدّاء.
"""
import io
import json
import os
import subprocess as sp
import sys
from duration_policy import audit_duration

P = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda n: json.load(io.open(os.path.join(P, n), encoding="utf-8"))
bad = []


def need(name):
    f = os.path.join(P, name)
    if not os.path.exists(f):
        bad.append("ملفٌّ ناقص: " + name)
        return False
    return True


for f in ("script.md", "sections.json", "reels.json", "publish.json", "meta.json"):
    need(f)
if bad:
    print("\n".join("⛔ " + b for b in bad))
    raise SystemExit(1)

# ① البوّابتان
# ⛔ `humanlint.py` حارسٌ مانعٌ لا مستشار (أمر المالك 2026-09-21: أسلوبٌ بشريّ،
#    ولا مثاليّةَ زائدةً توحي بأنّ السيناريو كُتب بالذكاء الاصطناعيّ). وتخطّيه
#    يكون بإصلاح النصّ أو بتحكيمٍ مكتوبٍ في `style_review.json`، لا بحذفه من هنا.
for tool in ("lint.py", "guard.py", "humanlint.py"):
    r = sp.run([sys.executable, os.path.join(HERE, tool), os.path.join(P, "script.md")],
               capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        bad.append(tool + " ردّ بمخالفة")
    if tool == "lint.py" and "ملاحظة وقائية" in r.stdout:
        bad.append("lint.py عنده ملاحظاتٌ لم تُحكَّم — راجعها ثمّ أعِد")

# ② البناء
r = sp.run([sys.executable, os.path.join(HERE, "build.py"), P], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
if r.returncode:
    raise SystemExit("⛔ build.py سقط")

blocks = J("blocks.json")
imgs = {i["id"] for i in J("images.json")}
shots = J("shots.json")
film = [b["id"] for b in blocks if not b.get("reel_only")]
reel_only = {b["id"] for b in blocks if b.get("reel_only")}
allb = {b["id"] for b in blocks}

# ③ اللقطات تشير إلى كتل الفيلم وحدها
for s in shots:
    if s["from"] not in film or s["to"] not in film:
        bad.append("لقطةٌ تشير إلى كتلةٍ ليست من الفيلم: %s" % s)
    if s["img"] not in imgs:
        bad.append("لقطةٌ تشير إلى صورةٍ غير موجودة: %s" % s["img"])
seen = {}
for s in shots:
    seen[s["img"]] = seen.get(s["img"], 0) + 1
dup = [k for k, v in seen.items() if v > 1]
if dup:
    bad.append("صورةٌ مستعمَلةٌ في أكثر من لقطة (فيديو أطولُ من الصوت): " + " ".join(dup))

# ④ الفصول
sec = J("sections.json")
if len(sec) < 3:
    bad.append("فصولُ يوتيوب تحتاج ثلاثةً فأكثر")
if sec and sec[0]["id"] != film[0]:
    bad.append("أوّلُ فصلٍ يجب أن يبدأ بأوّل كتلةٍ في الفيلم (يوتيوب يشترط 0:00)")
for s in sec:
    if s["id"] not in film:
        bad.append("فصلٌ يشير إلى كتلةٍ غير موجودةٍ في الفيلم: " + s["id"])
order = [film.index(s["id"]) for s in sec if s["id"] in film]
if order != sorted(order):
    bad.append("الفصولُ غيرُ مرتّبةٍ بترتيب الفيلم")

# ⑤ الريلزات
reels = J("reels.json")
if len(reels) != 2:
    bad.append("ريلزان اثنان لا غير (أمر المالك) — وُجد %d" % len(reels))
used_reel_blocks = set()
for r in reels:
    for b in r["blocks"]:
        if b not in allb:
            bad.append("ريلز %s يشير إلى كتلةٍ غير موجودة: %s" % (r["id"], b))
        used_reel_blocks.add(b)
    for i in r["imgs"]:
        if i not in imgs:
            bad.append("ريلز %s يشير إلى صورةٍ غير موجودة: %s" % (r["id"], i))
    if len(r["imgs"]) != 3:
        bad.append("ريلز %s: ثلاثُ صورٍ لا %d" % (r["id"], len(r["imgs"])))
    if not r.get("title"):
        bad.append("ريلز %s بلا عنوان" % r["id"])
for b in reel_only - used_reel_blocks:
    bad.append("كتلةُ ريلزٍ مولَّدةٌ ولا يستعملها ريلز (إهدارُ حصّة): " + b)

# ⑥ ملفّ النشر
pub = J("publish.json")
for k in ("film", "reels", "thumbs"):
    if k not in pub:
        bad.append("publish.json ينقصه: " + k)
f = pub.get("film", {})
if len(f.get("title", "")) > 100:
    bad.append("العنوان أطول من مئة حرف")
for ch in "*_#⭐":
    if ch in f.get("title", ""):
        bad.append("العنوان فيه رمزُ تنسيق: " + ch)
t = ",".join(f.get("tags", []))
if "،" in t:
    bad.append("وسومٌ بفاصلةٍ عربية")
if len(t) > 500:
    bad.append("الوسومُ تتجاوز خمسَ مئة حرف: %d" % len(t))
if f.get("tags") and max(map(len, f["tags"])) > 30:
    bad.append("وسمٌ أطولُ من ثلاثين حرفاً")
if not (25 <= len(f.get("tags", [])) <= 30):
    bad.append("الوسومُ خمسةٌ وعشرون إلى ثلاثين — وُجد %d" % len(f.get("tags", [])))
if "{CHAPTERS}" not in f.get("description", ""):
    bad.append("الوصفُ بلا موضعٍ للفصول {CHAPTERS} — فلا فصولَ على يوتيوب")
if len(f.get("description", "")) > 5000:
    bad.append("الوصفُ أطولُ من خمسةِ آلافِ حرف")
if len(pub.get("reels", [])) != 2:
    bad.append("ملفُّ النشر: ريلزان اثنان لا غير")
# ⛔⛔ درسٌ مقيسٌ 2026-09-21 (حلقة «الثور»): سقط عاملُ النشر بعد الشوط كلِّه على
#    `⛔ ملفا الريلز ليسا r1.mp4 وr2.mp4 بالضبط` — لأنّ الحمولة كتبت `"file": "r1"`.
#    وهو شرطٌ كان يُفحص في العدّاء آخرَ الطريق، فيُهدر شوطٌ كامل. ⇒ يُفحص هنا مجّاناً.
if sorted(r.get("file", "") for r in pub.get("reels", [])) != ["r1.mp4", "r2.mp4"]:
    bad.append("ملفّا الريلز في publish.json يجب أن يكونا r1.mp4 وr2.mp4 بالضبط "
               "(شرطُ publish_preflight.py)")
for r in pub.get("reels", []):
    if "{FILM_URL}" not in r.get("description", ""):
        bad.append("ريلز %s: وصفُه بلا رابطِ الفيلم" % r.get("file"))
    if r.get("title", "").strip().lower() in ("r1", "r2"):
        bad.append("⛔ عنوانُ شورتٍ داخليّ")
for th in pub.get("thumbs", []):
    if th["bg"] not in imgs:
        bad.append("مصغّرةٌ تشير إلى صورةٍ غير موجودة: " + th["bg"])
if len(pub.get("thumbs", [])) < 2:
    bad.append("مصغّرتان (أ/ب) للاختبار")

# ⑥ب القائمة — تُفحَص هنا مجّاناً لا بعد ساعاتٍ من التوليد
# ⛔⛔ «لا يُنشر فيلمٌ خارج قائمته» (أمر المالك 2026-09-14). وخطوةُ النشر آخرُ
#    الشوط، فسقوطُها هناك يُهدر حصّةَ يومٍ كاملة. ⇒ يُتحقَّق من وجود سبيلٍ إلى
#    القائمة قبل الختم: معرّفٌ صريح · أو سلسلةٌ مسجَّلة · أو playlistNew لسلسلةٍ جديدة.
# ⛔ فيلمٌ بلا `publishAt` ولا `publicNow` يُرفع **خاصّاً بلا موعد** فلا يراه أحدٌ أبداً،
#    والشوطُ ينجح! فيُدَّعى النشرُ وهو لم يقع. ⇒ يُشترط أحدُهما قبل الختم.
if not pub.get("publishAt") and not pub.get("publicNow"):
    bad.append("ملفُّ النشر بلا publishAt ولا publicNow — الفيلمُ سيبقى خاصّاً بلا موعد")

_series = pub.get("series") or pub.get("السلسلة")
if not pub.get("playlistId"):
    try:
        _pl = json.load(io.open(os.path.join(os.path.dirname(HERE), "ops", "state",
                                             "playlists.json"), encoding="utf-8"))
    except Exception:
        _pl = {}
    _known = _series and (_series in _pl.get("السلاسل", {}) or
                          any(_series in t for t in _pl.get("القوائم", {})))
    _new = pub.get("playlistNew", {}).get("title")
    if not _known and not (_series and _new):
        bad.append("لا سبيلَ إلى قائمةٍ: ضَع playlistId أو series مسجَّلاً في "
                   "ops/state/playlists.json أو playlistNew{title,description}")

# ⑦ تقديرُ المدّة والحصّة
DIAC = "ًٌٍَُِّْـ"
plain = lambda s: "".join(c for c in s if c not in DIAC)
n = sum(len(plain(b["text"])) for b in blocks if not b.get("reel_only"))
mins = n * 0.1198 / 60.0
print("\n── تقديرٌ قبل الدفع ──")
print("كتلُ الفيلم: %d | كتلُ الريلز: %d | صور: %d | لقطات: %d"
      % (len(film), len(reel_only), len(imgs), len(shots)))
print("حروفٌ بلا تشكيل: %d ⇒ المدّةُ المقدَّرة: %.1f دقيقة" % (n, mins))
measured_retry_factor = 506.0 / 170.0
tts_budget = int(len(blocks) * measured_retry_factor + 0.999) + 20
listen_budget = int((len(blocks) + 3) / 4) + 20
print("ميزانيةُ TTS المحافظة: %d محاولة (أحدثُ معاملٍ مقيس 506/170 + عشرون إصلاحاً)" % tts_budget)
print("ميزانيةُ الاستماع المجمّع: %d نداءً (أربعةُ مقاطع/نداء + هامش عشرين)" % listen_budget)
for problem in audit_duration(mins, J("meta.json")):
    bad.append(problem + ": %.1f دقيقة / %d حرف بلا تشكيل" % (mins, n))

print()
if bad:
    print("⛔ %d مانع:" % len(bad))
    for b in bad:
        print("  ·", b)
    raise SystemExit(1)
print("✅ الحمولةُ سليمة — يجوز الختمُ والدفع")
