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


def insights(ya, rows: list, today: dt.date, yt=None) -> dict:
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
    # بجوار أيّ فيديوهاتٍ يقترحنا يوتيوب؟ (عين جالوت: 70٪ من المقترحات) — عناوينها وقنواتها ومشاهداتها تكشف الطلب المجاور
    ain = [r for r in rows if r['id'] == 'ns76edypTgg']
    if ain:
        out['ما_يقترح_عين_جالوت'] = q(startDate=ain[0]['published'][:10], filters='video==ns76edypTgg;insightTrafficSourceType==RELATED_VIDEO',
                                       **{k: v for k, v in detail.items() if k != 'startDate'})
    if yt is not None:
        ids = []
        for k in ('فيديوهات_تقترحنا_90_يوماً', 'ما_يقترح_عين_جالوت'):
            if isinstance(out.get(k), list):
                ids += [r['insightTrafficSourceDetail'] for r in out[k]]
        ids = list(dict.fromkeys(ids))[:50]
        try:
            got = yt.videos().list(part='snippet,statistics', id=','.join(ids)).execute().get('items', []) if ids else []
            out['عناوين_المقترِحين'] = {v['id']: {'العنوان': v['snippet']['title'][:100], 'القناة': v['snippet']['channelTitle'],
                                                  'المشاهدات': int(v.get('statistics', {}).get('viewCount', 0)),
                                                  'النشر': v['snippet']['publishedAt'][:10]} for v in got}
        except Exception as e:
            out['عناوين_المقترِحين'] = {'خطأ': str(e)[:200]}
    return out


PAID = ('ADVERTISING', 'PROMOTED', 'CAMPAIGN_CARD')


