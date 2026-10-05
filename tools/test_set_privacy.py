# -*- coding: utf-8 -*-
"""تغيير الخصوصية (tools/set_privacy.py) بلا شبكة: التحديث يحفظ كلّ حقلٍ ويغيّر الخصوصية وحدها، والمتجر يرفض «خاصّ»
ويُبقي التضمين، وما على حاله لا يُحدَّث، ولا حذف."""
import io, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_privacy as sp  # noqa: E402

ST = {'privacyStatus': 'public', 'embeddable': True, 'license': 'youtube', 'publicStatsViewable': True,
      'selfDeclaredMadeForKids': False, 'uploadStatus': 'processed'}


class Fake:
    def __init__(self, status):
        self.status, self.updates, self.deleted = dict(status), [], False

    def videos(self):
        me = self

        class V:
            def list(self, part, id):
                class R:
                    def execute(_):
                        return {'items': [{'status': dict(me.status), 'snippet': {'title': '3 أوت 2026'}}]}
                return R()

            def update(self, part, body):
                class R:
                    def execute(_):
                        me.updates.append(body); me.status.update(body['status']); return body
                return R()

            def delete(self, id):
                me.deleted = True
        return V()


class PlanTest(unittest.TestCase):
    def test_only_privacy_changes_and_store_rules(self):
        body, _ = sp.plan(ST, {'privacy': 'unlisted', 'store': True})
        self.assertEqual(body, {'embeddable': True, 'license': 'youtube', 'publicStatsViewable': True,
                                'selfDeclaredMadeForKids': False, 'privacyStatus': 'unlisted'})
        self.assertIsNone(sp.plan(ST, {'privacy': 'private', 'store': True})[0])          # المتجر لا يقبل الخاصّ
        self.assertIsNone(sp.plan(dict(ST, privacyStatus='unlisted'), {'privacy': 'unlisted', 'store': True})[0])
        self.assertIsNone(sp.plan(ST, {'privacy': 'hidden'})[0])


class RunTest(unittest.TestCase):
    def test_queue_update_verify_move_no_delete(self):
        d = tempfile.mkdtemp(); cwd = os.getcwd(); os.chdir(d)
        try:
            os.makedirs(sp.PENDING)
            json.dump({'privacy': 'unlisted', 'store': True}, open(os.path.join(sp.PENDING, 'CL4RGstCWc0.json'), 'w'))
            yt = Fake(ST)
            self.assertEqual(sp.run(yt), 0)
            self.assertEqual(yt.status['privacyStatus'], 'unlisted')
            self.assertTrue(yt.status['embeddable'])
            self.assertFalse(yt.deleted)
            self.assertFalse(os.path.exists(os.path.join(sp.PENDING, 'CL4RGstCWc0.json')))
            rec = json.load(io.open(os.path.join(sp.DONE, 'CL4RGstCWc0.json'), encoding='utf-8'))
            self.assertEqual(rec['النتيجة'], 'unlisted')
        finally:
            os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
