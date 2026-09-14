# -*- coding: utf-8 -*-
"""تنزيلُ صور بوليناشنز — النسخةُ المعتمدة (نقلُ مذهب `imgdl3` إلى المصنع السحابيّ).

الاستعمال:  python imgdl3.py <projectDir>

⛔⛔ الدرسُ المقيس الذي أسقط الشوطَ الثامن (2026-09-13): كان `imgdl2.js` يتحقّق من
الصورة بـ`python -c "from PIL import ..."`، و**وظيفةُ الصور لا بايثون فيها ولا PIL**،
فكان كلُّ تحقّقٍ يرمي فيُحذف ملفٌّ سليمٌ نزل فعلاً — سبعٌ وستّون صورةً كلُّها «فاشلة»
في ساعتين، والشبكةُ سليمة. ⇒ التنزيلُ والتحقّقُ صارا في أداةٍ واحدةٍ ببايثون.

ومذهبُ `imgdl3` المقيس محفوظٌ بنصّه:
- عاملٌ **واحد** لا توازيَ البتّة (الطبقةُ المجانية: طابورٌ واحدٌ لكل عنوان).
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

PROJ = os.path.abspath(sys.argv[1])
TIMEOUT = 45          # محاولةٌ قصيرة تنجح حيث تفشل الطويلة (مقيس)
ATTEMPTS = 8
GAP_FAIL = 20         # بعد إخفاق
GAP_429 = 35          # بعد خنق
GAP_OK = 1.2          # بين صورتين ناجحتين
MINBYTES = 25000      # ⛔ لا ترفع العتبة: السليم يبدأ من ٢٩ ك.ب
TARGET = (1920, 1080)

IMGS = json.load(io.open(os.path.join(PROJ, "images.json"), encoding="utf-8"))
DIR = os.path.join(PROJ, "img")
ORIG = os.path.join(PROJ, "img-orig")
os.makedirs(DIR, exist_ok=True)
os.makedirs(ORIG, exist_ok=True)


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


def main():
    print("=== %s: %d صورة ===" % (os.path.basename(PROJ), len(IMGS)), flush=True)
    ok, failed = 0, []
    for it in IMGS:
        out = os.path.join(DIR, it["id"] + ".jpg")
        if sound(out):
            upscale(out)
            ok += 1
            continue
        got = False
        for attempt in range(1, ATTEMPTS + 1):
            seed = 1000 + attempt * 137 + sum(ord(c) for c in it["id"])
            code, size = fetch(it["prompt"], out, seed)
            wh = sound(out)
            if wh:
                wh = upscale(out)
                print("✓ %s · %s · %d ب · %dx%d" % (it["id"], code, size, wh[0], wh[1]), flush=True)
                got = True
                break
            print("  … %s محاولة %d/%d · حالة %s · %d بايت" % (it["id"], attempt, ATTEMPTS, code, size), flush=True)
            try:
                if os.path.exists(out):
                    os.remove(out)
            except OSError:
                pass
            time.sleep(GAP_429 if code == "429" else GAP_FAIL)
        if got:
            ok += 1
        else:
            failed.append(it["id"])
            print("✗ فشل %s بعد %d محاولة" % (it["id"], ATTEMPTS), flush=True)
        time.sleep(GAP_OK)
    print("\n%s: نجح %d | فشل %d" % (os.path.basename(PROJ), ok, len(failed)), flush=True)
    if failed:
        # ⛔ لا يُركَّب فيلمٌ ناقصُ الصور صامتاً
        raise SystemExit("⛔ صورٌ متعذّرة: " + " · ".join(failed))


if __name__ == "__main__":
    main()
