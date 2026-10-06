# -*- coding: utf-8 -*-
"""حارس المحظورات (tools/guard.py): سطور IMG في script.md، وأوامر كوديكس في codex_job.json (ثغرة مؤتة 2026-10-05)،
والمصغّرات تُعفى من الجملة الواقية ومن قاعدة الكتابة وحدهما لا من المحظورات."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402

TAIL = guard.REQUIRED_TAIL


def run(path):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = guard.main(path)
    return rc, buf.getvalue()


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def job(self, items):
        p = os.path.join(self.d, 'codex_job.json')
        json.dump({'folder': 'x', 'status': 'pending', 'items': items}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        return p

    def test_codex_job_is_checked(self):
        ok = {'file': 'images/A01.jpg', 'prompt': 'A banner in the dust, men seen from behind. ' + TAIL}
        self.assertEqual(run(self.job([ok]))[0], 0)
        rc, out = run(self.job([ok, {'file': 'images/A02.jpg', 'prompt': 'A woman at the tent. ' + TAIL},
                                {'file': 'images/A03.jpg', 'prompt': 'Riders on a road.'}]))
        self.assertEqual(rc, 1)
        self.assertIn('نساء', out)
        self.assertIn('الجملة الواقية ناقصة', out)
        self.assertIn('codex_job.json:images/A03.jpg', out)

    def test_thumbnail_text_allowed_but_bans_remain(self):
        th = {'file': 'thumbs/m-A.png', 'prompt': 'Write ONLY this Arabic text, large letters: «سيف الله». Only adult men.'}
        self.assertEqual(run(self.job([th]))[0], 0)
        rc, out = run(self.job([dict(th, prompt=th['prompt'] + ' A drum in the corner.')]))
        self.assertEqual(rc, 1)
        self.assertIn('آلات موسيقية', out)

    def test_text_cards_allowed_but_bans_remain(self):
        c = {'file': 'cards/slam_1.png', 'prompt': 'Huge Arabic display lettering: «سيف الله». Output a PNG with transparency.'}
        self.assertEqual(run(self.job([c]))[0], 0)
        rc, out = run(self.job([dict(c, prompt=c['prompt'] + ' A woman holds it.')]))
        self.assertEqual(rc, 1)
        self.assertIn('نساء', out)

    def test_script_md_still_checked(self):
        p = os.path.join(self.d, 'script.md')
        io.open(p, 'w', encoding='utf-8').write('n_001|S|نصّ\nIMG:A01|1920|Riders at dawn, a girl watching. ' + TAIL + '\n')
        rc, out = run(p)
        self.assertEqual(rc, 1)
        self.assertIn('نساء', out)


if __name__ == '__main__':
    unittest.main()
