# -*- coding: utf-8 -*-
"""دفترُ الحصص — لا تُهدر وحدةٌ، ولا يُبدأ عملٌ لا تحتمله الحصّةُ الباقية.

⭐ قاعدةُ المالك (2026-09-15): «نفعل أقصى ما يمكن، ولا نضيّع ولو مليمًا واحدًا،
   وما تؤخّره الحصّةُ يُجدوَل لأوّل تجدّدٍ ويُنفَّذ تلقائيًّا».

⛔ وحصّتا يوتيوب وجيميناي مختلفتان في كلّ شيء:
   · يوتيوب: عشرةُ آلاف وحدةٍ في اليوم للمشروع، وتتجدّد منتصفَ ليل المحيط الهادئ
     (‏نحو السابعة صباحاً بتوقيت غرينتش صيفاً) — ورفعُ فيديو واحدٍ ألفٌ وست مئة.
   · جيميناي: عشرُ توليداتٍ لكلّ مشروعٍ ولكلّ نموذج، وتتجدّد الثامنةَ صباحاً
     بتوقيت المالك (‏`ops/state/quota.json`).
"""
import io, json, os, time

STATE = os.path.join("ops", "state", "quota_usage.json")
CAP = 10000          # سقفُ يوتيوب اليوميّ للمشروع
MARGIN = 400         # هامشٌ يُترك لعملياتٍ صغيرةٍ لا تُحصى
COST = {"upload": 1600, "thumbnail": 50, "playlist_insert": 50,
        "video_update": 50, "read": 1}


def _today():
    # ⛔ يومُ حصّة يوتيوب يبدأ عند تجدّدها لا عند منتصف ليل غرينتش
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - 7 * 3600))


def load():
    try:
        d = json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        d = {}
    if d.get("يوتيوب", {}).get("اليوم") != _today():
        d["يوتيوب"] = {"اليوم": _today(), "وحدات": 0, "عمليات": []}
    return d


def save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    io.open(STATE, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1))


def spend(kind, note=""):
    """يُسجَّل بعد كلّ عمليةٍ واقعة — لا قبلها، فالمسجَّلُ أثرٌ لا نيّة."""
    d = load()
    d["يوتيوب"]["وحدات"] += COST.get(kind, 1)
    d["يوتيوب"]["عمليات"].append({"ما": kind, "متى": time.strftime("%FT%TZ", time.gmtime()),
                                  "عن": note})
    save(d)
    return d["يوتيوب"]["وحدات"]


def can(kind):
    """هل تحتمل الحصّةُ الباقيةُ هذه العملية؟ (بهامشِ أمان)"""
    d = load()
    used = d["يوتيوب"]["وحدات"]
    need = COST.get(kind, 1)
    return (used + need) <= (CAP - MARGIN), used, CAP - MARGIN - used


def remaining():
    d = load()
    return CAP - MARGIN - d["يوتيوب"]["وحدات"]
