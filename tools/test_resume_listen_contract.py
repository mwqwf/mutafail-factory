from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ResumeListeningContract(unittest.TestCase):
    def test_resume_reuses_old_media_and_current_listen_results(self):
        text = (ROOT/'.github/workflows/resume-listen.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', text)
        self.assertIn('cron: "5 7 17 9 *"', text)
        self.assertIn('2026-09-17', text)
        self.assertIn('ops/resume/*.json', text)
        self.assertIn('group: mutafail-film', text)
        self.assertIn('node tools/listen.js proj 2 --batch 4', text)
        self.assertIn('node tools/adjudicate_listen.js', text)
        self.assertIn('python tools/listen_gate.py proj', text)
        self.assertIn('python tools/publish_youtube.py proj', text)
        self.assertNotIn('gen25.js', text)
        self.assertNotIn('imgdl3.py', text)
        self.assertNotIn('turbo.py', text)
        self.assertGreaterEqual(text.count('run-id: ${{ needs.prepare.outputs.source_run }}'), 7)
        self.assertNotIn('actions/upload-artifact', text)
        self.assertNotIn('actions/download-artifact', text)

if __name__ == '__main__': unittest.main()
