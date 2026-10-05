# -*- coding: utf-8 -*-
"""تغيير خصوصية فيديو منشور بالواجهة البرمجيّة (عامّ ⇄ غير مدرج)، بلا حذفٍ ولا لمسٍ لغير الخصوصية.

أمر المالك 2026-10-05: المقطعان «3 أوت 2026» رُفعا عمداً، أحدهما لتطبيق منبر والآخر لمصحفك، ومرتبطان بالمتجر:
«اجعلهما غير مدرجين إن كانت سياسة المتجر تسمح بذلك دون حذفهما».
- سياسة Google Play في فيديو صفحة التطبيق: عامٌّ أو غير مدرج، لا خاصّ، وقابلٌ للتضمين، بلا تحقيقٍ للدخل، وبلا قيد عمر.
  ⇒ «غير مدرج» جائز، و«خاصّ» ممنوع هنا. والأداة ترفض «خاصّ» لكلّ فيديو موسومٍ بالمتجر.
- يُقرأ وضع الفيديو كاملاً أوّلاً. ثم يُرسَل في التحديث كلُّ حقلٍ قابلٍ للكتابة كما هو، وتتغيّر الخصوصية وحدها.
  (part=status يعيد ما لم يُرسل إلى افتراضه، وقد يُطفئ التضمين الذي يشترطه المتجر.)
- ثم يُقرأ مرّةً ثانية للتحقّق: الخصوصية الجديدة، والتضمين باقٍ.
- ⛔ لا حذف بحال (أمر المالك الدائم).

الطلب: ops/privacy_pending/<videoId>.json = {"privacy": "unlisted", "store": true, "سبب": "…"}.
ما نجح يُنقل إلى ops/state/privacy_done/، وما رُفض يبقى في الطابور مع سببه.
"""
import glob, io, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PENDING = os.path.join('ops', 'privacy_pending')
DONE = os.path.join('ops', 'state', 'privacy_done')
WRITABLE = ('embeddable', 'license', 'publicStatsViewable', 'selfDeclaredMadeForKids', 'containsSyntheticMedia')
ALLOWED = {'public', 'unlisted', 'private'}


def plan(status: dict, req: dict) -> tuple[dict | None, str]:
    """جسم status للتحديث من الوضع الحاليّ والطلب، أو (None، السبب) إن لم يلزم تحديثٌ أو لم يجز."""
    want = req.get('privacy')
    if want not in ALLOWED:
        return None, 'خصوصيةٌ غير معروفة: %r' % want
    if req.get('store') and want == 'private':
        return None, 'فيديو صفحةٍ في المتجر لا يكون خاصّاً (سياسة Google Play: عامٌّ أو غير مدرج)'
    if status.get('privacyStatus') == want and (not req.get('store') or status.get('embeddable', True)):
        return None, 'على الحال المطلوبة أصلاً'
    body = {k: status[k] for k in WRITABLE if k in status}
    body['privacyStatus'] = want
    if req.get('store'):
        body['embeddable'] = True               # شرط المتجر: يُضمَّن في صفحة التطبيق
    return body, ''


def run(svc, quota=None) -> int:
    bad = 0
    os.makedirs(DONE, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(PENDING, '*.json'))):
        vid = os.path.splitext(os.path.basename(f))[0]
        req = json.load(io.open(f, encoding='utf-8'))
        items = svc.videos().list(part='status,snippet', id=vid).execute().get('items', [])
        quota and quota.spend('read', vid)
        if not items:
            print('⛔ %s: لا يوجد في القناة' % vid); bad += 1; continue
        st = items[0]['status']
        body, why = plan(st, req)
        if body is None:
            print('%s %s: %s' % ('✅' if why.startswith('على الحال') else '⛔', vid, why))
            if not why.startswith('على الحال'):
                bad += 1; continue
        else:
            svc.videos().update(part='status', body={'id': vid, 'status': body}).execute()
            quota and quota.spend('video_update', vid)
            st = svc.videos().list(part='status', id=vid).execute()['items'][0]['status']
            quota and quota.spend('read', vid)
            ok = st.get('privacyStatus') == req['privacy'] and (not req.get('store') or st.get('embeddable'))
            print('%s %s: %s، التضمين %s' % ('✅' if ok else '⛔', vid, st.get('privacyStatus'), st.get('embeddable')))
            if not ok:
                bad += 1; continue
        rec = dict(req, النتيجة=st.get('privacyStatus'), التضمين=st.get('embeddable'), العنوان=items[0]['snippet'].get('title'))
        io.open(os.path.join(DONE, vid + '.json'), 'w', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False, indent=1))
        os.remove(f)
    return 1 if bad else 0


if __name__ == '__main__':
    import quota as q
    if len(sys.argv) < 2:
        sys.argv.append('proj')                 # publish_youtube يقرأ sys.argv[1] عند الاستيراد
    from publish_youtube import yt
    sys.exit(run(yt(), q))
