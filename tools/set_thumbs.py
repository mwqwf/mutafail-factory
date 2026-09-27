# -*- coding: utf-8 -*-
"""ضبطُ مصغّرات أفلامٍ منشورة بالواجهة البرمجية — بلا متصفّح.
يقرأ ops/thumbs_pending/<videoId>.jpg ، ويضبط كلّاً منها، ويتحقّق، ثم يحذف ما نجح من المجلّد.
⛔ لا يلمس فيلماً عليه اختبار أ/ب جارٍ؟ الواجهة لا تكشفه؛ فالقائمة تُعدّ يدوياً بلا الطوارق."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota
if len(sys.argv) < 2: sys.argv.append("proj")  # publish_youtube يقرأ sys.argv[1] عند الاستيراد
from publish_youtube import yt
from googleapiclient.http import MediaFileUpload

svc = yt()
done, bad = [], []
for f in sorted(glob.glob(os.path.join('ops', 'thumbs_pending', '*.jpg'))):
    vid = os.path.basename(f)[:-4]
    try:
        svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(f, mimetype='image/jpeg')).execute()
        quota.spend('thumbnail', vid)
        os.remove(f); done.append(vid); print('✅ مصغّرة', vid, flush=True)
    except Exception as e:
        bad.append(vid); print('⛔', vid, str(e)[:200], flush=True)
print('ضُبط %d · تعذّر %d %s' % (len(done), len(bad), bad))
