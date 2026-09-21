// اختبارُ قسمةِ الدفعة المتعذّرة في الفحص السمعيّ — بلا شبكةٍ وبلا حصّة.
//
// ⛔ العطبُ الذي يحرسه (مقيسٌ 2026-09-21، حلقة «الثور»): دفعةُ ستّ عشرة كتلةً
//    تتجاوز مهلةَ النداء فترجع كلُّها «مهلةٌ منتهية»، وإعادةُ الشوط تكرّر الدفعةَ
//    نفسَها فتسقط السقوطَ نفسَه ثلاثَ مرّات. والعلاجُ الذي يثبته هذا الاختبار:
//    تُقسم الدفعةُ حتى تمرّ، فلا تُهدر كتلةٌ سليمةٌ بسبب حجم الدفعة.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const proj = fs.mkdtempSync(path.join(os.tmpdir(), 'listen-split-'));
const blocks = [1, 2, 3, 4].map(n => ({ id: 'd_00' + n, voice: 'Charon', text: 'نَصٌّ ' + n }));
fs.writeFileSync(path.join(proj, 'blocks.json'), JSON.stringify(blocks), 'utf8');
fs.mkdirSync(path.join(proj, 'audio'));
for (const b of blocks) fs.writeFileSync(path.join(proj, 'audio', b.id + '.wav'), Buffer.from('RIFFwav'));
fs.writeFileSync(path.join(proj, 'keys.json'), JSON.stringify(['AIzaTESTKEYTESTKEYTESTKEY']), 'utf8');

process.argv = ['node', 'listen.js', proj, '1', '--keys', path.join(proj, 'keys.json'),
                '--group-deadline-ms', '150'];
const { checkGroup } = require('./listen.js');

// خادمٌ مزيّف: الدفعةُ الكبيرة تتعثّر دائماً، والصغيرةُ تمرّ — كحال النداء الحقيقيّ
let bigCalls = 0, smallCalls = 0;
global.fetch = async (url, opts) => {
  const body = JSON.parse(opts.body);
  const ids = body.contents[0].parts
    .map(p => (p.text || '').match(/المعرّف (d_\d{3})/))
    .filter(Boolean).map(m => m[1]);
  if (ids.length > 1) { bigCalls++; return { ok: false, status: 500, text: async () => 'boom' }; }
  smallCalls++;
  return {
    ok: true, status: 200,
    json: async () => ({ candidates: [{ content: { parts: [
      { text: JSON.stringify({ results: [{ id: ids[0], ok: true }] }) }] } }] }),
  };
};

(async () => {
  const group = blocks.map(b => ({ block: b, audio: Buffer.from('RIFFwav') }));
  const verdicts = await checkGroup(group);

  assert.deepStrictEqual(Object.keys(verdicts).sort(), blocks.map(b => b.id),
    'كلُّ كتلةٍ يجب أن يعود لها حكم');
  for (const b of blocks) {
    assert.strictEqual(verdicts[b.id].ok, true, `الكتلة ${b.id} بقيت بلا فحص`);
    assert.notStrictEqual(verdicts[b.id].why, 'مهلةٌ منتهية');
  }
  assert.ok(bigCalls > 0, 'لم تُجرَّب الدفعةُ الكبيرة أصلاً');
  assert.strictEqual(smallCalls, 4, 'القسمةُ لم تنزل إلى الآحاد');
  console.log(`✅ قسمةُ الدفعة المتعذّرة: ${bigCalls} نداءً كبيراً متعثّراً ثمّ ${smallCalls} آحاداً ناجحة`);
  fs.rmSync(proj, { recursive: true, force: true });
})();
