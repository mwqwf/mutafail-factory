"""سياسة مدة قابلة للاختبار قبل استهلاك أي حصة."""

def audit_duration(minutes, meta):
    errors = []
    target = meta.get("targetMinutes", 30)
    exception = meta.get("durationException")
    if not isinstance(target, (int, float)) or not 30 <= target <= 40:
        errors.append("targetMinutes يجب أن يكون بين 30 و40")
    if minutes > 55:
        errors.append("المدّة تتجاوز 55 دقيقة")
    if exception:
        if not isinstance(exception, str) or len(exception.strip()) < 20:
            errors.append("durationException يحتاج تعليلاً بحثياً محدداً")
        if minutes < 18:
            errors.append("حتى الاستثناء لا ينزل عن 18 دقيقة")
    elif minutes < 30:
        errors.append("المدّة دون هدف 30–40 دقيقة بلا استثناء بحثي")
    return errors
