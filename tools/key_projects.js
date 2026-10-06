// كم مشروعاً حقيقياً خلف مفاتيح جيميناي؟ (مؤتة 2026-10-06 — المالك: «ابحث فيما لم تبحث فيه»)
// حصّة نموذج الصوت لكلّ مشروع (GenerateRequestsPerDayPerProjectPerModel = 10)، فإن تشاركت المفاتيح مشاريع قلّت السعة.
// يسأل كلَّ مفتاحٍ واجهةً غيرَ مفعّلة في مشروعه (Vision ثم Natural Language ثم Translate)، فيذكر ردُّ جوجل
// «has not been used in project N» أو consumer=projects/N — بلا أيّ نداءٍ لجيميناي ولا صرفٍ من حصّته.
// المشروع يُطبع بوسمٍ مموَّه لا برقمه، والمفاتيح بأرقامها في القائمة.
//   node tools/key_projects.js --keys /tmp/keys.json
'use strict';
const fs = require('fs');
const crypto = require('crypto');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const tag = s => 'م' + crypto.createHash('sha256').update(String(s)).digest('hex').slice(0, 4);
const PROBES = [
  ['vision', k => ['https://vision.googleapis.com/v1/images:annotate?key=' + k, { requests: [] }]],
  ['language', k => ['https://language.googleapis.com/v1/documents:analyzeSentiment?key=' + k, { document: { type: 'PLAIN_TEXT', content: 'a' } }]],
  ['translate', k => ['https://translation.googleapis.com/language/translate/v2?key=' + k, { q: 'a', target: 'en' }]],
];

function loadKeys(file) {
  const t = fs.readFileSync(file, 'utf8');
  return [...new Set(t.match(/AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}/g) || [])];
}

function projectOf(txt) {
  const m = /project[s]?[\/ =:]+(\d{6,})/i.exec(txt) || /consumer"?\s*:\s*"?projects\/(\d{6,})/i.exec(txt);
  return m ? m[1] : null;
}

async function find(key) {
  const seen = [];
  for (const [name, mk] of PROBES) {
    const [url, body] = mk(key);
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      const txt = await r.text();
      const p = projectOf(txt);
      if (p) return { project: p, via: name };
      let reason = '';
      try { const e = JSON.parse(txt).error || {}; reason = (e.status || '') + ' ' + ((e.details || []).find(d => d.reason)?.reason || ''); } catch (e) {}
      seen.push(name + ':' + r.status + ' ' + reason.trim());
    } catch (e) { seen.push(name + ':شبكة'); }
  }
  return { project: null, seen };
}

// الطريق الثاني (حين لا تقبل المفاتيحُ واجهاتٍ غير جيميناي — مقصورةٌ عليه): ملفّات Files API تُحفظ لكلّ مشروع،
// فيُرفع بكلّ مفتاحٍ ملفٌّ صغير، ثم يُسأل كلّ مفتاحٍ أيّ الملفّات يرى: من يرى ملفّ غيره فهما في مشروعٍ واحد.
// لا توليد ولا صرف من حصّة الصوت، والملفّات تُحذف بعد الفحص (وتنتهي وحدها بعد 48 ساعة).
const GL = 'https://generativelanguage.googleapis.com';
async function viaFiles(keys) {
  const mine = {};
  for (let i = 0; i < keys.length; i++) {
    try {
      const r = await fetch(`${GL}/upload/v1beta/files?uploadType=media&key=${keys[i]}`, {
        method: 'POST', headers: { 'content-type': 'text/plain' }, body: 'probe ' + i });
      const j = await r.json();
      const name = j?.file?.name || j?.name;
      if (name) mine[name] = i; else console.log(`  #${i}: تعذّر الرفع (${r.status} ${(j?.error?.status || '')})`);
    } catch (e) { console.log(`  #${i}: تعذّر الرفع (شبكة)`); }
    await new Promise(z => setTimeout(z, 150));
  }
  const parent = keys.map((_, i) => i);
  const root = x => (parent[x] === x ? x : (parent[x] = root(parent[x])));
  for (let i = 0; i < keys.length; i++) {
    try {
      const r = await fetch(`${GL}/v1beta/files?pageSize=100&key=${keys[i]}`);
      const j = await r.json();
      for (const f of j.files || []) if (f.name in mine) parent[root(mine[f.name])] = root(i);
    } catch (e) {}
    await new Promise(z => setTimeout(z, 150));
  }
  for (const [name, i] of Object.entries(mine)) {
    try { await fetch(`${GL}/v1beta/${name}?key=${keys[i]}`, { method: 'DELETE' }); } catch (e) {}
  }
  const groups = {};
  for (const i of Object.values(mine)) (groups['م' + root(i)] = groups['م' + root(i)] || []).push(i);
  return { groups, uploaded: Object.keys(mine).length };
}

(async () => {
  const keys = loadKeys(arg('--keys'));
  if (process.argv.includes('--files')) {
    console.log(`خريطة المشاريع بالملفّات ${new Date().toISOString()} · المفاتيح ${keys.length} · بلا توليد`);
    const { groups, uploaded } = await viaFiles(keys);
    const gs = Object.values(groups).sort((a, b) => b.length - a.length);
    console.log(`رُفع ${uploaded} ملفّاً · المشاريع المتمايزة: ${gs.length} · السعة اليومية لنموذج الصوت ≈ ${gs.length} × 10 = ${gs.length * 10}`);
    const shared = gs.filter(g => g.length > 1);
    console.log(shared.length ? `مشاريع تحمل أكثر من مفتاح: ${shared.map(g => g.map(i => '#' + i).join(' ')).join(' | ')}` : 'كلّ مفتاحٍ في مشروعٍ مستقلّ');
    return;
  }
  console.log(`خريطة المشاريع ${new Date().toISOString()} · المفاتيح ${keys.length} · بلا نداءٍ لجيميناي`);
  const groups = {}, unknown = [];
  for (let i = 0; i < keys.length; i++) {
    const r = await find(keys[i]);
    if (r.project) (groups[tag(r.project)] = groups[tag(r.project)] || []).push(i);
    else unknown.push('#' + i + ' (' + r.seen.join(' · ') + ')');
    await new Promise(z => setTimeout(z, 200));
  }
  const gs = Object.entries(groups).sort((a, b) => b[1].length - a[1].length);
  const shared = gs.filter(([, ks]) => ks.length > 1);
  console.log(`المشاريع المتمايزة: ${gs.length} لـ${keys.length - unknown.length} مفتاحاً معروف المشروع · السعة اليومية لنموذج الصوت ≈ ${gs.length} × 10 = ${gs.length * 10}`);
  console.log(shared.length ? `مشاريع تحمل أكثر من مفتاح: ${shared.map(([p, ks]) => `${p}: ${ks.map(i => '#' + i).join(' ')}`).join(' | ')}`
                            : 'كلّ مفتاحٍ في مشروعٍ مستقلّ');
  if (unknown.length) console.log(`لم يُعرف مشروعه: ${unknown.join(' ; ')}`);
})();
