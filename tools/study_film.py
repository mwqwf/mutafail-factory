# -*- coding: utf-8 -*-
"""دراسة تشخيصيّة لفيلمٍ بعد نشره مقابل أقرانه (طلب المالك 2026-11-11: «لماذا لم ينفجر الكنانة كما انفجر جَرَجة؟»).

يقرأ: قائمة آخر المرفوعات بتواريخها، ولكلّ فيلمٍ سلسلته اليوميّة ومصادره يوماً بيوم وحالة الاشتراك
ومنحنى الاحتفاظ وتفصيل المصادر (المقترحات والريلزات وشاشة النهاية) والبلدان، وسلسلة القناة اليوميّة بالمصدر.
⛔ المخرج تحليلاتٌ خاصّة ⇒ يُرفع إلى الإصدار المسوّد channel-stats ولا يُودَع في المستودع العامّ.
الاستعمال: python tools/study_film.py <out.json>   (يحتاج YT_OAUTH_JSON)"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

START = '2026-09-25'
FILMS = {'الكنانة': '7n_bLN8Bkmk', 'جرجة': 'ZSI2NvQp8yc', 'ذو_القرنين': 'BEB_BNwleBY', 'النمرود': 'SztW3evU0uI',
         'ذات_العيون': 'ilFEoE-JGa4', 'أبرهة': 'XRyU7Y5-Krc', 'أليس': 'Ah2VnLPpMU0', 'الأرك': '_OK7JEf9r4s'}
REELS = {'ك_r1': '68INvkCBb4I', 'ك_r2': 'vPvn9YQwU9c', 'ك_r3': '0M35VVbbbQo'}
DETAIL = ['RELATED_VIDEO', 'SHORTS', 'END_SCREEN', 'YT_SEARCH', 'YT_CHANNEL', 'EXT_URL', 'PLAYLIST', 'SUBSCRIBER',
          'NOTIFICATION', 'YT_OTHER_PAGE', 'VIDEO_REMIXES', 'SHORTS_CONTENT_LINKS', 'HASHTAGS', 'CAMPAIGN_CARD']


def main(out: str) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    cred = Credentials(None, refresh_token=c['refresh_token'], client_id=c['client_id'], client_secret=c['client_secret'],
                       token_uri='https://oauth2.googleapis.com/token')
    ya = build('youtubeAnalytics', 'v2', credentials=cred, cache_discovery=False)
    yt = build('youtube', 'v3', credentials=cred, cache_discovery=False)
    today = dt.date.today().isoformat()
    res: dict = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'أخطاء': {}}

    def q(name, **kw):
        kw.setdefault('endDate', today)
        kw.setdefault('startDate', START)
        try:
            r = ya.reports().query(ids='channel==MINE', **kw).execute()
            cols = [h['name'] for h in r.get('columnHeaders', [])]
            res[name] = [dict(zip(cols, row)) for row in r.get('rows', [])]
        except Exception as e:  # كلُّ سؤالٍ مستقلّ: رفضُ واحدٍ لا يُسقط الباقي
            res['أخطاء'][name] = str(e)[:300]

    # آخر 100 مرفوع بتاريخه وحالته وطوله وأرقامه العامّة
    try:
        ch = yt.channels().list(part='contentDetails,statistics', mine=True).execute()['items'][0]
        res['القناة'] = ch['statistics']
        up = ch['contentDetails']['relatedPlaylists']['uploads']
        ids, tok = [], None
        for _ in range(2):
            r = yt.playlistItems().list(part='contentDetails', playlistId=up, maxResults=50, pageToken=tok).execute()
            ids += [i['contentDetails']['videoId'] for i in r['items']]
            tok = r.get('nextPageToken')
            if not tok:
                break
        vids = []
        for i in range(0, len(ids), 50):
            r = yt.videos().list(part='snippet,statistics,status,contentDetails', id=','.join(ids[i:i + 50])).execute()
            for v in r['items']:
                vids.append({'id': v['id'], 'العنوان': v['snippet']['title'], 'نُشر': v['snippet']['publishedAt'],
                             'الخصوصيّة': v['status']['privacyStatus'], 'publishAt': v['status'].get('publishAt'),
                             'الطول': v['contentDetails']['duration'], **v.get('statistics', {})})
        res['المرفوعات'] = vids
    except Exception as e:
        res['أخطاء']['المرفوعات'] = str(e)[:300]

    q('يومي_القناة_بالمصدر', dimensions='day,insightTrafficSourceType', metrics='views,estimatedMinutesWatched', sort='day')
    q('يومي_القناة_بالنوع', dimensions='day,creatorContentType', metrics='views,estimatedMinutesWatched,subscribersGained', sort='day')
    q('يومي_القناة_بالفيديو', startDate='2026-10-28', dimensions='day,video', metrics='views,estimatedMinutesWatched',
      sort='day', maxResults=1000, filters='video==' + ','.join(list(FILMS.values()) + list(REELS.values())))
    for n, v in {**FILMS, **REELS}.items():
        f = 'video==' + v
        q(f'{n}_يومي', dimensions='day', filters=f, sort='day',
          metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,shares,comments')
        q(f'{n}_يومي_المصادر', dimensions='day,insightTrafficSourceType', filters=f, sort='day',
          metrics='views,estimatedMinutesWatched')
        q(f'{n}_المصادر', dimensions='insightTrafficSourceType', filters=f,
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'{n}_حالة_الاشتراك', dimensions='subscribedStatus', filters=f,
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'{n}_الاحتفاظ', dimensions='elapsedVideoTimeRatio', filters=f,
          metrics='audienceWatchRatio,relativeRetentionPerformance')
        q(f'{n}_ظهور_يومي', dimensions='day', filters=f, sort='day',
          metrics='videoThumbnailImpressions,videoThumbnailImpressionsClickRate')
        q(f'{n}_ظهور', filters=f, metrics='videoThumbnailImpressions,videoThumbnailImpressionsClickRate')
        q(f'{n}_بطاقات', filters=f, metrics='cardImpressions,cardClicks,cardClickRate,cardTeaserImpressions,cardTeaserClicks')
        q(f'{n}_البلدان', dimensions='country', filters=f, sort='-views', maxResults=12,
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'{n}_الأجهزة', dimensions='deviceType', filters=f, metrics='views,averageViewDuration')
        for t in DETAIL:
            q(f'{n}_تفصيل_{t}', dimensions='insightTrafficSourceDetail', sort='-views', maxResults=25,
              filters=f + ';insightTrafficSourceType==' + t, metrics='views,estimatedMinutesWatched')
    # الأيّام الأربعة الأولى لكلّ فيلمٍ معزولةً (مقارنة عادلة)
    pub = {v['id']: v['نُشر'][:10] for v in res.get('المرفوعات', [])}
    for n, v in FILMS.items():
        if v in pub:
            s = dt.date.fromisoformat(pub[v])
            for k in (1, 3, 7):
                e = min(s + dt.timedelta(days=k), dt.date.today()).isoformat()
                q(f'{n}_أوّل_{k}ي_المصادر', startDate=s.isoformat(), endDate=e, dimensions='insightTrafficSourceType',
                  filters='video==' + v, metrics='views,estimatedMinutesWatched,averageViewDuration')
                q(f'{n}_أوّل_{k}ي', startDate=s.isoformat(), endDate=e, filters='video==' + v,
                  metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('أسئلة ناجحة:', len([k for k in res if k not in ('تاريخ', 'أخطاء')]), '| مرفوضة:', len(res['أخطاء']))


if __name__ == '__main__':
    main(sys.argv[1])
