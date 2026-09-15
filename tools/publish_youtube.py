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
from googleapiclient.errors import HttpError
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
    # ⭐ **درسٌ مقيسٌ 2026-09-14:** `madeForKids` **لا يُحسب فورَ الرفع** فيغيب من الردّ،
    #    والحاضرُ هو `selfDeclaredMadeForKids` — وهو ما أرسلناه نحن. فهو الفيصل،
    #    واشتراطُ الأوّل يُسقط رفعاً صحيحاً (‏أسقط ريلزَ جزيرة الفصح بعد رفعه).
    kids = st.get("madeForKids")
    declared = st.get("selfDeclaredMadeForKids")
    if kids is True or declared is True:
        raise SystemExit("⛔ صُنّف للأطفال على الخادم: " + json.dumps(st))
    if kids is None and declared is None:
        raise SystemExit("⛔ لا حقلَ أطفالٍ في الردّ أصلاً: " + json.dumps(st))
    synth = st.get("containsSyntheticMedia")
    print("✅ تحقّق", vid, "| للأطفال=False | وسمُ الذكاء الاصطناعي:",
          "true" if synth is True else "أُرسل ولا تُرجعه الواجهة (يُراجَع في الاستوديو)",
          flush=True)
    return st


def recent_uploads(svc, limit=50):
    """أحدثُ رفعات القناة {العنوان: المعرّف} — كلفتُها وحدتان من الحصّة لا أكثر.

    ⛔⛔ **درسٌ مقيسٌ 2026-09-14 (‏شوطا 3481353/3481367):** إعادةُ الشوط الساقط
    تستأنف من **الالتزام نفسه**، فلا ترى حالةً دُفعت بعده. فرُفع الريلزان مرّتين
    (‏qvR0-BKHPSQ و qCmyDbY5Ryw نسختان من LKJNDK-mC-E و 0QEkc7xrAuU)، وأُحرق
    ٣٢٠٠ وحدةٍ من الحصّة، وظهرت نسختان على القناة.
    ⇒ فالحارسُ الذي لا يخدعه جيتُ هَب هو **القناةُ نفسُها**: نقرأ عناوينَ آخر
      الرفعات، فإن كان العنوانُ مرفوعاً سلفاً تبنّيناه ولم نرفع ثانيةً.
    """
    try:
        ch = svc.channels().list(part="contentDetails", mine=True).execute()
        up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        r = svc.playlistItems().list(part="snippet", playlistId=up,
                                     maxResults=min(limit, 50)).execute()
        return {i["snippet"]["title"].strip(): i["snippet"]["resourceId"]["videoId"]
                for i in r.get("items", [])}
    except Exception as e:                 # ⛔ الحارسُ لا يُسقط شوطاً إن تعذّر
        print("⚠️ تعذّرت قراءةُ رفعات القناة:", e, flush=True)
        return {}


STATE_FILE = os.path.join(STATE, "last_publish.json")


