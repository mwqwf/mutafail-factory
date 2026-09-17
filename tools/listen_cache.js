// لا تُعاد نتيجة قديمة بعد تبدّل النص أو الصوت، ولا تُحفظ المهلة كفحص مكتمل.
const crypto = require('node:crypto');
function fingerprint(text, audio) {
  return crypto.createHash('sha256').update(text, 'utf8').update('\0').update(audio).digest('hex');
}
function reusable(result, digest) {
  return !!result && typeof result.ok === 'boolean' && result.input_sha256 === digest;
}
module.exports = { fingerprint, reusable };
