# -*- coding: utf-8 -*-
"""تهيئةُ إذنِ يوتيوب — مرّةً واحدةً في العمر، ثمّ لا يُطلب منك شيءٌ أبداً.

لماذا لا مفرّ منها: الحسابُ حسابُك، ولا يُؤذن لتطبيقٍ باسمك إلا بموافقتك أنت.
وما ينتج منها **رمزُ تجديدٍ دائم** يُخزَّن سرَّ أكشنز، فيرفع وينشر بلا متصفّحٍ بعدها.

الاستعمال:
    python oauth_bootstrap.py <client_id> <client_secret>
ثمّ افتح الرابطَ المطبوع، وائذن، والصق الرمز.
وفي الآخر يطبع سطرَ JSON الذي يوضع في السرّ `YT_OAUTH_JSON`.
"""
import sys, json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

cid, csec = sys.argv[1], sys.argv[2]
cfg = {"installed": {
    "client_id": cid,
    "client_secret": csec,
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
}}

flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

out = {"client_id": cid, "client_secret": csec, "refresh_token": creds.refresh_token}
print("\n════ ضَعْ هذا في السرّ YT_OAUTH_JSON ════\n")
print(json.dumps(out, ensure_ascii=False))
