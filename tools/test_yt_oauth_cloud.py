# -*- coding: utf-8 -*-
"""تجديد تفويض يوتيوب من الهاتف (tools/yt_oauth_cloud.py) بلا شبكة: الرابط بـPKCE والحالة، واستخراج الرمز من عنوان
ما بعد الإذن، ورفضُ الحالة المخالفة والإذن المرفوض والحساب بلا قناة، وأنّ المخرَج لا يُطبع."""
import base64
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_oauth_cloud as yo  # noqa: E402

def rj(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


OLD = json.dumps({'client_id': 'cid.apps', 'client_secret': 'SEC', 'refresh_token': 'dead'})


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(token: dict, items=('UC1',)):
    def op(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.startswith(yo.TOKEN):
            fake_urlopen.sent = urllib.parse.parse_qs(req.data.decode())
            return Resp(json.dumps(token).encode())
        assert req.headers.get('Authorization') == 'Bearer AT'
        return Resp(json.dumps({'items': [{'id': i} for i in items]}).encode())
    return op


class OAuthTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {'YT_OAUTH_JSON': OLD})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_url_has_pkce_state_offline_and_both_scopes(self):
        url = yo.make_url(self.d)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        sess = rj(os.path.join(self.d, 'session.json'))
        chal = base64.urlsafe_b64encode(hashlib.sha256(sess['verifier'].encode()).digest()).decode().rstrip('=')
        self.assertEqual(q['code_challenge'], [chal])
        self.assertEqual(q['state'], [sess['state']])
        self.assertEqual((q['access_type'], q['prompt'], q['client_id']), (['offline'], ['consent'], ['cid.apps']))
        self.assertEqual(set(q['scope'][0].split()), set(yo.SCOPES))
        self.assertNotIn('SEC', url)                                         # لا سرّ في الرابط

    def test_parse_code_from_full_url_and_bare_code(self):
        self.assertEqual(yo.parse_code('http://localhost:8822/?state=S&code=4/abc&scope=x'), ('4/abc', 'S', ''))
        self.assertEqual(yo.parse_code('localhost:8822/?code=4/xyz'), ('4/xyz', '', ''))
        self.assertEqual(yo.parse_code(' 4/bare '), ('4/bare', '', ''))
        self.assertEqual(yo.parse_code('http://localhost:8822/?error=access_denied')[2], 'access_denied')

    def test_exchange_writes_token_without_printing_it(self):
        yo.make_url(self.d)
        st = rj(os.path.join(self.d, 'session.json'))
        out = os.path.join(self.d, 'tok', 'yt_oauth.json')
        tok = {'access_token': 'AT', 'refresh_token': 'NEWRT', 'scope': ' '.join(yo.SCOPES), 'refresh_token_expires_in': 604799}
        buf = io.StringIO()
        with mock.patch.object(yo.urllib.request, 'urlopen', fake_urlopen(tok)), redirect_stdout(buf):
            info = yo.exchange('http://localhost:8822/?state=%s&code=4/C' % st['state'], self.d, out)
        self.assertEqual(rj(out),
                         {'client_id': 'cid.apps', 'client_secret': 'SEC', 'refresh_token': 'NEWRT'})
        self.assertEqual(fake_urlopen.sent['code_verifier'], [st['verifier']])
        self.assertEqual((info['analytics'], info['expires_days']), (True, 7.0))
        self.assertNotIn('NEWRT', buf.getvalue())
        self.assertNotIn('SEC', buf.getvalue())
        self.assertIn('وضع الاختبار', buf.getvalue())

    def test_exchange_refuses_wrong_state_denial_and_no_channel(self):
        yo.make_url(self.d)
        out = os.path.join(self.d, 'o.json')
        tok = {'access_token': 'AT', 'refresh_token': 'R'}
        with mock.patch.object(yo.urllib.request, 'urlopen', fake_urlopen(tok)):
            with self.assertRaises(SystemExit):
                yo.exchange('http://localhost:8822/?state=OTHER&code=4/C', self.d, out)
            with self.assertRaises(SystemExit):
                yo.exchange('http://localhost:8822/?error=access_denied', self.d, out)
        with mock.patch.object(yo.urllib.request, 'urlopen', fake_urlopen(tok, items=())), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                yo.exchange('4/C', self.d, out)
        self.assertFalse(os.path.exists(out))                                 # لا رمز يُكتب من إذنٍ ناقص


if __name__ == '__main__':
    unittest.main()
