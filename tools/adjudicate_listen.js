// تحكيمٌ آلي مستقلّ للرايات، لا يُسمّى مراجعةً بشرية ولا يمرّر نتيجةً مجهولة.
const fs = require('fs'), path = require('path');
const {fingerprint} = require('./listen_cache');

const argv = process.argv.slice(2);
const flag = (name, def) => { const i = argv.indexOf('--' + name); return i >= 0 ? argv[i + 1] : def; };
const PROJ = argv[0], KEYFILE = flag('keys', null);
const SHARD = Number(flag('shard', '0')), SHARDS = Number(flag('shards', '1'));
const MODEL = flag('model', 'gemini-3.5-flash');
if (!PROJ || !KEYFILE) throw new Error('usage: adjudicate_listen.js <project> --keys file');

const raw = fs.readFileSync(KEYFILE, 'utf8');
let vals;
try { const j = JSON.parse(raw); vals = Array.isArray(j) ? j : (j.keys || Object.values(j)); }
catch (_) { vals = raw.split(/[\r\n,"\s]+/); }
const keys = [...new Set(vals.filter(x => typeof x === 'string').map(x => x.trim()).filter(x => x.startsWith('AIza') || x.startsWith('AQ.')))];
const dead = new Set(); let cursor = SHARD % Math.max(keys.length, 1);
const nextKey = () => {
  for (let n = 0; n < keys.length; n++) {
    const k = keys[(cursor + n) % keys.length];
    if (!dead.has(k)) { cursor = (cursor + n + 1) % keys.length; return k; }
  }
  return null;
};

const blocks = JSON.parse(fs.readFileSync(path.join(PROJ, 'blocks.json'), 'utf8'))
  .filter((_, i) => i % SHARDS === SHARD);
const results = {};
for (const file of fs.readdirSync(PROJ).filter(x => /^listen_results.*\.json$/.test(x)))
  Object.assign(results, JSON.parse(fs.readFileSync(path.join(PROJ, file), 'utf8')));
const out = path.join(PROJ, `listen_reviews${SHARDS > 1 ? '.' + SHARD : ''}.json`);
let reviews = {}; try { reviews = JSON.parse(fs.readFileSync(out, 'utf8')); } catch (_) {}

const flagged = blocks.map(block => {
  const audio = fs.readFileSync(path.join(PROJ, 'audio', block.id + '.wav'));
  return {block, audio, digest: fingerprint(block.text, audio), flag: results[block.id]};
}).filter(x => x.flag && x.flag.ok === false &&
  !(reviews[x.block.id] && reviews[x.block.id].input_sha256 === x.digest &&
    ['false_positive', 'true_error'].includes(reviews[x.block.id].decision)));

const PROMPT = `أنت حكمٌ ثانٍ مستقلّ على رايات تدقيق صوت عربي مشكول. لكل مقطع: معرّف، النص، وسبب الراية الأولى، ثم الصوت.
احكم من الصوت نفسه: false_positive إذا كان المنطوق صحيحاً أو الفرق المزعوم مجرد وقف عربي مشروع لا يُسمع فيه الإعراب؛ وtrue_error إذا سقط أو تبدّل حرف/كلمة أو ظهرت حركة خاطئة مسموعة في الوصل. لا تجامل الحكم الأول.
أعد JSON فقط: {"reviews":[{"id":"...","decision":"false_positive|true_error","reason":"تعليل محدد","heard":"...","written":"..."}]}. يجب أن تعيد كل معرّف مرة واحدة.`;

function parts(items) {
  const p = [{text: PROMPT}];
  items.forEach((x, i) => {
    p.push({text: `\nالمقطع ${i + 1} — ${x.block.id}\nالنص: ${x.block.text}\nالراية الأولى: ${JSON.stringify(x.flag)}`});
    p.push({inlineData: {mimeType: 'audio/wav', data: x.audio.toString('base64')}});
  });
  return p;
}
function parse(text, ids) {
  const j = JSON.parse(text), rows = j && j.reviews;
  if (!Array.isArray(rows)) throw new Error('missing-reviews');
  const need = new Set(ids), got = new Map();
  for (const row of rows) {
    if (!row || !need.has(row.id) || got.has(row.id) ||
        !['false_positive', 'true_error'].includes(row.decision) ||
        typeof row.reason !== 'string' || !row.reason.trim() ||
        typeof row.heard !== 'string' || !row.heard.trim() ||
        typeof row.written !== 'string' || !row.written.trim()) throw new Error('invalid-review');
    got.set(row.id, row);
  }
  if (got.size !== need.size) throw new Error('missing-review');
  return got;
}

(async () => {
  if (!flagged.length) { console.log('لا رايات جديدة للتحكيم'); return; }
  if (!keys.length) throw new Error('لا مفاتيح للتحكيم');
  let hasTrueError = false;
  for (let start = 0; start < flagged.length; start += 4) {
    const group = flagged.slice(start, start + 4);
    const ids = group.map(x => x.block.id);
    let verdicts = null, invalid = 0;
    while (!verdicts) {
      const key = nextKey(); if (!key) throw new Error('nokeys-adjudication');
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
      const response = await fetch(url, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({
        contents: [{parts: parts(group)}], generationConfig: {temperature: 0, responseMimeType: 'application/json'}
      })});
      if (response.status === 429) {
        const body = await response.text();
        if (/PerDay/i.test(body)) { dead.add(key); continue; }
        await new Promise(r => setTimeout(r, 3000)); continue;
      }
      if (!response.ok) throw new Error(`adjudication-http-${response.status}`);
      const j = await response.json();
      const text = j?.candidates?.[0]?.content?.parts?.map(p => p.text).join('') || '';
      try { verdicts = parse(text, ids); }
      catch (_) {
        invalid += 1;
        if (invalid >= 3) throw new Error('adjudication-invalid-response-after-3-attempts');
      }
    }
    for (const x of group) {
      const v = verdicts.get(x.block.id);
      reviews[x.block.id] = {...v, input_sha256: x.digest,
        review_kind: 'automated_independent', reviewer: `automated-independent-review:${MODEL}`,
        primary_model: MODEL, review_model: MODEL,
        independence: 'separate_call_same_model'};
      if (v.decision === 'true_error') hasTrueError = true;
      console.log(`${v.decision === 'false_positive' ? '✓' : '⛔'} ${x.block.id}: ${v.reason}`);
    }
    fs.writeFileSync(out + '.tmp', JSON.stringify(reviews, null, 1)); fs.renameSync(out + '.tmp', out);
  }
  if (hasTrueError) process.exitCode = 2;
})().catch(e => { console.error('⛔', e.message); process.exit(1); });
