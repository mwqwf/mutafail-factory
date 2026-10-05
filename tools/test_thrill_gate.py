import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thrill_gate as g  # noqa: E402


def proj(blocks, sections, reels, title="سؤال؟", shots=None, genre=None):
    d = Path(tempfile.mkdtemp())
    pub = {"film": {"title": title}, **({"genre": genre} if genre else {})}
    files = [("blocks.json", blocks), ("sections.json", sections), ("reels.json", reels), ("publish.json", pub)]
    if shots is not None:
        files.append(("shots.json", shots))
    for name, obj in files:
        (d / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return d


def B(i, t, **k):
    return dict({"id": i, "voice": "Charon", "text": t}, **k)


GOOD = [B("d1", "سُفُنٌ تَمْشِي عَلَى ظُهُورِ الْإِبِلْ."), B("d2", "فَمَنْ صَاحِبُ الْفِكْرَةِ؟"), B("d3", "وَإِلَى أَيْنَ؟ سَنَكْشِفُ لَكُمْ"),
        B("d4", "ثُمَّ مَاذَا جَرَى؟"), B("d5", "فَصْلٌ ثَانٍ يَبْدَأُ قَصِيرًا"), B("d6", "وَلَكِنَّ الْمُفَاجَأَةَ لَمْ تَأْتِ بَعْدُ…")]
REELS = [{"id": f"r{i}", "blocks": [f"x{i}a", f"x{i}b"]} for i in (1, 2, 3)]
RB = [b for i in (1, 2, 3) for b in (B(f"x{i}a", "صَدْمَةٌ قَصِيرَةٌ.", reel_only=True), B(f"x{i}b", "فَمَنْ؟ الْجَوَابُ فِي الْفِيلْمْ.", reel_only=True))]
SECS = [{"id": "d1", "title": "أ"}, {"id": "d5", "title": "ب"}]
# ⭐ حكم المالك 2026-10-05: الافتتاح البارد مشهدٌ متّصل ≥ 25 ث بلا سؤال (4 × 14 كلمة × 0.46 ث ≈ 26 ث)
COLD = [B(f"k{i}", " ".join(["سُيُوفٌ"] * 14) + ".") for i in range(1, 5)]
SECS_C = [{"id": "k1", "title": "أ"}, {"id": "d5", "title": "ب"}]


class ThrillGateTests(unittest.TestCase):
    def test_good_structure_passes(self):
        errs, _ = g.check(proj(COLD + GOOD + RB, SECS_C, REELS), None)
        self.assertEqual(errs, [])

    def test_greeting_first_flat_chapter_and_two_reels_fail(self):
        blocks = [B("d0", "السَّلَامُ عَلَيْكُمْ")] + GOOD[1:3] + [B("d4", "وَانْتَهَى الْفَصْلُ.")] + GOOD[4:] + RB
        errs, _ = g.check(proj(blocks, SECS, REELS[:2]), None)
        text = "\n".join(errs)
        self.assertIn("تحيّة", text)
        self.assertIn("بمعلّقة", text)
        self.assertIn("2 ريلز", text)

    def test_owner_reel_count_override(self):
        # الأرك 2026-10-04: «الريلزات يكفي اثنان فقط لهذا الفيلم» ⇒ publish.json: reels_required = 2
        d = proj(GOOD + RB, SECS, REELS[:2])
        pub = json.loads((d / "publish.json").read_text(encoding="utf-8")); pub["reels_required"] = 2
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertFalse(any("ريلز (المطلوب" in e for e in errs))

    def test_thumb_text_with_tashkeel_or_too_long_fails(self):
        d = proj(GOOD + RB, SECS, REELS)
        t = d / "thumbs.json"
        t.write_text(json.dumps({"thumbs": [{"file": "a.png", "text": ["أسوارٌ صمدت ألف عام"]}]}, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, t)
        self.assertTrue(any("مشكول" in e for e in errs) and any("طويل" in e for e in errs))


    # ⭐ الإيقاع والتركيز على المعركة (أمر المالك 2026-10-03)
    def battle(self, phases, words_per=(4, 4, 4, 4)):
        w = lambda n, tail="": " ".join(["كَلِمَةٌ"] * n) + tail
        blocks = COLD + [B("d1", "سُيُوفٌ فِي اللَّيْلِ"), B("d2", "فَمَنْ؟"), B("d3", "وَلِمَاذَا؟")]
        secs = [{"id": "k1", "title": "افتتاح"}]
        for k, (ph, n) in enumerate(zip(phases, words_per)):
            i = f"c{k}"
            blocks.append(B(i, w(n, "؟")))
            secs.append({"id": i, "title": ph, "phase": ph})
        return blocks + RB, secs

    def test_battle_film_needs_phases_and_battle_focus(self):
        blocks, secs = self.battle(["setup", "buildup", "battle", "aftermath"], (40, 20, 20, 20))
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        text = "\n".join(errs)
        self.assertIn("المعركة 20%", text)
        self.assertIn("التمهيد 40%", text)
        self.assertIn("أوّل كتلة قتالٍ", text)
        for x in secs:
            x.pop("phase", None)
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        self.assertTrue(any("phase" in e for e in errs))

    def test_battle_focused_film_passes(self):
        blocks, secs = self.battle(["setup", "battle", "battle", "aftermath"], (5, 50, 40, 5))
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        self.assertEqual(errs, [])

    def test_long_still_shot_fails_pacing(self):
        long_ = B("d4", " ".join(["كَلِمَةٌ"] * 40) + "؟")
        blocks = GOOD[:3] + [long_] + GOOD[4:] + RB
        shots = [{"id": "S1", "blocks": ["d1", "d2", "d3"]}, {"id": "S2", "blocks": ["d4"]}, {"id": "S3", "blocks": ["d5", "d6"]}]
        errs, _ = g.check(proj(blocks, SECS, REELS, shots=shots), None)
        self.assertTrue(any("أطول من" in e and "S2" in e for e in errs))

    def test_absolute_superlative_in_title_fails_but_qualified_and_takbir_pass(self):
        errs, _ = g.check(proj(GOOD + RB, SECS, REELS, title="أعظم معركة في التاريخ؟"), None)
        self.assertTrue(any("تفضيلٌ مطلق" in e for e in errs))
        ok = COLD + GOOD[:4] + [B("d5", "اللَّهُ أَكْبَرُ")] + GOOD[5:] + RB
        errs, warns = g.check(proj(ok, SECS_C, REELS, title="من أعظم معارك التاريخ؟"), None)
        self.assertEqual(errs, [])
        self.assertFalse(any("تفضيلٌ مطلق" in w for w in warns))


    def test_source_citation_in_narration_fails(self):
        blocks = GOOD[:4] + [B("d5", "رَوَاهُ الْإِمَامُ أَحْمَدُ وَحَسَّنَهُ الْهَيْثَمِيُّ.")] + GOOD[5:] + RB
        errs, _ = g.check(proj(blocks, SECS, REELS), None)
        self.assertTrue(any("ذكرُ مصدرٍ" in e and "d5" in e for e in errs))

    def test_animation_cost_must_fit_budget(self):
        long_ = [B(f"L{i}", " ".join(["كَلِمَةٌ"] * 15) + "؟") for i in range(60)]
        blocks = GOOD + long_ + RB
        shots = [{"id": f"S{i}", "kind": "حيّة", "blocks": [f"L{i}"]} for i in range(60)]
        d = proj(blocks, SECS, REELS, shots=shots)
        pub = json.loads((d / "publish.json").read_text(encoding="utf-8")); pub["budget_total_usd"] = 15
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertTrue(any("قصّر الفيلم" in e for e in errs))   # 60 × 6.9 ث × 0.07$ ≈ 29$ > 13.5$
        pub["budget_total_usd"] = 65
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertFalse(any("قصّر الفيلم" in e for e in errs))


    # ⭐⭐ حكم المالك 2026-10-05: موانع الافتتاح البارد والطلب والأرقام واللقطات والدقائق 1–6 والسلسلة والمأثور
    def test_owner_1005_rules_fail_and_pass(self):
        w = lambda n, tail=".": " ".join(["كَلِمَةٌ"] * n) + tail
        bad = [B("a1", "فَمَنْ هَذَا الرَّجُلُ؟"), B("a2", "ثَلَاثَةُ آلَافٍ أَمَامَ مِئَتَيْ أَلْفٍ سَنَةَ ثَمَانٍ لِلْهِجْرَةِ.")]
        bad += [B("a3", w(14)), B("a4", "اشْتَرِكُوا فِي الْقَنَاةِ وَفَعِّلُوا الْجَرَسَ؟")]
        bad += [B(f"z{i}", w(14)) for i in range(20)] + [B("q1", "قَالَ:", speaker="ابن رواحة")]
        d = proj(bad + RB, [{"id": "a1", "title": "أ"}, {"id": "z0", "title": "ب"}], REELS)
        pub = json.loads((d / "publish.json").read_text(encoding="utf-8")); pub["series"] = "سيف الله"
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        (d / "shots.json").write_text(json.dumps([{"id": "S1", "blocks": ["a1", "a2", "a3", "a4"]}]), encoding="utf-8")
        text = "\n".join(g.check(d, None)[0])
        for k in ("قبل الدقيقة الرابعة", "الافتتاح البارد يُقطع", "أرقام في أوّل 30", "تاريخٌ في أوّل 30", "لقطةً في أوّل 30",
                  "بلا إعادة شدٍّ", "خطّافٍ للحلقة التالية", "بلا رقم دعوى"):
            self.assertIn(k, text)
        good = COLD + [B("g1", "فَمَنْ يَرْفَعُ الرَّايَةَ؟")] + [B(f"y{i}", w(14, "…")) for i in range(30)]
        good += [B("n1", "وَفِي الْحَلْقَةِ الْقَادِمَةِ… حَدِيقَةُ الْمَوْتِ؟"), B("q2", "قَالَ:", speaker="ابن رواحة", claim="م-12")]
        d2 = proj(good + RB, [{"id": "k1", "title": "أ"}, {"id": "y0", "title": "ب"}], REELS)
        pub["film"] = {"title": "سؤال؟"}
        (d2 / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        (d2 / "shots.json").write_text(json.dumps([{"id": f"H{i}", "blocks": [], "hold": 2} for i in range(13)] +
                                                   [{"id": "S", "blocks": [b["id"] for b in good]}]), encoding="utf-8")
        text = "\n".join(g.owner_1005(good, good, json.loads((d2 / "shots.json").read_text(encoding="utf-8")), pub)[0])
        self.assertEqual(text, "")

    def test_story_promise_is_timed_not_counted(self):
        # مؤتة 2026-10-05: جملٌ قصيرةٌ كثيرة في الافتتاح تدفع الوعد إلى الكتلة الخامسة عشرة وهو عند الثانية 45
        short = [B("s%02d" % i, "سُيُوفٌ تَنْقَطِعُ.") for i in range(1, 15)]                   # 14 × 2 كلمة ≈ 13 ث
        promise = B("p1", "سَتَرَى كَيْفَ صَارَ رَجُلٌ بِلَا إِمْرَةٍ سَيْفاً.")
        _, warns = g.check(proj(short + [promise] + GOOD + RB, [{"id": "s01", "title": "أ"}, {"id": "d5", "title": "ب"}],
                                REELS), None)
        self.assertFalse(any("لا وعدَ صريحاً" in w for w in warns))
        late = [B("l%d" % i, " ".join(["سُيُوفٌ"] * 30) + ".") for i in range(1, 6)]           # 5 × 30 كلمة ≈ 69 ث
        _, warns = g.check(proj(late + [promise] + GOOD + RB, [{"id": "l1", "title": "أ"}, {"id": "d5", "title": "ب"}],
                                REELS), None)
        self.assertTrue(any("لا وعدَ صريحاً" in w for w in warns))

    def test_debunk_promise_loops_and_citations(self):
        w = lambda n, tail=".": " ".join(["كَلِمَةٌ"] * n) + tail
        pub = {"series": "سيف الله"}
        # وعد الكشف في أوّل ثلاث دقائق مانع (دراسة الأسلوب 2026-10-05)، والوعد بالقصّة جائز
        film = COLD + [B("p1", "وَسَنَكْشِفُ لَكُمْ حَقَائِقَ كُنْتُمْ تَحْسَبُونَهَا مُسَلَّمَاتٍ؟")] + [B(f"y{i}", w(14, "…")) for i in range(30)]
        self.assertIn("وعدُ كشفٍ", "\n".join(g.owner_1005(film, film, [], pub)[0]))
        film[4] = B("p1", "وَسَتَرَى كَيْفَ خَرَجُوا مِنْ بَيْنِ أَيْدِيهِمْ؟")
        self.assertNotIn("وعدُ كشفٍ", "\n".join(g.owner_1005(film, film, [], pub)[0]))
        # سجلّ الحلقات: حلقةٌ واحدة مفتوحة بعد الثانية 45 لا تكفي، وإعادة الشدّ تُقاس بالفتح لا بالترقيم
        loops = COLD[:1] + [dict(COLD[1], opens=["سيوف"])] + COLD[2:] + [B("c1", w(14), opens=["نجاة"])]
        loops += [B(f"l{i}", w(14, "…"), closes=["سيوف"] if i == 3 else []) for i in range(30)]
        text = "\n".join(g.owner_1005(loops, loops, [], pub)[0])
        self.assertIn("حلقاتٍ مفتوحة", text)
        self.assertIn("بلا إعادة شدٍّ", text)                          # «…» لا تُحسب حين يوجد السجلّ
        self.assertIn("ذكرُ مصدرٍ", "\n".join(g.check(proj(COLD + GOOD + [B("e1", "وَيَرْوِي ابْنُ إِسْحَاقَ أَنَّهُ…")] + RB, SECS_C, REELS), None)[0]))
        self.assertEqual(g.absolute("أَخْطَرُ مَنِ ادَّعَى النُّبُوَّةَ"), ["أخطر"])
        self.assertEqual(g.absolute("مِنْ أَخْطَرِ الْمَعَارِكِ"), [])


if __name__ == "__main__":
    unittest.main()
