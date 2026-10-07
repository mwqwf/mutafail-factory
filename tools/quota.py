# -*- coding: utf-8 -*-
"""دفترُ الحصص — لا تُهدر وحدةٌ، ولا يُبدأ عملٌ لا تحتمله الحصّةُ الباقية.

⭐ قاعدةُ المالك (2026-09-15): «نفعل أقصى ما يمكن، ولا نضيّع ولو مليمًا واحدًا،
   وما تؤخّره الحصّةُ يُجدوَل لأوّل تجدّدٍ ويُنفَّذ تلقائيًّا».

⛔ وحصّتا يوتيوب وجيميناي مختلفتان في كلّ شيء:
   · يوتيوب: ثلاث حصصٍ يوميّة للمشروع، تتجدّد كلّها منتصفَ ليل المحيط الهادئ
     (‏نحو السابعة صباحاً بتوقيت غرينتش صيفاً):
       - الرفع (videos.insert) في حصّةٍ مستقلّة: مئة رفعةٍ في اليوم افتراضاً.
       - البحث (search.list) في حصّةٍ مستقلّة: مئة بحثٍ في اليوم افتراضاً.
       - وسائر الطرق عشرة آلاف وحدة: المصغّرة والتحديث والإضافة إلى قائمة 50، والقراءة 1.
   · جيميناي: عشرُ توليداتٍ لكلّ مشروعٍ ولكلّ نموذج، وتتجدّد الثامنةَ صباحاً
     بتوقيت المالك (‏`ops/state/quota.json`).

⛔⛔ درسٌ مقيس 2026-10-07 (ريلز الأرك r1): كان الدفتر يحسب الرفع 1600 وحدةٍ من العشرة آلاف،
   وهو تسعيرٌ نسخته الواجهة مرّتين، فأجّل رفعاً كانت حصّته تتّسع لخمسٍ وتسعين رفعة.
   وسجلّ مراجعات الواجهة (revision_history):
     - 2025-12-04: نزلت كلفة الرفع من نحو 1600 وحدة إلى نحو 100.
     - 2026-06-01: صار videos.insert وsearch.list كلٌّ في حصّته، وسائر الطرق في الحصّة القديمة.
   ⇒ تُعاد الحصص الثلاث من سجلّ «عمليات» عند كلّ قراءة، فيصحّ يومٌ كُتب بالتسعير القديم.
   ⇒ والحكم الأخير للخادم: الدفتر لا يرى ما أنفقته أدواتٌ لا تكتب فيه.
"""
import io, json, os, time

STATE = os.path.join("ops", "state", "quota_usage.json")
CAP = 10000          # سقفُ يوتيوب اليوميّ للمشروع لسائر الطرق
MARGIN = 400         # هامشٌ يُترك لعملياتٍ صغيرةٍ لا تُحصى
COST = {"upload": 1, "thumbnail": 50, "playlist_insert": 50,
        "video_update": 50, "read": 1,
        "search": 1}   # search.list — بحث الطلب الخارجيّ (tools/topic_demand.py، 2026-10-05)
# ⭐ الحصّتان المستقلّتان (منذ 2026-06-01): عددُ النداءات في اليوم، ومفتاحُ عدّادها في الدفتر
OWN = {"upload": {"سقف": 100, "هامش": 5, "مفتاح": "رفعات"},
       "search": {"سقف": 100, "هامش": 5, "مفتاح": "بحث"}}


def _today(now=None):
    # ⛔ يومُ حصّة يوتيوب يبدأ عند تجدّدها: منتصف ليل المحيط الهادئ بتوقيته الصيفيّ والشتويّ
    #    (كانت إزاحةً ثابتة −7 س فيفتح الدفترُ يوماً جديداً شتاءً قبل التجدّد بساعة — تدقيق كوديكس MF-14)
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    t = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    return t.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")


def load():
    try:
        with io.open(STATE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    y = d.get("يوتيوب", {})
    if y.get("اليوم") != _today():
        y = {"اليوم": _today(), "عمليات": []}
    ops = y.setdefault("عمليات", [])
    # ⭐ العدّادات تُعاد من السجلّ لا من رقمٍ مخزون، فيصحّ يومٌ كُتب بتسعير الرفع القديم (1600)
    y["وحدات"] = sum(COST.get(o.get("ما"), 1) for o in ops if o.get("ما") not in OWN)
    for kind, o in OWN.items():
        y[o["مفتاح"]] = sum(1 for x in ops if x.get("ما") == kind)
    d["يوتيوب"] = y
    return d


def save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with io.open(STATE, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1))


def spend(kind, note=""):
    """يُسجَّل بعد كلّ عمليةٍ واقعة — لا قبلها، فالمسجَّلُ أثرٌ لا نيّة."""
    d = load()
    y = d["يوتيوب"]
    y["عمليات"].append({"ما": kind, "متى": time.strftime("%FT%TZ", time.gmtime()), "عن": note})
    if kind in OWN:
        y[OWN[kind]["مفتاح"]] += 1
    else:
        y["وحدات"] += COST.get(kind, 1)
    save(d)
    return y["وحدات"]


def remaining(kind=None):
    """ما بقي بعد الهامش: نداءاتٌ في حصّةٍ مستقلّة (الرفع والبحث)، أو وحداتٌ من الحصّة العامّة."""
    y = load()["يوتيوب"]
    if kind in OWN:
        o = OWN[kind]
        return o["سقف"] - o["هامش"] - y[o["مفتاح"]]
    return CAP - MARGIN - y["وحدات"]


def can(kind):
    """هل تحتمل الحصّةُ الباقيةُ هذه العملية؟ (بهامشِ أمان) ⇒ (نعم أو لا، المستهلَك، المتبقّي)"""
    y = load()["يوتيوب"]
    if kind in OWN:
        used = y[OWN[kind]["مفتاح"]]
        left = remaining(kind)
        return left >= 1, used, left
    used = y["وحدات"]
    return (used + COST.get(kind, 1)) <= (CAP - MARGIN), used, CAP - MARGIN - used
