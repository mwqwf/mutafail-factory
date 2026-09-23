# -*- coding: utf-8 -*-
"""⛔ حارسٌ على حفظ الحالة: لا يمحو شوطٌ ما كتبه غيرُه في master."""
import io, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge_playlists

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StateMerge(unittest.TestCase):
    def test_master_playlist_survives_a_stale_run_copy(self):
        master = {"القوائم": {"أ": "P1", "كائنات": "PLJ"}, "السلاسل": {"كائنات": "PLJ"},
                  "السلسلة_الجارية": "كائنات"}
        run = {"القوائم": {"أ": "P1", "جديدة": "P2"}, "السلاسل": {"جديدة": "P2"},
               "السلسلة_الجارية": "جديدة"}
        out = merge_playlists.merge(master, run)
        self.assertEqual(out["القوائم"], {"أ": "P1", "كائنات": "PLJ", "جديدة": "P2"})
        self.assertEqual(out["السلاسل"], {"كائنات": "PLJ", "جديدة": "P2"})
        self.assertEqual(out["السلسلة_الجارية"], "جديدة")

    def test_publish_step_no_longer_copies_the_whole_state_dir(self):
        wf = io.open(os.path.join(ROOT, ".github", "workflows", "film.yml"), encoding="utf-8").read()
        self.assertNotIn("cp -a /tmp/state_keep/state/. ops/state/", wf)
        self.assertIn("merge_playlists.py", wf)
        self.assertIn("--untracked-files=all ops/state ops/ready", wf)


if __name__ == "__main__":
    unittest.main()
