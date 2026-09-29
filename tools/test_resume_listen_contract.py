from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ResumeListeningContract(unittest.TestCase):
    """resume-listen.yml صار سيرَ «نشر amal-4 المجاني مرة واحدة» يُطلق بالدفع (لا يدوياً ولا بجدول).
    العقد: عامٌّ مجانيّ، لا يتكرّر بعد النشر، يمرّ ببوّابة الإصغاء وفحص ما قبل النشر، وكلُّ تنزيلٍ خاصٌّ مشفّر."""
    def test_one_time_free_publish_contract(self):
        text = (ROOT/'.github/workflows/resume-listen.yml').read_text(encoding='utf-8')
        self.assertIn("- 'ops/resume-free-amal4.txt'", text)
        self.assertNotIn('workflow_dispatch:', text)
        self.assertNotIn('cron:', text)
        self.assertIn('github.event.repository.private', text)      # يرفض العمل في مستودعٍ خاصٍّ مدفوع
        self.assertIn('active=', text)                              # منع التكرار بعد النشر
        self.assertIn('group: mutafail-film', text)
        self.assertIn('python tools/listen_gate.py proj', text)
        self.assertIn('python tools/publish_preflight.py proj amal-4', text)
        self.assertIn('python tools/publish_youtube.py proj', text)
        downloads = text.count('uses: ./.github/actions/private-download')
        self.assertGreater(downloads, 0)
        self.assertEqual(text.count("private-key: '${{ secrets.CONTENT_PRIVATE_KEY }}'"), downloads)
        self.assertNotIn('actions/upload-artifact', text)
        self.assertNotIn('actions/download-artifact', text)
        self.assertNotIn('imgdl3.py', text)

if __name__ == '__main__': unittest.main()
