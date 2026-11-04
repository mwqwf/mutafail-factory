# -*- coding: utf-8 -*-
"""اختبارات أداة اكس بلا شبكة: التوقيع بمتّجه التوثيق الرسميّ، وحارس الإنفاق، وبوّابة السياسات، والتصنيف."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_api as x  # noqa: E402


class TestX(unittest.TestCase):
    def test_signature_official_vector(self):
        # المثال المنشور في توثيق اكس «Creating a signature»
        keys = {'api_key': 'xvz1evFS4wEEPTGEFPHBog', 'api_secret': 'kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw',
                'access_token': '370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb',
                'access_secret': 'LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE'}
        params = {'include_entities': 'true', 'status': 'Hello Ladies + Gentlemen, a signed OAuth request!'}
        h = x.oauth_header('POST', 'https://api.twitter.com/1.1/statuses/update.json', params, keys,
                           nonce='kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg', ts='1318622958')
        self.assertIn('oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"', h)

    def test_single_secret(self):
        os.environ['X_KEYS'] = 'a\n b \n\nc\nd\n'
        try:
            self.assertEqual(x.env_keys(), {'api_key': 'a', 'api_secret': 'b', 'access_token': 'c', 'access_secret': 'd'})
            os.environ['X_KEYS'] = 'a\nb'
            with self.assertRaises(SystemExit):
                x.env_keys()
        finally:
            del os.environ['X_KEYS']

    def test_pick_refresh(self):
        self.assertEqual(x.pick_refresh('S', None), 'S')
        self.assertEqual(x.pick_refresh('S', {'src': x.fp('S'), 'refresh_token': 'R2'}), 'R2')
        self.assertEqual(x.pick_refresh('S_NEW', {'src': x.fp('S'), 'refresh_token': 'R2'}), 'S_NEW')

    def test_oauth2_mode(self):
        d = tempfile.mkdtemp()
        tf = os.path.join(d, 't.json')
        open(tf, 'w').write('{"access_token": "AT"}')
        os.environ['X_KEYS'] = 'cid\ncsec\nrt'
        os.environ['X_TOKEN_FILE'] = tf
        try:
            self.assertEqual(x.env_keys(), {'bearer': 'AT'})
        finally:
            del os.environ['X_KEYS'], os.environ['X_TOKEN_FILE']

    def test_oauth1_preferred(self):
        env = {'X_API_KEY': 'a', 'X_API_SECRET': 'b', 'X_ACCESS_TOKEN': 'c', 'X_ACCESS_SECRET': 'd',
               'X_CLIENT_ID': 'i', 'X_CLIENT_SECRET': 's', 'X_REFRESH_TOKEN': 'r'}
        os.environ.update(env)
        try:
            self.assertEqual(x.env_keys(), {'api_key': 'a', 'api_secret': 'b', 'access_token': 'c', 'access_secret': 'd'})
        finally:
            for k in env:
                del os.environ[k]

    def test_ledger_guard(self):
        d = tempfile.mkdtemp()
        led = x.Ledger(d, cap=0.05)
        led.add(0.04)
        led.guard(0.01)
        with self.assertRaises(SystemExit):
            led.guard(0.02)
        self.assertEqual(x.Ledger(d, cap=0.05).spent(), 0.04)
        led.guard(1.0, bucket='تنظيف', cap=2.0)  # سقف التنظيف مستقلّ

    def test_url_cost(self):
        self.assertTrue(x.has_url('شاهد الفيلم https://youtu.be/abc'))
        self.assertTrue(x.has_url('youtube.com/@x'))
        self.assertFalse(x.has_url('خالد بن الوليد في مؤتة.'))

    def test_policy_blocks(self):
        self.assertEqual(x.policy_check('معركة مؤتة: كيف نجا الجيش؟'), [])

    def test_kind(self):
        self.assertEqual(x.kind({'referenced_tweets': [{'type': 'retweeted', 'id': '1'}]}), 'إعادة_نشر')
        self.assertEqual(x.kind({'referenced_tweets': [{'type': 'replied_to', 'id': '1'}]}), 'ردّ')
        self.assertEqual(x.kind({}), 'منشور')

    # ── منع التكرار ──
    def _fake(self, d, fail_post_status=None, recent=None):
        """عميلٌ بلا شبكة: يسجّل الطلبات ويحاكي نشراً ينجح أو يفشل بحالةٍ مجهولة."""
        calls = []
        state = {'n': 100, 'recent': list(recent or [])}

        def call(method, path, query=None, js=None, multipart=None, cost=0.0, retries=6, idempotent=True):
            calls.append((method, path, js, idempotent))
            if path == '/2/users/me':
                return {'data': {'id': 'U'}}
            if path.startswith('/2/users/'):
                return {'data': state['recent']}
            if path == '/2/tweets':
                state['n'] += 1
                tid = str(state['n'])
                rec = {'id': tid, 'text': js.get('text', '') + ' https://t.co/x', 'created_at': x.now().isoformat()}
                if js.get('reply'):
                    rec['referenced_tweets'] = [{'type': 'replied_to', 'id': js['reply']['in_reply_to_tweet_id']}]
                state['recent'].insert(0, rec)
                if fail_post_status is not None:
                    raise x.XError(fail_post_status, 'boom')
                return {'data': {'id': tid}}
            raise AssertionError(path)
        return calls, state, call

    def _run(self, req, posts=None, **kw):
        d = tempfile.mkdtemp()
        rq = os.path.join(d, 'r.json')
        import json
        json.dump(req, open(rq, 'w', encoding='utf-8'), ensure_ascii=False)
        if posts is not None:
            json.dump(posts, open(os.path.join(d, 'posts.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        calls, state, call = self._fake(d, **kw)
        orig_env, orig_call, orig_sleep = x.env_keys, x.Client.call, x.time.sleep
        x.env_keys = lambda: {'bearer': 'T'}
        x.Client.call = lambda self_, *a, **k: call(*a, **k)
        x.time.sleep = lambda s: None
        try:
            rc = None
            try:
                rc = x.cmd_post(type('A', (), {'req': rq, 'dir': d})())
            except SystemExit as e:
                rc = str(e)
        finally:
            x.env_keys, x.Client.call, x.time.sleep = orig_env, orig_call, orig_sleep
        posted = [c for c in calls if c[1] == '/2/tweets']
        return rc, posted, d

    def test_post_not_retried_by_client(self):
        self.assertTrue(all(c[3] is False for c in self._run({'النص': 'أ', 'الردود': ['ب']})[1]))

    def test_already_logged_skips(self):
        log = [{'id': '1', 'الطلب': 'r.json', 'الجزء': 0}, {'id': '2', 'الطلب': 'r.json', 'الجزء': 1}]
        rc, posted, _ = self._run({'النص': 'أ', 'الردود': ['ب']}, posts=log)
        self.assertEqual((rc, posted), (0, []))

    def test_resume_partial(self):
        rc, posted, _ = self._run({'النص': 'أ', 'الردود': ['ب', 'ج']}, posts=[{'id': '7', 'الطلب': 'r.json', 'الجزء': 0}])
        self.assertEqual(rc, 0)
        self.assertEqual([p[2]['text'] for p in posted], ['ب', 'ج'])
        self.assertEqual(posted[0][2]['reply']['in_reply_to_tweet_id'], '7')

    def test_same_text_in_account_blocks(self):
        recent = [{'id': '9', 'text': 'لا تصاميم ولا وعود… https://t.co/a', 'created_at': x.now().isoformat()}]
        rc, posted, _ = self._run({'النص': 'لا تصاميم  ولا وعود…'}, recent=recent)
        self.assertIn('لا نشر مكرّر', rc)
        self.assertEqual(posted, [])

    def test_explicit_repost_allowed(self):
        recent = [{'id': '9', 'text': 'أ', 'created_at': x.now().isoformat()}]
        rc, posted, _ = self._run({'النص': 'أ', 'إعادة_النشر': True}, recent=recent)
        self.assertEqual((rc, len(posted)), (0, 1))

    def test_unknown_5xx_found_in_account(self):
        # الخادم أخطأ لكنّ المنشور وصل: يُسجَّل ولا يُعاد، وتكمل السلسلة ردّاً عليه
        import json
        rc, posted, d = self._run({'النص': 'أ'}, fail_post_status=503)
        self.assertEqual((rc, len(posted)), (0, 1))
        self.assertEqual(json.load(open(os.path.join(d, 'posts.json'), encoding='utf-8'))[0]['id'], '101')

    def test_client_no_retry_on_5xx_when_not_idempotent(self):
        import urllib.error
        n = {'k': 0}

        def boom(req, timeout=0):
            n['k'] += 1
            raise urllib.error.HTTPError(req.full_url, 502, 'bad', {}, io.BytesIO(b'x'))
        import io
        orig, orig_sleep = x.urllib.request.urlopen, x.time.sleep
        x.urllib.request.urlopen, x.time.sleep = boom, (lambda s: None)
        try:
            c = x.Client({'bearer': 'T'}, x.Ledger(tempfile.mkdtemp()))
            with self.assertRaises(x.XError):
                c.call('POST', '/2/tweets', js={'text': 'أ'}, idempotent=False)
            self.assertEqual(n['k'], 1)
            n['k'] = 0
            with self.assertRaises(x.XError):
                c.call('GET', '/2/users/me', retries=3)
            self.assertEqual(n['k'], 3)
        finally:
            x.urllib.request.urlopen, x.time.sleep = orig, orig_sleep


if __name__ == '__main__':
    unittest.main()
