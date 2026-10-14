// أيّ مفاتيح جيميناي فيها رصيد؟ — أمر المالك 2026-10-14: «جرّب توليد مقطعٍ لأحدث نموذج… وحدّد المفاتيح التي فيها رصيد بأقلّ تكلفة».
//   ١) نداء القائمة لكلّ مفتاح (مجّانيّ): أيّ النماذج يراها؟ المفاتيح المجانية لا ترى النماذج الأحدث المدفوعة أصلاً.
//   ٢) أحدثُ نموذج صوتٍ غير «flash/lite» (الأعلى رقماً) يُسأل بتوليدةٍ واحدةٍ قصيرة جداً من المفاتيح التي تراه فقط،
//      ويُتوقَّف عند أوّل نجاح ⇒ كلفةُ أجزاءٍ من السنت. والمقطع يُحفظ في out/paid_sample.wav ليُسمع.
// لا مفاتيح في السجلّ — أرقامها في القائمة فقط.   node tools/paid_key_probe.js --keys /tmp/keys.json
'use strict';
const fs = require('fs');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const GL = 'https://generativelanguage.googleapis.com/v1beta';
const keys = [...new Set(fs.readFileSync(arg('--keys'), 'utf8').match(/AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}/g) || [])];
const mask = s => String(s).replace(/AIza[0-9A-Za-z_\-]{10,}|AQ\.[0-9A-Za-z_\-]{10,}/g, '***');
const ver = n => (n.match(/(\d+(?:\.\d+)?)/) || [0, 0])[1] * 1;

function wav(pcm, rate = 24000) {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + pcm.length, 4); h.write('WAVEfmt ', 8); h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(rate, 24); h.writeUInt32LE(rate * 2, 28);
  h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write('data', 36); h.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([h, pcm]);
}

(async () => {
  console.log(`فحص الرصيد ${new Date().toISOString()} · المفاتيح ${keys.length}`);
  const seen = [];
  for (let i = 0; i < keys.length; i++) {
    try {
      const j = await (await fetch(`${GL}/models?pageSize=1000&key=${keys[i]}`)).json();
      seen[i] = (j.models || []).map(m => m.name.replace(/^models\//, ''));
      if (j.error) console.log(`#${i}: خطأ ${j.error.code} ${mask(j.error.message).slice(0, 80)}`);
    } catch (e) { seen[i] = []; console.log(`#${i}: شبكة`); }
  }
  const all = [...new Set(seen.flat())];
  const common = all.filter(m => seen.every(s => !s.length || s.includes(m)));
  const extra = all.filter(m => !common.includes(m));
  console.log(`نماذج يراها كلّ مفتاح: ${common.length} · نماذج لا يراها إلا بعضها: ${extra.join('، ') || '—'}`);
  seen.forEach((s, i) => { const x = s.filter(m => extra.includes(m)); if (x.length) console.log(`#${i} يرى: ${x.join('، ')}`); });
  const tts = all.filter(m => /tts/i.test(m) && !/flash|lite/i.test(m)).sort((a, b) => ver(b) - ver(a));
  console.log(`نماذج الصوت الأعلى (غير الخفيفة): ${tts.join('، ') || '—'}`);
  const model = tts[0];
  if (!model) return console.log('لا نموذج صوتٍ غير خفيف تراه أيّ مفاتيح.');
  const cand = keys.map((_, i) => i).filter(i => seen[i].includes(model));
  console.log(`أحدثها ${model} · يراه ${cand.length} مفتاحاً: ${cand.map(i => '#' + i).join(' ')}`);
  const res = [];
  for (const i of cand) {
    const r = await fetch(`${GL}/models/${model}:generateContent?key=${keys[i]}`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: 'قل بصوتٍ حماسيّ: قاتلوا الخليفة طوال النهار… ولم يكن هو!' }] }],
        generationConfig: { responseModalities: ['AUDIO'], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Charon' } } } } }) });
    const txt = await r.text();
    if (r.ok) {
      const d = JSON.parse(txt).candidates?.[0]?.content?.parts?.find(p => p.inlineData)?.inlineData?.data;
      fs.mkdirSync('out', { recursive: true });
      if (d) fs.writeFileSync('out/paid_sample.wav', wav(Buffer.from(d, 'base64')));
      console.log(`✓ المفتاح #${i} فيه رصيد: ولّد ${model}${d ? ' (out/paid_sample.wav)' : ''}`);
      res.push(i); break;
    }
    let m = ''; try { m = JSON.parse(txt).error.message; } catch (e) {}
    console.log(`✗ #${i}: ${r.status} ${mask(m).slice(0, 110)}`);
  }
  console.log(res.length ? `النتيجة: المفتاح ذو الرصيد #${res[0]}` : 'النتيجة: لم ينجح أيّ مفتاح.');
})();
