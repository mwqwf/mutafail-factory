# طلبات تعديل `tools/` (موصوفة، غير منفَّذة — `tools/` لا يُعدَّل من هذا الفرع)

## ١) شعار لكل قناة في `envpaths.logo()`
اليوم يأخذ `envpaths.logo()` `assets/logo.png` وحده، فتخرج كل أداة بشعار التاريخ. المقترح:
```python
def logo(required=True):
    ch = os.environ.get("MUTAFAIL_CHANNEL", "history")
    if ch != "history":
        cfg = os.path.join(_REPO, "ops", "channels", ch, "channel.json")
        p = os.path.join(_REPO, json.load(open(cfg, encoding="utf-8"))["logo"]["asset"])
        if os.path.exists(p): return p
        raise SystemExit("⛔ شعار القناة %s غير موجود: %s" % (ch, p))
    ...  # المسار الحاليّ كما هو
```
بعده يُحذف `ops/channels/hikayat/tools/hk_run.py` ويكفي `MUTAFAIL_CHANNEL=hikayat python3 tools/mont_hybrid.py proj`.

## ٢) لا بديل kb3d صامت للّقطة الحيّة (يخصّ القناتين)
في `mont_hybrid.py`: إن كانت اللقطة `kind == 'live'` ولا مقطع لها ولا هي في `proj/live_waivers.json` ⇒ توقّف بخطأ يسمّي اللقطات، إلا مع `ALLOW_LIVE_FALLBACK=1` الصريح (للمعاينة فقط، ويُكتب في `film.mp4.json` أنه غير صالح للنشر).

## ٣) نسبة دنيا للتحريك الحقيقيّ في `motion_plan.py lint`
قراءة `min_live_share` (افتراض 0.5 لأمر المالك 2026-11-27) وحسابها على `timeline.json`/`real_timing.json`؛ الفشل إن قلّت. يخصّ قناة التاريخ أيضاً: «إسلام خالد» مخطَّط 28٪ وظاهر نحو 5٪.

## ٤) `logocheck.py` لكل قناة
يقارن اليوم الإطار بخطّ أساس فقط؛ يُضاف تحقّق أن الشعار الظاهر هو شعار القناة (ارتباط بالأصل، كما في `parity_gate.py logo`).
