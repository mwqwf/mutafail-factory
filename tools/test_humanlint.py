# -*- coding: utf-8 -*-
"""اختبارُ حارسِ الأسلوب البشريّ — يُختبر نصّاً قبل أن يُعتمد (شرطُ الدستور).

⛔ وهذه الاختباراتُ نفسُها حارسٌ على الحارس: تمنع أن يُفرَّغ من مضمونه بتخفيف
   عتبةٍ أو بحذفِ استدعائه من `precheck.py`.
"""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import humanlint

ROOT = Path(__file__).resolve().parents[1]

# كتلٌ متساويةُ الطول، كلُّها تبدأ بالواو، بلا سؤالٍ ولا جملةٍ قصيرة — نمطُ المولِّد
ROBOTIC = "\n".join(
    "d_%03d|C|وَكَانَ هَذَا الْأَمْرُ ظَاهِراً فِي تِلْكَ الْبِلَادِ ظُهُوراً بَيِّناً لَا يَخْفَى عَلَى النَّاظِرِ رَقْمُ %d."
    % (i, i) for i in range(1, 41))

HUMAN = """d_001|C|هَذَا هُوَ السُّؤَالْ.
d_002|C|وَلِمَ لَمْ يَحْرُثِ النَّاسُ بِالْخَيْلِ وَهِيَ أَسْرَعُ مِنَ الثَّوْرِ فِي كُلِّ شَيْءْ؟
d_003|C|الْجَوَابُ لَيْسَ فِي السُّرْعَةْ.
d_004|C|هُوَ فِي رَقَبَةِ الْحَيَوَانِ نَفْسِهَا، وَفِي طَرِيقَةِ رَبْطِ الْحَبْلِ عَلَيْهَا، وَهَذَا مَا سَنُفَصِّلُهُ الْآنَ بِشَيْءٍ مِنَ الْبَيَانْ.
d_005|C|فَالثَّوْرُ لَهُ كَتِفٌ عَرِيضٌ يَسْتَقِرُّ عَلَيْهِ النِّيرْ.
d_006|C|أَمَّا الْفَرَسُ فَيَضْغَطُ الْحَبْلُ عَلَى حَلْقِهِ، فَيَخْنُقُهُ، فَتَذْهَبُ قُوَّتُهُ فِي غَيْرِ مَا أُرِيدَ لَهَا أَنْ تَذْهَبَ فِيهِ أَصْلاً.
d_007|C|جَرِّبْ أَنْ تَشُدَّ حَبْلاً عَلَى عُنُقِكَ ثُمَّ تَجُرَّ ثَقِيلاً، تَعْرِفِ الْمَعْنَى بِلَا شَرْحْ.
d_008|C|وَهُنَاكَ سَبَبٌ ثَانٍ أَرْخَصُ وَأَوْضَحْ.
d_009|C|الْعَلَفْ.
d_010|C|فَالْفَرَسُ يُرِيدُ حُبُوباً غَالِيَةً كُلَّ يَوْمٍ، وَالثَّوْرُ يَكْفِيهِ تِبْنٌ وَكَلَأٌ مِمَّا لَا يَأْكُلُهُ الْإِنْسَانُ أَصْلاً.
d_011|C|وَمَنْ كَانَ فِي جَيْبِهِ قَلِيلٌ اخْتَارَ الرَّخِيصْ.
d_012|C|هَكَذَا كَانَتِ الْمَسْأَلَةُ فِي عَيْنِ الْفَلَّاحِ: لَا ذَوْقَ وَلَا عَادَةَ، بَلْ حِسَابُ مَا يَمْلِكُ وَمَا يُطِيقْ.
d_013|C|وَفِي الشَّمَالِ حَيْثُ رَخُصَ الشَّعِيرُ دَخَلَتِ الْخَيْلُ الْحَقْلَ بِالْفِعْلْ.
d_014|C|وَبَقِيَ الثَّوْرُ سَيِّدَ الْمِحْرَاثِ فِي سَائِرِ الْأَرْضْ.
d_015|C|ثُمَّ جَاءَ الْمُحَرِّكْ.
d_016|C|فَانْتَهَى الْجِدَالُ كُلُّهُ فِي عِشْرِينَ سَنَةً، لَا بِحُجَّةٍ وَلَا بِفَتْوَى، بَلْ بِثَمَنِ بِرْمِيلِ وَقُودٍ صَارَ فِي مُتَنَاوَلِ الْمَزَارِعْ.
d_017|C|أَتَظُنُّ أَنَّ الْفَلَّاحَ حَزِنَ عَلَى ثَوْرِهْ؟
d_018|C|بَعْضُهُمْ حَزِنَ فِعْلاً، وَكُتِبَتْ فِي ذَلِكَ رَسَائِلُ تُقْرَأُ الْيَوْمَ فَيُعْجَبُ مِنْهَا النَّاسْ.
d_019|C|لَكِنَّ الْأَرْضَ لَا تَنْتَظِرُ حُزْنَ أَحَدْ.
d_020|C|وَالْمَطَرُ يَنْزِلُ فِي وَقْتِهِ، فَمَنْ لَمْ يَكُنْ قَدْ حَرَثَ فَقَدْ خَسِرَ سَنَتَهُ كُلَّهَا مَهْمَا كَانَ وَفِيّاً لِدَابَّتِهْ.
d_021|C|هَذَا كُلُّ مَا فِي الْأَمْرْ.
d_022|C|وَالْبَاقِي تَفْصِيلٌ سَنَأْتِي عَلَيْهِ فِي مَوْضِعِهِ مِنَ الْحَلَقَةِ بَعْدَ قَلِيلٍ إِنْ شَاءَ اللَّهْ.
"""


