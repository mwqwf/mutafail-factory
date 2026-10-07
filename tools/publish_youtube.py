# -*- coding: utf-8 -*-
"""نشرُ الحلقة وريلزيها على يوتيوب بلا متصفّحٍ ولا يد.

⭐ **الحقلُ الذي ظُنّ حاجزاً وليس بحاجز:** `status.containsSyntheticMedia`
   أضافته الواجهة البرمجية في 2024-10-30، فإفصاحُ الذكاء الاصطناعي آليٌّ تامّ.

⛔ **وما لا تبلغه الواجهة**: ربطُ الريلز بالفيلم في حقل «فيديو مشابه».
   فيُكتب رابطُ الفيلم في الوصف، **ويُسجَّل الريلز في `ops/state/pending_links.json`**
   ليُربط لاحقاً بنقرةٍ واحدة من الهاتف — ولا يُدَّعى أنه رُبط.

الحصّة: للرفع حصّةٌ مستقلّة منذ 2026-06-01، مئة رفعةٍ في اليوم، وسائر الطرق من العشرة آلاف (tools/quota.py).
"""
import json, io, os, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota

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


def reel_shape(path):
    """⛔ حارسُ الريلز (أمر المالك 2026-09-29: «تأكّد أنه سيظهر كريلز وليس كفيلم كما وقع سابقاً»).
    يوتيوب يعدّ الفيديو «Shorts» إن كان عموديّاً أو مربّعاً ومدّته ≤ 3 دقائق؛ وإلا نشره فيلماً عاديّاً.
    ⇒ لا يُرفع ريلز إلا عموديّاً (الارتفاع > العرض) ومدّته ≤ 175 ث. يعيد (سليم؟، وصف)."""
    import subprocess as _sp
    o = _sp.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                 '-of', 'json', path], capture_output=True, text=True)
    try:
        j = json.loads(o.stdout); w, h = j['streams'][0]['width'], j['streams'][0]['height']; d = float(j['format']['duration'])
    except Exception:
        return False, 'تعذّرت قراءة أبعاده'
    return (h > w and d <= 175.0), '%dx%d · %.1f ث' % (w, h, d)