def load_state():
    try:
        return json.load(io.open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(d):
    """⛔ تُكتب الحالةُ فورَ كلّ أثرٍ لا رجعةَ فيه، لا في آخر الشوط —
       فالسقوطُ بعد الرفع وقبل الكتابة يُنتج نسخةً ثانيةً عند الإعادة."""
    os.makedirs(STATE, exist_ok=True)
    cur = load_state()
    cur.update(d)
    io.open(STATE_FILE, "w", encoding="utf-8").write(
        json.dumps(cur, ensure_ascii=False, indent=1))


def _save_playlist(series, title, pid):
    """يُسجَّل المعرّفُ الجديدُ في `ops/state/playlists.json` فورَ إنشائه.

    ⛔ وخطوةُ «تسجيلُ المنجَز» في `film.yml` تدفع `ops/state` كلَّه بـ`if: always()`،
       فلا يضيع المعرّفُ ولو سقط ما بعده.
    """
    f = os.path.join(STATE, "playlists.json")
    try:
        m = json.load(io.open(f, encoding="utf-8"))
    except Exception:
        m = {}
    m.setdefault("القوائم", {})[title] = pid
    m.setdefault("السلاسل", {})[series] = pid
    m["السلسلة_الجارية"] = series
    os.makedirs(STATE, exist_ok=True)
    io.open(f, "w", encoding="utf-8").write(json.dumps(m, ensure_ascii=False, indent=1))
    print("✅ سُجّلت القائمةُ في playlists.json:", series, "→", pid, flush=True)


def channel_playlists(svc):
    """قوائمُ القناة {العنوان: المعرّف} — كلفتُها وحدةٌ واحدة، وتُقرأ صفحةً صفحة.

    ⛔⛔ هذا هو الحارسُ الذي لا يخدعه جيتُ هَب (وهو عينُ درس `recent_uploads`):
       شوطٌ سقط بعد إنشاء القائمة وقبل دفع الحالة كان سيُنشئ قائمةً ثانيةً بالاسم
       نفسِه عند الإعادة، فتنقسم السلسلةُ على قائمتين. ⇒ نسأل القناةَ لا الدفتر.
    """
    out, tok = {}, None
    try:
        while True:
            r = svc.playlists().list(part="snippet", mine=True,
                                     maxResults=50, pageToken=tok).execute()
            for i in r.get("items", []):
                out[i["snippet"]["title"].strip()] = i["id"]
            tok = r.get("nextPageToken")
            if not tok:
                return out
    except Exception as e:
        print("⚠️ تعذّرت قراءةُ قوائم القناة:", e, flush=True)
        return out


def resolve_playlist(meta, svc=None):
    """⛔⛔ لا يُنشر فيلمٌ خارج قائمته (أمر المالك 2026-09-14).

    ولا يُتّكل على أن يتذكّر الدماغُ المعرّف: يُقبل `playlistId` صريحاً، وإلّا
    يُستنبط من اسم السلسلة عبر `ops/state/playlists.json` — فالنسيانُ لا يُسقط قائمة.

    ⭐ **وأوّلُ حلقةٍ من سلسلةٍ جديدةٍ لا قائمةَ لها بعدُ** — وهذا يقع في كلّ مرّةٍ
       يدور فيها جدولُ `PLAN §٣` إلى سلسلةٍ تالية. فكانت القاعدةُ تُوقف النشرَ
       انتظاراً ليدٍ بشريّةٍ تُنشئ القائمة. ⇒ تُنشأ هنا من `playlistNew` في ملفّ
       النشر: أوّلاً تُطلب من القناة بعنوانها (فلا تتكرّر)، وإلّا أُنشئت وسُجّلت.
    """
    pl = meta.get("playlistId")
    if pl:
        return pl
    series = meta.get("series") or meta.get("السلسلة")
    try:
        m = json.load(io.open(os.path.join(STATE, "playlists.json"), encoding="utf-8"))
    except Exception:
        m = {}
    by_series = m.get("السلاسل", {})
    by_title = m.get("القوائم", {})
    if not series:
        # ٣) السلسلةُ الجارية في الخطة — تُحدَّث عند الانتقال إلى سلسلةٍ أخرى
        series = m.get("السلسلة_الجارية")
    if series:
        if series in by_series:
            return by_series[series]
        for t, i in by_title.items():
            if series in t or t.startswith(series):
                return i

    nw = meta.get("playlistNew")
    if nw and nw.get("title") and series and svc is not None:
        title = nw["title"].strip()
        seen = channel_playlists(svc).get(title)
        if seen:
            print("↻ القائمةُ قائمةٌ على القناة سلفاً بعنوانها:", seen, flush=True)
            _save_playlist(series, title, seen)
            return seen
        r = svc.playlists().insert(part="snippet,status", body={
            "snippet": {"title": title[:150],
                        "description": nw.get("description", "")[:5000],
                        "defaultLanguage": "ar"},
            "status": {"privacyStatus": "public"}}).execute()
        pid = r["id"]
        print("✅ أُنشئت قائمةُ السلسلة:", title, "→", pid, flush=True)
        _save_playlist(series, title, pid)
        return pid

    raise SystemExit(
        "⛔ لا قائمةَ للفيلم: ضَع playlistId في publish.json أو series يطابق "
        "ops/state/playlists.json أو playlistNew لسلسلةٍ جديدة — "
        "ولا يُنشر فيلمٌ خارج قائمته")


def _is_404(e):
    return getattr(e, "resp", None) is not None and e.resp.status == 404


def playlist_ids(svc, pl, tolerate_missing=False):
    """كلُّ القائمة صفحةً صفحة — ⛔ صفحةٌ واحدةٌ تكذب (خمسون بندًا فقط).

    ⛔⛔ **درسٌ مقيسٌ 2026-09-15 (شوط amal-1):** القائمةُ التي تُنشأ للتوّ
       **لا تُقرأ فوراً**: ردّ يوتيوب `404 playlistNotFound` على قائمةٍ أنشأها هو
       قبل ثانيةٍ واحدة. وهو عينُ درسِ 09-14 في تأخّر اتّساق القراءة، إلّا أنّه
       يظهر هنا **استثناءً يُسقط الشوط** لا قائمةً فارغةً تُعاد قراءتُها.
    ⇒ `tolerate_missing` يُرجع `None` بدل أن يرمي، فيُفرَّق بين «قائمةٌ فارغة»
      و«قائمةٌ لم تظهر بعدُ».
    """
    out, tok = [], None
    while True:
        try:
            r = svc.playlistItems().list(part="contentDetails", playlistId=pl,
                                         maxResults=50, pageToken=tok).execute()
        except HttpError as e:
            if tolerate_missing and _is_404(e):
                return None
            raise
        out += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            return out


def add_to_playlist(svc, pl, vid):
    import time
    cur = playlist_ids(svc, pl, tolerate_missing=True)
    if cur is not None and vid in cur:
        print("✅ في القائمة أصلاً", vid, flush=True)
        return
    # ⛔ والإدراجُ نفسُه يردّ 404 على قائمةٍ أُنشئت للتوّ، فيُعاد بمهلةٍ متدرّجة
    for wait in (0, 3, 5, 8, 13, 21):
        if wait:
            time.sleep(wait)
        try:
            svc.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pl,
                "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            break
        except HttpError as e:
            if not _is_404(e):
                raise
            print("… القائمةُ لم تظهر للخادم بعدُ، إعادةُ الإدراج", flush=True)
    else:
        raise SystemExit("⛔ تعذّر إدراجُ الفيلم في القائمة %s بعد ستّ محاولات" % pl)
    # ⛔⛔ درسٌ مقيسٌ 2026-09-14 (شوط الموحّدين 34826549950): الإضافةُ نجحت بلا خطأ،
    #    ثمّ قراءةُ القائمة **فورَ الإضافة** لم تجد الفيلم فسقط الشوط بعد رفعٍ صحيح.
    #    والسببُ أنّ قراءةَ القائمة عند يوتيوب لا تتّسق فورَ الكتابة.
    #    ⇒ الإعلانُ يبقى غيرَ أثر، لكنّ الأثرَ يُطلب بمهلةٍ متدرّجة لا بنظرةٍ واحدة.
    for wait in (0, 3, 5, 8, 13, 21):
        if wait:
            time.sleep(wait)
        cur = playlist_ids(svc, pl, tolerate_missing=True)
        if cur is not None and vid in cur:
            print("✅ أُضيف إلى القائمة وتحقَّق بعد %d ثانية" % wait, flush=True)
            return
        print("… لم يظهر في القائمة بعدُ، إعادةُ القراءة", flush=True)
    raise SystemExit("⛔ الفيلم لم يدخل القائمة %s بعد ستّ قراءاتٍ — الشوطُ فاشل" % pl)


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
    # ⭐ **استئنافٌ لا إعادة**: إن سقط شوطٌ بعد الرفع، يُمرَّر معرّفُ الفيلم
    #    في `FILM_VIDEO_ID` فيُكمِل المصنعُ ما بقي بلا أن يرفع نسخةً ثانية.
    # ⛔⛔ **فجوةٌ مقيسةٌ في التصميم (2026-09-15):** الريلزان يُرفعان **عامَّين فوراً**
    #    وفي وصفِهما رابطُ الفيلم، والفيلمُ يبقى **خاصّاً** حتى موعد `publishAt`.
    #    ⇒ فبين رفعِ الريلز وموعدِ الجدولة نافذةٌ يرى فيها المشاهدُ شورتاً عامّاً
    #      يحيل إلى فيديو غير متاح. وهي ساعاتٌ في كلّ حلقةٍ نُشرت هكذا.
    #    ⇒ و`publicNow` في ملفّ النشر يُغلقها: الفيلمُ عامٌّ لحظةَ رفعه، فلا جدولةَ
    #      ولا فجوة. وهو أيضاً أمرُ المالك المتكرّر في 2026-09-14: «اجعلها عامّة».
    when = meta.get("publishAt")   # ISO-8601 UTC
    public_now = bool(meta.get("publicNow"))
    if public_now:
        when = None
    film_id = os.environ.get("FILM_VIDEO_ID", "").strip()
    if film_id:
        print("↻ استئناف: الفيلم مرفوعٌ سلفاً", film_id, flush=True)
    else:
        ft = meta["film"]["title"].strip()[:100]
        seen = recent_uploads(svc).get(ft)
        if seen:                               # ↻ محاولةٌ سابقةٌ رفعته ثمّ سقطت
            print("↻ الفيلم مرفوعٌ على القناة سلفاً بعنوانه:", seen, flush=True)
            film_id = seen
            save_state({"film": {"id": film_id}})
    if not film_id:
        film_id = upload(svc, P("film.mp4"), meta["film"],
                         publish_at=when, public_now=public_now)
        save_state({"film": {"id": film_id}})      # ⛔ يُسجَّل فورَ الرفع لا بعد كلّ شيء
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
    add_to_playlist(svc, resolve_playlist(meta, svc), film_id)

    # ─── الريلزان: عامّان فوراً، ورابطُ الفيلم في الوصف ───
    link = "https://youtu.be/" + film_id
    prev = load_state()
    # ⛔⛔ درسٌ مقيسٌ 2026-09-14 (شوطا الموحّدين والخاتمة): حالةُ الاستئناف مفتاحُها
    #    اسمُ الملفّ (r1.mp4) وهو **واحدٌ في كلّ حلقة**. فقرأ المحرّكُ حالةَ حلقةٍ
    #    سابقةٍ فظنّ ريلزَي هذه الحلقة مرفوعَين، فتخطّاهما، وكتب في الحالة معرّفَي
    #    ريلزٍ **من حلقةٍ أخرى**. فخرجت حلقتان بلا ريلزات، والحالةُ تدّعي خلافَ الواقع.
    #    ⇒ الاستئنافُ لا يصحّ إلا داخل الحلقة نفسِها: يُقيَّد بالـslug.
    slug = meta.get("slug") or os.path.basename(os.path.abspath(PROJ))
    if prev.get("slug") != slug:
        if prev.get("reels"):
            print("↻ حالةُ حلقةٍ أخرى (%s) — لا تُستعمل لاستئناف %s"
                  % (prev.get("slug"), slug), flush=True)
        prev = {}
    done = {x.get("file"): x for x in prev.get("reels", []) if x.get("file")}
    onchannel = recent_uploads(svc)            # ⛔ الحارسُ الثاني: القناةُ نفسُها
    reels = []
    for r in meta.get("reels", []):
        if r["file"] in done:                      # ↻ استئناف: لا يُرفع مرّتين
            print("↻ الريلز مرفوعٌ سلفاً", r["file"], flush=True)
            reels.append(done[r["file"]]); continue
        t = r["title"].strip()[:100]
        if t in onchannel:                         # ↻ رُفع في محاولةٍ سابقةٍ سقطت
            print("↻ عنوانٌ مرفوعٌ على القناة سلفاً — لا نسخةَ ثانية:",
                  onchannel[t], flush=True)
            reels.append({"id": onchannel[t], "title": r["title"], "file": r["file"]})
            save_state({"slug": slug, "film": {"id": film_id}, "reels": reels})
            continue
        rm = dict(r)
        rm["description"] = r["description"].replace("{FILM_URL}", link)
        rid = upload(svc, P("reels", r["file"]), rm, public_now=True)
        # ⛔ يُسجَّل **قبل** التحقّق: سقوطُ التحقّق بعد رفعٍ واقعٍ كان يُنتج نسخةً ثانية.
        reels.append({"id": rid, "title": r["title"], "file": r["file"]})
        save_state({"slug": slug, "film": {"id": film_id}, "reels": reels})
        verify(svc, rid)

    # ─── ما لا تبلغه الواجهة: يُسجَّل ولا يُدَّعى ───
    os.makedirs(STATE, exist_ok=True)
    pend = P("..", "pending")
    out = {
        "slug": slug,
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
