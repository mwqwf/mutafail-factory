from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PrivateWorkflowTests(unittest.TestCase):
    def test_all_film_artifact_edges_use_private_wrappers(self):
        text=(ROOT/'.github/workflows/film.yml').read_text(encoding='utf-8')
        self.assertNotIn('uses: actions/upload-artifact',text)
        self.assertNotIn('uses: actions/download-artifact',text)
        self.assertEqual(text.count('uses: ./.github/actions/private-upload'),7)
        self.assertEqual(text.count('uses: ./.github/actions/private-download'),23)
        self.assertEqual(text.count("private-key: '${{ secrets.CONTENT_PRIVATE_KEY }}'"),23)

    def test_finish_uses_authenticated_decryption_not_plaintext_download(self):
        text=(ROOT/'.github/workflows/finish.yml').read_text(encoding='utf-8')
        self.assertIn('uses: ./.github/actions/private-download',text)
        self.assertNotIn('gh run download',text)
        self.assertIn('listening-gate',text)

if __name__=='__main__': unittest.main()
