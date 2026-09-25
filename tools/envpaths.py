# -*- coding: utf-8 -*-
"""مواضعُ الأدوات والخطوط — تعمل على وندوز المالك وعلى عدّاء لينكس معاً.

⛔ الدرس المقيس (2026-09-14): كلُّ أدوات المونتاج كانت تُثبّت مسارَ `ffmpeg.exe`
تحت `Desktop\\claude-media`، فما كانت لتعمل في السحاب أبداً. وهذا الملفُّ يحلّها
مرّةً واحدةً للجميع: يُفضَّل مسارُ وندوز إن وُجد، وإلا أُخذ من `PATH`.
"""
import os
import shutil

_WINBIN = os.path.expanduser(
    "~/Desktop/claude-media/ffbin/ffmpeg-9.0.1-essentials_build/bin")
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tool(name):
    win = os.path.join(_WINBIN, name + ".exe")
    if os.path.exists(win):
        return win
    found = shutil.which(name)
    return found if found else name


FF = _tool("ffmpeg")
FP = _tool("ffprobe")


def font(bold=True):
    """خطٌّ عربيّ للبطاقات — أميري أوّلاً، ثمّ ما توفّر في النظام."""
    name = "Amiri-Bold.ttf" if bold else "Amiri-Regular.ttf"
    cands = [
        os.path.join(os.path.expanduser("~"), "Downloads", name),
        os.path.join(_REPO, "assets", name),
        "/usr/share/fonts/truetype/hosny-amiri/" + name,
        "/usr/share/fonts/truetype/amiri/" + name,
        # بدائلُ النظام — تُستعمل إن غاب أميري، ولا يتعطّل التصيير
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-%s.ttf" % ("Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    raise SystemExit("⛔ لم يوجد خطٌّ عربيّ — جرّب: apt-get install fonts-hosny-amiri")


def logo(required=True):
    """شعارُ القناة. ⛔⛔ أمرُ المالك 2026-09-15: «لا يخرج مخرَجٌ بلا شعار تحت أيّ ظرف».

    فكانت الدالّةُ تردّ None عند غيابه، والأدواتُ تتخطّاه صامتةً فيخرج الفيلمُ
    والريلزُ بلا هويّة ولا يعلم أحد. ⇒ الغيابُ صار **سقوطاً صريحاً** لا صمتاً،
    و`required=False` لا تُستعمل إلا في فحصٍ يريد معرفةَ الوجود لا الرسم.
    """
    # الأصل المعتمد في المستودع يسبق النسخ التاريخية على جهاز المالك.
    for c in (os.path.join(_REPO, "assets", "logo.png"),
              os.path.join(os.path.expanduser("~"), "Desktop", "claude-media", "muw", "logo.png")):
        if os.path.exists(c):
            return c
    if required:
        raise SystemExit(
            "⛔⛔ شعارُ القناة غيرُ موجود (assets/logo.png) — ولا يخرج مخرَجٌ بلا شعار.\n"
            "    يُجلب بدفع ملفٍّ في ops/logo/ فيشتغل logo.yml ويجلبه من واجهة يوتيوب.")
    return None


# ══════════ العربيّة على PIL — ⛔ الدرسُ المقيس (2026-09-14) ══════════
# عناوينُ الريلزات خرجت **مقلوبة**. السببُ ليس في النصّ ولا في الخطّ، بل في
# اختلافِ محرّك التخطيط بين جهاز المالك والعدّاء السحابيّ:
#   • وندوز: Pillow بلا RAQM ⇒ يلزم قلبُ النصّ يدويًّا (reshape + bidi).
#   • لينكس (عجلةُ pip): Pillow **مع RAQM** ⇒ يقلب النصّ بنفسه.
# فإذا سُلّم إليه نصٌّ مقلوبٌ سلفًا قَلَبه ثانيةً ⇒ **قلبٌ مزدوج** = عنوانٌ معكوس.
# ⇒ الحلُّ الواحدُ للبيئتين: نقلب يدويًّا **ونُلزم** المحرّكَ البسيط BASIC،
#   فلا يقلب أحدٌ بعدنا. ⛔ لا تستدعِ ImageFont.truetype مباشرةً في أدوات
#   البطاقات — استعمل arfont() وar() من هنا، وفحصُ tools/bidicheck.py يحرس هذا.

def ar(s):
    """النصُّ العربيُّ مهيّأً للرسم بمحرّك BASIC (تشكيلُ الحروف ثمّ ترتيبٌ بصريّ)."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(s))


def arfont(size, bold=True, path=None):
    """خطُّ البطاقات بمحرّك تخطيطٍ بسيطٍ إلزامًا — يمنع القلبَ المزدوج."""
    from PIL import ImageFont
    return ImageFont.truetype(path or font(bold=bold), size,
                              layout_engine=ImageFont.Layout.BASIC)
