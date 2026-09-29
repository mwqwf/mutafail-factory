# -*- coding: utf-8 -*-
"""تصحيحُ عنوان فيديو منشور بالواجهة البرمجية، مع حفظ وصفه ووسومه وتصنيفه كما هي.
الاستعمال: python tools/retitle.py ops/publish/<slug>.json   (المفتاح "retitle": {"<videoId>": "<العنوان الجديد>"})
درس عين جالوت 2026-09-29: عنوان ريلز الافتتاحية قال «أعظم معركة» والصدق «واحدة من أعظم المعارك».
لا حذف ولا إعادة رفع: يُعدَّل العنوان وحده."""
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota
cfg = json.load(io.open(sys.argv[1], encoding='utf-8')).get('retitle', {})
if not cfg:
    print('لا عناوين للتصحيح'); sys.exit(0)
sys.argv[1:] = ['proj']                     # publish_youtube يقرأ sys.argv[1] عند الاستيراد
from publish_youtube import yt
svc = yt()
for vid, title in cfg.items():
    it = svc.videos().list(part='snippet', id=vid).execute().get('items', [])
    quota.spend('read', vid)
    if not it:
        raise SystemExit('⛔ لا فيديو بهذا المعرّف: ' + vid)
    sn = it[0]['snippet']
    if sn['title'] == title:
        print('✅ العنوان صحيحٌ سلفاً', vid); continue
    body = {'id': vid, 'snippet': {k: sn[k] for k in ('title', 'description', 'categoryId', 'tags', 'defaultLanguage', 'defaultAudioLanguage') if k in sn}}
    body['snippet']['title'] = title[:100]
    svc.videos().update(part='snippet', body=body).execute()
    quota.spend('video_update', vid)
    got = svc.videos().list(part='snippet', id=vid).execute()['items'][0]['snippet']['title']
    if got != title[:100]:
        raise SystemExit('⛔ لم يثبت العنوان الجديد على %s: %s' % (vid, got))
    print('✅ صُحّح العنوان', vid, '←', got)
