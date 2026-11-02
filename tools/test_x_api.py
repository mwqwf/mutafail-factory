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


if __name__ == '__main__':
    unittest.main()
