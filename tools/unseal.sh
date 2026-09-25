#!/usr/bin/env bash
# فضُّ الختم داخل العدّاء وحده — النصفُ الخاصّ سرُّ أكشنز لا ينزل إلى جلسة.
# الاستعمال: CONTENT_PRIVATE_KEY=... unseal.sh <مجلد_المختوم> <مجلد_الوجهة>
set -euo pipefail
DST="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
mkdir -p "$DST"
cd "$1"
PAYLOAD=./payload.enc
JOINED=./.payload.joined.tmp
if compgen -G './payload.part.*.enc' >/dev/null; then
  mapfile -t PARTS < <(printf '%s\n' ./payload.part.*.enc | sort)
  cat "${PARTS[@]}" > "$JOINED"
  PAYLOAD="$JOINED"
fi
if [ -f ./trigger.json ]; then
  EXPECTED="$(python3 -c 'import json; print(json.load(open("trigger.json", encoding="utf-8"))["payload_sha256"])')"
  ACTUAL="$(sha256sum "$PAYLOAD" | cut -d' ' -f1)"
  [ "$ACTUAL" = "$EXPECTED" ] || { echo "⛔ بصمة الحمولة المجمعة لا تطابق الزناد"; rm -f "$JOINED"; exit 1; }
fi
printf '%s' "$CONTENT_PRIVATE_KEY" > ./.priv.tmp
openssl pkeyutl -decrypt -inkey ./.priv.tmp -in ./key.enc -out ./.k.raw -pkeyopt rsa_padding_mode:oaep
tr -d '\r\n' < ./.k.raw > ./.k.tmp
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in "$PAYLOAD" -out ./.p.tgz -pass file:./.k.tmp
tar xzf ./.p.tgz -C "$DST"
rm -f ./.priv.tmp ./.k.tmp ./.k.raw ./.p.tgz "$JOINED"
echo "فُضّ الختم إلى $DST"