def truth(ya, rows: list, today: dt.date) -> dict:
    """ما تقوله الأرقام حقّاً — طلب المالك 2026-10-05: «أغلب الأفلام المنتشرة انتشرت بالإعلان، وأحياناً أعتمد الإعلان
    الممول لفيديوهاتٍ ناجحة فعلاً». لكلّ فيديوٍ عامّ: المشاهدات المدفوعة والطبيعية (كلّ ما عدا الإعلان: التصفّح والمقترحات
    والبحث والشورتس والمشتركون…) ومدّة بقاء كلٍّ منهما؛ ثمّ منحنىً يوميّ للفيديوهات المموَّلة: هل أطلق الإعلانُ مشاهداتٍ
    طبيعية بعده أم انطفأ معه؟ والاشتراكات والمشاركات لكلّ فيديو."""
    end = today.isoformat()

    def q(**kw):
        try:
            r = ya.reports().query(ids='channel==MINE', endDate=end, **kw).execute()
            return [dict(zip([h['name'] for h in r.get('columnHeaders', [])], row)) for row in r.get('rows', [])]
        except Exception as e:
            return {'خطأ': str(e)[:200]}

    per = []
    for r in rows:
        src = q(startDate=r['published'][:10], dimensions='insightTrafficSourceType', filters='video==' + r['id'],
                metrics='views,estimatedMinutesWatched,averageViewDuration', sort='-views')
        if not isinstance(src, list):
            per.append({'id': r['id'], 'خطأ': src}); continue
        paid = [x for x in src if x['insightTrafficSourceType'] in PAID]
        org = [x for x in src if x['insightTrafficSourceType'] not in PAID]
        pv, ov = sum(x['views'] for x in paid), sum(x['views'] for x in org)
        pm, om = sum(x['estimatedMinutesWatched'] for x in paid), sum(x['estimatedMinutesWatched'] for x in org)
        days = max(1, (today - dt.date.fromisoformat(r['published'][:10])).days)
        per.append({'id': r['id'], 'العنوان': r['title'][:90], 'النشر': r['published'][:10], 'الأيام': days,
                    'الطول_ث': r['seconds'], 'ريلز': r['seconds'] <= SHORT_MAX,
                    'مدفوعة': pv, 'طبيعية': ov, 'طبيعية_يومياً': round(ov / days, 1),
                    'بقاء_المدفوعة_ث': round(pm * 60 / pv, 1) if pv else None,
                    'بقاء_الطبيعية_ث': round(om * 60 / ov, 1) if ov else None,
                    'نسبة_بقاء_الطبيعية': round(100 * om * 60 / ov / r['seconds'], 1) if ov and r['seconds'] else None,
                    'دقائق_طبيعية': round(om), 'المصادر': {x['insightTrafficSourceType']: [x['views'], round(x['averageViewDuration'])]
                                                         for x in src}})
    out = {'لكل_فيديو': per}
    # الاشتراكات والمشاركات: تقرير «أعلى الفيديوهات» يشترط ترتيباً تنازلياً بمقياسٍ مطلوب
    subs = {}
    vids = [r['id'] for r in rows]
    for i in range(0, len(vids), 200):
        got = q(startDate=min(r['published'][:10] for r in rows), dimensions='video', filters='video==' + ','.join(vids[i:i + 200]),
                metrics='views,subscribersGained,subscribersLost,shares,likes', sort='-views', maxResults=200)
        if isinstance(got, list):
            for x in got:
                subs[x['video']] = {k: x[k] for k in ('subscribersGained', 'subscribersLost', 'shares', 'likes')}
        else:
            subs['خطأ'] = got
    out['الاشتراكات_والمشاركات'] = subs
    # المنحنى اليوميّ للفيديوهات المموَّلة: مدفوعة/طبيعية في كلّ يوم منذ النشر
    funded = sorted([p for p in per if p.get('مدفوعة', 0) > 300], key=lambda p: -p['مدفوعة'])[:10]
    daily = {}
    for p in funded:
        got = q(startDate=p['النشر'], dimensions='day,insightTrafficSourceType', filters='video==' + p['id'], metrics='views', sort='day')
        if not isinstance(got, list):
            daily[p['id']] = got; continue
        dd = {}
        for x in got:
            k = 'مدفوعة' if x['insightTrafficSourceType'] in PAID else 'طبيعية'
            dd.setdefault(x['day'], {'مدفوعة': 0, 'طبيعية': 0})[k] += x['views']
        daily[p['id']] = dd
    out['يومي_للمموَّلة'] = daily
    # منحنى البقاء الطبيعيّ (audienceType==ORGANIC) لأعلى الأفلام طبيعيّاً: أين يغادر المشاهد الحقيقيّ بالضبط؟
    films = sorted([p for p in per if not p.get('ريلز') and p.get('طبيعية', 0) >= 100], key=lambda p: -p['طبيعية_يومياً'])[:8]
    curves = {}
    for p in films:
        got = q(startDate=p['النشر'], dimensions='elapsedVideoTimeRatio', metrics='audienceWatchRatio,relativeRetentionPerformance',
                filters='video==%s;audienceType==ORGANIC' % p['id'])
        curves[p['id']] = got if not isinstance(got, list) else [[x['elapsedVideoTimeRatio'], round(x['audienceWatchRatio'], 3),
                                                                  round(x.get('relativeRetentionPerformance', 0), 3)] for x in got]
    out['منحنى_البقاء_الطبيعي'] = curves
    return out


