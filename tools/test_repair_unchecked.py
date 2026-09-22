# -*- coding: utf-8 -*-
"""⛔ حارسٌ على دورة الإصلاح: ما تردّه بوّابةُ الاستماع يُعاد توليدُه.

الثقبُ المقيس (شوط 35705031085): كتلةٌ بلا نتيجةِ فحصٍ ليست «خطأً مؤكَّداً»،
فكان العاملُ يتركها فتسقط البوّابةُ عليها كلَّ إعادةٍ حتى يُستنفد الشوط.
"""
import hashlib, io, json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repair_true_errors


def _project(tmp, results, reviews=None):
    os.makedirs(os.path.join(tmp, "audio"))
    blocks = [{"id": "d_001", "voice": "Charon", "text": "أَلِفْ"},
              {"id": "r_002", "voice": "Charon", "text": "بَاءْ"}]
    io.open(os.path.join(tmp, "blocks.json"), "w", encoding="utf-8").write(
        json.dumps(blocks, ensure_ascii=False))
    digests = {}
    for block in blocks:
        path = os.path.join(tmp, "audio", block["id"] + ".wav")
        open(path, "wb").write(block["id"].encode("utf-8"))
        digests[block["id"]] = hashlib.sha256(
            block["text"].encode("utf-8") + b"\0" + open(path, "rb").read()).hexdigest()
    filled = {}
    for ident, value in results.items():
        value = dict(value)
        if value.get("input_sha256") == "@":
            value["input_sha256"] = digests[ident]
        filled[ident] = value
    io.open(os.path.join(tmp, "listen_results.json"), "w", encoding="utf-8").write(
        json.dumps(filled, ensure_ascii=False))
    if reviews:
        out = {}
        for ident, value in reviews.items():
            value = dict(value)
            if value.get("input_sha256") == "@":
                value["input_sha256"] = digests[ident]
            out[ident] = value
        io.open(os.path.join(tmp, "listen_reviews.json"), "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False))
    return digests


def _run(tmp):
    out = os.path.join(tmp, "repair.json")
    repair_true_errors.main(tmp, out)
    return json.load(io.open(out, encoding="utf-8"))["ids"]


class RepairCoversUnchecked(unittest.TestCase):
    def test_block_without_any_result_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            _project(tmp, {"d_001": {"ok": True, "input_sha256": "@"}})
            self.assertEqual(_run(tmp), ["r_002"])

    def test_flagged_without_adjudication_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            _project(tmp, {"d_001": {"ok": True, "input_sha256": "@"},
                           "r_002": {"ok": False, "input_sha256": "@"}})
            self.assertEqual(_run(tmp), ["r_002"])

    def test_all_verified_rebuilds_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _project(tmp, {"d_001": {"ok": True, "input_sha256": "@"},
                           "r_002": {"ok": True, "input_sha256": "@"}})
            self.assertEqual(_run(tmp), [])

    def test_documented_false_positive_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            _project(tmp,
                     {"d_001": {"ok": True, "input_sha256": "@"},
                      "r_002": {"ok": False, "input_sha256": "@"}},
                     {"r_002": {"decision": "false_positive", "input_sha256": "@",
                                "reason": "الفارقُ في التشكيل لا في الحرف المنطوق",
                                "reviewer": "automated-independent-review:gemini",
                                "review_kind": "automated_independent",
                                "independence": "separate_call_same_model",
                                "heard": "باء", "written": "بَاءْ"}})
            self.assertEqual(_run(tmp), [])

    def test_rebuilt_block_loses_its_audio_and_stale_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            _project(tmp, {"d_001": {"ok": True, "input_sha256": "@"}})
            _run(tmp)
            self.assertFalse(os.path.isfile(os.path.join(tmp, "audio", "r_002.wav")))
            left = json.load(io.open(os.path.join(tmp, "listen_results.json"), encoding="utf-8"))
            self.assertNotIn("r_002", left)
            self.assertIn("d_001", left)

    def test_guard_is_wired_to_the_gate_itself(self):
        source = io.open(repair_true_errors.__file__, encoding="utf-8").read()
        self.assertIn("listen_gate", source)
        self.assertIn("stuck_unverified", source)


if __name__ == "__main__":
    unittest.main()
