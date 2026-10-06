#!/usr/bin/env bash
# بديل stage_media.sh للجلسة السحابية التي لا تملك gh: يختم الحمولة ويدفعها مشفّرةً إلى فرعٍ يتيم sealed/<slug>.
# الاستعمال: bash tools/stage_branch.sh <slug> <مجلد_النصوص> [مجلد_الوسائط]
#   <مجلد_الوسائط> (اختياري) فيه images/ thumbs/ shorts/ — بدونه تُختم النصوص وحدها (يكفي لمرحلة الصوت).
# ⛔ لا يدخل git إلا المشفَّر (key.enc و part_*)؛ فكّه يحتاج CONTENT_PRIVATE_KEY الذي لا يملكه إلا العدّاء.
set -euo pipefail
SLUG="$1"; TXT="$(cd "$2" && pwd)"; MED="${3:-}"
[ -n "${SEAL_INTO:-}" ] && SEAL_INTO="$(mkdir -p "$SEAL_INTO" && cd "$SEAL_INTO" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
mkdir -p "$W/proj"
cp "$TXT"/*.json "$W/proj/"; cp "$TXT"/*.md "$W/proj/" 2>/dev/null || true; cp "$TXT"/*.txt "$W/proj/" 2>/dev/null || true
if [ -n "$MED" ]; then
  for d in images thumbs shorts ui audio_fix cards map; do [ -d "$MED/$d" ] && cp -r "$MED/$d" "$W/proj/$d"; done   # map: أصول الخريطة الحيّة
  python3 - "$W/proj" <<'PY'
import sys,os,json
from PIL import Image
p=sys.argv[1]; bad=[]
for d in ('images','thumbs','shorts','cards'):
    for f in (os.listdir(os.path.join(p,d)) if os.path.isdir(os.path.join(p,d)) else []):
        if f.lower().endswith(('.jpg','.png')):
            try: Image.open(os.path.join(p,d,f)).convert('RGB')
            except Exception: bad.append(f)
shots=json.load(open(os.path.join(p,'shots.json'),encoding='utf-8'))
miss=[s['file'] for s in shots if not os.path.exists(os.path.join(p,'images',s['file']))]
cj=os.path.join(p,'cards.json')
nc=[c['file'] for c in json.load(open(cj,encoding='utf-8')).values() if not os.path.exists(os.path.join(p,c['file']))] if os.path.exists(cj) else []
if nc: print('⚠ بطاقات كوديكس الغائبة (يُتخطّى عنصرها):',len(nc))
print('صور معطوبة:',bad,'| ناقصة:',miss)
sys.exit(1 if bad or miss else 0)
PY
fi
bash "$ROOT/tools/seal.sh" "$W/proj" "$W/sealed"
cd "$W/sealed" && split -b 90m -d payload.enc part_ && rm payload.enc && sha256sum part_* key.enc > SHA256SUMS
# SEAL_INTO=<مجلد> ⇒ يُنسخ المختوم إلى ذلك المجلد (ops/sealed/<slug> في فرع الجلسة) بدل دفع فرعٍ يتيم
if [ -n "${SEAL_INTO:-}" ]; then
  rm -f "$SEAL_INTO"/part_* && cp key.enc SHA256SUMS part_* "$SEAL_INTO"/
  echo "✅ خُتم المصدر في $SEAL_INTO — ادفعه مع ops/run/$SLUG.json"; exit 0
fi
git init -q && git checkout -q --orphan "sealed/$SLUG" && git add -A
git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -q -m "حمولة مختومة: $SLUG [skip ci]"
git push -q -f "$(git -C "$ROOT" remote get-url origin)" "sealed/$SLUG:sealed/$SLUG"
echo "✅ دُفع المصدر المختوم إلى الفرع sealed/$SLUG — ثم شغّل weekly-film.yml بـ slug=$SLUG"