def reach(ya, rows: list, today: dt.date) -> dict:
    """الظهور ونسبة النقر لكلّ فيديو (videoThumbnailImpressions وClickRate) — سؤال المالك 2026-10-05: «لماذا قنواتٌ أقلّ
    جودةً تحتفظ بالمشاهد أكثر؟». منحنى البقاء يقيس من نقر؛ وهذا يقيس هل يُعرض الفيلم أصلاً وهل يُنقر عليه:
    ظهورٌ كثيرٌ بنقرٍ قليل ⇒ العنوان والمصغّرة؛ ونقرٌ جيّدٌ ثم سقوطٌ في 30 ث ⇒ الافتتاحية. فشلُ النداء لا يُسقط التقرير.
    ⛔ الشوط 37313830497: رُفض الطلب (400) مع مرشّح الفيديوهات ⇒ صيغٌ متدرّجة، وسببُ الرفض من جسم الردّ لا من الرابط.
    ⛔ الشوط 37316034122: رُفضت الصيغ الثلاث «The query is not supported» ⇒ الظهور والنقر يُقرآن من الاستوديو حتى تدعمهما الواجهة."""
    if not rows:
        return {}
    start, end = min(r['published'][:10] for r in rows), today.isoformat()
    M = 'videoThumbnailImpressions,videoThumbnailImpressionsClickRate'

    def why(e):
        c = getattr(e, 'content', b'') or b''
        return (c.decode('utf-8', 'ignore') if isinstance(c, bytes) else str(c))[:400] or str(e)[:200]

    tries = [dict(dimensions='video', metrics=M, sort='-videoThumbnailImpressions', maxResults=200),
             dict(dimensions='video', metrics=M + ',views', sort='-views', maxResults=200),
             dict(metrics=M)]
    errs = []
    for kw in tries:
        try:
            r = ya.reports().query(ids='channel==MINE', startDate=start, endDate=end, **kw).execute()
            heads = [h['name'] for h in r.get('columnHeaders', [])]
            got = [dict(zip(heads, row)) for row in r.get('rows', [])]
            if 'video' in heads:
                return {'لكل_فيديو': {x['video']: {'الظهور': x['videoThumbnailImpressions'],
                                                   'نسبة_النقر': round(x['videoThumbnailImpressionsClickRate'], 2)} for x in got},
                        **({'أخطاء': errs} if errs else {})}
            return {'القناة': got, 'أخطاء': errs}
        except Exception as e:
            errs.append(why(e))
    return {'أخطاء': errs}


# أهداف خطّة القياس في وثيقة «بحث الاحتفاظ بالمشاهد» (2026-10-05) — أعلى قليلاً من أفضل ما حقّقناه، لا أرقامٌ مستوردة
TARGETS = {'بقاء_30ث': 70, 'بقاء_150ث': 40, 'متوسط_المشاهدة_ث': 240, 'طبيعية_يومياً': 300, 'حصة_المقترحات': 50,
           'نسبي_عشر': 50, 'نسبي_تسعة_أعشار': 50}      # 50 = وسط يوتيوب لما في طول الفيلم (دراسة مؤتة §١)
SUGGESTED = ('RELATED_VIDEO', 'SUBSCRIBER')     # المقترحات وميزات التصفّح: محرّك الانتشار الطبيعيّ


