# -*- coding: utf-8 -*-
"""الطلب الخارجيّ المقيس على موضوعات الأفلام — طلب المالك 2026-10-05: «بحثٌ حقيقيّ جادّ يكون فيه الاقتراحات فعّالة
نبني عليها أفلاماً أو سلاسل قادمة، وأهمّ هدفٍ الاحتفاظ بالمشاهد».

لكلّ موضوعٍ في ops/stats/topics.json: أعلى الفيديوهات مشاهدةً منذ «منذ» (search.list بترتيب المشاهدات، لغةً عربية)،
ثم مشاهداتها وتواريخها وأطوالها وقنواتها (videos.list) ⇒ مؤشّرات الطلب: وسيط أعلى عشرة، وعدد ما تجاوز مئة ألف ومليوناً،
ونسبة الطويل (> 8 د)، وأكبر القنوات. ومعها اقتراحات البحث الشائعة في يوتيوب لبذورٍ عامّة ولكلّ موضوع (بلا حصّة).
⛔ حصّة يوتيوب: البحث 100 وحدة. يُحسب المسموح من دفتر الحصص (tools/quota.py) مع حجز رفعٍ واحد، ويُسجَّل كلّ إنفاق.
الاستعمال: python tools/topic_demand.py <out.json>   (يحتاج YT_OAUTH_JSON)
⛔ التقرير إلى الإصدار المسوّد الخاصّ channel-stats، لا إلى المستودع العامّ."""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import statistics
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota  # noqa: E402

RESERVE = 1650   # رفعٌ واحد ومصغّرة لا يمسّهما البحث


def secs(iso: str) -> int:
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def suggest(q: str) -> list:
    """اقتراحات البحث في يوتيوب (ما يكتبه الناس فعلاً) — بلا حصّة؛ فشلُها لا يُسقط شيئاً."""
    url = 'https://suggestqueries.google.com/complete/search?' + urllib.parse.urlencode(
        {'client': 'firefox', 'ds': 'yt', 'hl': 'ar', 'q': q})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))[1][:10]
    except Exception as e:
        return ['خطأ: ' + str(e)[:80]]


def allowance() -> int:
    d = quota.load()
    used = d.get('يوتيوب', {}).get('وحدات', 0)
    return max(0, (quota.CAP - quota.MARGIN - RESERVE - used) // quota.COST['search'])


def main(out: str) -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    cred = Credentials(None, refresh_token=c['refresh_token'], client_id=c['client_id'], client_secret=c['client_secret'],
                       token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=cred, cache_discovery=False)
    spec = json.load(io.open(os.path.join('ops', 'stats', 'topics.json'), encoding='utf-8'))
    since = spec.get('منذ', '2025-01-01') + 'T00:00:00Z'
    topics = spec['الموضوعات']
    n = min(len(topics), allowance())
    rep = {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'منذ': since[:10],
           'المسموح_بالحصّة': n, 'المطلوب': len(topics), 'الموضوعات': [], 'اقتراحات_عامة': {}}
    for s in spec.get('بذور', []):
        rep['اقتراحات_عامة'][s] = suggest(s)
    today = dt.date.today()
    for t in topics[:n]:
        row = {'المعرّف': t['id'], 'الفئة': t.get('cat', ''), 'البحث': t['q']}
        try:
            r = yt.search().list(part='id', q=t['q'], type='video', order='viewCount', publishedAfter=since,
                                 relevanceLanguage='ar', maxResults=25).execute()
            quota.spend('search', t['q'][:40])
            ids = [x['id']['videoId'] for x in r.get('items', []) if x.get('id', {}).get('videoId')]
            vs = yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(ids)).execute().get('items', []) if ids else []
            quota.spend('read', t['id'])
            vids = []
            for v in vs:
                pub = v['snippet']['publishedAt'][:10]
                vids.append({'id': v['id'], 'العنوان': v['snippet']['title'][:90], 'القناة': v['snippet']['channelTitle'],
                             'المشاهدات': int(v.get('statistics', {}).get('viewCount', 0)), 'النشر': pub,
                             'الطول_د': round(secs(v['contentDetails'].get('duration')) / 60, 1),
                             'العمر_يوماً': max(1, (today - dt.date.fromisoformat(pub)).days)})
            vids.sort(key=lambda v: -v['المشاهدات'])
            top = [v['المشاهدات'] for v in vids[:10]]
            longs = [v for v in vids if v['الطول_د'] > 8]
            row.update({'عدد': len(vids), 'وسيط_أعلى_عشرة': int(statistics.median(top)) if top else 0,
                        'أعلى': top[0] if top else 0, 'فوق_مئة_ألف': sum(v['المشاهدات'] >= 100_000 for v in vids),
                        'فوق_مليون': sum(v['المشاهدات'] >= 1_000_000 for v in vids),
                        'الطويل': len(longs), 'وسيط_الطويل': int(statistics.median([v['المشاهدات'] for v in longs[:10]])) if longs else 0,
                        'يومياً_لأعلى_عشرة': int(statistics.median([v['المشاهدات'] / v['العمر_يوماً'] for v in vids[:10]])) if vids else 0,
                        'القنوات': sorted({v['القناة'] for v in vids[:10]}), 'الأعلى': vids[:8],
                        'اقتراحات': suggest(t['q'])})
        except Exception as e:
            row['خطأ'] = str(e)[:200]
        rep['الموضوعات'].append(row)
        print('%-22s | %3s فيديو | وسيط أعلى عشرة %8s | فوق مليون %s | طويل %s' % (
            t['id'], row.get('عدد', '-'), row.get('وسيط_أعلى_عشرة', '-'), row.get('فوق_مليون', '-'), row.get('الطويل', '-')), flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(rep, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('المسموح بالحصّة: %d من %d موضوعاً' % (n, len(topics)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/topic_demand.json')
