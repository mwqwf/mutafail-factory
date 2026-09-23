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


class RepairRerenderSource(unittest.TestCase):
    def test_repair_downloads_fall_back_to_this_run(self):
        wf = io.open(os.path.join(ROOT, ".github", "workflows", "film.yml"), encoding="utf-8").read()
        start = wf.index("  repair:")
        end = wf.index("  listening-gate:")
        block = wf[start:end]
        self.assertNotIn("run-id: ${{ needs.prepare.outputs.film_source_run }}\n", block)
        self.assertEqual(block.count("film_source_run || github.run_id"), 3)


class MergeToolSurvivesReset(unittest.TestCase):
    def test_tool_copied_before_reset(self):
        wf = open(os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "film.yml"), encoding="utf-8").read()
        i_cp = wf.index("cp tools/merge_playlists.py /tmp/state_keep/")
        i_reset = wf.index("git reset -q --hard origin/master")
        self.assertLess(i_cp, i_reset)
        self.assertIn("python3 /tmp/state_keep/.merge_playlists.py", wf)
        self.assertNotIn("python3 tools/merge_playlists.py", wf)
