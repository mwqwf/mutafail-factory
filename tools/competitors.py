# -*- coding: utf-8 -*-
"""لماذا تحتفظ قنواتٌ أقلّ إتقاناً بالمشاهد أكثر منّا؟ — سؤال المالك 2026-10-05.

لأعلى الفيديوهات الطويلة المنافسة في ops/stats/competitors.json (من تقرير الطلب الخارجيّ): العنوان والوصف والوسوم
والطول والإعجابات والتعليقات (رضا المشاهد مقيساً بنسبتها إلى المشاهدات)، ثم قنواتها (المشتركون والمشاهدات وعدد الفيديوهات)،
وآخر 25 فيديو لكلّ قناة (وسيط المشاهدات والطول ووتيرة النشر) ⇒ ما الذي يصنعه الناجحون ولا نصنعه.
⛔ بلا بحث: videos.list وchannels.list وplaylistItems.list وحدةٌ لكلّ نداء، وتُسجَّل في دفتر الحصص.
الاستعمال: python tools/competitors.py <out.json>   (يحتاج YT_OAUTH_JSON) — والتقرير إلى الإصدار المسوّد الخاصّ."""
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
    ids = json.load(io.open(os.path.join('ops', 'stats', 'competitors.json'), encoding='utf-8'))['الفيديوهات']
    vids, chans = [], {}
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(ids[i:i + 50])).execute()
        quota.spend('read', 'competitors')
        for v in r.get('items', []):
            s, st = v['snippet'], v.get('statistics', {})
            views = int(st.get('viewCount', 0))
            vids.append({'id': v['id'], 'العنوان': s['title'], 'القناة': s['channelTitle'], 'channelId': s['channelId'],
                         'النشر': s['publishedAt'][:10], 'الطول_د': round(secs(v['contentDetails'].get('duration')) / 60, 1),
                         'المشاهدات': views, 'الإعجابات': int(st.get('likeCount', 0)), 'التعليقات': int(st.get('commentCount', 0)),
                         'إعجاب_لكلّ_ألف': round(1000 * int(st.get('likeCount', 0)) / views, 1) if views else None,
                         'تعليق_لكلّ_ألف': round(1000 * int(st.get('commentCount', 0)) / views, 2) if views else None,
                         'الوصف': (s.get('description') or '')[:700], 'الوسوم': (s.get('tags') or [])[:15],
                         'اللغة': s.get('defaultAudioLanguage') or s.get('defaultLanguage')})
            chans.setdefault(s['channelId'], {})
    cids = list(chans)
    for i in range(0, len(cids), 50):
        r = yt.channels().list(part='snippet,statistics,contentDetails', id=','.join(cids[i:i + 50])).execute()
        quota.spend('read', 'competitors')
        for ch in r.get('items', []):
            st = ch.get('statistics', {})
            chans[ch['id']] = {'الاسم': ch['snippet']['title'], 'البلد': ch['snippet'].get('country'),
                               'المشتركون': int(st.get('subscriberCount', 0) or 0), 'المشاهدات': int(st.get('viewCount', 0)),
                               'الفيديوهات': int(st.get('videoCount', 0)), 'الإنشاء': ch['snippet'].get('publishedAt', '')[:10],
                               'الوصف': (ch['snippet'].get('description') or '')[:400],
                               'uploads': ch['contentDetails']['relatedPlaylists']['uploads']}
    today = dt.date.today()
    for cid, ch in chans.items():
        if not ch.get('uploads'):
            continue
        try:
            r = yt.playlistItems().list(part='contentDetails', playlistId=ch['uploads'], maxResults=25).execute()
            quota.spend('read', 'competitors')
            vv = [x['contentDetails']['videoId'] for x in r.get('items', [])]
            rr = yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(vv)).execute().get('items', []) if vv else []
            quota.spend('read', 'competitors')
            rec = [{'العنوان': x['snippet']['title'][:90], 'النشر': x['snippet']['publishedAt'][:10],
                    'الطول_د': round(secs(x['contentDetails'].get('duration')) / 60, 1),
                    'المشاهدات': int(x.get('statistics', {}).get('viewCount', 0))} for x in rr]
            longs = [x for x in rec if x['الطول_د'] > 3]
            dates = sorted(dt.date.fromisoformat(x['النشر']) for x in rec)
            ch['آخر_25'] = {'وسيط_المشاهدات': int(statistics.median([x['المشاهدات'] for x in rec])) if rec else 0,
                            'وسيط_الطويل': int(statistics.median([x['المشاهدات'] for x in longs])) if longs else 0,
                            'وسيط_الطول_د': statistics.median([x['الطول_د'] for x in rec]) if rec else 0,
                            'أيام_بين_النشر': round((dates[-1] - dates[0]).days / max(1, len(dates) - 1), 1) if len(dates) > 1 else None,
                            'منذ_آخر_نشر': (today - dates[-1]).days if dates else None, 'عيّنة': rec[:12]}
        except Exception as e:
            ch['آخر_25'] = {'خطأ': str(e)[:150]}
    rep = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'الفيديوهات': vids,
           'القنوات': {k: {kk: vv for kk, vv in v.items() if kk != 'uploads'} for k, v in chans.items()}}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(rep, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('فيديوهات:', len(vids), '| قنوات:', len(chans))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/competitors.json')
