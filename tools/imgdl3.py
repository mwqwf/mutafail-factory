# -*- coding: utf-8 -*-
"""تنزيلُ صور بوليناشنز — النسخةُ المعتمدة (نقلُ مذهب `imgdl3` إلى المصنع السحابيّ).

الاستعمال:  python imgdl3.py <projectDir>

⛔⛔ الدرسُ المقيس الذي أسقط الشوطَ الثامن (2026-09-13): كان `imgdl2.js` يتحقّق من
الصورة بـ`python -c "from PIL import ..."`، و**وظيفةُ الصور لا بايثون فيها ولا PIL**،
فكان كلُّ تحقّقٍ يرمي فيُحذف ملفٌّ سليمٌ نزل فعلاً — سبعٌ وستّون صورةً كلُّها «فاشلة»
في ساعتين، والشبكةُ سليمة. ⇒ التنزيلُ والتحقّقُ صارا في أداةٍ واحدةٍ ببايثون.

ومذهبُ `imgdl3` المقيس محفوظٌ بنصّه:
- عاملٌ **واحد** لا توازيَ البتّة (الطبقةُ المجانية: طابورٌ واحدٌ لكل عنوان).
  ⭐ والتسريعُ بالقسمة على عدّائين فأكثر (`--shard/--shards`) لا يخالف هذا: كلُّ
    عدّاءٍ عنوانٌ مستقلٌّ بطابورٍ مستقلّ. ⛔ أمّا داخل العدّاء فواحدٌ كما كان.
- محاولاتٌ **قصيرة**: ٤٥ ثانية × ٨، وفاصلُ ٢٠ ثانية بعد الإخفاق و٣٥ بعد ٤٢٩.
- **يقول لماذا فشل**: رمزُ الحالة والحجم في كل إخفاق — لا «✗ فشل» صمّاء.
- `https://` مع اتّباع التحويل (`-L`): الخادمُ يردّ ٣٠١ على `http://`.
- التحقّقُ بـPIL لا بالحجم: صورةٌ مبتورةٌ تتجاوز ٢٥ ك.ب فتخدع.
- الخدمةُ تسقف المجّانيّ عند ١٠٢٤×٥٧٦ ⇒ تُرقّى محليًّا إلى ١٩٢٠×١٠٨٠ ويُحفظ الأصل.
"""
import io
import json
import os
import subprocess as sp
import sys
import time
import urllib.parse

from PIL import Image

# ⛔ تُقرأ الوسائطُ عند التشغيل لا عند الاستيراد، وإلّا سقط استيرادُ الاختبار
#    (‏`sys.argv[1]` غيرُ موجودٍ في مشغّل الاختبارات) فبقي الحارسُ بلا اختبار.
PROJ = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ""
TIMEOUT = 45          # محاولةٌ قصيرة تنجح حيث تفشل الطويلة (مقيس)
ATTEMPTS = 8
GAP_FAIL = 20         # بعد إخفاق
GAP_429 = 35          # بعد خنق
GAP_OK = 1.2          # بين صورتين ناجحتين
# ⭐ جولاتٌ متأخّرة (2026-09-25): ردّ الخادمُ بـ500 على صورٍ بعينها ثماني مرّاتٍ متتالية ثمّ
#    أجاب غيرها بعد دقائق، فسقط شوطا «الساعة» و«الحصان» بصورتين أو تسعٍ لكلّ سهم. ⇒ ما فشل
#    يُعاد في آخر السهم بعد تبريد، ولا تُمسّ عتبةُ السلامة ولا يُركَّب فيلمٌ ناقص.
ROUNDS = 3
COOLDOWN = 180


def _shard_args(argv):
    """`--shard N --shards M` — القسمةُ على عدّائين، لا خيوطٌ داخل العدّاء الواحد.

    ⭐ المقياسُ الذي أوجبها (2026-09-21): خمسٌ وسبعون صورةً في ثمانين دقيقة، صفرُ
       فشلٍ نهائيّ، وزمنُ الصورة الواحدة ≈٤٥ ثانيةً كلُّها انتظارُ توليدٍ عند الخادم.
       ⇒ العنقُ ليس فواصلَنا بل زمنُ الخادم، ولا يُحلّ إلا بطابورٍ آخر.
    ⛔ ومذهبُ «عاملٌ واحدٌ لا توازيَ البتّة» باقٍ على وجهه: **طابورٌ واحدٌ لكلّ
       عنوان**. وكلُّ عدّاءٍ في مصفوفة الأعمال عنوانٌ مستقلّ، فلا يُخالَف المقياس.
       ⛔ ولا يُزاد التوازي داخل العدّاء الواحد بخيوطٍ أو عمليّات.
    """
    shard, shards = 0, 1
    for i, a in enumerate(argv):
        if a == "--shard" and i + 1 < len(argv):
            shard = int(argv[i + 1])
        elif a == "--shards" and i + 1 < len(argv):
            shards = int(argv[i + 1])
    if shards < 1 or not (0 <= shard < shards):
        raise SystemExit("⛔ قسمةٌ غيرُ صالحة: --shard %d من --shards %d" % (shard, shards))
    return shard, shards


