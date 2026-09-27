# -*- coding: utf-8 -*-
"""رفع مصغرات PNG المطابقة لمعرّفات الفيديو والتحقق منها."""
import glob
import os
import sys
import urllib.request

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota
from publish_youtube import yt


def main(folder):
    svc = yt()
    channel = svc.channels().list(part="id", mine=True).execute()["items"][0]["id"]
    files = sorted(glob.glob(os.path.join(folder, "*.png")))
    if len(files) != 10:
        raise SystemExit("⛔ المتوقع عشر صور PNG، وُجد: %d" % len(files))
    failed = []
    for path in files:
        name = os.path.basename(path)
        vid = name.rsplit("-", 1)[-1][:-4]
        item = svc.videos().list(part="snippet", id=vid).execute().get("items", [])
        if not item or item[0]["snippet"].get("channelId") != channel:
            raise SystemExit("⛔ الفيديو غير موجود أو لا يتبع القناة: " + vid)
        thumbs = item[0]["snippet"].get("thumbnails", {})
        url = next((thumbs[k]["url"] for k in ("maxres", "standard", "high", "medium", "default")
                    if k in thumbs and "url" in thumbs[k]), None)
        if not url:
            raise SystemExit("⛔ لم أجد المصغرة الحالية لحفظها: " + vid)
        os.makedirs("thumbnail-backup", exist_ok=True)
        urllib.request.urlretrieve(url, os.path.join("thumbnail-backup", vid + ".jpg"))
    for path in files:
        vid = os.path.basename(path).rsplit("-", 1)[-1][:-4]
        ok, used, left = quota.can("thumbnail")
        if not ok:
            raise SystemExit("⛔ الحصة لا تحتمل المصغرة؛ المتبقي %d" % left)
        try:
            result = svc.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(path, mimetype="image/png"),
            ).execute()
        except HttpError as exc:
            failed.append(vid)
            print("⛔ رفض يوتيوب المصغرة:", vid, str(exc)[:240], flush=True)
            continue
        uploaded = result.get("items", [])
        if not uploaded or not any(
            isinstance(value, dict) and value.get("url")
            for value in uploaded[0].values()
        ):
            raise SystemExit("⛔ رد رفع غير مكتمل: " + vid)
        quota.spend("thumbnail", vid)
        current = svc.videos().list(part="snippet", id=vid).execute().get("items", [])
        if not current or current[0].get("id") != vid or not current[0]["snippet"].get("thumbnails"):
            raise SystemExit("⛔ لم تظهر بيانات الفيديو بعد رفع المصغرة: " + vid)
        print("✅ رُفعت وتحققت المصغرة:", vid, flush=True)
    if failed:
        raise SystemExit("⛔ لم تُقبل المصغرات لهذه المعرّفات: " + ", ".join(failed))


if __name__ == "__main__":
    main(sys.argv[1])
