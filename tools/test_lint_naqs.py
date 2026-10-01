# -*- coding: utf-8 -*-
"""حارس التنقّص (أمر المالك 2026-10-01): تعليقٌ يُفهم منه تنقّصٌ يوقف التوليد، والواقعة المجرّدة تمرّ."""
import os, subprocess, sys, tempfile, unittest
LINT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lint.py')

def run(text):
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(text)
    r = subprocess.run([sys.executable, LINT, f.name], capture_output=True, text=True)
    os.unlink(f.name); return r

class Naqs(unittest.TestCase):
    def test_commentary_blocks(self):
        r = run('d_001|C|وَقُتِلَ الْأَسْرَى، وَالتَّارِيخُ لَا يَعْمَلُ بِالْعَوَاطِفْ.\n')
        self.assertEqual(r.returncode, 1); self.assertIn('تنقّص', r.stdout)
    def test_judgement_on_companion_blocks(self):
        self.assertEqual(run('d_002|C|حِينَ أَخْطَأَ أَحَدُهُمْ خَطَأً كَبِيرًا قَالَ النَّبِيّْ.\n').returncode, 1)
    def test_plain_fact_passes(self):
        r = run('d_003|C|وَانْهَزَمَتْ قُرَيْشٌ حِينَ زَالَتِ الشَّمْسْ.\nIMG:F001|desert, no text\n')
        self.assertEqual(r.returncode, 0, r.stdout)

if __name__ == '__main__': unittest.main()
