#!/usr/bin/env bash
# يجلب حالة شوطٍ سابق من إصدار <tag> إلى <dir>/state.tgz — ملفّاً واحداً أو أجزاءً (state.tgz.part_*)
# (ملاذكرد 2026-10-03: الفيلم كلّه حيّ ⇒ الحالة تجاوزت حدّ أصول GitHub 2 غ.ب، فرُفضت وضاعت مقاطع مدفوعة)
# الاستعمال: bash tools/state_fetch.sh <tag> <dir> — رمز الخروج 1 إن لم توجد حالة
set -uo pipefail
TAG="$1"; D="$2"; mkdir -p "$D"; rm -f "$D"/state.tgz "$D"/state.tgz.part_*
gh release download "$TAG" -R "$GITHUB_REPOSITORY" -p 'state.tgz.part_*' -D "$D" --clobber 2>/dev/null
if ls "$D"/state.tgz.part_* >/dev/null 2>&1; then
  cat "$D"/state.tgz.part_* > "$D/state.tgz" && rm -f "$D"/state.tgz.part_*
else
  gh release download "$TAG" -R "$GITHUB_REPOSITORY" -p 'state.tgz' -D "$D" --clobber 2>/dev/null || exit 1
fi
[ -s "$D/state.tgz" ]
