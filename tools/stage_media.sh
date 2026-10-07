#!/usr/bin/env bash
# تجهيز حمولة الفيلم للسحابة (الجلسة تشغّله بعد اكتمال صور كوديكس) — ⛔ لا يرفع شيئاً غير مختوم.
# الاستعمال: bash tools/stage_media.sh <slug> <مجلد_النصوص>
#   <مجلد_النصوص> فيه: script.md blocks.json shots.json publish.json الفصول.txt(اختياري) reels.json
# يسحب صور mwqwf/<slug>-media (images/ thumbs/ shorts/)، ويجمعها مع النصوص، ويختمها (seal.sh)،
# ويقسمها أجزاءً ويرفعها إلى إصدار مسوّدة <slug>-src — ثم يُطلق الشوطُ بدفع ops/run/<slug>.json
# (الجلسة السحابية تُرَدّ بـ403 على workflow_dispatch وتملك الدفع — زنادُ weekly-film منذ 2026-09-27).
set -euo pipefail
SLUG="$1"; TXT="$(cd "$2" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
gh repo clone "mwqwf/$SLUG-media" "$W/media" -- -q --depth 1
mkdir -p "$W/proj"
cp -r "$W/media/images" "$W/proj/images"
[ -d "$W/media/thumbs" ] && cp -r "$W/media/thumbs" "$W/proj/thumbs"
[ -d "$W/media/shorts" ] && cp -r "$W/media/shorts" "$W/proj/shorts"
[ -d "$W/media/cards" ] && cp -r "$W/media/cards" "$W/proj/cards"
[ -d "$W/media/map" ] && cp -r "$W/media/map" "$W/proj/map"   # أصول الخريطة الحيّة
cp "$TXT"/*.json "$W/proj/"; cp "$TXT"/*.md "$W/proj/" 2>/dev/null || true; cp "$TXT"/*.txt "$W/proj/" 2>/dev/null || true
python - "$W/proj" <<'PY'
import sys,os,json
from PIL import Image
p=sys.argv[1]; bad=[]
for d in ('images','thumbs','shorts'):
    for f in (os.listdir(os.path.join(p,d)) if os.path.isdir(os.path.join(p,d)) else []):
        if f.lower().endswith(('.jpg','.png')):
            try: Image.open(os.path.join(p,d,f)).convert('RGB')
            except Exception: bad.append(f)
shots=json.load(open(os.path.join(p,'shots.json'),encoding='utf-8'))
miss=[s['file'] for s in shots if not os.path.exists(os.path.join(p,'images',s['file']))]
print('صور معطوبة:',bad,'| ناقصة:',miss)
sys.exit(1 if bad or miss else 0)
PY
bash "$ROOT/tools/seal.sh" "$W/proj" "$W/sealed"
cd "$W/sealed" && split -b 90m -d payload.enc part_ && rm payload.enc && sha256sum part_* key.enc > SHA256SUMS
TAG="$SLUG-src"
gh release view "$TAG" -R mwqwf/mutafail-factory >/dev/null 2>&1 || \
  gh release create "$TAG" -R mwqwf/mutafail-factory --draft --title "مصدر مختوم — $SLUG" --notes "حمولة مشفّرة (seal.sh)."
for f in key.enc SHA256SUMS part_*; do
  for i in 1 2 3 4 5 6 7 8; do gh release upload "$TAG" "$f" -R mwqwf/mutafail-factory --clobber && break || sleep 30; done
done
echo "✅ رُفع المصدر المختوم إلى $TAG"
echo "   الإطلاق من الجلسة بالدفع (لا workflow_dispatch — 403):"
echo "   mkdir -p ops/run && printf '{\"slug\":\"%s\",\"stage\":\"audio\"}\\n' $SLUG > ops/run/$SLUG.json"
echo "   git add -- ops/run/$SLUG.json && git commit -m \"run: $SLUG audio\" -- ops/run/$SLUG.json && git push"
echo "   (stage: audio أوّلاً ثمّ animate بعد صوتٍ سليم؛ أو all. والمالكُ يملك أيضاً زرّ Run workflow.)"
