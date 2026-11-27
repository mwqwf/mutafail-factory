"""يبني proj/meta.json وproj/publish.json وproj/الفصول.txt من publish/package.md (لا رفع ولا نشر)."""
import json, os, re
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(D, 'proj')
pk = open(os.path.join(D, 'publish', 'package.md'), encoding='utf-8').read()
desc = pk.split('## الوصف')[1].split('\n---\n')[1].strip()
title = re.search(r'\*\*أ \(الافتراضي\):\*\* (.+)', pk).group(1).strip()
title_b = re.search(r'\*\*ب \(Test & Compare\):\*\* (.+)', pk).group(1).strip()
tags = [t.strip() for t in pk.split('## الوسوم')[1].strip().split('\n')[0].split(',')]
chap = '\n'.join(l for l in desc.split('\n') if re.match(r'^\d\d:\d\d ', l))
pub = json.load(open(os.path.join(P, 'publish.json'), encoding='utf-8')) if os.path.exists(os.path.join(P, 'publish.json')) else {}
TAGS_R = ['خالد بن الوليد', 'سيف الله', 'قصص الصحابة', 'السيرة النبوية', 'المتفائل']
rd = lambda t: 'من قصة إسلام خالد بن الوليد — «سيف الله».\nالقصة كاملة: {FILM_URL}\n\n#خالد_بن_الوليد #سيف_الله #قصص_الصحابة'
pub.update(live_open=False,  # أمر المالك 2026-11-27: لا استعارة مقطعٍ من لقطةٍ أخرى (مشهدٌ في غير موضعه خطأ معنى)
           slug='islam-khalid', series='سيف الله', publicNow=False,  # مؤقتاً: لا نشر قبل قرار المالك (publish_preflight يشترط true)
           publishAt='2026-11-27T17:00:00Z',
           film={'title': title, 'title_b': title_b, 'description': desc, 'tags': tags, 'categoryId': '27',
                 'card': {'at': '3:54', 'video': 'W1UtJ-W3YqI'}, 'endscreen': '8:39-8:58'},
           reels=[{'file': 'r1.mp4', 'title': '«لو حملنا عليهم!» لماذا تراجع خالد بن الوليد؟', 'description': rd(1), 'tags': TAGS_R, 'from': '0:00-0:50'},
                  {'file': 'r2.mp4', 'title': 'كتابٌ غيّر خالد بن الوليد: «ما مثله جهل الإسلام»', 'description': rd(2), 'tags': TAGS_R, 'from': '1:59-2:49'}])
json.dump(pub, open(os.path.join(P, 'publish.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'slug': 'islam-khalid', 'title': title, 'series': 'سيف الله'}, open(os.path.join(P, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(P, 'الفصول.txt'), 'w', encoding='utf-8').write(chap + '\n')
print(title, '|', len(desc), 'حرفاً |', len(tags), 'وسماً |', chap.count('\n') + 1, 'فصول')
