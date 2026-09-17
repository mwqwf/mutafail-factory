from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ResumeListeningContract(unittest.TestCase):
    def test_resume_reuses_old_media_and_current_listen_results(self):
        text = (ROOT/'.github/workflows/resume-listen.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', text)
        self.assertIn('cron: "5 7 * * *"', text)
        self.assertNotIn('paths: ["ops/resume/*.json"]', text)
        self.assertIn('active=false', text)
        self.assertIn('group: mutafail-film', text)
        self.assertIn('node tools/listen.js proj 2 --batch 4', text)
        self.assertIn('node tools/adjudicate_listen.js', text)
        self.assertIn('python tools/listen_gate.py proj', text)
        self.assertIn('python tools/publish_youtube.py proj', text)
        self.assertIn('repair_true_errors.py', text)
        self.assertIn('node tools/gen25.js proj 1', text)
        self.assertIn('--shard "$shard" --shards 3', text)
        self.assertIn('name: film-final', text)
        self.assertIn('listen_public_summary.py', text)
        self.assertNotIn('imgdl3.py', text)
        self.assertIn('python tools/turbo.py "$PWD/proj" 0 1', text)
        self.assertGreaterEqual(text.count('run-id: ${{ needs.prepare.outputs.source_run }}'), 7)
        self.assertNotIn('actions/upload-artifact', text)
        self.assertNotIn('actions/download-artifact', text)

if __name__ == '__main__': unittest.main()
