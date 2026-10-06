// هل نفدت حصّة النماذج الأخرى أم النموذج الأحدث وحده؟ (مؤتة 2026-10-06 — سؤال المالك)
// الحصّة عند جوجل لكلّ نموذجٍ على حدة. فإن ولّدت نماذج الصوت الأخرى ونماذج الإصغاء ورُفض الأحدث وحده،
// فالعلّة فيه لا في مشاريعنا. وإن رُفضت كلّها فالقيد على المشروع أو الحساب.
//   ١) يسرد نماذج الصوت المتاحة للمفتاح (نداء قائمة، بلا توليد).
//   ٢) يسأل كلَّ نموذجٍ بمفاتيح من مشاريع مختلفة حتى أوّل نجاح: توليدةٌ واحدة لكلّ نموذجٍ متاح، وحدٌّ أقصى للمحاولات.
//   ٣) يطبع لكلّ رفضٍ نوعَه (حدّ اليوم أو حدّ الدقيقة أو «مستنفد» بلا معرّف) والحدَّ المعلن والمهلة.
// لا مفاتيح في السجلّ — أرقامها في القائمة فقط.
//   node tools/models_probe.js --keys /tmp/keys.json [--max 5] [--text gemini-3.5-flash,...]
'use strict';
const fs = require('fs');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const GL = 'https://generativelanguage.googleapis.com/v1beta';
const MAX = +arg('--max', 5);
const TEXT = arg('--text', 'gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.8-flash,gemini-flash-latest').split(',').filter(Boolean);
// المفاتيح المشاركةُ غيرَها مشروعاً (خريطة الملفّات 2026-10-06): يُترك كلٌّ منها ويُكتفى بأوّل مفتاحٍ في مشروعه
const SHARED_EXTRA = new Set([4, 15, 30, 37, 10, 25, 27, 32, 20, 33, 34, 42]);
const sleep = ms => new Promise(z => setTimeout(z, ms));

function loadKeys(file) {
  const t = fs.readFileSync(file, 'utf8');
  return [...new Set(t.match(/AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}/g) || [])];
}
const mask = s => String(s).replace(/AIza[0-9A-Za-z_\-]{10,}|AQ\.[0-9A-Za-z_\-]{10,}/g, '***');

function kind(status, txt) {
  if (status !== 429) return status >= 500 ? 'خادم' : 'مرفوض ' + status;
  if (/PerDay/i.test(txt)) return 'حدّ اليوم';
  if (/PerMinute/i.test(txt)) return 'حدّ الدقيقة';
  return 'مستنفد بلا معرّف';
}
function details(txt) {
  try {
    const det = JSON.parse(txt)?.error?.details || [];
    const v = det.find(d => /QuotaFailure/.test(d['@type'] || ''))?.violations?.[0] || {};
    const r = det.find(d => /RetryInfo/.test(d['@type'] || ''))?.retryDelay;
    return { id: v.quotaId || '', limit: v.quotaValue || '', retry: r || '' };
  } catch (e) { return {}; }
}

function body(model) {
  if (/tts/i.test(model)) return {
    contents: [{ parts: [{ text: 'قل بهدوء: مرحبا' }] }],
    generationConfig: { responseModalities: ['AUDIO'], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Charon' } } } },
  };
  return { contents: [{ parts: [{ text: 'أجب بكلمةٍ واحدة: نعم' }] }], generationConfig: { maxOutputTokens: 8 } };
}

async function probe(model, keys, order) {
  const seen = {}; let last = {};
  for (let n = 0; n < Math.min(MAX, order.length); n++) {
    const i = order[n]; const t0 = Date.now();
    try {
      const r = await fetch(`${GL}/models/${model}:generateContent?key=${keys[i]}`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body(model)) });
      const txt = await r.text();
      if (r.ok) {
        let j = {}; try { j = JSON.parse(txt); } catch (e) {}
        const parts = j?.candidates?.[0]?.content?.parts || [];
        const got = parts.some(p => p.inlineData) ? 'صوت' : parts.some(p => p.text) ? 'نصّ' : 'بلا مخرَج';
        const pre = Object.keys(seen).length ? ` بعد ${Object.entries(seen).map(([k, v]) => k + ' ' + v).join('، ')}` : '';
        return `✓ ${model}: ${got} من المحاولة ${n + 1} (المفتاح #${i})${pre} · ${((Date.now() - t0) / 1000).toFixed(1)} ث`;
      }
      const k = kind(r.status, txt); seen[k] = (seen[k] || 0) + 1; last = details(txt);
      if (r.status === 404 || r.status === 400) {
        let m = ''; try { m = JSON.parse(txt)?.error?.message || ''; } catch (e) {}
        return `⚠ ${model}: ${r.status} — ${mask(m).slice(0, 140)}`;
      }
    } catch (e) { seen['شبكة'] = (seen['شبكة'] || 0) + 1; }
    await sleep(1500);
  }
  const extra = [last.id && 'المعرّف ' + last.id, last.limit && 'الحدّ المعلن ' + last.limit, last.retry && 'المهلة ' + last.retry].filter(Boolean).join(' · ');
  return `✗ ${model}: رُفض ${Object.values(seen).reduce((a, b) => a + b, 0)} مرّة — ${Object.entries(seen).map(([k, v]) => k + ' ' + v).join('، ')}${extra ? ' · ' + extra : ''}`;
}

(async () => {
  const keys = loadKeys(arg('--keys'));
  const order = keys.map((_, i) => i).filter(i => !SHARED_EXTRA.has(i));
  console.log(`فحص حصص النماذج ${new Date().toISOString()} · المفاتيح ${keys.length} · مشاريع مختلفة في الترتيب ${order.length} · أقصى المحاولات لكلّ نموذج ${MAX}`);
  let tts = [];
  try {
    const r = await fetch(`${GL}/models?pageSize=1000&key=${keys[order[0]]}`);
    const j = await r.json();
    tts = (j.models || []).map(m => m.name.replace(/^models\//, '')).filter(n => /tts/i.test(n));
    console.log(`نماذج الصوت المتاحة للمفتاح (${tts.length}): ${tts.join('، ') || '—'}`);
  } catch (e) { console.log('تعذّر سرد النماذج: ' + mask(e.message)); }
  if (!tts.includes('gemini-3.8-flash-tts')) tts.unshift('gemini-3.8-flash-tts');
  console.log('── نماذج الصوت:');
  for (const m of tts) { console.log(await probe(m, keys, order)); await sleep(1500); }
  console.log('── نماذج الإصغاء والنصّ:');
  for (const m of TEXT) { console.log(await probe(m, keys, order)); await sleep(1500); }
})();
