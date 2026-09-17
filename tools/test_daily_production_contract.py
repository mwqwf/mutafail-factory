from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DailyProductionContract(unittest.TestCase):
    def test_controller_dispatches_only_ready_sealed_command(self):
        controller = (ROOT / '.github/workflows/daily-production.yml').read_text(encoding='utf-8')
        film = (ROOT / '.github/workflows/film.yml').read_text(encoding='utf-8')
        self.assertIn('actions: write', controller)
        self.assertIn('ops/ready/*.json', controller)
        self.assertIn('payload.enc', controller)
        self.assertIn('key.enc', controller)
        self.assertIn('gh workflow run film.yml', controller)
        self.assertIn('gh workflow run resume-listen.yml', controller)
        self.assertIn('gh workflow run finish.yml', controller)
        self.assertIn("if now.hour == 7:", controller)
        self.assertIn('steps.deferred.outputs.resume_file', controller)
        self.assertIn('steps.deferred.outputs.finish_file', controller)
        self.assertIn("resume=f'ops/resume/{slug}.json'", controller)
        self.assertIn("if pending: continue", controller)
        self.assertIn('group: mutafail-film', film)
        self.assertIn('workflow_dispatch:', film)
        self.assertIn('COMMAND_DIR: ${{ inputs.command_dir }}', film)
        self.assertIn("d['تمّ']", film)


if __name__ == '__main__': unittest.main()
