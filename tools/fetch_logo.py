# -*- coding: utf-8 -*-
"""جلبُ شعار القناة من واجهة يوتيوب وحفظُه في assets/logo.png.

⭐ لماذا: الريلزاتُ والمصغّراتُ تُصنع بلا شعارٍ ما دام الملفُّ غائباً، وجلبُه
   يدويّاً يقف على المالك. والجلبُ من الواجهة **يكلّف وحدةً واحدةً** من حصّة
   يوتيوب (channels.list)، ولا يمسّ حصّةَ التوليد البتّة.
⛔ ولا يعمل في بيئة الجلسة السحابيّة: شبكتُها محجوبة. فموضعُه العدّاء.
"""
import io, json, os, sys, urllib.request, hashlib

# بعد اعتماد هوية مستقلة للمصنع لا تستبدلها بصورة الحساب القديمة أو بكاش يوتيوب.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_manifest = os.path.join(_root, "assets", "branding", "manifest.json")
if os.path.exists(_manifest):
    with open(_manifest, encoding="utf-8") as _fh:
        _brand = json.load(_fh)
    _approved = os.path.join(_root, "assets", "logo.png")
    with open(_approved, "rb") as _fh:
        _sha = hashlib.sha256(_fh.read()).hexdigest()
    if _sha != _brand["assets"]["assets/logo.png"]["sha256"]:
        raise SystemExit("⛔ بصمة الشعار لا تطابق الهوية المعتمدة؛ أصلح الأصل ولا تستبدله تلقائياً")
    print("✅ الهوية المعتمدة محفوظة؛ لا جلب لصورة الحساب فوق شعار المصنع")
    raise SystemExit(0)

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "logo.png")

c = json.loads(os.environ["YT_OAUTH_JSON"])
creds = Credentials(None, refresh_token=c["refresh_token"], client_id=c["client_id"],
                    client_secret=c["client_secret"],
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=["https://www.googleapis.com/auth/youtube"])
svc = build("youtube", "v3", credentials=creds, cache_discovery=False)
r = svc.channels().list(part="snippet", mine=True).execute()
sn = r["items"][0]["snippet"]
thumbs = sn["thumbnails"]
# أعلى دقّةٍ متاحة — والشعارُ يُصغَّر إلى مئةٍ وثمانيةَ عشرَ بكسلاً عند الرسم
url = (thumbs.get("high") or thumbs.get("medium") or thumbs["default"])["url"]
print("القناة:", sn.get("title", ""), flush=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
tmp = OUT + ".tmp"
urllib.request.urlretrieve(url, tmp)

im = Image.open(tmp)
im.verify()                      # ⛔ الحجمُ لا يكفي — الفحصُ الوحيد المعتمد هو PIL
im = Image.open(tmp).convert("RGB")
if min(im.size) < 64:
    raise SystemExit("⛔ الشعارُ المجلوب أصغرُ من أن يُستعمل: %s" % (im.size,))
im.save(OUT, "PNG")
os.remove(tmp)
print("✅ حُفظ الشعار:", OUT, im.size, flush=True)
