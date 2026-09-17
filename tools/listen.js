// الفاحصُ السمعيّ — البوّابةُ الثانية بعد التوليد.
//
// الاستعمال:
//   node listen.js <projectDir> [workers] [--keys keys.json] [--shard i --shards n]
//
// ⛔⛔ **لماذا هذا الملفّ موجود:** الدستور يوجب بعد التوليد ثلاثَ بوّابات، ثانيتُها
//    **إصغاءٌ واعٍ بالتشكيل**: يُمرَّر الصوتُ والنصُّ المشكولُ معاً إلى نموذجٍ نصّيّ
//    ليؤشّر على كلّ تنوينٍ وإعرابٍ مخالف. والمحرّكُ السحابيّ كان يُخرج أفلاماً **بلا
//    هذه البوّابة أصلاً** — والتفريغُ الآليُّ وحدَه أعمى عن التشكيل (درسٌ مكلف).
//
// ⭐ وحصّةُ نموذج الفحص **منفصلةٌ عن حصّة التوليد** فلا يزاحمه.
// الرايات تحتاج تحكيماً لا تصديقاً آلياً؛ لكن الفحص الناقص يسقط الشوط ليستأنف.
// بوابة listen_gate تمنع النشر قبل اكتمال النتائج وحداثتها وتحكيم الرايات.
const fs = require('fs'), path = require('path'), os = require('os');
const { fingerprint, reusable } = require('./listen_cache');
const { pack, requestParts, parseResponse } = require('./listen_batch');

const argv = process.argv.slice(2);
function flag(name, def) {
  const i = argv.indexOf('--' + name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : def;
}
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));

const PROJ = positional[0];
const WORKERS = parseInt(positional[1] || '4', 10);
const KEYFILE = flag('keys', null);
const SHARD = parseInt(flag('shard', '0'), 10);
const SHARDS = parseInt(flag('shards', '1'), 10);
const MODEL = flag('model', 'gemini-3.5-flash');
const BATCH = Math.max(1, parseInt(flag('batch', '4'), 10));
if (!PROJ) { console.error('usage: node listen.js <projectDir> [workers] [--keys f]'); process.exit(1); }

const KEYFILES = [
  path.join(os.homedir(), '.claude', 'skills', 'video-factory', 'keys.txt'),
  path.join(os.homedir(), 'Desktop', 'claude-media', 'muw', 'مفاتيح-جديدة.txt'),
];
function harvest(text, into) {
  const t = String(text).trim();
  try {
    const j = JSON.parse(t);
    const arr = Array.isArray(j) ? j : (Array.isArray(j.keys) ? j.keys : Object.values(j));
    arr.forEach(v => { if (typeof v === 'string') { const s = v.trim(); if (s.startsWith('AIza') || s.startsWith('AQ.')) into.add(s); } });
    return;
  } catch (e) {}
  t.split(/[\r\n,"\s]+/).forEach(l => { l = l.trim(); if (l.startsWith('AIza') || l.startsWith('AQ.')) into.add(l); });
}
function loadKeys() {
  const s = new Set();
  if (KEYFILE) { try { harvest(fs.readFileSync(KEYFILE, 'utf8'), s); } catch (e) {} }
  for (const f of KEYFILES) { try { harvest(fs.readFileSync(f, 'utf8'), s); } catch (e) {} }
  return [...s];
}

const OUT = path.join(PROJ, `listen_results${SHARDS > 1 ? '.' + SHARD : ''}.json`);
let res = {};
try { res = JSON.parse(fs.readFileSync(OUT, 'utf8')); } catch (e) { res = {}; }

const all = JSON.parse(fs.readFileSync(path.join(PROJ, 'blocks.json'), 'utf8'));
const blocks = all.filter((_, i) => i % SHARDS === SHARD);
const keys = loadKeys();
let ki = 0;
const dead = {};
function nextKey() {
  for (let n = 0; n < keys.length; n++) {
    const k = keys[(ki + n) % keys.length];
    if (!dead[k]) { ki = (ki + n + 1) % keys.length; return k; }
  }
  return null;
}

const PROMPT = `أنت مدقّقٌ لغويّ عربيّ دقيق. ستتلقى {COUNT} مقاطع مستقلة، ولكل مقطع معرّف ونص مشكول يسبقان صوته مباشرة.
قارن كل منطوق بمكتوبه حرفاً حرفاً وحركةً حركة. لا تخلط المقاطع، ولا تسقط واحداً، وأجب بـJSON وحده:
{"results":[{"id":"<المعرّف نفسه>","ok":true},{"id":"<المعرّف نفسه>","ok":false,"why":"<سبب موجز>","heard":"<المسموع>","written":"<المكتوب>"}]}
وانتبه لهذه الأنماط خاصّةً: سقوطُ كلمةٍ أو إبدالُها بمرادف · تنوينٌ في موضع السكون أو عكسه ·
حركةُ إعرابٍ مخالفة · ابتلاعُ آخر كلمة · حروفُ العلم الأعجميّ الناقصة.
⚠️ ولا تعتبر اختلافَ النبر أو مدَّ الصوت مخالفةً — المخالفةُ في الحرف والحركة وحدهما.
`;

async function checkGroup(group) {
  const ids = group.map(x => x.block.id);
  const deadline = Date.now() + 3 * 60 * 1000;
  while (Date.now() < deadline) {
    const key = nextKey();
    if (!key) return Object.fromEntries(ids.map(id => [id, {ok: null, why: 'nokeys'}]));
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
    const body = {
      contents: [{ parts: requestParts(group, PROMPT) }],
      generationConfig: { temperature: 0, responseMimeType: 'application/json',
        responseSchema: {type: 'OBJECT', required: ['results'], properties: {
          results: {type: 'ARRAY', items: {type: 'OBJECT', required: ['id','ok'], properties: {
            id: {type: 'STRING'}, ok: {type: 'BOOLEAN'}, why: {type: 'STRING'},
            heard: {type: 'STRING'}, written: {type: 'STRING'}
          }}}
        }}
      },
    };
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 120000);
      const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal });
      clearTimeout(t);
      if (r.status === 429) {
        const txt = await r.text();
        if (/PerDay/i.test(txt)) { dead[key] = 1; continue; }
        await new Promise(z => setTimeout(z, 3000)); continue;
      }
      if (r.status === 404 || r.status === 400) {
        const txt = await r.text();
        return Object.fromEntries(ids.map(id => [id, {ok: null, why: `${r.status}: ${txt.slice(0, 120).replace(/\s+/g, ' ')}`} ]));
      }
      if (!r.ok) { await new Promise(z => setTimeout(z, 2000)); continue; }
      const j = await r.json();
      const txt = j?.candidates?.[0]?.content?.parts?.map(p => p.text).join('') || '';
      try {
        return parseResponse(txt, ids);
      } catch (e) { return Object.fromEntries(ids.map(id => [id, {ok: null, why: 'ردٌّ مجمّع غير صالح'}])); }
    } catch (e) { await new Promise(z => setTimeout(z, 2000)); }
  }
  return Object.fromEntries(ids.map(id => [id, {ok: null, why: 'مهلةٌ منتهية'}]));
}

