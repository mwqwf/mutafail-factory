# -*- coding: utf-8 -*-
"""دراسة نافذتين متماثلتين (طلب المالك 2026-11-06: «ادرس ما لم يشمله تقرير الـ28 يوماً»).

يقرأ من واجهة التحليلات ما لا يقرؤه channel_stats.py: السلسلة اليومية للقناة (المشاهدات والدقائق والمشتركون)،
ومصادر الزيارات يوماً بيوم، وتوزيع كلّ نافذةٍ بالفيديو والمصدر ونوع المحتوى والبلد وحالة الاشتراك،
ومن أين جاء المشتركون، ومصادر كلّ فيلمٍ يوماً بيوم في أسبوعيه الأوّلين.
⛔ المخرج تحليلاتٌ خاصّة ⇒ يُرفع إلى الإصدار المسوّد channel-stats، ولا يُودَع في المستودع العامّ.
الاستعمال: python tools/study_window.py <out.json>   (يحتاج YT_OAUTH_JSON)"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

# النافذتان: التقرير (9 أكتوبر–5 نوفمبر) والسابقة المماثلة (11 سبتمبر–8 أكتوبر)
WIN = {'السابقة': ('2026-09-11', '2026-10-08'), 'الحالية': ('2026-10-09', '2026-11-05')}
SERIES_START = '2026-08-15'
FILMS = ['_OK7JEf9r4s', 'Ah2VnLPpMU0', 'ZSI2NvQp8yc', 'AQW7phGZJUE', 'tmCR_aieXeA', 'XRyU7Y5-Krc', 'SztW3evU0uI',
         'ilFEoE-JGa4', 'BEB_BNwleBY', 'l4trFSrZBUo', 'xz6vw0XRBIY', 'al2AeXMgZ-Q', 'eiX_YWNXTOE', 'kuR5HYfTbvE', 'U4EorbKnR7Y']


def main(out: str) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    cred = Credentials(None, refresh_token=c['refresh_token'], client_id=c['client_id'], client_secret=c['client_secret'],
                       token_uri='https://oauth2.googleapis.com/token')
    ya = build('youtubeAnalytics', 'v2', credentials=cred, cache_discovery=False)
    today = dt.date.today().isoformat()
    res: dict = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'النافذتان': WIN, 'أخطاء': {}}

    def q(name, **kw):
        kw.setdefault('endDate', today)
        try:
            r = ya.reports().query(ids='channel==MINE', **kw).execute()
            cols = [h['name'] for h in r.get('columnHeaders', [])]
            res[name] = [dict(zip(cols, row)) for row in r.get('rows', [])]
        except Exception as e:  # كلُّ سؤالٍ مستقلّ: رفضُ واحدٍ لا يُسقط الباقي
            res['أخطاء'][name] = str(e)[:300]

    base = 'views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,shares,likes'
    q('يومي_القناة', startDate=SERIES_START, dimensions='day', metrics=base + ',engagedViews', sort='day')
    q('يومي_القناة_بلا_engaged', startDate=SERIES_START, dimensions='day', metrics=base, sort='day')
    q('يومي_المصادر', startDate=SERIES_START, dimensions='day,insightTrafficSourceType',
      metrics='views,estimatedMinutesWatched', sort='day')
    q('يومي_النوع', startDate=SERIES_START, dimensions='day,creatorContentType',
      metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained', sort='day')
    for w, (s, e) in WIN.items():
        q(f'{w}_الفيديو', startDate=s, endDate=e, dimensions='video', maxResults=200, sort='-views',
          metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,shares,likes')
        q(f'{w}_الفيديو_بالمشتركين', startDate=s, endDate=e, dimensions='video', maxResults=50, sort='-subscribersGained',
          metrics='views,subscribersGained,subscribersLost')
        q(f'{w}_المصادر', startDate=s, endDate=e, dimensions='insightTrafficSourceType',
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'{w}_النوع', startDate=s, endDate=e, dimensions='creatorContentType',
          metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost')
        q(f'{w}_النوع_والمصدر', startDate=s, endDate=e, dimensions='creatorContentType,insightTrafficSourceType',
          metrics='views,estimatedMinutesWatched')
        q(f'{w}_حالة_الاشتراك', startDate=s, endDate=e, dimensions='subscribedStatus',
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'{w}_البلدان', startDate=s, endDate=e, dimensions='country', maxResults=25, sort='-views',
          metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost')
        q(f'{w}_البلدان_بالمشتركين', startDate=s, endDate=e, dimensions='country', maxResults=25, sort='-subscribersGained',
          metrics='views,subscribersGained,subscribersLost')
        q(f'{w}_الأجهزة', startDate=s, endDate=e, dimensions='deviceType', metrics='views,estimatedMinutesWatched')
        q(f'{w}_الإجمالي', startDate=s, endDate=e, metrics=base)
    for v in FILMS:
        q(f'فيلم_{v}_يومي_المصادر', startDate=SERIES_START, dimensions='day,insightTrafficSourceType',
          filters='video==' + v, metrics='views,estimatedMinutesWatched', sort='day')
        q(f'فيلم_{v}_حالة_الاشتراك', startDate=SERIES_START, dimensions='subscribedStatus', filters='video==' + v,
          metrics='views,estimatedMinutesWatched,averageViewDuration')
        q(f'فيلم_{v}_يومي', startDate=SERIES_START, dimensions='day', filters='video==' + v,
          metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained', sort='day')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('أسئلة ناجحة:', len([k for k in res if k not in ('تاريخ', 'النافذتان', 'أخطاء')]), '| مرفوضة:', len(res['أخطاء']))


if __name__ == '__main__':
    main(sys.argv[1])
