"""سياسة المدّة بحقّ المادّة — أمر المالك (العقد الأسبوعي) وحُدّث 2026-11-22.

المدّة لا يحدّدها حدّ أدنى ولا أقصى مسبق (30–40 دقيقة أُلغيت كقيد). يحكمها دسامة
المادّة الموثّقة وندرتها وجودتها. يبقى مانع وحيد للفيلم التامّ القصير جداً (< دقيقتين)
إن لم يكن ريلز/تشويقاً ولم يُعلَّل في durationNote.
"""


def audit_duration(minutes, meta):
    errors = []
    meta = meta or {}
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        errors.append("المدّة غير صالحة")
        return errors
    kind = (meta.get("kind") or meta.get("type") or "").lower()
    short_ok = kind in ("teaser", "reel", "short", "promo", "reels")
    note = meta.get("durationNote") or meta.get("durationException")
    if minutes < 2 and not short_ok:
        if not (isinstance(note, str) and len(note.strip()) >= 20):
            errors.append("فيلم أقصر من دقيقتين يحتاج تعليل مادّته في durationNote")
    return errors
