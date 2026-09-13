#!/usr/bin/env bash
# فضُّ الختم داخل العدّاء وحده — النصفُ الخاصّ سرُّ أكشنز لا ينزل إلى جلسة.
# الاستعمال: CONTENT_PRIVATE_KEY=... unseal.sh <مجلد_المختوم> <مجلد_الوجهة>
set -euo pipefail
DST="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
mkdir -p "$DST"
cd "$1"
printf '%s' "$CONTENT_PRIVATE_KEY" > ./.priv.tmp
openssl pkeyutl -decrypt -inkey ./.priv.tmp -in ./key.enc -out ./.k.raw -pkeyopt rsa_padding_mode:oaep
tr -d '\r\n' < ./.k.raw > ./.k.tmp
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in ./payload.enc -out ./.p.tgz -pass file:./.k.tmp
tar xzf ./.p.tgz -C "$DST"
rm -f ./.priv.tmp ./.k.tmp ./.k.raw ./.p.tgz
echo "فُضّ الختم إلى $DST"