(async () => {
  console.log(`مفاتيح: ${keys.length} | كتلُ الحصّة ${SHARD}/${SHARDS}: ${blocks.length} | نموذج: ${MODEL} | تجميع: ${BATCH}`);
  if (!keys.length) { console.error('⛔ لا مفاتيح — الفحصُ السمعيّ لم يجرِ'); process.exit(1); }
  const digests = new Map(blocks.map(b => {
    const file = path.join(PROJ, 'audio', b.id + '.wav');
    return [b.id, fs.existsSync(file) ? fingerprint(b.text, fs.readFileSync(file)) : null];
  }));
  const todo = blocks.filter(b => !digests.get(b.id) || !reusable(res[b.id], digests.get(b.id)))
    .map(block => ({block, audio: fs.readFileSync(path.join(PROJ, 'audio', block.id + '.wav'))}));
  const batches = pack(todo, BATCH);
  let i = 0, done = 0;
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    while (i < batches.length) {
      const group = batches[i++];
      const verdicts = await checkGroup(group);
      for (const {block} of group) {
        res[block.id] = verdicts[block.id];
        res[block.id].input_sha256 = digests.get(block.id);
      }
      fs.writeFileSync(OUT + '.tmp', JSON.stringify(res, null, 1));
      fs.renameSync(OUT + '.tmp', OUT);
      done += group.length;
      if (done % 20 === 0) {
        console.log(`… ${done}/${todo.length}`);
      }
    }
  }));
  fs.writeFileSync(OUT + '.tmp', JSON.stringify(res, null, 1));
  fs.renameSync(OUT + '.tmp', OUT);

  const vals = Object.entries(res);
  const flags = vals.filter(([, v]) => v && v.ok === false);
  const skipped = vals.filter(([, v]) => !v || typeof v.ok !== 'boolean');
  const checked = vals.length - skipped.length;
  const pct = checked ? (flags.length * 100 / checked) : 0;
  console.log(`\n── الفحصُ السمعيّ ──`);
  console.log(`مفحوص: ${checked} | رايات: ${flags.length} (${pct.toFixed(1)}٪) | لم يُفحص: ${skipped.length}`);
  console.log(`والهدف المعتمد: أقلّ من خمسةٍ في المئة.`);
  for (const [id, v] of flags.slice(0, 40)) {
    console.log(`  ⚑ ${id}: ${v.why || ''} | سُمع «${v.heard || ''}» والمكتوب «${v.written || ''}»`);
  }
  if (skipped.length) {
    process.exitCode = 1;
    // ⛔ ما لم يُفحص يُسمّى ولا يُدَّعى أنه اجتاز
    console.log(`⚠️ ${skipped.length} كتلةً لم تُفحص — لا يُقال إنها اجتازت البوّابة.`);
    // ⛔⛔ درسٌ مقيسٌ 2026-09-14 (حلقة الموحّدين): اجتاز الفحصُ اثنتي عشرةَ كتلةً
    //    من إحدى وستّين، وسكت السجلُّ عن **السبب**. فبقي الدماغُ لا يدري:
    //    أنفدت الحصّة؟ أم النموذجُ غيرُ موجود؟ أم الشبكة؟ ⇒ يُحصى السببُ بنصّه.
    const tally = {};
    for (const [, v] of skipped) {
      const why = (v && v.why) ? String(v.why).slice(0, 60) : 'بلا نتيجة';
      tally[why] = (tally[why] || 0) + 1;
    }
    console.log('أسبابُ عدم الفحص:');
    Object.entries(tally).sort((a, b) => b[1] - a[1])
      .forEach(([w, n]) => console.log(`  · ${n} × ${w}`));
  }
})();
