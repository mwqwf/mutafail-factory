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


def logo():
    """شعارُ القناة إن وُجد، وإلا فـNone — والبطاقةُ تُرسم بلا شعارٍ ولا تتعطّل."""
    for c in (os.path.join(os.path.expanduser("~"), "Desktop", "claude-media", "muw", "logo.png"),
              os.path.join(_REPO, "assets", "logo.png")):
        if os.path.exists(c):
            return c
    return None
