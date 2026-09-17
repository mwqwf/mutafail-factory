# -*- coding: utf-8 -*-
"""إذنُ يوتيوب على خطوتين — لأنّ `run_local_server` يولّد حالةً جديدة تخالف
الحالةَ التي فُتح بها الرابط (‏MismatchingStateError مقيسٌ 2026-09-14).

    الخطوة ١:  python oauth2step.py url  <client_secret.json> <ملف_الجلسة> <ملف_الرابط>
    الخطوة ٢:  python oauth2step.py code <ملف_الجلسة> <الرمز> <ملف_المخرَج>

⛔ لا يطبع سرّاً.
"""
import sys, json, io, os, base64, hashlib, secrets, urllib.parse, urllib.request

AUTH = "https://accounts.google.com/o/oauth2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube"
REDIRECT = "http://localhost:8822/"

mode = sys.argv[1]

if mode == "url":
    src, sess, urlfile = sys.argv[2], sys.argv[3], sys.argv[4]
    cfg = json.load(io.open(src, encoding="utf-8"))
    k = "installed" if "installed" in cfg else "web"
    cid, csec = cfg[k]["client_id"], cfg[k]["client_secret"]
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    q = urllib.parse.urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT,
        "scope": SCOPE, "code_challenge": challenge,
        "code_challenge_method": "S256", "prompt": "consent",
        "access_type": "offline"})
    io.open(urlfile, "w", encoding="utf-8").write(AUTH + "?" + q)
    io.open(sess, "w", encoding="utf-8").write(json.dumps(
        {"client_id": cid, "client_secret": csec, "verifier": verifier}))
    print("OK url")

elif mode == "code":
    sess, code, out = sys.argv[2], sys.argv[3], sys.argv[4]
    s = json.load(io.open(sess, encoding="utf-8"))
    data = urllib.parse.urlencode({
        "code": code, "client_id": s["client_id"], "client_secret": s["client_secret"],
        "redirect_uri": REDIRECT, "grant_type": "authorization_code",
        "code_verifier": s["verifier"]}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN, data=data)) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        raise SystemExit("⛔ لا رمزَ تجديدٍ في الردّ — أعِد الإذن بـprompt=consent")
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"client_id": s["client_id"], "client_secret": s["client_secret"],
         "refresh_token": tok["refresh_token"]}, ensure_ascii=False))
    print("OK token len=%d" % len(tok["refresh_token"]))