def slice_for(items, shard, shards):
    """قسمةٌ دوريّةٌ ثابتة: كلُّ صورةٍ في سهمٍ واحدٍ لا غير، وبلا فجوة."""
    return [it for n, it in enumerate(items) if n % shards == shard]


SHARD, SHARDS = _shard_args(sys.argv[2:]) if len(sys.argv) > 1 else (0, 1)
MINBYTES = 25000      # ⛔ لا ترفع العتبة: السليم يبدأ من ٢٩ ك.ب
TARGET = (1920, 1080)

DIR = os.path.join(PROJ, "img")
ORIG = os.path.join(PROJ, "img-orig")


def sound(path):
    """سليمةٌ فعلاً؟ PIL أوّلاً ثمّ الحجم — لا العكس."""
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            wh = im.size
    except Exception:
        return None
    if os.path.getsize(path) < MINBYTES:
        return None
    return wh


def upscale(path):
    """ترقيةٌ محليّةٌ مجّانية إلى ١٩٢٠×١٠٨٠ مع حفظ الأصل."""
    with Image.open(path) as im:
        if im.size == TARGET:
            return im.size
        keep = os.path.join(ORIG, os.path.basename(path))
        if not os.path.exists(keep):
            im.save(keep, quality=95, subsampling=0)
        big = im.convert("RGB").resize(TARGET, Image.LANCZOS)
    big.save(path, quality=94, subsampling=0)
    return TARGET


def fetch(prompt, out, seed):
    """يُرجع (رمزُ الحالة، الحجم) — ولا يبتلع السبب أبداً."""
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt, safe="")
           + "?width=1920&height=1080&model=flux&nologo=true&seed=%d" % seed)
    r = sp.run(["curl", "-s", "-L", "-m", str(TIMEOUT), "-o", out,
                "-w", "%{http_code}", url], capture_output=True, text=True)
    code = (r.stdout or "").strip()[-3:]
    size = os.path.getsize(out) if os.path.exists(out) else 0
    return code, size


def one(it, rnd):
    """صورةٌ واحدة: ثماني محاولاتٍ قصيرة؛ والبذرةُ تتغيّر بين الجولات."""
    out = os.path.join(DIR, it["id"] + ".jpg")
    if sound(out):
        upscale(out)
        return True
    for attempt in range(1, ATTEMPTS + 1):
        seed = 1000 + attempt * 137 + (rnd - 1) * 7919 + sum(ord(c) for c in it["id"])
        code, size = fetch(it["prompt"], out, seed)
        wh = sound(out)
        if wh:
            wh = upscale(out)
            print("✓ %s · %s · %d ب · %dx%d" % (it["id"], code, size, wh[0], wh[1]), flush=True)
            return True
        print("  … %s محاولة %d/%d · حالة %s · %d بايت" % (it["id"], attempt, ATTEMPTS, code, size), flush=True)
        try:
            if os.path.exists(out):
                os.remove(out)
        except OSError:
            pass
        time.sleep(GAP_429 if code == "429" else GAP_FAIL)
    print("✗ فشل %s بعد %d محاولة (الجولة %d)" % (it["id"], ATTEMPTS, rnd), flush=True)
    return False


def main():
    global IMGS
    IMGS = json.load(io.open(os.path.join(PROJ, "images.json"), encoding="utf-8"))
    os.makedirs(DIR, exist_ok=True)
    os.makedirs(ORIG, exist_ok=True)
    mine = slice_for(IMGS, SHARD, SHARDS)
    print("=== %s: %d صورة (سهم %d من %d ⇐ %d صورة) ==="
          % (os.path.basename(PROJ), len(IMGS), SHARD, SHARDS, len(mine)), flush=True)
    ok, pending = 0, list(mine)
    for rnd in range(1, ROUNDS + 1):
        if rnd > 1:
            if not pending:
                break
            print("\n↻ جولةٌ متأخّرة %d/%d لـ%d صورة بعد تبريد %d ثانية"
                  % (rnd, ROUNDS, len(pending), COOLDOWN), flush=True)
            time.sleep(COOLDOWN)
        failed = []
        for it in pending:
            if one(it, rnd):
                ok += 1
            else:
                failed.append(it)
            time.sleep(GAP_OK)
        pending = failed
    failed = [it["id"] for it in pending]
    print("\n%s: نجح %d | فشل %d" % (os.path.basename(PROJ), ok, len(failed)), flush=True)
    if failed:
        # ⛔ لا يُركَّب فيلمٌ ناقصُ الصور صامتاً
        raise SystemExit("⛔ صورٌ متعذّرة: " + " · ".join(failed))


if __name__ == "__main__":
    main()