def _write(tmp, script, review=None):
    io.open(os.path.join(tmp, "script.md"), "w", encoding="utf-8").write(script)
    if review is not None:
        io.open(os.path.join(tmp, "style_review.json"), "w", encoding="utf-8").write(
            json.dumps(review, ensure_ascii=False))
    return tmp


class HumanLintGuard(unittest.TestCase):
    def test_robotic_script_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, ROBOTIC)
            self.assertEqual(humanlint.main(tmp), 1)

    def test_robotic_flags_name_the_three_measures(self):
        blocks = humanlint.read_blocks(_write(tempfile.mkdtemp(), ROBOTIC) + "/script.md")
        rules = {f[0] for f in humanlint.audit(blocks)}
        self.assertIn("uniform_length", rules)
        self.assertIn("no_short_beats", rules)
        self.assertIn("waw_opening", rules)

    def test_human_script_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, HUMAN)
            self.assertEqual(humanlint.main(tmp), 0)

    def test_blanket_waiver_is_refused(self):
        """«كلُّ الرايات مقبولة» ليس تحكيماً — ولا تعليلٌ قصيرٌ ولا محكِّمٌ مجهول."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, ROBOTIC, {"all": True, "rules": {"uniform_length": {"reason": "مقبول"}}})
            self.assertEqual(humanlint.main(tmp), 1)

    def test_named_written_arbitration_is_honoured(self):
        reasons = {
            r: {"reason": "تحكيمٌ مكتوبٌ مفصَّلٌ يبيّن سببَ قبولِ هذه الرايةِ في هذه الحلقةِ بعينها",
                "reviewer": "مناوبةُ التحرير"}
            for r in ("uniform_length", "no_short_beats", "waw_opening",
                      "repeated_opening", "no_questions")
        }
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, ROBOTIC, {"rules": reasons})
            self.assertEqual(humanlint.main(tmp), 0)

    def test_precheck_still_calls_the_guard(self):
        text = (ROOT / "tools" / "precheck.py").read_text(encoding="utf-8")
        self.assertIn('"humanlint.py"', text)


if __name__ == "__main__":
    unittest.main()