def fresh(ya, per: list, today: dt.date) -> dict:
    """مؤشّرات كلّ فيلمٍ جديد (3–14 يوماً) على خطّة القياس: البقاء الطبيعيّ عند 30 ث و150 ث، ومتوسط المشاهدة، والمشاهدات
    الطبيعية يومياً، وحصّة المقترحات والتصفّح — وما سقط منها دون الحدّ. تحليلات يوتيوب تتأخّر يومين إلى ثلاثة.
    ⛔ خاصّة: إلى الإصدار المسوّد وحده، لا إلى سجلّ التشغيل العامّ."""
    out = {}
    for p in per:
        if p.get('ريلز') or 'خطأ' in p or not 3 <= p.get('الأيام', 0) <= 14:
            continue
        curve = []
        try:
            r = ya.reports().query(ids='channel==MINE', startDate=p['النشر'], endDate=today.isoformat(),
                                   dimensions='elapsedVideoTimeRatio', metrics='audienceWatchRatio,relativeRetentionPerformance',
                                   filters='video==%s;audienceType==ORGANIC' % p['id']).execute()
            curve = [(row[0] * p['الطول_ث'], row[1], row[2] if len(row) > 2 else None, row[0]) for row in r.get('rows', [])]
        except Exception:
            pass

        def at(sec):
            # أقرب نقطةٍ مقيسة لا السابقة: نقاط المنحنى كلّ 1٪ من الطول، أي نحو 17 ث في فيلم 28 د، فكانت «السابقة» للثانية
            # 30 هي نقطة الثانية 17 (102٪ لبدر في أوّل تشغيل 2026-10-05). وتُذكر ثانيتها الفعلية مع القيمة.
            if not curve:
                return None, None
            t, v = min(curve, key=lambda c: abs(c[0] - sec))[:2]
            return round(100 * v), round(t)

        def rel(ratio):
            # الأداء النسبيّ (relativeRetentionPerformance): يقارن يوتيوب البقاء في كلّ لحظةٍ بأفلامٍ في طوله، و50 وسطها.
            # بحث الاحتفاظ 2026-10-05: عند عُشر الفيلم (موضع النزيف بعد الخطّاف) وعند تسعة أعشاره (الخاتمة) كنّا دون الوسط.
            got = [c for c in curve if c[2] is not None]
            return round(100 * min(got, key=lambda c: abs(c[3] - ratio))[2]) if got else None
        org = {k: v for k, v in (p.get('المصادر') or {}).items() if k not in PAID}
        tot = sum(v[0] for v in org.values())
        (b30, t30), (b150, t150) = at(30), at(150)
        k = {'بقاء_30ث': b30, 'بقاء_150ث': b150, 'متوسط_المشاهدة_ث': p.get('بقاء_الطبيعية_ث'),
             'طبيعية_يومياً': p.get('طبيعية_يومياً'),
             'حصة_المقترحات': round(100 * sum(org.get(s, [0])[0] for s in SUGGESTED) / tot) if tot else None,
             'نسبي_عشر': rel(0.10), 'نسبي_نصف': rel(0.50), 'نسبي_تسعة_أعشار': rel(0.90)}
        out[p['id']] = {'العنوان': p.get('العنوان'), 'الأيام': p['الأيام'], **k, 'عند_ث': [t30, t150],
                        'تحت_الحدّ': [n for n, t in TARGETS.items() if k[n] is not None and k[n] < t]}
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
    ins, tr, rc, fk = {}, {}, {}, {}
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
        ins = insights(ya, rows, dt.date.today(), yt)
        tr = truth(ya, rows, dt.date.today())
        rc = reach(ya, rows, dt.date.today())
        fk = fresh(ya, tr.get('لكل_فيديو', []), dt.date.today())
    except HttpError as e:
        analytics = 'غير متاحة: %s' % str(e)[:200]
    except Exception as e:                       # نطاق التحليلات غير ممنوح أو المكتبة غير مثبّتة
        analytics = 'غير متاحة: %s' % str(e)[:200]
    ranked = rank(rows, dt.date.today())
    rep = {'القناة': ch['snippet']['title'], 'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
           'التحليلات': analytics, 'عدد_العام': len(rows), 'عدد_الريلزات': len(ranked),
           'الريلزات_من_الأضعف': ranked,
           'رؤى': ins, 'الحقيقة': tr, 'الظهور_والنقر': rc, 'مؤشرات_الأفلام_الجديدة': fk,
           'الأفلام': sorted([r for r in rows if r['seconds'] > SHORT_MAX], key=lambda r: r['published'], reverse=True)}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(rep, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('القناة:', rep['القناة'], '| عامّ:', len(rows), '| ريلزات:', len(ranked), '| التحليلات:', analytics)
    for r in ranked[:8]:
        print('  %s | %s | %d مشاهدة · %.1f/يوم%s%s' % (r['id'], r['title'][:50], r['views'], r['views_per_day'],
              ' · مشاهدة %.0f%%' % r['avg_view_pct'] if r.get('avg_view_pct') is not None else '', ' · مبكّر' if r['early'] else ''))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/channel_stats.json')
