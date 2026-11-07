# -*- coding: utf-8 -*-
"""أيّ فيديوهات المعارك العربية انفجرت؟ — دراسة اختيار الحلقة 2026-10-14 (طلب المالك: «أوسع عيّنةٍ ممكنة»).

١) يكتشف القنوات بالبحث (search.list بحصّته المستقلّة) عن عباراتٍ في ops/stats/outliers.json،
   ويضيف إليها قنواتٍ مسمّاةً في الملفّ نفسه.
٢) لكلّ قناة: كلّ فيديوهاتها حتى «الحدّ» (playlistItems + videos.list، وحدةٌ لكلّ نداء).
٣) لكلّ فيديو طويل: «المضاعف» = مشاهداته ÷ وسيط مشاهدات فيديوهات قناته الطويلة ⇒ يفصل أثر الموضوع
   والعنوان والمصغّرة عن حجم القناة. ورابط المصغّرة ليُرى بالعين.
الاستعمال: python tools/battle_outliers.py <out.json>   (يحتاج YT_OAUTH_JSON) — والتقرير إلى الإصدار المسوّد الخاصّ."""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota  # noqa: E402
from topic_demand import secs  # noqa: E402


def main(out: str) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    cred = Credentials(None, refresh_token=c['refresh_token'], client_id=c['client_id'], client_secret=c['client_secret'],
                       token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=cred, cache_discovery=False)
    cfg = json.load(io.open(os.path.join('ops', 'stats', 'outliers.json'), encoding='utf-8'))
    hits = {}
    for q in cfg['البحث']:
        try:
            r = yt.search().list(part='snippet', q=q, type='video', order='viewCount', relevanceLanguage='ar',
                                 maxResults=50).execute()
            quota.spend('search', 'battle_outliers')
        except Exception as e:  # الحصّة أو غيرها: نكمل بما جُمع
            print('بحث فشل:', q, str(e)[:120])
            break
        for it in r.get('items', []):
            hits.setdefault(it['snippet']['channelId'], set()).add(q)
    chans = list(dict.fromkeys(cfg.get('القنوات', []) + sorted(hits, key=lambda k: -len(hits[k]))))[:cfg.get('أقصى_القنوات', 90)]
    limit = cfg.get('الحدّ', 300)
    rep_ch, vids = {}, []
    for i in range(0, len(chans), 50):
        r = yt.channels().list(part='snippet,statistics,contentDetails', id=','.join(chans[i:i + 50])).execute()
        quota.spend('read', 'battle_outliers')
        for ch in r.get('items', []):
            rep_ch[ch['id']] = {'الاسم': ch['snippet']['title'], 'البلد': ch['snippet'].get('country'),
                                'المشتركون': int(ch['statistics'].get('subscriberCount', 0) or 0),
                                'الفيديوهات': int(ch['statistics'].get('videoCount', 0)),
                                'ظهر_في_البحث': sorted(hits.get(ch['id'], [])),
                                'uploads': ch['contentDetails']['relatedPlaylists']['uploads']}
    for cid, ch in rep_ch.items():
        ids, tok, up = [], None, ch.pop('uploads')
        try:
            while len(ids) < limit:
                r = yt.playlistItems().list(part='contentDetails', playlistId=up, maxResults=50, pageToken=tok).execute()
                quota.spend('read', 'battle_outliers')
                ids += [x['contentDetails']['videoId'] for x in r.get('items', [])]
                tok = r.get('nextPageToken')
                if not tok:
                    break
        except Exception as e:
            ch['خطأ'] = str(e)[:150]
        mine = []
        for j in range(0, len(ids), 50):
            rr = yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(ids[j:j + 50])).execute()
            quota.spend('read', 'battle_outliers')
            for v in rr.get('items', []):
                s, st = v['snippet'], v.get('statistics', {})
                L = secs(v['contentDetails'].get('duration'))
                th = s.get('thumbnails', {})
                mine.append({'id': v['id'], 'القناة': cid, 'العنوان': s['title'], 'النشر': s['publishedAt'][:10],
                             'الطول_ث': L, 'المشاهدات': int(st.get('viewCount', 0)),
                             'الإعجابات': int(st.get('likeCount', 0) or 0), 'التعليقات': int(st.get('commentCount', 0) or 0),
                             'المصغّرة': (th.get('maxres') or th.get('high') or th.get('medium') or {}).get('url')})
        longs = [x['المشاهدات'] for x in mine if x['الطول_ث'] > 180]
        med = statistics.median(longs) if longs else 0
        ch['وسيط_الطويل'] = int(med)
        ch['عدد_الطويل'] = len(longs)
        for x in mine:
            x['المضاعف'] = round(x['المشاهدات'] / med, 2) if med and x['الطول_ث'] > 180 else None
        vids += mine
    rep = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'البحث': cfg['البحث'],
           'القنوات': {k: {kk: vv for kk, vv in v.items() if kk != 'uploads'} for k, v in rep_ch.items()},
           'الفيديوهات': vids}
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    json.dump(rep, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('قنوات:', len(rep_ch), '| فيديوهات:', len(vids))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/battle_outliers.json')
