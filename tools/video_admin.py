# -*- coding: utf-8 -*-
"""تعديلاتُ ما بعد النشر على يوتيوب — بأمرٍ مكتوبٍ لا بيد.

الاستعمال: python tools/video_admin.py ops/admin/<ملف>.json
والملفُّ: {"videoId": "...", "public": true,
           "descriptionPrepend": "سطرٌ يُضاف في أوّل الوصف",
           "publishAt": "2026-10-07T13:00:00Z",   ← إعادةُ جدولة فيديو خاصّ (لا مع public)
           "playlists": ["PL..."]}

⛔ الكلفة من حصّة يوتيوب لا من حصّة التوليد: قراءةُ فيديو (١) + تعديلُه (٥٠)
   + إضافةُ قائمةٍ (٥٠). ولا يمسّ رصيدَ جيميناي البتّة.
⭐ ولا يُحذف منشورٌ ولا يُخفى: هذه الأداةُ تُظهر وتضيف، ولا تُنقص.
"""
import io, json, os, sys, time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CMD = json.load(io.open(sys.argv[1], encoding="utf-8"))
c = json.loads(os.environ["YT_OAUTH_JSON"])
svc = build("youtube", "v3", credentials=Credentials(
    None, refresh_token=c["refresh_token"], client_id=c["client_id"],
    client_secret=c["client_secret"],
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/youtube"]), cache_discovery=False)

vid = CMD["videoId"]
r = svc.videos().list(part="snippet,status", id=vid).execute()
if not r.get("items"):
    raise SystemExit("⛔ لا فيديو بهذا المعرّف: " + vid)
item = r["items"][0]
sn, st = item["snippet"], item["status"]
print("الفيديو:", sn["title"][:60], "| الخصوصيّة:", st.get("privacyStatus"),
      "| الموعد:", st.get("publishAt") or "—", flush=True)

changed = False
add = CMD.get("descriptionPrepend", "").strip()
if add and add not in sn.get("description", ""):
    sn["description"] = add + "\n\n" + sn.get("description", "")
    changed = True
if CMD.get("public") and st.get("privacyStatus") != "public":
    st["privacyStatus"] = "public"
    st.pop("publishAt", None)          # ⛔ الجدولةُ تمنع النشرَ الفوريّ فتُرفع
    changed = True
# ⭐ إعادةُ جدولة فيديو خاصٍّ بمعرّفه (مؤتة 2026-10-07: «اجعل ساعة بينهما»): بلا إعادة شوط النشر، فلا رفعَ ثانٍ
#    ولا عودةَ لمصغّرة الحمولة. والعامُّ لا يُعاد جدولته (يوتيوب لا يرجع بالمنشور إلى الخاصّ هنا).
at = CMD.get("publishAt", "").strip()
if at:
    import re, datetime as dt
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", at):
        raise SystemExit("⛔ publishAt بصيغة 2026-10-07T13:00:00Z وحدها: " + at)
    if dt.datetime.fromisoformat(at.replace("Z", "+00:00")) <= dt.datetime.now(dt.timezone.utc):
        raise SystemExit("⛔ موعدٌ مضى: " + at)
    if st.get("privacyStatus") == "public":
        print("⚠ الفيديو عامٌّ سلفاً — لا تُعاد جدولته", flush=True); at = ""
    elif st.get("publishAt", "").replace(".000", "") != at:
        st["privacyStatus"] = "private"
        st["publishAt"] = at
        changed = True

if changed:
    svc.videos().update(part="snippet,status", body={
        "id": vid, "snippet": sn, "status": st}).execute()
    # ⛔ الإعلانُ ليس أثراً — يُقرأ من الخادم بعد الكتابة
    for wait in (0, 3, 5, 8):
        if wait:
            time.sleep(wait)
        g = svc.videos().list(part="snippet,status", id=vid).execute()["items"][0]
        ok_pub = (not CMD.get("public")) or g["status"]["privacyStatus"] == "public"
        ok_des = (not add) or add in g["snippet"].get("description", "")
        ok_at = (not at) or g["status"].get("publishAt", "").replace(".000", "") == at
        if ok_pub and ok_des and ok_at:
            print("✅ تحقّق: الخصوصيّة =", g["status"]["privacyStatus"],
                  "| الوصفُ مُحدَّث =", bool(ok_des), "| الموعد =", g["status"].get("publishAt", "—"), flush=True)
            break
    else:
        raise SystemExit("⛔ التعديلُ لم يثبت على الخادم")
else:
    print("↻ لا تغييرَ مطلوبٌ في الوصف ولا الخصوصيّة ولا الموعد", flush=True)


def ids(pl):
    out, tok = [], None
    while True:
        p = svc.playlistItems().list(part="contentDetails", playlistId=pl,
                                     maxResults=50, pageToken=tok).execute()
        out += [i["contentDetails"]["videoId"] for i in p["items"]]
        tok = p.get("nextPageToken")
        if not tok:
            return out


for pl in CMD.get("playlists", []):
    if vid in ids(pl):
        print("✅ في القائمة أصلاً", pl, flush=True); continue
    svc.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    for wait in (0, 3, 5, 8, 13):
        if wait:
            time.sleep(wait)
        if vid in ids(pl):
            print("✅ أُضيف إلى القائمة وتحقَّق:", pl, flush=True); break
    else:
        raise SystemExit("⛔ لم يدخل القائمة: " + pl)
print("تمّ.", flush=True)
