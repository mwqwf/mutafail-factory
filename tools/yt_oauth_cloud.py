# -*- coding: utf-8 -*-
"""تجديد تفويض يوتيوب من الهاتف بلا حاسوب المالك (مؤتة 2026-10-06: «invalid_grant: Token has been expired or revoked»).

لا يُجدَّد الإذن إلا بموافقة صاحب الحساب، فهذه الأداة تجعل موافقته نقرةً من الهاتف، والباقي في سير yt-oauth.yml:

الخطوة ١ — السير عند دفع ops/oauth/request.json:
    python tools/yt_oauth_cloud.py url <مجلد_الجلسة>
  يقرأ معرّف العميل من YT_OAUTH_JSON (العميل سليم، والميّت رمز التجديد وحده)، ويكتب في مجلد الجلسة المتحقّقَ (PKCE)
  والحالةَ ليُختما بالمفتاح العامّ، ويطبع رابط الإذن. وليس في الرابط سرّ: معرّف العميل علنيٌّ بطبعه.
الخطوة ٢ — المالك: يفتح الرابط من هاتفه ويأذن بحساب القناة، فينتهي المتصفّح إلى صفحةٍ لا تُفتح عنوانها
  http://localhost:8822/?…code=… فينسخ ذلك العنوان كاملاً ويرسله.
الخطوة ٣ — السير عند دفع ops/oauth/code.json:
    python tools/yt_oauth_cloud.py exchange <العنوان_أو_الرمز> <مجلد_الجلسة_المفضوضة> <ملف_المخرَج>
  يطابق الحالة، ويبادل الرمز (يحتاج سرّ العميل والمتحقّق المختوم، فالرمز وحده لا ينفع من يراه في المستودع العامّ)،
  ويجرّب القناة بنداءٍ واحد، ويكتب YT_OAUTH_JSON الجديد في ملفٍّ يُختم ولا يُطبع.

⛔ لا يطبع سرّاً. والنطاقان: إدارة يوتيوب (الرفع والمصغّرات والخصوصية) وقراءة التحليلات (منحنيات البقاء في channel_stats.py).
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

AUTH = 'https://accounts.google.com/o/oauth2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
CHANNELS = 'https://www.googleapis.com/youtube/v3/channels?part=id&mine=true'
SCOPES = ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/yt-analytics.readonly']
REDIRECT = 'http://localhost:8822/'


def client() -> tuple[str, str]:
    c = json.loads(os.environ['YT_OAUTH_JSON'])
    return c['client_id'], c['client_secret']


def make_url(sess_dir: str) -> str:
    cid, _ = client()
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip('=')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state = secrets.token_urlsafe(16)
    os.makedirs(sess_dir, exist_ok=True)
    with io.open(os.path.join(sess_dir, 'session.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'verifier': verifier, 'state': state}))
    q = urllib.parse.urlencode({
        'response_type': 'code', 'client_id': cid, 'redirect_uri': REDIRECT, 'scope': ' '.join(SCOPES),
        'code_challenge': challenge, 'code_challenge_method': 'S256', 'state': state,
        'prompt': 'consent', 'access_type': 'offline'})
    return AUTH + '?' + q


def parse_code(raw: str) -> tuple[str, str, str]:
    """(الرمز، الحالة، الخطأ) من عنوان ما بعد الإذن كاملاً، أو من الرمز وحده."""
    s = raw.strip()
    if '://' in s or s.startswith('localhost'):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s if '://' in s else 'http://' + s).query)
        return q.get('code', [''])[0], q.get('state', [''])[0], q.get('error', [''])[0]
    return s, '', ''


def _post(url: str, data: dict) -> dict:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(data).encode()),
                                    timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            j = json.loads(body)
            body = j.get('error_description') or j.get('error') or body
        except ValueError:
            pass
        raise SystemExit('⛔ تعذّر تبادل الرمز (%d): %s' % (e.code, str(body)[:200]))


def exchange(raw: str, sess_dir: str, out: str) -> dict:
    code, state, err = parse_code(raw)
    if err:
        raise SystemExit('⛔ لم يُؤذَن: %s' % err)
    if not code:
        raise SystemExit('⛔ لا رمز في العنوان المرسَل')
    with io.open(os.path.join(sess_dir, 'session.json'), encoding='utf-8') as f:
        sess = json.load(f)
    if state and state != sess['state']:
        raise SystemExit('⛔ الحالة لا تطابق جلسة الرابط — العنوان من رابطٍ أقدم؟ يُطلب رابطٌ جديد')
    cid, csec = client()
    tok = _post(TOKEN, {'code': code, 'client_id': cid, 'client_secret': csec, 'redirect_uri': REDIRECT,
                        'grant_type': 'authorization_code', 'code_verifier': sess['verifier']})
    if 'refresh_token' not in tok:
        raise SystemExit('⛔ لا رمز تجديدٍ في الردّ')
    req = urllib.request.Request(CHANNELS, headers={'Authorization': 'Bearer ' + tok['access_token']})
    with urllib.request.urlopen(req, timeout=60) as r:
        if not json.load(r).get('items'):
            raise SystemExit('⛔ الحساب المأذون بلا قناة — يُختار حساب القناة عند الإذن')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'client_id': cid, 'client_secret': csec, 'refresh_token': tok['refresh_token']}))
    info = {'analytics': 'yt-analytics' in tok.get('scope', ''),
            'expires_days': round(tok['refresh_token_expires_in'] / 86400, 1) if tok.get('refresh_token_expires_in') else None}
    print('✅ رمز تجديدٍ جديد يعمل على القناة · التحليلات: %s' % ('معه' if info['analytics'] else '⚠️ لم تُمنح'))
    if info['expires_days']:
        print('⚠️ ينتهي الرمز بعد %s يوماً: تطبيق الإذن في «وضع الاختبار» — يُنقل إلى «الإنتاج» في وحدة تحكّم جوجل '
              'ليدوم الرمز' % info['expires_days'])
    return info


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == 'url':
        print(make_url(argv[1]))
        return 0
    if len(argv) >= 4 and argv[0] == 'exchange':
        exchange(argv[1], argv[2], argv[3])
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
