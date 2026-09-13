#!/usr/bin/env bash
# ختمُ حمولةِ حلقةٍ بمفتاحٍ عامّ — لا يحتاج سرّاً، فيصلح للجلسة السحابية.
# الاستعمال: seal.sh <مجلد_الحمولة> <مجلد_المخرَج>
# ⚠️ يعمل داخل مجلد المخرَج بأسماء مجرّدة، لأن openssl على ويندوز لا يقرأ مسارات git-bash.
set -euo pipefail
SRC="$(cd "$1" && pwd)"
PUB="$(cd "$(dirname "$0")/.." && pwd)/content_public.pem"
mkdir -p "$2"; cd "$2"
cp "$PUB" ./.pub.tmp
tar czf ./.p.tgz -C "$SRC" .
# ⛔ المفتاح بلا أيّ نهاية سطر: openssl يعامل النهاية اختلافاً بين ويندوز ولينكس
#    فيصير ما شُفّر على ويندوز لا يُفكّ على العدّاء (‏bad decrypt مقيسٌ 2026-09-13).
openssl rand -hex 32 | tr -d '\r\n' > ./.k.tmp
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -in ./.p.tgz -out ./payload.enc -pass file:./.k.tmp
openssl pkeyutl -encrypt -pubin -inkey ./.pub.tmp -in ./.k.tmp -out ./key.enc -pkeyopt rsa_padding_mode:oaep
rm -f ./.k.tmp ./.p.tgz ./.pub.tmp
echo "خُتمت الحمولة: $(du -h ./payload.enc | cut -f1)"
