import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from finish_command import read_command
from resume_deferred import next_deferred
import resume_deferred


class FinishCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "ops/finish").mkdir(parents=True)
        self.data = dict(runId="123", videoId="abcdefghijk", command="episode-1")

    def save(self):
        (self.root / "ops/finish/episode-1.json").write_text(
            json.dumps(self.data), encoding="utf-8")

    def test_valid(self):
        self.save()
        self.assertEqual(read_command(self.root, "ops/finish/episode-1.json"), self.data)

    def test_done_not_repeated(self):
        self.data.update({"تمّ": "done", "مؤجَّل": True})
        self.save()
        self.assertIsNone(next_deferred(self.root))

    def test_only_explicitly_deferred(self):
        self.save()
        self.assertIsNone(next_deferred(self.root))
        self.data["مؤجَّل"] = True
        self.save()
        self.assertEqual(next_deferred(self.root), "ops/finish/episode-1.json")

    def test_injection_rejected(self):
        self.data["command"] = "$(echo bad)"
        self.save()
        with self.assertRaises(ValueError):
            read_command(self.root, "ops/finish/episode-1.json")

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            read_command(self.root, "ops/finish/../../secret.json")

    def test_mismatch_rejected(self):
        self.data["command"] = "episode-2"
        self.save()
        with self.assertRaises(ValueError):
            read_command(self.root, "ops/finish/episode-1.json")

    @patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"})
    @patch("resume_deferred.subprocess.run")
    @patch("resume_deferred.subprocess.check_output")
    @patch("resume_deferred.next_deferred", return_value="ops/finish/episode-1.json")
    def test_explicit_dispatch(self, pending, query, dispatch):
        query.return_value = '[{"workflow_runs": []}]'
        resume_deferred.main()
        self.assertIn("workflow", dispatch.call_args.args[0])
        self.assertIn("command_file=ops/finish/episode-1.json", dispatch.call_args.args[0])

    @patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"})
    @patch("resume_deferred.subprocess.run")
    @patch("resume_deferred.subprocess.check_output")
    def test_queued_prevents_dispatch(self, query, dispatch):
        query.return_value = json.dumps([{"workflow_runs": [
            {"status": "queued", "path": ".github/workflows/finish.yml"}]}])
        resume_deferred.main()
        dispatch.assert_not_called()

    @patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"})
    @patch("resume_deferred.subprocess.run")
    @patch("resume_deferred.subprocess.check_output", side_effect=RuntimeError("API unavailable"))
    def test_api_failure_stops_dispatch(self, query, dispatch):
        with self.assertRaises(RuntimeError):
            resume_deferred.main()
        dispatch.assert_not_called()
