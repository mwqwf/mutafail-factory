# -*- coding: utf-8 -*-
"""نشرُ الحلقة وريلزيها على يوتيوب بلا متصفّحٍ ولا يد.

⭐ **الحقلُ الذي ظُنّ حاجزاً وليس بحاجز:** `status.containsSyntheticMedia`
   أضافته الواجهة البرمجية في 2024-10-30، فإفصاحُ الذكاء الاصطناعي آليٌّ تامّ.

⛔ **وما لا تبلغه الواجهة**: ربطُ الريلز بالفيلم في حقل «فيديو مشابه».
   فيُكتب رابطُ الفيلم في الوصف، **ويُسجَّل الريلز في `ops/state/pending_links.json`**
   ليُربط لاحقاً بنقرةٍ واحدة من الهاتف — ولا يُدَّعى أنه رُبط.

الحصّة: رفعُ فيديو = 1600 وحدة من 10000 يومياً ⇒ ستّ رفعات. وفيلمٌ بريلزيه = ثلاث.
"""
import json, io, os, sys, datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJ = sys.argv[1]
P = lambda *a: os.path.join(PROJ, *a)
STATE = os.path.join("ops", "state")


def yt():
    c = json.loads(os.environ["YT_OAUTH_JSON"])
    creds = Credentials(
        None,
        refresh_token=c["refresh_token"],
        client_id=c["client_id"],
        client_secret=c["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(svc, path, meta, publish_at=None, public_now=False):
    status = {
        "privacyStatus": "public" if public_now else "private",
        "selfDeclaredMadeForKids": False,      # ⛔ لازمٌ وإلا رُفض الحفظ صامتاً (درس 09-13)
        "containsSyntheticMedia": True,        # ⭐ إفصاحُ الذكاء الاصطناعي
    }
    if publish_at:
        status["publishAt"] = publish_at       # جدولةٌ عامّة في وقتٍ محدّد
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"][:5000],
            "tags": meta.get("tags", [])[:60],
            "categoryId": meta.get("categoryId", "27"),   # التعليم
            "defaultLanguage": "ar",
            "defaultAudioLanguage": "ar",
        },
        "status": status,
    }
    media = MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    res, prog = None, 0
    while res is None:
        prog, res = req.next_chunk()
        if prog:
            print("  رفع %d%%" % int(prog.progress() * 100), flush=True)
    vid = res["id"]
    print("✅ رُفع:", vid, "·", meta["title"][:50], flush=True)
    return vid


def verify(svc, vid):
    """⛔ الإعلانُ ليس أثراً — لكنّ المقروءَ غيرُ المكتوب.

    ⭐ **درسٌ مقيسٌ 2026-09-14:** الواجهةُ **تقبل** `containsSyntheticMedia` كتابةً
       **ولا تُرجعه** في `videos.list(part=status)`. فاشتراطُ قراءته يُسقط شوطاً
       ناجحاً (‏سقط شوطُ جزيرة الفصح بعد رفعٍ صحيح، والوسمُ ثابتٌ في الاستوديو).
    ⇒ يُتحقَّق ممّا يُقرأ فعلاً، ويُسجَّل ما لا يُقرأ بوصفه غيرَ قابلٍ للقراءة لا فاشلاً.
    """
    r = svc.videos().list(part="status", id=vid).execute()
    st = r["items"][0]["status"]
    if st.get("madeForKids") is not False:
        raise SystemExit("⛔ حقلُ الأطفال لم يثبت على الخادم: " + json.dumps(st))
    synth = st.get("containsSyntheticMedia")
    print("✅ تحقّق", vid, "| للأطفال=False | وسمُ الذكاء الاصطناعي:",
          "true" if synth is True else "أُرسل ولا تُرجعه الواجهة (يُراجَع في الاستوديو)",
          flush=True)
    return st


