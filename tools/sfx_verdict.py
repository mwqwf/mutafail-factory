# -*- coding: utf-8 -*-
"""حكمُ صوت Kling مربوطٌ ببصمة المقطع (تدقيق كوديكس MF-07، 2026-10-02).

كان `clips/<id>.ok` ملفّاً فيه كلمة الحكم وحدها، فإذا أُعيد تحريك اللقطة بالمعرّف نفسه ورث المقطعُ الجديد
حكمَ القديم ودخل صوتُه الفيلمَ بلا فحص. الآن يحمل الحكمُ بصمةَ SHA-256 للمقطع الذي سُمع، ولا يُقبل
إلا إن طابقت بصمةَ المقطع الحاليّ. والحكمُ القديم بلا بصمة يُعامل كأنه لم يكن: يُعاد فحصه، ولا يدخل صوتُه حتى ذلك.
"""
import hashlib, io, json, os


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _read(p):
    try:
        return json.load(io.open(p, encoding='utf-8'))
    except Exception:
        return None


def write(clip, verdict, clean):
    """يكتب .ok (نظيف) أو .reject، ويحذف الآخر حتى لا يبقى حكمان متعارضان."""
    keep, drop = (clip[:-4] + '.ok', clip[:-4] + '.reject') if clean else (clip[:-4] + '.reject', clip[:-4] + '.ok')
    if os.path.exists(drop):
        os.remove(drop)
    io.open(keep, 'w', encoding='utf-8').write(json.dumps({'verdict': str(verdict), 'sha256': sha(clip)}, ensure_ascii=False))


def judged(clip):
    """للمقطع الحاليّ حكمٌ مطابقٌ لبصمته (مقبولٌ أو مرفوض) ⇒ لا يُعاد فحصه."""
    s = sha(clip)
    return any((_read(clip[:-4] + ext) or {}).get('sha256') == s for ext in ('.ok', '.reject'))


def ok(clip):
    """صوتُ المقطع مقبولٌ لهذا المقطع بعينه."""
    d = _read(clip[:-4] + '.ok')
    return bool(d) and d.get('sha256') == sha(clip)
