# -*- coding: utf-8 -*-
"""إعادة الرفع بأمر المالك، وسؤال يوتيوب «أريلزٌ هو؟» (الأرك r1، 2026-10-07)، بلا شبكةٍ ولا مكتبات جوجل."""
import io
import sys
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for name in ("google", "google.oauth2", "google.oauth2.credentials",
             "googleapiclient", "googleapiclient.discovery", "googleapiclient.errors", "googleapiclient.http"):
    sys.modules.setdefault(name, types.ModuleType(name))
for mod, attr in (("google.oauth2.credentials", "Credentials"), ("googleapiclient.discovery", "build"),
                  ("googleapiclient.errors", "HttpError"), ("googleapiclient.http", "MediaFileUpload")):
    if not hasattr(sys.modules[mod], attr):
        setattr(sys.modules[mod], attr, type(attr, (Exception,), {}))
_argv = sys.argv[:]
sys.argv = [sys.argv[0], "proj"]
import publish_youtube as pub  # noqa: E402
sys.argv = _argv


class _Svc:
    def __init__(self, items=None, boom=False):
        self.items, self.boom = items, boom

    def videos(self):
        return self

    def list(self, **k):
        return self

    def execute(self):
        if self.boom:
            raise RuntimeError("انقطاع")
        return {"items": self.items or []}


class Exists(unittest.TestCase):
    def test_present_absent_and_unreadable(self):
        self.assertTrue(pub.exists(_Svc(items=[{"id": "x"}]), "x"))
        self.assertFalse(pub.exists(_Svc(items=[]), "x"))
        self.assertTrue(pub.exists(_Svc(boom=True), "x"))      # التعذّر لا يجيز نسخةً ثانية


class _Resp:
    def __init__(self, body):
        self.body = body

    def getcode(self):
        return 200

    def read(self, n=-1):
        return self.body.encode("utf-8")


class IsShort(unittest.TestCase):
    def run_with(self, outcome):
        class _Op:
            def open(self, req, timeout=None):
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome
        old = urllib.request.build_opener
        urllib.request.build_opener = lambda *a: _Op()
        try:
            return pub.is_short("ff_X4FhcOmQ", tries=1, wait=0)
        finally:
            urllib.request.build_opener = old

    def test_short_page_names_itself(self):
        page = '<link rel="canonical" href="https://www.youtube.com/shorts/ff_X4FhcOmQ">'
        self.assertIs(self.run_with(_Resp(page)), True)

    def test_redirect_to_watch_is_not_a_short(self):
        err = urllib.error.HTTPError("u", 303, "See Other", {"Location": "https://www.youtube.com/watch?v=ff_X4FhcOmQ"}, io.BytesIO())
        self.assertIs(self.run_with(err), False)

    def test_page_without_the_tag_is_unknown(self):
        self.assertIsNone(self.run_with(_Resp("<html>Video unavailable</html>")))


if __name__ == "__main__":
    unittest.main()
