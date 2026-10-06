// فحص حصّة نموذج الصوت بلا توليدٍ يُذكر (مؤتة 2026-10-06 — افتراض المالك: «ما استُهلك اليوم جزءٌ من حصّة الأمس، وحصّة اليوم لم تتجدّد»).
// يسأل كلّ مفتاحٍ طلباً قصيراً واحداً بالترتيب، ويقف عند أوّل نجاح (فلا يُصرف إلا توليدةٌ واحدة إن كانت الحصّة متاحة)،
// ويجمع من أجسام 429: معرّف الحدّ، وقيمته المعلنة (quotaValue)، ومهلة الرفع (retryDelay) — ومنها وقت التجدّد المتوقّع.
// لا مفاتيح ولا روابط في السجلّ: المفاتيح بأرقامها في القائمة.
//   node tools/quota_probe.js --keys /tmp/keys.json [--model gemini-3.8-flash-tts]
'use strict';
const fs = require('fs');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const MODEL = arg('--model', 'gemini-3.8-flash-tts');

function loadKeys(file) {
  const t = fs.readFileSync(file, 'utf8');
  const found = t.match(/AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}/g) || [];
  return [...new Set(found)];
}

function seconds(d) { const m = /^(\d+(?:\.\d+)?)s$/.exec(String(d || '')); return m ? Math.round(+m[1]) : null; }

async function ask(key) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
  const body = {
    contents: [{ parts: [{ text: 'نَعَمْ.' }] }],
    generationConfig: { responseModalities: ['AUDIO'], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Algenib' } } } },
  };
  try {
    const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    const txt = await r.text();
    if (r.ok) return { ok: true };
    let det = [];
    try { det = JSON.parse(txt)?.error?.details || []; } catch (e) {}
    const v = det.flatMap(d => d.violations || []);
    const retry = det.find(d => /RetryInfo/.test(d['@type'] || ''))?.retryDelay;
    return { ok: false, status: r.status, ids: v.map(x => x.quotaId), limits: v.map(x => x.quotaValue).filter(Boolean), retry };
  } catch (e) {
    return { ok: false, status: 'net', ids: [], limits: [] };
  }
}

(async () => {
  const keys = loadKeys(arg('--keys'));
  const now = new Date();
  console.log(`فحص الحصّة ${now.toISOString()} · النموذج ${MODEL} · المفاتيح ${keys.length}`);
  const tally = {};
  for (let i = 0; i < keys.length; i++) {
    const r = await ask(keys[i]);
    if (r.ok) {
      console.log(`✅ المفتاح #${i} ولّد: الحصّة متاحة الآن — وقف الفحص بتوليدةٍ واحدة (سبقه ${i} مفتاحاً بلا إنتاج)`);
      break;
    }
    const id = (r.ids[0] || ('حالة ' + r.status));
    const t = tally[id] || (tally[id] = { n: 0, limits: new Set(), retries: [] });
    t.n++; r.limits.forEach(x => t.limits.add(x));
    const s = seconds(r.retry); if (s !== null) t.retries.push(s);
    if (i === keys.length - 1) console.log('⛔ لم يولّد مفتاحٌ واحد');
    await new Promise(z => setTimeout(z, 300));
  }
  for (const [id, t] of Object.entries(tally)) {
    const rs = t.retries.sort((a, b) => a - b);
    const mid = rs.length ? rs[Math.floor(rs.length / 2)] : null;
    const at = mid !== null ? new Date(now.getTime() + mid * 1000).toISOString().slice(11, 16) + 'Z' : '—';
    console.log(`${id}: ${t.n} مفتاحاً · الحدّ المعلن ${[...t.limits].join('/') || '—'} · المهلة (أدنى/وسيط/أعلى) ${rs.length ? rs[0] + '/' + mid + '/' + rs[rs.length - 1] + ' ث' : '—'} · الرفع المتوقّع ≈ ${at}`);
  }
})();