def playlist_ids(svc, pl):
    """كلُّ القائمة صفحةً صفحة — ⛔ صفحةٌ واحدةٌ تكذب (خمسون بندًا فقط)."""
    out, tok = [], None
    while True:
        r = svc.playlistItems().list(part="contentDetails", playlistId=pl,
                                     maxResults=50, pageToken=tok).execute()
        out += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            return out


def add_to_playlist(svc, pl, vid):
    if vid in playlist_ids(svc, pl):
        print("✅ في القائمة أصلاً", vid, flush=True)
        return
    svc.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": pl,
        "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    if vid not in playlist_ids(svc, pl):      # ⛔ الإعلان ليس أثراً
        raise SystemExit("⛔ الفيلم لم يدخل القائمة %s — الشوطُ فاشل" % pl)
    print("✅ أُضيف إلى القائمة وتحقَّق", flush=True)


def main():
    meta = json.load(io.open(P("publish.json"), encoding="utf-8"))

    # ⛔ فصولُ يوتيوب لا تعمل إلا إن كانت **داخل الوصف** بتوقيتاتها، وتوقيتاتُها
    #    لا تُعرف إلا بعد التركيب. فيُكتب في الوصف موضعٌ اسمُه {CHAPTERS} ويُملأ هنا.
    ch = P("الفصول.txt")
    chapters = io.open(ch, encoding="utf-8").read().strip() if os.path.exists(ch) else ""
    if "{CHAPTERS}" in meta["film"]["description"]:
        if not chapters:
            raise SystemExit("⛔ الوصفُ ينتظر الفصول ولا ملفَّ فصولٍ — لا يُرفع فيلمٌ بلا فصول")
        meta["film"]["description"] = meta["film"]["description"].replace("{CHAPTERS}", chapters)

    svc = yt()

    # ─── الفيلم ───
    when = meta.get("publishAt")   # ISO-8601 UTC، مثل 2026-09-14T05:00:00Z
    film_id = upload(svc, P("film.mp4"), meta["film"], publish_at=when)
    verify(svc, film_id)

    # ─── المصغّرة: لازمة، ولا تُتخطّى ───
    thumb = P("thumb-a.jpg")
    if not os.path.exists(thumb):
        raise SystemExit("⛔ لا مصغّرة — لا يُنشر فيلمٌ بلا مصغّرة")
    svc.thumbnails().set(videoId=film_id, media_body=MediaFileUpload(thumb)).execute()
    print("✅ المصغّرة", flush=True)

    # ─── القائمة: لازمة، وتُتحقَّق من الخادم ───
    # ⛔⛔ أمرُ المالك 2026-09-14: «لم يُضف الفيلم للقائمة وهذا لا تسامح معه».
    #    فلا يُقبل هنا إعلانٌ بلا أثر: نُضيف ثمّ **نقرأ القائمة كلَّها صفحةً صفحة**.
    pl = meta.get("playlistId")
    if not pl:
        raise SystemExit("⛔ لا playlistId في publish.json — لا يُنشر فيلمٌ خارج قائمته")
    add_to_playlist(svc, pl, film_id)

    # ─── الريلزان: عامّان فوراً، ورابطُ الفيلم في الوصف ───
    link = "https://youtu.be/" + film_id
    reels = []
    for r in meta.get("reels", []):
        rm = dict(r)
        rm["description"] = r["description"].replace("{FILM_URL}", link)
        rid = upload(svc, P("reels", r["file"]), rm, public_now=True)
        verify(svc, rid)
        reels.append({"id": rid, "title": r["title"]})

    # ─── ما لا تبلغه الواجهة: يُسجَّل ولا يُدَّعى ───
    os.makedirs(STATE, exist_ok=True)
    pend = P("..", "pending")
    out = {
        "film": {"id": film_id, "title": meta["film"]["title"], "publishAt": when},
        "reels": reels,
        "يتبقّى_يدويّاً": "ربطُ كلّ ريلز بالفيلم في حقل «فيديو مشابه» — "
                          "من تطبيق يوتيوب: قناتك ← الشورت ← ⋮ ← تعديل ← فيديو مشابه.",
    }
    io.open(os.path.join(STATE, "last_publish.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
