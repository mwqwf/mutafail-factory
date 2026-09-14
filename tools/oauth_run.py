# -*- coding: utf-8 -*-
"""إذنُ يوتيوب مرّةً واحدة — يكتب رابطَ الإذن في ملفّ (لا في الشاشة، فالمخرَج يُخزَّن مؤقّتاً)،
ثمّ يستقبل الرمزَ على منفذٍ ثابت، ويكتب سرَّ YT_OAUTH_JSON. ⛔ لا يطبع سرّاً.

الاستعمال: python oauth_run.py <ملف_client_secret.json> <ملف_المخرَج> <ملف_رابط_الإذن>
"""
import sys, json, io, os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]
PORT = 8822

src, out, urlfile = sys.argv[1], sys.argv[2], sys.argv[3]
cfg = json.load(io.open(src, encoding="utf-8"))
key = "installed" if "installed" in cfg else "web"
cid, csec = cfg[key]["client_id"], cfg[key]["client_secret"]

flow = InstalledAppFlow.from_client_config(
    {"installed": {
        "client_id": cid, "client_secret": csec,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:%d/" % PORT],
    }}, SCOPES)
flow.redirect_uri = "http://localhost:%d/" % PORT
auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
io.open(urlfile, "w", encoding="utf-8").write(auth_url)

creds = flow.run_local_server(port=PORT, open_browser=False,
                              authorization_prompt_message="")
io.open(out, "w", encoding="utf-8").write(json.dumps(
    {"client_id": cid, "client_secret": csec, "refresh_token": creds.refresh_token},
    ensure_ascii=False))
io.open(urlfile + ".done", "w", encoding="utf-8").write(
    "ok len=%d" % len(creds.refresh_token or ""))