def is_short(vid, tries=None, wait=None):
    """⛔ أمر المالك 2026-10-07: حذف ريلزاً قال إنّه ظهر له «فيديو لا ريلز»، وكان الملفّ عموديّاً 31 ث.
    ⇒ بعد الرفع يُسأل يوتيوب نفسه: رابط /shorts/<id> يجيب 200 للريلز، ويحوّل إلى /watch لغيره.
       للعامّ وحده (الخاصّ لا يُفتح بلا دخول). يعيد True أو False أو None (تعذّر الحكم)."""
    import time, urllib.request, urllib.error
    tries = int(os.environ.get("SHORT_CHECK_TRIES", tries or 20))
    wait = float(os.environ.get("SHORT_CHECK_WAIT", wait or 30))

    class _Stay(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    op = urllib.request.build_opener(_Stay)
    canon = 'href="https://www.youtube.com/shorts/%s"' % vid      # صفحة الريلز تسمّي نفسها ريلزاً
    last = None
    for i in range(tries):
        try:
            r = op.open(urllib.request.Request("https://www.youtube.com/shorts/" + vid,
                        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ar"}), timeout=20)
            code, loc, body = r.getcode(), "", r.read(3_000_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            code, loc, body = e.code, e.headers.get("Location", ""), ""
        except Exception as e:
            code, loc, body = None, str(e)[:80], ""
        if code == 200 and canon in body:
            return True
        last = (code, loc, "200 بلا وسم الريلز" if code == 200 else "")
        if i < tries - 1:
            time.sleep(wait)                       # المعالجة قد تؤخّر التصنيف دقائق
    print("  آخر جوابٍ لرابط الريلز:", last, flush=True)
    return False if last and last[0] in (301, 302, 303, 307) and "/watch" in (last[1] or "") else None


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
    quota.spend("upload", meta["title"][:40])
    print("✅ رُفع:", vid, "·", meta["title"][:50],
          "| بقي من رفعات اليوم:", quota.remaining("upload"), flush=True)
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


def reschedule(svc, vid, at):
    """يعدّل موعدَ فيديو مرفوعٍ ما دام خاصّاً (تصحيحُ موعدٍ بعد رفعه، بلا نسخةٍ ثانية)؛
    وبلا موعدٍ (at=None) يجعله عامّاً الآن."""
    st = svc.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    if st.get("privacyStatus") == "public":
        print("↻", vid, "عامٌّ سلفاً — لا يُعاد جدولته", flush=True); return
    if not at:
        svc.videos().update(part="status", body={"id": vid, "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}).execute()
        print("🌐 صار عامّاً الآن", vid, flush=True); return
    if st.get("publishAt", "").replace(".000", "") == at:
        return
    svc.videos().update(part="status", body={"id": vid, "status": {
        "privacyStatus": "private", "publishAt": at,
        "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}).execute()
    print("🕒 أُعيدت جدولة", vid, "إلى", at, flush=True)


def reel_at(film_at, i):
    """موعدُ الريلز رقم i: بعد موعد الفيلم بـREEL_OFFSETS دقيقةً (افتراضاً 30 ثم 150)، أو فوراً إن لم يُجدول الفيلم
    أو كان REEL_OFFSETS = "now" (أمر المالك 2026-09-28: «الشورتات لا تجدولهما، يكفي جدولة الفيلم»)."""
    import datetime as dt
    env = os.environ.get("REEL_OFFSETS", "").strip()
    if env == "now":
        return None
    if not film_at:
        # ⭐ أمر المالك 2026-09-30 (حطّين): الفيلم عامٌّ فوراً، ثم الريلزات على مواعيد من لحظة النشر
        #    («0,30,60»: الأوّل فوراً، ثم بعد نصف ساعة، ثم بعد نصف ساعة أخرى) — يُجدولها يوتيوب نفسه فلا تنتظر أحداً.
        if not env:
            return None
        offs = [int(x) for x in env.split(",") if x.strip()]
        off = offs[min(i, len(offs) - 1)]
        if off <= 0:
            return None
        base = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)
        return (base + dt.timedelta(minutes=off)).strftime("%Y-%m-%dT%H:%M:%SZ")
    offs = [int(x) for x in (env or "30,150").split(",") if x.strip()]
    base = dt.datetime.fromisoformat(film_at.replace("Z", "+00:00"))
    return (base + dt.timedelta(minutes=offs[min(i, len(offs) - 1)])).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    quota.spend("playlist_insert", vid)
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


def defer(slug, film_id, what, used, left):
    """يكتب أمرَ إتمامٍ لنافذة التجدّد القادمة بدل إسقاط الشوط أو إهمال العمل."""
    d = os.path.join("ops", "finish")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, slug + ".json")
    try:
        cur = json.load(io.open(f, encoding="utf-8"))
    except Exception:
        cur = {}
    cur.update({"runId": os.environ.get("GITHUB_RUN_ID", cur.get("runId", "")),
                "videoId": film_id, "command": slug,
                "مؤجَّل": True,
                "ملاحظة": "حصّةُ رفع يوتيوب لا تحتمل المزيد اليوم (رفعات اليوم %d، المتبقّي %d). "
                          "يُتمّ في نافذة التجدّد القادمة." % (used, left)})
    pend = cur.setdefault("المتبقّي", [])
    if what not in pend:
        pend.append(what)
    io.open(f, "w", encoding="utf-8").write(json.dumps(cur, ensure_ascii=False, indent=1))
    print("⏳ جُدوِل إلى نافذة التجدّد: %s (المتبقّي من رفعات اليوم %d)" % (what, left),
          flush=True)


def main():
    meta = json.load(io.open(P("publish.json"), encoding="utf-8"))

    # ⛔ فصولُ يوتيوب لا تعمل إلا إن كانت **داخل الوصف** بتوقيتاتها، وتوقيتاتُها
    #    لا تُعرف إلا بعد التركيب. فيُكتب في الوصف موضعٌ اسمُه {CHAPTERS} ويُملأ هنا.
    ch = P("الفصول.txt")
    chapters = io.open(ch, encoding="utf-8").read().strip() if os.path.exists(ch) else ""
    if "{CHAPTERS}" in meta.get("film", {}).get("description", ""):
        if not chapters:
            raise SystemExit("⛔ الوصفُ ينتظر الفصول ولا ملفَّ فصولٍ — لا يُرفع فيلمٌ بلا فصول")
        meta["film"]["description"] = meta["film"]["description"].replace("{CHAPTERS}", chapters)

    svc = yt()
    # ⭐ ريلزٌ دعائيٌّ وحده (ريلز السلسلة 2026-09-30): لا فيلم يُرفع ولا مصغّرة ولا قائمة؛ و{FILM_URL} يُحال إلى قائمة السلسلة
    reels_only = bool(meta.get("reels_only"))
    # ⭐ ريلزاتٌ لفيلمٍ منشورٍ سلفاً (الأرك 2026-10-07: ريلزان أُعيدا بعد إصلاح تجمّد آخرهما): film_video_id وreels_for_film في
    #    ملفّ النشر ⇒ لا يُمسّ الفيلم ولا مصغّرته ولا قائمته (والحصّة لا تتّسع إلا لرفع الريلزات)، ورابطه في وصف كلّ ريلز
    reels_for_film = os.environ.get("FILM_VIDEO_ID", "").strip() if os.environ.get("REELS_FOR_FILM") == "1" else ""
    if reels_for_film:
        reels_only = True
    when = None; film_id = None; env_at = os.environ.get("PUBLISH_AT", "").strip()
    # ⭐ الأرك r1 (2026-10-07، أمر المالك «انشرها الآن الجدولة لغد»): ريلزاتٌ لفيلمٍ منشور على موعدٍ مطلق.
    #    PUBLISH_AT أساسُ مواعيدها، ومعه REEL_OFFSETS دقائق. والفيلم لا يُمسّ، وموعده في السجلّ يبقى فارغاً.
    reel_base = env_at if reels_for_film and env_at and env_at != "now" else None
    if not reels_only:

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
        # ⭐ موعدٌ يحدّده المالك عند النشر (ops/publish/<slug>.json ← PUBLISH_AT) يغلب ما في الحمولة المختومة،
        #    والريلزان يُجدولان بعده بدقائق REEL_OFFSETS فلا يحيلان إلى فيلمٍ لم يُعرض بعد.
        env_at = os.environ.get("PUBLISH_AT", "").strip()
        if env_at == "now":                            # أمر المالك 2026-09-28: «اجعلهم منشورين من الآن»
            when, public_now = None, True
        elif env_at:
            when, public_now = env_at, False
        public_now = public_now and not when
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
        resumed = bool(film_id)
        if not film_id:
            film_id = upload(svc, P("film.mp4"), meta["film"],
                             publish_at=when, public_now=public_now)
            save_state({"film": {"id": film_id}})      # ⛔ يُسجَّل فورَ الرفع لا بعد كلّ شيء
        verify(svc, film_id)
        if resumed and env_at:
            reschedule(svc, film_id, when)

        # ─── المصغّرة: لازمة، ولا تُتخطّى ───
        thumb = P("thumb-a.jpg")
        if not os.path.exists(thumb):
            raise SystemExit("⛔ لا مصغّرة — لا يُنشر فيلمٌ بلا مصغّرة")
        try:
            svc.thumbnails().set(videoId=film_id, media_body=MediaFileUpload(thumb)).execute()
            quota.spend("thumbnail", film_id)
            print("✅ المصغّرة", flush=True)
        except HttpError as e:
            # ⛔ درس اليرموك 2026-09-27: اختبارُ «الاختبار والمقارنة» الجاري يمنع ضبط المصغّرة (403)،
            #    وحدُّ «مصغّرات كثيرة مؤخراً» (429) — فلا يُسقط الاستئنافُ رفعَ الريلزات.
            if resumed:
                print("⚠ تعذّرت المصغّرة (الفيلم منشورٌ سلفاً) — يُكمَل:", str(e)[:160], flush=True)
            else:
                raise

        # ─── القائمة: لازمة، وتُتحقَّق من الخادم ───
        # ⛔⛔ أمرُ المالك 2026-09-14: «لم يُضف الفيلم للقائمة وهذا لا تسامح معه».
        #    فلا يُقبل هنا إعلانٌ بلا أثر: نُضيف ثمّ **نقرأ القائمة كلَّها صفحةً صفحة**.
        add_to_playlist(svc, resolve_playlist(meta, svc), film_id)

        # ─── الريلزان: عامّان فوراً، ورابطُ الفيلم في الوصف ───
    if reels_for_film:
        film_id = reels_for_film
        link = "https://youtu.be/" + film_id
    else:
        link = meta.get("link") or ("https://www.youtube.com/playlist?list=" + meta.get("playlistId", "")) if reels_only else "https://youtu.be/" + film_id
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
    # ⭐ عنوانٌ مُعدَّل لريلزٍ بعينه من ملفّ النشر (reel_titles): حارس العنوان أعلاه يمنع رفع نسخةٍ مصحّحة بعنوان القديمة نفسه
    titles = json.loads(os.environ.get("REEL_TITLES") or "{}")
    # ⭐ إعادة رفعٍ بأمر المالك الصريح وحده (reupload في ملفّ النشر): ريلزٌ في الحالة حذفه المالك فيُرفع من جديد.
    #    (حذف r1 الأرك المجدول 2026-10-07 وأمر بنشره الآن). وحارس العنوان أدناه يبقى: لا نسخة ثانية لما على القناة.
    reupload = set(json.loads(os.environ.get("REUPLOAD") or "[]"))
    for r in meta.get("reels", []):
        if r.get("file") in titles:
            r = dict(r, title=titles[r["file"]])
        if r["file"] in done and r["file"] in reupload:
            print("↻ إعادة رفعٍ بأمر المالك:", r["file"], "— كان", done[r["file"]].get("id"), flush=True)
        elif r["file"] in done:                    # ↻ استئناف: لا يُرفع مرّتين
            print("↻ الريلز مرفوعٌ سلفاً", r["file"], flush=True)
            if env_at: reschedule(svc, done[r["file"]]["id"], reel_at(when or reel_base, len(reels)))
            reels.append(done[r["file"]]); continue
        t = r["title"].strip()[:100]
        if t in onchannel:                         # ↻ رُفع في محاولةٍ سابقةٍ سقطت
            print("↻ عنوانٌ مرفوعٌ على القناة سلفاً — لا نسخةَ ثانية:",
                  onchannel[t], flush=True)
            if env_at: reschedule(svc, onchannel[t], reel_at(when or reel_base, len(reels)))
            reels.append({"id": onchannel[t], "title": r["title"], "file": r["file"]})
            save_state({"slug": slug, "film": {"id": film_id}, "reels": reels})
            continue
        ok, used, left = quota.can("upload")
        if not ok:
            # ⭐ قاعدةُ المالك: لا يُهدر شيءٌ ولا يُدَّعى إنجازٌ لم يقع — ما تمنعه
            #    الحصّةُ **يُجدوَل** لأوّل تجدّدٍ ويُنفَّذ تلقائيّاً، ولا يسقط الشوط.
            defer(slug, film_id, r["file"], used, left)
            continue
        okshape, shape = reel_shape(P("reels", r["file"]))
        if not okshape:                            # ⛔ لا يُنشر فيلماً عاديّاً ما أُريد ريلزاً
            print("⛔ الريلز %s ليس عموديّاً أو أطول من 175 ث (%s) — لم يُرفع" % (r["file"], shape), flush=True)
            continue
        rm = dict(r)
        rm["description"] = r["description"].replace("{FILM_URL}", link)
        if "#Shorts" not in rm["description"]:
            rm["description"] = rm["description"].rstrip() + "\n\n#Shorts"
        rat = reel_at(when or reel_base, len(reels))
        rid = upload(svc, P("reels", r["file"]), rm, publish_at=rat, public_now=not rat)
        # ⛔ يُسجَّل **قبل** التحقّق: سقوطُ التحقّق بعد رفعٍ واقعٍ كان يُنتج نسخةً ثانية.
        reels.append({"id": rid, "title": r["title"], "file": r["file"]})
        save_state({"slug": slug, "film": {"id": film_id}, "reels": reels})
        verify(svc, rid)
        if not rat:                                # عامٌّ الآن ⇒ يُسأل يوتيوب: ريلزٌ هو أم فيديو؟
            ok_s = is_short(rid)
            print({True: "✅ ريلزٌ على يوتيوب: https://youtube.com/shorts/" + rid,
                   False: "⛔ نشره يوتيوب فيديو عاديّاً لا ريلزاً: " + rid,
                   None: "⚠ تعذّر الحكم أريلزٌ هو: " + rid}[ok_s], flush=True)

    # ─── ما لا تبلغه الواجهة: يُسجَّل ولا يُدَّعى ───
    os.makedirs(STATE, exist_ok=True)
    pend = P("..", "pending")
    out = {
        "slug": slug,
        "film": {"id": film_id, "title": meta.get("film", {}).get("title", ""), "publishAt": when},
        "reels": reels,
        "قيد_واجهة_غير_متاح_API": "حقل «فيديو مشابه» للشورت لا تتيحه YouTube Data API؛ "
                                  "وُضع رابط الفيلم في وصف كل ريلز، ولا يُنسب ربطٌ لم يقع.",
    }
    io.open(os.path.join(STATE, "last_publish.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
