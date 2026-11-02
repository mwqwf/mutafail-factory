# -*- coding: utf-8 -*-
"""أداة اكس الرسمية: الربط والنشر والمراقبة وتنظيف الحساب (طلب المالك 2026-11-02).

الواجهة الرسمية v2 بالدفع بالاستعمال (لا مستوى مجّانيّ منذ فبراير 2026)، والسقف الشهريّ 5$ بموافقة المالك.
التفويض من console.x.com في سرٍّ واحد X_KEYS:
  ثلاثة أسطر ⇒ OAuth 2.0: Client ID، Client Secret، Refresh Token (المعتمد 2026-11-02: لوحة اكس الجديدة تعطي الرمز بها).
     رمز التجديد يتبدّل مع كلّ تجديد ⇒ يُختم الجديد فوراً في الإصدار الخاصّ x-stats (tools/seal.sh)، ويُفضَّل على السرّ
     ما دام السرّ لم يتغيّر.
  أربعة أسطر ⇒ OAuth 1.0a: API Key، API Key Secret، Access Token، Access Token Secret (أو أربعة أسرار منفصلة).
بلا مكتبةٍ خارجية: التوقيع HMAC-SHA1 بالمكتبة القياسية.

⛔ المستودع عامّ: لا يُطبع في السجلّ إلا أعداد؛ النصوص والأرقام في الإصدار المسوّد الخاصّ x-stats.
⛔ حارس الإنفاق: كلّ طلبٍ يُقدَّر ثمنه ويُسجَّل في دفتر الشهر، ويُرفض ما يتجاوز السقف قبل إرساله.
   والحدّ الأعلى الحقيقيّ هو حدّ الإنفاق الذي يضعه المالك في لوحة اكس.
⛔ النشر يمرّ أوّلاً ببوّابة السياسات النصّية نفسها التي تحرس يوتيوب (tools/policy_gate.py).
⛔ الحذف لا رجعة فيه: «plan» يعدّ ويقدّر بلا حذف، و«clean» لا يعمل إلا بسقفٍ صريح من طلب المالك.

الاستعمال:
  python tools/x_api.py check   <dir>                 — من الحساب المربوط (يحفظ معرّفه)
  python tools/x_api.py post    <req.json> <dir>      — نشر منشور (نصّ ووسائط اختيارية)
  python tools/x_api.py stats   <dir>                 — مقاييس منشورات آخر 30 يوماً، لقطةٌ تُلحق بالسجلّ
  python tools/x_api.py plan    <dir>                 — خطّة التنظيف: العدد بالنوع والكلفة المقدّرة، بلا حذف
  python tools/x_api.py clean   <dir> --cap <دولار>    — تنفيذ الخطّة (قابلٌ للاستئناف)
<dir> مجلّد الحالة الخاصّة (يُنزَّل من الإصدار المسوّد ويُرفع إليه): ledger.json وme.json وstats.json وclean_*.json."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

API = 'https://api.x.com'
MONTHLY_CAP = float(os.environ.get('X_MONTHLY_CAP_USD', '5'))

# أسعار docs.x.com/x-api/getting-started/pricing كما قُرئت 2026-11-02 (تُراجع إن تغيّرت):
PRICE = {
    'post': 0.015,          # إنشاء منشور
    'post_url': 0.200,      # منشورٌ فيه رابط
    'owned_read': 0.001,    # قراءة منشوراتك أنت
    'read': 0.005,          # قراءة منشورٍ عامّ (احتياط إن لم تُحسب «مملوكة»)
    'user': 0.010,          # جلب مستخدم (users/me)
    'delete': 0.010,        # Interaction: Delete
    'media': 0.0,           # الرفع غير مسعَّر في الصفحة
}


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ─────────────────────────── التوقيع OAuth 1.0a ───────────────────────────

def pct(s) -> str:
    return urllib.parse.quote(str(s), safe='~')


def oauth_header(method: str, url: str, params: dict, keys: dict, nonce: str | None = None, ts: str | None = None) -> str:
    """ترويسة Authorization. params: معاملات الاستعلام والنموذج المشفّر وحدها (لا جسم JSON ولا multipart)."""
    oa = {
        'oauth_consumer_key': keys['api_key'],
        'oauth_nonce': nonce or secrets.token_hex(16),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': ts or str(int(time.time())),
        'oauth_token': keys['access_token'],
        'oauth_version': '1.0',
    }
    allp = {**params, **oa}
    base_params = '&'.join('%s=%s' % kv for kv in sorted((pct(k), pct(v)) for k, v in allp.items()))
    base = '&'.join([method.upper(), pct(url.split('?')[0]), pct(base_params)])
    key = '%s&%s' % (pct(keys['api_secret']), pct(keys['access_secret']))
    oa['oauth_signature'] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return 'OAuth ' + ', '.join('%s="%s"' % (pct(k), pct(v)) for k, v in sorted(oa.items()))


def env_keys() -> dict:
    names = {'api_key': 'X_API_KEY', 'api_secret': 'X_API_SECRET', 'access_token': 'X_ACCESS_TOKEN', 'access_secret': 'X_ACCESS_SECRET'}
    # سرٌّ واحد أيسر على المالك من الهاتف (2026-11-02): X_KEYS أربعة أسطر بهذا الترتيب
    lines = keys_lines()
    if len(lines) == 3:
        # OAuth 2.0 (لوحة اكس الجديدة تعطي رمز الوصول بها): رمزٌ يصلح ساعتين يُجدَّد بخطوة refresh قبل كلّ شوط
        tf = os.environ.get('X_TOKEN_FILE', '')
        if not tf or not os.path.exists(tf):
            raise SystemExit('⛔ وضع OAuth 2.0: لا رمز وصولٍ مجدَّد — تُشغَّل خطوة refresh أوّلاً')
        return {'bearer': json.load(io.open(tf, encoding='utf-8'))['access_token']}
    if lines:
        if len(lines) != 4:
            raise SystemExit('⛔ السرّ X_KEYS فيه %d أسطر، والمطلوب أربعة: API Key ثمّ API Key Secret ثمّ Access Token ثمّ Access Token Secret' % len(lines))
        return dict(zip(names, lines))
    miss = [v for v in names.values() if not os.environ.get(v, '').strip()]
    if miss:
        raise SystemExit('⛔ أسرار اكس ناقصة: %s — تُضاف من إعدادات المستودع ← Secrets and variables ← Actions' % ' '.join(miss))
    return {k: os.environ[v].strip() for k, v in names.items()}


# ─────────────────────────── دفتر الإنفاق ───────────────────────────

class Ledger:
    def __init__(self, d: str, cap: float = MONTHLY_CAP):
        self.path = os.path.join(d, 'ledger.json')
        self.cap = cap
        self.data = json.load(io.open(self.path, encoding='utf-8')) if os.path.exists(self.path) else {}

    @property
    def month(self) -> str:
        return now().strftime('%Y-%m')

    def spent(self, bucket: str = 'عادي') -> float:
        return round(self.data.get(self.month, {}).get(bucket, 0.0), 4)

    def guard(self, cost: float, bucket: str = 'عادي', cap: float | None = None):
        cap = self.cap if cap is None else cap
        if self.spent(bucket) + cost > cap + 1e-9:
            raise SystemExit('⛔ حارس الإنفاق: %.3f$ مصروفة هذا الشهر في «%s» + %.3f$ تتجاوز السقف %.2f$ — لا طلب'
                             % (self.spent(bucket), bucket, cost, cap))

    def add(self, cost: float, bucket: str = 'عادي'):
        m = self.data.setdefault(self.month, {})
        m[bucket] = round(m.get(bucket, 0.0) + cost, 4)
        self.save()

    def save(self):
        json.dump(self.data, io.open(self.path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


# ─────────────────────────── العميل ───────────────────────────

class XError(Exception):
    def __init__(self, status: int, body: str, headers=None):
        super().__init__('HTTP %d: %s' % (status, body[:300]))
        self.status, self.body, self.headers = status, body, headers or {}


class Client:
    def __init__(self, keys: dict, ledger: Ledger, bucket: str = 'عادي', cap: float | None = None):
        self.keys, self.ledger, self.bucket, self.cap = keys, ledger, bucket, cap

    def call(self, method: str, path: str, query: dict | None = None, js=None, multipart: dict | None = None,
             cost: float = 0.0, retries: int = 6):
        self.ledger.guard(cost, self.bucket, self.cap)
        url = API + path
        query = {k: v for k, v in (query or {}).items() if v is not None}
        full = url + ('?' + urllib.parse.urlencode(query, quote_via=urllib.parse.quote) if query else '')
        for attempt in range(retries):
            auth = ('Bearer ' + self.keys['bearer']) if 'bearer' in self.keys else oauth_header(method, url, query, self.keys)
            headers = {'Authorization': auth, 'User-Agent': 'mutafail-factory'}
            data = None
            if js is not None:
                data = json.dumps(js, ensure_ascii=False).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            elif multipart is not None:
                data, ctype = encode_multipart(multipart)
                headers['Content-Type'] = ctype
            req = urllib.request.Request(full, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    raw = r.read().decode('utf-8') or '{}'
                    self.ledger.add(cost, self.bucket)
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', 'replace')
                if e.code == 429 and attempt < retries - 1:
                    reset = int(e.headers.get('x-rate-limit-reset') or 0)
                    wait = max(15, min(960, reset - int(time.time()) + 5)) if reset else 60 * (attempt + 1)
                    print('⏳ حدّ المعدّل — انتظار %d ث' % wait, flush=True)
                    time.sleep(wait)
                    continue
                if e.code >= 500 and attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise XError(e.code, body, dict(e.headers))
        raise XError(0, 'نفدت المحاولات')


def encode_multipart(fields: dict) -> tuple[bytes, str]:
    b = '----mutafail' + uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\n' % b).encode())
        if isinstance(v, bytes):
            out.write(('Content-Disposition: form-data; name="%s"; filename="blob"\r\n'
                       'Content-Type: application/octet-stream\r\n\r\n' % k).encode())
            out.write(v)
        else:
            out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n%s' % (k, v)).encode())
        out.write(b'\r\n')
    out.write(('--%s--\r\n' % b).encode())
    return out.getvalue(), 'multipart/form-data; boundary=' + b


# ─────────────────────────── الحساب ───────────────────────────

def me(c: Client, d: str, refresh: bool = False) -> dict:
    p = os.path.join(d, 'me.json')
    if os.path.exists(p) and not refresh:
        return json.load(io.open(p, encoding='utf-8'))
    r = c.call('GET', '/2/users/me', {'user.fields': 'public_metrics,created_at,verified_type'}, cost=PRICE['user'])['data']
    json.dump(r, io.open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return r


def cmd_check(a) -> int:
    c = Client(env_keys(), Ledger(a.dir))
    u = me(c, a.dir, refresh=True)
    pm = u.get('public_metrics', {})
    print('✅ الحساب المربوط: @%s · منشورات %s · متابعون %s' % (u.get('username'), pm.get('tweet_count'), pm.get('followers_count')))
    return 0


# ─────────────────────────── النشر ───────────────────────────

def policy_check(text: str) -> list[dict]:
    import policy_gate as pg
    lex = pg.load_lex()
    items = [('body:x', 'x', text), ('metadata:x', 'x', text)]
    return [h for h in pg.scan_text(items, lex) if h['الشدة'] == 'block']


def has_url(text: str) -> bool:
    import re
    return bool(re.search(r'https?://|www\.|\b[\w-]+\.(com|be|net|org|io|ly|me)\b/?', text, re.I))


def upload_media(c: Client, path: str) -> str:
    size = os.path.getsize(path)
    mtype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    cat = 'tweet_video' if mtype.startswith('video/') else ('tweet_gif' if mtype == 'image/gif' else 'tweet_image')
    init = c.call('POST', '/2/media/upload/initialize', js={'media_type': mtype, 'total_bytes': size, 'media_category': cat},
                  cost=PRICE['media'])
    mid = init['data']['id']
    with open(path, 'rb') as f:
        i = 0
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            c.call('POST', '/2/media/upload/%s/append' % mid, multipart={'segment_index': str(i), 'media': chunk})
            i += 1
    fin = c.call('POST', '/2/media/upload/%s/finalize' % mid)
    info = (fin.get('data') or {}).get('processing_info')
    deadline = time.time() + 900
    while info and info.get('state') in ('pending', 'in_progress'):
        if time.time() > deadline:
            raise SystemExit('⛔ معالجة الوسائط لم تنتهِ في 15 دقيقة')
        time.sleep(max(2, int(info.get('check_after_secs', 5))))
        st = c.call('GET', '/2/media/upload', {'command': 'STATUS', 'media_id': mid})
        info = (st.get('data') or {}).get('processing_info')
    if info and info.get('state') == 'failed':
        raise SystemExit('⛔ رفضت اكس الوسائط: %s' % json.dumps(info.get('error', {}), ensure_ascii=False)[:300])
    return mid


def cmd_post(a) -> int:
    req = json.load(io.open(a.req, encoding='utf-8'))
    text = (req.get('النص') or '').strip()
    media = req.get('الوسائط')
    if not text and not media:
        raise SystemExit('⛔ لا نصّ ولا وسائط')
    blocks = policy_check(text)
    if blocks:
        for h in blocks:
            print('⛔ [%s] %s' % (h['الفئة'], ', '.join(h['ما وُجد'])))
        raise SystemExit('⛔ بوّابة السياسات منعت المنشور — يُحذف ما أمسكته من النصّ لا يُعاد صوغه')
    cost = PRICE['post_url'] if has_url(text) else PRICE['post']
    led = Ledger(a.dir)
    led.guard(cost)
    c = Client(env_keys(), led)
    body = {}
    if text:
        body['text'] = text
    if media:
        body['media'] = {'media_ids': [upload_media(c, media)]}
    if req.get('ردّ_على'):
        body['reply'] = {'in_reply_to_tweet_id': str(req['ردّ_على'])}
    r = c.call('POST', '/2/tweets', js=body, cost=cost)
    pid = r['data']['id']
    log = os.path.join(a.dir, 'posts.json')
    posts = json.load(io.open(log, encoding='utf-8')) if os.path.exists(log) else []
    posts.append({'id': pid, 'وقت': now().isoformat(timespec='seconds'), 'الطلب': os.path.basename(a.req), 'الكلفة': cost})
    json.dump(posts, io.open(log, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('✅ نُشر المنشور %s (الكلفة المقدّرة %.3f$، مصروف الشهر %.3f$)' % (pid, cost, led.spent()))
    return 0


# ─────────────────────────── المراقبة ───────────────────────────

FIELDS = 'created_at,public_metrics,non_public_metrics,organic_metrics,referenced_tweets'


def timeline(c: Client, uid: str, start: str | None = None, per_post: float = PRICE['owned_read'], fields: str = FIELDS):
    """كلّ منشورات الحساب (حتى 3200 الأحدث بحدّ الواجهة)، صفحةً صفحة بحارس الإنفاق قبل كلّ صفحة."""
    token = None
    while True:
        q = {'max_results': 100, 'tweet.fields': fields, 'pagination_token': token, 'start_time': start}
        # الحارس على أسوأ صفحة، والدفتر على ما رجع فعلاً (لقطةٌ يومية بلا منشورات لا تكلّف شيئاً)
        c.ledger.guard(100 * per_post, c.bucket, c.cap)
        r = c.call('GET', '/2/users/%s/tweets' % uid, q)
        c.ledger.add(len(r.get('data', [])) * per_post, c.bucket)
        for t in r.get('data', []):
            yield t
        token = r.get('meta', {}).get('next_token')
        if not token:
            return


def cmd_stats(a) -> int:
    led = Ledger(a.dir)
    c = Client(env_keys(), led)
    u = me(c, a.dir)
    start = (now() - dt.timedelta(days=29, hours=23)).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        posts = list(timeline(c, u['id'], start))
    except XError as e:
        if e.status not in (400, 403):
            raise
        # المقاييس الخاصّة قد تُرفض لمنشورٍ معيّن (ترويجٌ أو أقدم من 30 يوماً) ⇒ العامّة وحدها خيرٌ من لا شيء
        posts = list(timeline(c, u['id'], start, fields='created_at,public_metrics,referenced_tweets'))
    snap = {'وقت': now().isoformat(timespec='seconds'), 'المتابعون': None, 'المنشورات': posts}
    p = os.path.join(a.dir, 'stats.json')
    hist = json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else []
    hist.append(snap)
    json.dump(hist[-120:], io.open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    imp = sum((t.get('non_public_metrics') or t.get('organic_metrics') or {}).get('impression_count', 0) for t in posts)
    print('✅ لقطة اكس: %d منشوراً في 30 يوماً · ظهور %d · مصروف الشهر %.3f$' % (len(posts), imp, led.spent()))
    return 0


# ─────────────────────────── التنظيف ───────────────────────────

def kind(t: dict) -> str:
    refs = {r['type'] for r in t.get('referenced_tweets') or []}
    if 'retweeted' in refs:
        return 'إعادة_نشر'
    if 'replied_to' in refs:
        return 'ردّ'
    return 'منشور'


def cmd_plan(a) -> int:
    led = Ledger(a.dir)
    c = Client(env_keys(), led, bucket='تنظيف', cap=a.cap)
    u = me(c, a.dir, refresh=True)
    items = [{'id': t['id'], 'النوع': kind(t), 'الأصل': next((r['id'] for r in t.get('referenced_tweets') or []
                                                              if r['type'] == 'retweeted'), None)}
             for t in timeline(c, u['id'], fields='created_at,referenced_tweets')]
    counts = {}
    for i in items:
        counts[i['النوع']] = counts.get(i['النوع'], 0) + 1
    total = u.get('public_metrics', {}).get('tweet_count', len(items))
    plan = {'وقت': now().isoformat(timespec='seconds'), 'الحساب': u.get('username'), 'العدد_في_الملف': total,
            'المتاح_للواجهة': len(items), 'بالنوع': counts, 'الكلفة_المقدّرة': round(len(items) * PRICE['delete'], 2),
            'العناصر': items}
    json.dump(plan, io.open(os.path.join(a.dir, 'clean_plan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('📋 خطّة التنظيف: %d عنصراً تصلها الواجهة من %s في الملف · %s · كلفة الحذف المقدّرة %.2f$'
          % (len(items), total, ' · '.join('%s %d' % kv for kv in counts.items()), plan['الكلفة_المقدّرة']))
    if total > len(items):
        print('⚠️ %d أقدم من حدّ الواجهة (3200): تحتاج أرشيف الحساب' % (total - len(items)))
    return 0


def cmd_clean(a) -> int:
    pp = os.path.join(a.dir, 'clean_plan.json')
    if not os.path.exists(pp):
        raise SystemExit('⛔ لا خطّة: شغّل plan أوّلاً واعرضها على المالك')
    plan = json.load(io.open(pp, encoding='utf-8'))
    types = set(a.types.split(',')) if a.types else None
    dp = os.path.join(a.dir, 'clean_done.json')
    done = set(json.load(io.open(dp, encoding='utf-8'))) if os.path.exists(dp) else set()
    led = Ledger(a.dir)
    c = Client(env_keys(), led, bucket='تنظيف', cap=a.cap)
    uid = me(c, a.dir)['id']
    todo = [i for i in plan['العناصر'] if i['id'] not in done and (types is None or i['النوع'] in types)]
    print('🧹 التنظيف: %d متبقٍّ · السقف %.2f$ · مصروف التنظيف %.3f$' % (len(todo), a.cap, led.spent('تنظيف')))
    deadline = time.time() + a.minutes * 60
    n = 0
    for i in todo:
        if time.time() > deadline:
            print('⏸ انتهت مهلة الشوط — يُستأنف من حيث وقف')
            break
        try:
            if i['النوع'] == 'إعادة_نشر' and i.get('الأصل'):
                c.call('DELETE', '/2/users/%s/retweets/%s' % (uid, i['الأصل']), cost=PRICE['delete'])
            else:
                c.call('DELETE', '/2/tweets/%s' % i['id'], cost=PRICE['delete'])
        except XError as e:
            if e.status != 404:  # المحذوف من قبل ليس خطأ
                raise
        done.add(i['id'])
        n += 1
        if n % 25 == 0:
            json.dump(sorted(done), io.open(dp, 'w', encoding='utf-8'))
            print('… حُذف %d (مصروف التنظيف %.3f$)' % (n, led.spent('تنظيف')), flush=True)
    json.dump(sorted(done), io.open(dp, 'w', encoding='utf-8'))
    left = len(todo) - n
    print('✅ حُذف %d في هذا الشوط · متبقٍّ %d · مصروف التنظيف %.3f$' % (n, left, led.spent('تنظيف')))
    return 0 if left == 0 else 3


# ─────────────────────────── تجديد OAuth 2.0 ───────────────────────────

def keys_lines() -> list[str]:
    """X_KEYS بأسطره، أو ثلاثة أسرارٍ منفصلة أيسر على المالك (قيمةٌ واحدة في كلّ سرّ)."""
    sep = [os.environ.get(k, '').strip() for k in ('X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REFRESH_TOKEN')]
    if all(sep):
        return sep
    return [l.strip() for l in os.environ.get('X_KEYS', '').splitlines() if l.strip()]


def oauth2_lines() -> list[str]:
    lines = keys_lines()
    if len(lines) != 3:
        miss = [k for k in ('X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REFRESH_TOKEN') if not os.environ.get(k, '').strip()]
        raise SystemExit('⛔ وضع OAuth 2.0: أسرارٌ ناقصة أو فارغة: %s' % ' '.join(miss))
    return lines


def fp(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def pick_refresh(secret_rt: str, sealed: dict | None) -> str:
    """رمز التجديد يتبدّل مع كلّ تجديد (يبطل القديم): المختوم المحفوظ أحدث من السرّ، إلا إن وضع المالك في السرّ رمزاً جديداً."""
    if sealed and sealed.get('src') == fp(secret_rt) and sealed.get('refresh_token'):
        return sealed['refresh_token']
    return secret_rt


def cmd_refresh(a) -> int:
    cid, csec, srt = oauth2_lines()
    sp = os.path.join(a.tokdir, 'x_token.json')
    sealed = json.load(io.open(sp, encoding='utf-8')) if os.path.exists(sp) else None
    rt = pick_refresh(srt, sealed)
    body = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': rt, 'client_id': cid}).encode()
    basic = base64.b64encode(('%s:%s' % (cid, csec)).encode()).decode()
    req = urllib.request.Request(API + '/2/oauth2/token', data=body, method='POST', headers={
        'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Basic ' + basic})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit('⛔ رفضت اكس تجديد الرمز (HTTP %d): %s — يولّد المالك Refresh Token جديداً ويضعه سطراً ثالثاً في X_KEYS'
                         % (e.code, e.read().decode('utf-8', 'replace')[:200]))
    for k in ('access_token', 'refresh_token'):
        if tok.get(k):
            print('::add-mask::' + tok[k])
    if not tok.get('refresh_token'):
        raise SystemExit('⛔ لم يرجع رمز تجديد: يُولَّد الرمز مع «Include refresh token (offline.access)»')
    os.makedirs(a.tokdir, exist_ok=True)
    out = {'access_token': tok['access_token'], 'refresh_token': tok['refresh_token'], 'src': fp(srt),
           'expires_at': int(time.time()) + int(tok.get('expires_in', 7200)), 'scope': tok.get('scope', '')}
    json.dump(out, io.open(sp, 'w', encoding='utf-8'))
    print('🔑 جُدِّد رمز اكس (%s) · الصلاحيات: %s' % ('من السرّ' if rt == srt else 'من المختوم', out['scope']))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('refresh'); s.add_argument('tokdir')
    s = sub.add_parser('check'); s.add_argument('dir')
    s = sub.add_parser('post'); s.add_argument('req'); s.add_argument('dir')
    s = sub.add_parser('stats'); s.add_argument('dir')
    s = sub.add_parser('plan'); s.add_argument('dir'); s.add_argument('--cap', type=float, default=4.0)
    s = sub.add_parser('clean'); s.add_argument('dir'); s.add_argument('--cap', type=float, required=True)
    s.add_argument('--types'); s.add_argument('--minutes', type=float, default=330)
    a = ap.parse_args(argv)
    os.makedirs(a.dir, exist_ok=True) if hasattr(a, 'dir') else None
    return {'refresh': cmd_refresh, 'check': cmd_check, 'post': cmd_post, 'stats': cmd_stats, 'plan': cmd_plan, 'clean': cmd_clean}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
