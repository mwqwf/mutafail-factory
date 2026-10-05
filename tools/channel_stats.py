# -*- coding: utf-8 -*-
"""إحصاءات القناة وأضعف الريلزات — أمر المالك 2026-10-04: «إذا كان يوتيوب يتيح معرفة ذلك اعرف لنا أضعف الريلزات الأخرى
وأضفها للطابور لكي يستبدلها كوديكس».

يقرأ كلّ ما رُفع إلى القناة: المشاهدات والإعجابات والتعليقات ومعدّلها اليوميّ منذ النشر (واجهة البيانات)، ونسبةَ المشاهدة
ومتوسّطَ مدّتها لكلّ فيديو إن أتاحها التفويض (واجهة التحليلات؛ وإلا يُذكر أنها غير متاحة). ثم يرتّب الريلزات (≤ 180 ث)
من الأضعف: نسبة المشاهدة أوّلاً إن وُجدت، وإلا المشاهدات اليومية — والريلز الأحدث من 3 أيام «مبكّرٌ على الحكم» فلا يُعدّ ضعيفاً.
الاستعمال: python tools/channel_stats.py <out.json>   (يحتاج YT_OAUTH_JSON)
⛔ التقرير فيه تحليلاتٌ خاصّة بالقناة ⇒ يُرفع إلى إصدارٍ مسوّد خاصّ، لا يُودَع في المستودع العامّ.
الكلفة من حصّة يوتيوب: قراءة القناة (١) + قائمة الرفع (١ لكلّ ٥٠) + الفيديوهات (١ لكلّ ٥٠) — زهيدة، ولا تمسّ جيميناي."""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import statistics
import sys

SHORT_MAX = 180


def seconds(iso: str) -> int:
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def rank(rows: list, today: dt.date) -> list:
    """الريلزات من الأضعف. لكلّ صفٍّ: views_per_day، وavg_view_pct إن وُجدت. الأحدث من 3 أيام في آخر القائمة (early)."""
    shorts = [r for r in rows if r['seconds'] and r['seconds'] <= SHORT_MAX]
    for r in shorts:
        r['days'] = max(1, (today - dt.date.fromisoformat(r['published'][:10])).days)
        r['views_per_day'] = round(r['views'] / r['days'], 2)
        r['early'] = r['days'] < 3
    mature = [r for r in shorts if not r['early']]
    med = statistics.median([r['views_per_day'] for r in mature]) if mature else 0
    have_pct = [r for r in mature if r.get('avg_view_pct') is not None]
    # ريلزٌ بلا نسبةٍ والبقيّةُ لها نسبة ⇒ يُعطى الوسيط، فلا يبدو أضعفَ لمجرّد غياب الرقم
    med_pct = statistics.median([r['avg_view_pct'] for r in have_pct]) if have_pct else None
    for r in shorts:
        rel = r['views_per_day'] / med if med else 0
        pct = r['avg_view_pct'] if r.get('avg_view_pct') is not None else med_pct
        # نسبة المشاهدة أصدقُ مقياسٍ للريلز (هل يكمله المشاهد؟)، والمشاهدات اليومية نسبةً إلى الوسيط تكملها
        r['score'] = round((pct / 100.0 if pct is not None else 0) + rel, 3)
    return sorted(shorts, key=lambda r: (r['early'], r['score']))


def insights(ya, rows: list, today: dt.date) -> dict:
    """من أين جاء المشاهدون؟ — طلب المالك 2026-10-05: «اقترح فلماً عليه طلبٌ حقيقيّ».
    مشاهداتٌ كثيرة بنسبة بقاءٍ 3٪ (اليرموك) نمطُ إعلانٍ أو تجربةِ تصفّح لا طلب؛ فالفيصل مصادر الزيارات لكلّ فيديو بارز،
    وكلماتُ البحث التي جاءت بالمشاهدين (الطلب الحقيقيّ)، والفيديوهات التي تقترحنا، والبلدان. كلّ استعلامٍ مستقلّ:
    فشلُ واحدٍ يُسجَّل بنصّه ولا يُسقط غيره."""
    end, start90 = today.isoformat(), (today - dt.timedelta(days=90)).isoformat()
    out = {}

    def q(**kw):
        try:
            r = ya.reports().query(ids='channel==MINE', endDate=end, **kw).execute()
            return [dict(zip([h['name'] for h in r.get('columnHeaders', [])], row)) for row in r.get('rows', [])]
        except Exception as e:                   # نطاقٌ أو بُعدٌ غير متاح: يُسمّى ولا يُدّعى
            return {'خطأ': str(e)[:200]}

    top = sorted(rows, key=lambda r: -r['views'])[:12]
    out['مصادر_الزيارات'] = {r['id']: {'العنوان': r['title'][:80], 'المشاهدات': r['views'],
                                         'المصادر': q(startDate=r['published'][:10], dimensions='insightTrafficSourceType',
                                                     metrics='views,estimatedMinutesWatched,averageViewDuration',
                                                     filters='video==' + r['id'], sort='-views')} for r in top}
    detail = dict(startDate=start90, dimensions='insightTrafficSourceDetail', metrics='views,estimatedMinutesWatched',
                  sort='-views', maxResults=25)
    out['كلمات_البحث_90_يوماً'] = q(filters='insightTrafficSourceType==YT_SEARCH', **detail)
    out['فيديوهات_تقترحنا_90_يوماً'] = q(filters='insightTrafficSourceType==RELATED_VIDEO', **detail)
    out['مصادر_القناة_90_يوماً'] = q(startDate=start90, dimensions='insightTrafficSourceType',
                                     metrics='views,estimatedMinutesWatched,averageViewDuration', sort='-views')
    out['البلدان_90_يوماً'] = q(startDate=start90, dimensions='country', sort='-views', maxResults=15,
                                metrics='views,estimatedMinutesWatched,averageViewDuration')
    out['العمر_والجنس_90_يوماً'] = q(startDate=start90, dimensions='ageGroup,gender', metrics='viewerPercentage')
    return out


