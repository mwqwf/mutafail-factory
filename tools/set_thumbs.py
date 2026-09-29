# -*- coding: utf-8 -*-
"""ضبطُ مصغّرات أفلامٍ منشورة بالواجهة البرمجية — بلا متصفّح.
يقرأ ops/thumbs_pending/<videoId>.jpg ، ويضبط كلّاً منها، ويتحقّق، ثم يحذف ما نجح من المجلّد.
⛔ لا يلمس فيلماً عليه اختبار أ/ب جارٍ؟ الواجهة لا تكشفه؛ فالقائمة تُعدّ يدوياً بلا الطوارق.

⛔ درس 2026-09-29 (عين جالوت): تسعُ مصغّراتٍ رفضها يوتيوب بـ403 «forbidden» في كلّ شوط نشرٍ منذ 09-27،
   وكلُّ محاولةٍ فاشلةٍ تُحتسب من حصّة يوتيوب (50 وحدة) فتُهدر ~450 وحدة في كلّ شوط.
   ⇒ عند 403 يُشخَّص الفيديو (المدّة، الخصوصية، حالة الرفع، سببُ الرفض كاملاً) ويُسجَّل،
     ويُخرج من الطابور إلى ops/state/thumbs_blocked/ فلا يُعاد بلا تدخّلٍ من المالك.
     وما سواه من الأخطاء (مهلة، 5xx، 429) يبقى في الطابور ليُعاد.
"""
import glob, io, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota
if len(sys.argv) < 2: sys.argv.append("proj")  # publish_youtube يقرأ sys.argv[1] عند الاستيراد
from publish_youtube import yt
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

BLOCKED = os.path.join('ops', 'state', 'thumbs_blocked')
LOG = os.path.join(BLOCKED, 'blocked.json')


def reason(e):
    try:
        err = json.loads(e.content.decode('utf-8')).get('error', {})
        return '; '.join('%s: %s' % (x.get('reason'), x.get('message')) for x in err.get('errors', [])) or err.get('message', '')
    except Exception:
        return str(e)[:300]


def describe(svc, vid):
    """ما يكشفه يوتيوب عن الفيديو ليُعرف سببُ الرفض (1 وحدة)."""
    try:
        it = svc.videos().list(part='snippet,contentDetails,status', id=vid).execute().get('items', [])
        quota.spend('videos_list', vid)
    except Exception as e:
        return {'خطأ_الوصف': str(e)[:200]}
    if not it:
        return {'موجود': False}
    v = it[0]
    return {'موجود': True, 'العنوان': v['snippet'].get('title', ''), 'المدة': v['contentDetails'].get('duration'),
            'الخصوصية': v['status'].get('privacyStatus'), 'الرفع': v['status'].get('uploadStatus'),
            'للأطفال': v['status'].get('madeForKids'), 'القناة': v['snippet'].get('channelTitle', '')}


svc = yt()
done, bad, blocked = [], [], []
log = {}
if os.path.exists(LOG):
    log = json.load(io.open(LOG, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join('ops', 'thumbs_pending', '*.jpg'))):
    vid = os.path.basename(f)[:-4]
    try:
        svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(f, mimetype='image/jpeg')).execute()
        quota.spend('thumbnail', vid)
        os.remove(f); done.append(vid); print('✅ مصغّرة', vid, flush=True)
    except HttpError as e:
        quota.spend('thumbnail', vid + ' (مرفوض)')      # المحاولة الفاشلة تُحتسب من الحصّة أيضاً
        r = reason(e)
        if e.resp.status == 403:
            info = describe(svc, vid)
            os.makedirs(BLOCKED, exist_ok=True)
            shutil.move(f, os.path.join(BLOCKED, vid + '.jpg'))
            log[vid] = {'السبب': r, 'الفيديو': info}
            blocked.append(vid)
            print('⛔ مرفوضة نهائياً — أُخرجت من الطابور:', vid, '|', r[:160], '|', json.dumps(info, ensure_ascii=False), flush=True)
        else:
            bad.append(vid); print('⚠ تُعاد لاحقاً', vid, e.resp.status, r[:160], flush=True)
    except Exception as e:
        bad.append(vid); print('⚠ تُعاد لاحقاً', vid, str(e)[:200], flush=True)
if blocked:
    with io.open(LOG, 'w', encoding='utf-8') as h:
        json.dump(log, h, ensure_ascii=False, indent=1)
print('ضُبط %d · يُعاد %d %s · أُخرج %d %s' % (len(done), len(bad), bad, len(blocked), blocked))
