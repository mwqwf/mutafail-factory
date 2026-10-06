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

(async () => {
  const keys = loadKeys(arg('--keys'));
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