def main(out: str) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    # بلا scopes عند التجديد: يُعاد الرمزُ بما مُنح أصلاً، فلا يُرفض التجديد إن لم يُمنح نطاق التحليلات
    cred = Credentials(None, refresh_token=c['refresh_token'], client_id=c['client_id'], client_secret=c['client_secret'],
                       token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=cred, cache_discovery=False)
    ch = yt.channels().list(part='contentDetails,snippet', mine=True).execute()['items'][0]
    up = ch['contentDetails']['relatedPlaylists']['uploads']
    ids, tok = [], None
    while True:
        r = yt.playlistItems().list(part='contentDetails', playlistId=up, maxResults=50, pageToken=tok).execute()
        ids += [x['contentDetails']['videoId'] for x in r.get('items', [])]
        tok = r.get('nextPageToken')
        if not tok:
            break
    ids = list(dict.fromkeys(ids))      # قائمة الرفع قد تعيد الفيديو نفسه مرّتين (وقع في تقرير 2026-10-04)
    rows = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part='snippet,contentDetails,statistics,status', id=','.join(ids[i:i + 50])).execute()
        for v in r.get('items', []):
            st = v.get('statistics', {})
            rows.append({'id': v['id'], 'title': v['snippet']['title'], 'published': v['snippet']['publishedAt'],
                         'seconds': seconds(v['contentDetails'].get('duration')), 'privacy': v['status'].get('privacyStatus'),
                         'views': int(st.get('viewCount', 0)), 'likes': int(st.get('likeCount', 0)),
                         'comments': int(st.get('commentCount', 0)),
                         # أوّل الوصف العامّ: يكشف موضوع الريلز إن كان عنوانه مؤقّتاً («reel2») فيُبنى غلافه على مضمونه
                         'description': (v['snippet'].get('description') or '')[:300]})
    rows = [r for r in rows if r['privacy'] == 'public']
    analytics = 'غير متاحة'
    ins = {}
    try:
        ya = build('youtubeAnalytics', 'v2', credentials=cred, cache_discovery=False)
        start = min(r['published'][:10] for r in rows) if rows else dt.date.today().isoformat()
        got = {}
        vids = [r['id'] for r in rows]
        for i in range(0, len(vids), 200):
            q = ya.reports().query(ids='channel==MINE', startDate=start, endDate=dt.date.today().isoformat(),
                                   metrics='views,averageViewDuration,averageViewPercentage', dimensions='video',
                                   filters='video==' + ','.join(vids[i:i + 200]), maxResults=200,
                                   sort='-views').execute()   # تقرير «أعلى الفيديوهات» يشترط ترتيباً تنازلياً
            for row in q.get('rows', []):
                got[row[0]] = {'avg_view_seconds': row[2], 'avg_view_pct': row[3]}
        for r in rows:
            r.update(got.get(r['id'], {}))
        analytics = 'متاحة (%d فيديو)' % len(got)
        ins = insights(ya, rows, dt.date.today())
    except HttpError as e:
        analytics = 'غير متاحة: %s' % str(e)[:200]
    except Exception as e:                       # نطاق التحليلات غير ممنوح أو المكتبة غير مثبّتة
        analytics = 'غير متاحة: %s' % str(e)[:200]
    ranked = rank(rows, dt.date.today())
    rep = {'القناة': ch['snippet']['title'], 'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
           'التحليلات': analytics, 'عدد_العام': len(rows), 'عدد_الريلزات': len(ranked),
           'الريلزات_من_الأضعف': ranked,
           'رؤى': ins,
           'الأفلام': sorted([r for r in rows if r['seconds'] > SHORT_MAX], key=lambda r: r['published'], reverse=True)}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(rep, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('القناة:', rep['القناة'], '| عامّ:', len(rows), '| ريلزات:', len(ranked), '| التحليلات:', analytics)
    for r in ranked[:8]:
        print('  %s | %s | %d مشاهدة · %.1f/يوم%s%s' % (r['id'], r['title'][:50], r['views'], r['views_per_day'],
              ' · مشاهدة %.0f%%' % r['avg_view_pct'] if r.get('avg_view_pct') is not None else '', ' · مبكّر' if r['early'] else ''))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/channel_stats.json')
