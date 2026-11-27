"""اختبارات tools/source_lookup.py بلا شبكة (كل النداءات مُحاكاة)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import source_lookup as sl  # noqa: E402

MATN = "حدثنا فلان عن فلان قال كنا مع رسول الله بعسفان وعلى المشركين خالد بن الوليد فصلينا الظهر فقال المشركون لقد اصبنا غره لقد اصبنا غفله"


def api_json(num, text=MATN, grades=None):
    return {"hadiths": [{"hadithnumber": num, "arabicnumber": num, "text": text,
                         "grades": grades or [{"name": "Al-Albani", "grade": "Hasan Sahih"}, {"name": "X", "grade": "-"}],
                         "reference": {}}]}


def find_result(page_id, text):
    return {"results": [], "evidence": {"sources": [
        {"book_id": 117359, "page_id": page_id, "text": text,
         "citation": {"markdown": f"[سنن أبي داود](https://shamela.ws/book/117359/{page_id})"}}]}}


class Helpers(unittest.TestCase):
    def test_number_marker_boundaries(self):
        self.assertTrue(sl.has_number_marker("نص ١٢٣٦ - حدثنا", 1236))
        self.assertFalse(sl.has_number_marker("نص ١١٢٣٦ - حدثنا", 1236))
        self.assertFalse(sl.has_number_marker("١٢٣٦٧ - حدثنا", 1236))

    def test_segments_range_and_continuation(self):
        segs = sl.segments("تتمة سابقة. ٢٧٣١ - ٢٧٣٢ - حدثني عبد الله ... ٢٧٣٣ - حدثنا آخر")
        self.assertIsNone(segs[0][0])
        self.assertEqual(segs[1][0], {2731, 2732})
        self.assertEqual(segs[2][0], {2733})

    def test_resolve_book_arabic(self):
        self.assertEqual(sl.resolve_book("البخاري"), "bukhari")
        self.assertEqual(sl.resolve_book("أبو داود"), "abudawud")

    def test_phrase_windows_from_matn(self):
        w = sl.phrase_windows(MATN)
        self.assertTrue(w and all(len(p.split()) == 9 for p in w))
        self.assertTrue(all(sl.contains_phrase(MATN, p) for p in w))

    def test_grades_drop_dash(self):
        with mock.patch.object(sl, "get_json", return_value=api_json(1236)):
            g = sl.hadith_api("abudawud", 1236)["grades"]
        self.assertEqual([x["name"] for x in g], ["Al-Albani"])


class Verify(unittest.TestCase):
    def run_verify(self, page_text, number=1236, pages=None):
        pages = pages or {}

        def fake_mcp(url, name, args):
            if name == "shamela_find_scoped":
                return find_result(1044, page_text)
            if name == "shamela_open":
                return pages[args["page_id"]]
            raise AssertionError(name)
        with mock.patch.object(sl, "get_json", return_value=api_json(number)), \
             mock.patch.object(sl, "mcp_call", side_effect=fake_mcp):
            return sl.verify_hadith("abudawud", number)

    def test_verified_when_number_owns_phrase(self):
        r = self.run_verify("١٢٣٥ - حدثنا غيره. ١٢٣٦ - " + MATN)
        self.assertEqual(r["status"], "verified")
        self.assertEqual(r["shamela"]["shamela_numbers"], [1236])

    def test_mismatch_when_phrase_under_other_number(self):
        r = self.run_verify("١٢٣٦ - حدثنا غيره. ١٢٣٧ - " + MATN)
        self.assertEqual(r["status"], "mismatch")
        self.assertEqual(r["shamela"]["shamela_numbers"], [1237])

    def test_continuation_walks_back_to_previous_page(self):
        pages = {1044: {"text": MATN, "navigation": {"previous_page_id": 1043}},
                 1043: {"text": "١٢٣٥ - شيء. ١٢٣٦ - حدثنا سعيد", "navigation": {"previous_page_id": 1042}}}
        r = self.run_verify(MATN, pages=pages)
        self.assertEqual(r["status"], "verified")

    def test_unverifiable_when_phrase_absent(self):
        pages = {1044: {"text": "نص لا علاقة له", "navigation": {}}}
        r = self.run_verify("نص لا علاقة له", pages=pages)
        self.assertEqual(r["status"], "unverifiable")

    def test_unknown_book_is_not_verified(self):
        with mock.patch.object(sl, "get_json", return_value=api_json(5)):
            r = sl.verify_hadith("muslim", 5)
        self.assertEqual(r["status"], "unverifiable")


class Transport(unittest.TestCase):
    def test_sse_and_structured_content(self):
        raw = 'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\\"ok\\":true}"}]}}\n'
        with mock.patch.object(sl, "_post", return_value=(raw, {})):
            self.assertEqual(sl.mcp_call("u", "t", {}), {"ok": True})

    def test_error_retries_with_initialize(self):
        calls = []

        def fake_post(url, body, headers=None):
            calls.append((body["method"], headers))
            if len(calls) == 1:
                return ('{"jsonrpc":"2.0","id":2,"error":{"message":"init required"}}', {})
            if body["method"] == "initialize":
                return ('{"jsonrpc":"2.0","id":1,"result":{}}', {"Mcp-Session-Id": "abc"})
            return ('{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"plain"}]}}', {})
        with mock.patch.object(sl, "_post", side_effect=fake_post):
            self.assertEqual(sl.mcp_call("u", "t", {}), "plain")
        self.assertEqual(calls[2][1]["Mcp-Session-Id"], "abc")

    def test_shamela_scope_error_raises(self):
        with mock.patch.object(sl, "mcp_call", return_value={"ok": False, "error": "scope_too_large", "message": "x"}):
            with self.assertRaises(sl.SourceError):
                sl.shamela_search("نص", book="صحيح البخاري")


if __name__ == "__main__":
    unittest.main()
