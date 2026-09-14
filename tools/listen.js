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
// ⚠️ ومخرَجُه **استشاريّ**: يكتب تقريراً ولا يُسقط الشوط. فنصفُ الرايات تقريباً يكون
//    عيبُها في النصّ المكتوب لا في الصوت، والحكمُ فيها لنا لا للآلة.
const fs = require('fs'), path = require('path'), os = require('os');

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

const PROMPT = `أنت مدقّقٌ لغويّ عربيّ دقيق. سأعطيك مقطعاً صوتيّاً والنصَّ المشكولَ الذي وُلِّد منه.
قارن **المنطوق** بـ**المكتوب** حرفاً حرفاً وحركةً حركة، ثمّ أجب بـJSON وحده بلا أيّ شرحٍ خارجه:
{"ok": true}  إذا طابق المنطوقُ المكتوبَ في الكلمات وفي الإعراب والتشكيل.
{"ok": false, "why": "<سببٌ في سطرٍ واحد>", "heard": "<الكلمة كما سُمعت>", "written": "<الكلمة كما كُتبت>"}  إذا خالف.
وانتبه لهذه الأنماط خاصّةً: سقوطُ كلمةٍ أو إبدالُها بمرادف · تنوينٌ في موضع السكون أو عكسه ·
حركةُ إعرابٍ مخالفة · ابتلاعُ آخر كلمة · حروفُ العلم الأعجميّ الناقصة.
⚠️ ولا تعتبر اختلافَ النبر أو مدَّ الصوت مخالفةً — المخالفةُ في الحرف والحركة وحدهما.

النصّ المشكول:
`;

async function checkOne(blk) {
  const wav = path.join(PROJ, 'audio', blk.id + '.wav');
  if (!fs.existsSync(wav)) return { ok: null, why: 'لا ملفَّ صوتٍ' };
  const b64 = fs.readFileSync(wav).toString('base64');
  const deadline = Date.now() + 3 * 60 * 1000;
  while (Date.now() < deadline) {
    const key = nextKey();
    if (!key) return { ok: null, why: 'nokeys' };
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
    const body = {
      contents: [{ parts: [
        { text: PROMPT + blk.text },
        { inlineData: { mimeType: 'audio/wav', data: b64 } },
      ] }],
      generationConfig: { temperature: 0, responseMimeType: 'application/json' },
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
        return { ok: null, why: `${r.status}: ${txt.slice(0, 120).replace(/\s+/g, ' ')}` };
      }
      if (!r.ok) { await new Promise(z => setTimeout(z, 2000)); continue; }
      const j = await r.json();
      const txt = j?.candidates?.[0]?.content?.parts?.map(p => p.text).join('') || '';
      try { return JSON.parse(txt); } catch (e) { return { ok: null, why: 'ردٌّ غيرُ مفهوم' }; }
    } catch (e) { await new Promise(z => setTimeout(z, 2000)); }
  }
  return { ok: null, why: 'مهلةٌ منتهية' };
}

(async () => {
  console.log(`مفاتيح: ${keys.length} | كتلُ الحصّة ${SHARD}/${SHARDS}: ${blocks.length} | نموذج: ${MODEL}`);
  if (!keys.length) { console.error('⛔ لا مفاتيح — الفحصُ السمعيّ لم يجرِ'); process.exit(0); }
  const todo = blocks.filter(b => !(b.id in res));
  let i = 0, done = 0;
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    while (i < todo.length) {
      const blk = todo[i++];
      res[blk.id] = await checkOne(blk);
      done++;
      if (done % 20 === 0) {
        fs.writeFileSync(OUT, JSON.stringify(res, null, 1));
        console.log(`… ${done}/${todo.length}`);
      }
    }
  }));
  fs.writeFileSync(OUT, JSON.stringify(res, null, 1));

  const vals = Object.entries(res);
  const flags = vals.filter(([, v]) => v && v.ok === false);
  const skipped = vals.filter(([, v]) => !v || v.ok === null);
  const checked = vals.length - skipped.length;
  const pct = checked ? (flags.length * 100 / checked) : 0;
  console.log(`\n── الفحصُ السمعيّ ──`);
  console.log(`مفحوص: ${checked} | رايات: ${flags.length} (${pct.toFixed(1)}٪) | لم يُفحص: ${skipped.length}`);
  console.log(`والهدف المعتمد: أقلّ من خمسةٍ في المئة.`);
  for (const [id, v] of flags.slice(0, 40)) {
    console.log(`  ⚑ ${id}: ${v.why || ''} | سُمع «${v.heard || ''}» والمكتوب «${v.written || ''}»`);
  }
  if (skipped.length) {
    // ⛔ ما لم يُفحص يُسمّى ولا يُدَّعى أنه اجتاز
    console.log(`⚠️ ${skipped.length} كتلةً لم تُفحص — لا يُقال إنها اجتازت البوّابة.`);
  }
})();
