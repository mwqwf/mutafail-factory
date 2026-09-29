from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PrivateWorkflowTests(unittest.TestCase):
    def test_all_film_artifact_edges_use_private_wrappers(self):
        text=(ROOT/'.github/workflows/film.yml').read_text(encoding='utf-8')
        self.assertNotIn('uses: actions/upload-artifact',text)
        self.assertNotIn('uses: actions/download-artifact',text)
        # العددُ الثابت (10 و31) كسر الاختبار حين زِيدت رفعاتٌ خاصّة سليمة (14 و36)؛ فالعقدُ هو الثابت لا العدد:
        # كلُّ رفعٍ وتنزيلٍ يمرّ عبر الغلاف الخاص، وكلُّ تنزيلٍ يحمل مفتاح الفكّ.
        uploads = text.count('uses: ./.github/actions/private-upload')
        downloads = text.count('uses: ./.github/actions/private-download')
        self.assertGreaterEqual(uploads, 10)
        self.assertGreaterEqual(downloads, 31)
        self.assertEqual(text.count("private-key: '${{ secrets.CONTENT_PRIVATE_KEY }}'"), downloads)
        self.assertIn('python tools/repair_true_errors.py proj repair.json', text)
        self.assertIn('name: audio-final', text)
        self.assertIn('name: listen-final', text)
        self.assertIn('defer-resume:', text)

    def test_finish_uses_authenticated_decryption_not_plaintext_download(self):
        text=(ROOT/'.github/workflows/finish.yml').read_text(encoding='utf-8')
        self.assertIn('uses: ./.github/actions/private-download',text)
        self.assertNotIn('gh run download',text)
        self.assertIn('listening-gate',text)

if __name__=='__main__': unittest.main()
