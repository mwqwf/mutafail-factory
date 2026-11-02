#!/usr/bin/env bash
# تجديد رمز اكس (OAuth 2.0) وختم رمز التجديد المتبدّل فوراً في الإصدار الخاصّ x-stats.
# يُستدعى من سير x.yml قبل أيّ طلب، ومن tools/x_api.py في التنظيف الطويل قبل انتهاء الساعتين.
# المحفوظ محلياً (/tmp/xtok) أحدث من المختوم، فلا يُنزَّل إلا حين يغيب.
set -euo pipefail
N=$(printf '%s\n' "${X_KEYS:-}" | grep -c . || true)
[ -n "${X_REFRESH_TOKEN:-}" ] && N=3
[ "$N" = 3 ] || { echo "🔑 وضع OAuth 1.0a — لا تجديد"; exit 0; }
mkdir -p /tmp/xtok
if [ ! -s /tmp/xtok/x_token.json ]; then
  rm -rf /tmp/xsealed && mkdir -p /tmp/xsealed
  if gh release download x-stats -p 'xtok.*' -D /tmp/xsealed --clobber 2>/dev/null && [ -s /tmp/xsealed/xtok.key.enc ]; then
    mv /tmp/xsealed/xtok.payload.enc /tmp/xsealed/payload.enc; mv /tmp/xsealed/xtok.key.enc /tmp/xsealed/key.enc
    bash tools/unseal.sh /tmp/xsealed /tmp/xtok >/dev/null
  fi
fi
python3 tools/x_api.py refresh /tmp/xtok
rm -rf /tmp/xtokonly /tmp/xsealed && mkdir -p /tmp/xtokonly && cp /tmp/xtok/x_token.json /tmp/xtokonly/
bash tools/seal.sh /tmp/xtokonly /tmp/xsealed >/dev/null && rm -rf /tmp/xtokonly
mv /tmp/xsealed/payload.enc /tmp/xsealed/xtok.payload.enc; mv /tmp/xsealed/key.enc /tmp/xsealed/xtok.key.enc
gh release upload x-stats /tmp/xsealed/xtok.payload.enc /tmp/xsealed/xtok.key.enc --clobber >/dev/null
echo "✅ خُتم رمز التجديد الجديد في x-stats"
