# -*- coding: utf-8 -*-
"""يقرأ ملفَّ اعتمادِ العميل المنزَّل من وحدة تحكّم جوجل، ويُجري الإذن مرّةً واحدة،
ثمّ يكتب سرَّ YT_OAUTH_JSON في ملفٍّ محلّيّ — ⛔ ولا يطبع سرّاً في الشاشة.

الاستعمال: python oauth_from_file.py <ملف_client_secret.json> <ملف_المخرَج>
"""
import sys, json, io, glob, os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

src = sys.argv[1] if len(sys.argv) > 1 else sorted(
    glob.glob(os.path.expanduser("~/Downloads/client_secret*.json")),
    key=os.path.getmtime)[-1]
out = sys.argv[2]

cfg = json.load(io.open(src, encoding="utf-8"))
key = "installed" if "installed" in cfg else "web"
cid = cfg[key]["client_id"]
csec = cfg[key]["client_secret"]

flow = InstalledAppFlow.from_client_config(
    {"installed": {
        "client_id": cid, "client_secret": csec,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }}, SCOPES)

print("افتح الرابط الذي سيظهر، وائذن للتطبيق باسم قناة المتفائل.", flush=True)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline",
                              open_browser=False,
                              authorization_prompt_message="\n>>> افتح هذا الرابط:\n{url}\n")

io.open(out, "w", encoding="utf-8").write(json.dumps(
    {"client_id": cid, "client_secret": csec, "refresh_token": creds.refresh_token},
    ensure_ascii=False))
print("✅ كُتب السرّ في:", out, "| طول رمز التجديد:", len(creds.refresh_token or ""), flush=True)
