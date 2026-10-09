# -*- coding: utf-8 -*-
"""تصحيحُ رابط الفيلم في وصف ريلزاتٍ منشورة بعد استبدال الفيلم بنسخةٍ مصحّحة (حديقة الموت 2026-10-09).
الاستعمال: python tools/relink.py ops/publish/<slug>.json
  المفتاح "relink": {"old": "<معرّف الفيلم القديم>", "new": "<معرّف الجديد>", "videos": ["<معرّف ريلز>", ...]}
يُستبدل المعرّف القديم بالجديد في الوصف وحده، ويبقى العنوان والوسوم والتصنيف كما هي. لا حذف ولا إعادة رفع."""
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota
cfg = json.load(io.open(sys.argv[1], encoding='utf-8')).get('relink') or {}
if not cfg:
    print('لا روابط للتصحيح'); sys.exit(0)
old, new = cfg['old'], cfg['new']
assert re.fullmatch(r'[A-Za-z0-9_-]{11}', old) and re.fullmatch(r'[A-Za-z0-9_-]{11}', new)
sys.argv[1:] = ['proj']                     # publish_youtube يقرأ sys.argv[1] عند الاستيراد
from publish_youtube import yt
svc = yt()
for vid in cfg.get('videos', []):
    it = svc.videos().list(part='snippet', id=vid).execute().get('items', [])
    quota.spend('read', vid)
    if not it:
        raise SystemExit('⛔ لا فيديو بهذا المعرّف: ' + vid)
    sn = it[0]['snippet']
    if old not in sn.get('description', ''):
        print('✅ الوصف لا يحمل الرابط القديم', vid); continue
    body = {'id': vid, 'snippet': {k: sn[k] for k in ('title', 'description', 'categoryId', 'tags', 'defaultLanguage', 'defaultAudioLanguage') if k in sn}}
    body['snippet']['description'] = sn['description'].replace(old, new)
    svc.videos().update(part='snippet', body=body).execute()
    quota.spend('video_update', vid)
    print('✅ صُحّح رابط الفيلم في وصف', vid, ':', old, '←', new)
