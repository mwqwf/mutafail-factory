// مولّد الصوت — يعمل على جهاز المالك وعلى عدّاء أكشنز معاً.
//
// الاستعمال:
//   node gen25.js <projectDir> [workers] [--keys keys.json] [--shard i --shards n] [--model m]
//
// ⛔⛔ عطبان مقيسان أُصلحا في 2026-09-14 (الشوط الثامن: «نجح 0 | فشل 6» في كل سهم):
//   ١) الأداة كانت تقرأ المفاتيح من مسارات وندوز وحدها، فترد `nokeys` في السحاب
//      مهما كان السرّ مضبوطاً — لأنّ `--keys` لم يكن يُقرأ أصلاً.
//   ٢) `--shard` لم يكن يُقرأ كذلك، فكانت الأسهم الستّة تولّد **الكتل كلّها ستّ مرّات**
//      ⇒ إحراقُ ستّة أضعاف الحصّة. والحصّة عندنا ٦٠٠ توليدة في اليوم كلّه.
//
// ⭐ والنموذج المعتمد هو الأحدث (`gemini-3.1-flash-tts-preview`) بأمر المالك،
//    و`2.5` احتياطٌ بحصّةٍ منفصلة — و`dead` تُحفظ **لكل نموذج على حدة**،
//    وإلا ورث الاحتياطُ موتى الأوّل فردّ `nokeys` كذباً (درس «المغول» 2026-09-11).
const fs = require('fs'), path = require('path'), os = require('os');

const argv = process.argv.slice(2);
function flag(name, def) {
  const i = argv.indexOf('--' + name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : def;
}
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));

const PROJ = positional[0];
const WORKERS = parseInt(positional[1] || '6', 10);
const KEYFILE = flag('keys', null);
const SHARD = parseInt(flag('shard', '0'), 10);
const SHARDS = parseInt(flag('shards', '1'), 10);

if (!PROJ) { console.error('usage: node gen25.js <projectDir> [workers] [--keys f] [--shard i --shards n]'); process.exit(1); }

// ⭐ دائماً الأحدث أوّلاً، والاحتياطُ بحصّةٍ منفصلة
const MODELS = (flag('model', '') ? [flag('model', '')] : [
  'gemini-3.1-flash-tts-preview',
  'gemini-2.5-flash-preview-tts',
]);

// ── المفاتيح: من الوسيط أوّلاً (السحاب)، ثمّ من ملفّات المالك (وندوز) ──
const KEYFILES = [
  path.join(os.homedir(), '.claude', 'skills', 'video-factory', 'keys.txt'),
  path.join(os.homedir(), 'Desktop', 'claude-media', 'muw', 'مفاتيح-جديدة.txt'),
  path.join(os.homedir(), 'Downloads', 'مفاتيح-جيميناي-نسخة-احتياطية.txt'),
];
function harvest(text, into) {
  // يقبل: مصفوفة JSON · كائناً فيه keys · نصّاً سطراً لكل مفتاح
  let t = String(text).trim();
  try {
    const j = JSON.parse(t);
    const arr = Array.isArray(j) ? j : (Array.isArray(j.keys) ? j.keys : Object.values(j));
    arr.forEach(v => { if (typeof v === 'string') { const s = v.trim(); if (s.startsWith('AIza') || s.startsWith('AQ.')) into.add(s); } });
    return;
  } catch (e) { /* ليس JSON — يُقرأ سطوراً */ }
  t.split(/[\r\n,"\s]+/).forEach(l => { l = l.trim(); if (l.startsWith('AIza') || l.startsWith('AQ.')) into.add(l); });
}
function loadKeys() {
  const s = new Set();
  if (KEYFILE) {
    try { harvest(fs.readFileSync(KEYFILE, 'utf8'), s); }
    catch (e) { console.error('⛔ تعذّرت قراءة ملفّ المفاتيح ' + KEYFILE + ': ' + e.message); }
  }
  for (const f of KEYFILES) {
    try { harvest(fs.readFileSync(f, 'utf8'), s); } catch (e) {}
  }
  return [...s];
}

const OUT = path.join(PROJ, 'audio');
fs.mkdirSync(OUT, { recursive: true });
const STATE = path.join(PROJ, `gen_state${SHARDS > 1 ? '.' + SHARD : ''}.json`);
let state = {};
try { state = JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch (e) { state = {}; }
state.done = state.done || {}; state.dead = state.dead || {}; state.calls = state.calls || 0;
state.model_of = state.model_of || {};
// ⭐ إحياء المفاتيح بعد تجديد الحصّة اليوميّ (07:00 UTC / 08:00 الجزائر).
{
  const now = new Date();
  const qd = new Date(now.getTime() - 7 * 3600 * 1000).toISOString().slice(0, 10);
  if (state.quotaDay !== qd) {
    const n = Object.keys(state.dead).length;
    state.dead = {}; state.quotaDay = qd;
    if (n) console.log(`♻️ يومُ حصّةٍ جديد (${qd}) — أُحييت ${n} مفتاحًا`);
  }
}
function save() { fs.writeFileSync(STATE, JSON.stringify(state, null, 1)); }

const allBlocks = JSON.parse(fs.readFileSync(path.join(PROJ, 'blocks.json'), 'utf8'));
// ⭐ التقسيم على الأسهم — بالتناوب فتتوزّع الكتل الطويلة والقصيرة بالعدل
const blocks = allBlocks.filter((_, i) => i % SHARDS === SHARD);

const keys = loadKeys();
let ki = 0;
// ⭐ الموتى لكلّ نموذجٍ على حدة: `dead[model][key]`
function deadOf(m) { state.dead[m] = state.dead[m] || {}; return state.dead[m]; }
function nextKey(model) {
  const dead = deadOf(model);
  for (let n = 0; n < keys.length; n++) {
    const k = keys[(ki + n) % keys.length];
    if (!dead[k]) { ki = (ki + n + 1) % keys.length; return k; }
  }
  return null;
}

function wavHeader(dataLen, rate = 24000, ch = 1, bits = 16) {
  const b = Buffer.alloc(44);
  b.write('RIFF', 0); b.writeUInt32LE(36 + dataLen, 4); b.write('WAVE', 8);
  b.write('fmt ', 12); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20);
  b.writeUInt16LE(ch, 22); b.writeUInt32LE(rate, 24);
  b.writeUInt32LE(rate * ch * bits / 8, 28); b.writeUInt16LE(ch * bits / 8, 32);
  b.writeUInt16LE(bits, 34); b.write('data', 36); b.writeUInt32LE(dataLen, 40);
  return b;
}

async function genWith(model, blk) {
  const outFile = path.join(OUT, blk.id + '.wav');
  // ⭐ 3.8 بطيء والنتّ ضعيف ⇒ مهلة أطول (SKILL §٢: 600 ث للطلب)
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    const key = nextKey(model);
    if (!key) return 'nokeys';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
    const body = {
      // توجيه الأداء (style) يسبق النصّ بصيغة «Say …: نص» الموثّقة؛ والفاحص السمعي يمسك أيّ نطقٍ له
      contents: [{ parts: [{ text: (blk.style ? blk.style + ': ' : '') + blk.text }] }],
      generationConfig: {
        responseModalities: ['AUDIO'],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: blk.voice || 'Charon' } } },
      },
    };
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 600000);
      const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal });
      clearTimeout(t);
      state.calls++;
      if (r.status === 429) {
        const txt = await r.text();
        // ⭐ اقرأ جسم الخطأ: ميّز حدّ اليوم من حدّ الدقيقة
        if (/PerDay/i.test(txt)) { deadOf(model)[key] = 'daily'; save(); continue; }
        await new Promise(z => setTimeout(z, 3000)); continue;
      }
      if (r.status === 404 || r.status === 400) {
        // النموذج غير متاحٍ لهذا المفتاح أصلاً — لا تطحن عليه
        const txt = await r.text();
        console.log(`  ⚠ ${model}: ${r.status} — ${txt.slice(0, 160).replace(/\s+/g, ' ')}`);
        return 'nomodel';
      }
      if (!r.ok) { await new Promise(z => setTimeout(z, 2000)); continue; }
      const j = await r.json();
      const p = j?.candidates?.[0]?.content?.parts?.find(x => x.inlineData);
      if (!p) { await new Promise(z => setTimeout(z, 1500)); continue; }
      const pcm = Buffer.from(p.inlineData.data, 'base64');
      fs.writeFileSync(outFile, Buffer.concat([wavHeader(pcm.length), pcm]));
      state.done[blk.id] = true; state.model_of[blk.id] = model; save();
      return 'ok';
    } catch (e) { await new Promise(z => setTimeout(z, 2000)); }
  }
  return 'timeout';
}

// النماذج بالترتيب: الأحدث، فإن نفدت حصّتُه كلُّها فالاحتياط
const disabled = new Set();
async function genOne(blk) {
  const outFile = path.join(OUT, blk.id + '.wav');
  if (state.done[blk.id] && fs.existsSync(outFile) && fs.statSync(outFile).size > 8000) return 'skip';
  let last = 'nokeys';
  for (const m of MODELS) {
    if (disabled.has(m)) continue;
    const r = await genWith(m, blk);
    if (r === 'ok') return 'ok';
    if (r === 'nomodel') { disabled.add(m); continue; }
    last = r;
  }
  return last;
}

(async () => {
  console.log(`مفاتيح: ${keys.length} | كتل الحمولة: ${allBlocks.length} | حصّة السهم ${SHARD}/${SHARDS}: ${blocks.length} | نماذج: ${MODELS.join(' ← ')}`);
  if (!keys.length) {
    console.error('⛔⛔ لا مفاتيح البتّة. في السحاب: تحقّق من سرّ GEMINI_KEYS_JSON و--keys.');
    process.exit(1);            // ⛔ لا تنجح صامتاً كما وقع في الشوط الثامن
  }
  // ⛔⛔ درسٌ مقيسٌ 2026-09-14 (أمر المالك: «لا يضيع شيءٌ من الحصّة»):
  //    الحالةُ `gen_state` لا تعبر بين الأشواط، والملفُّ المولَّد يعبر (أثَرُ الصوت).
  //    فكان الاستئنافُ يُعيد توليدَ كتلةٍ صوتُها موجودٌ فعلاً ⇒ حرقُ حصّةٍ بلا مقابل.
  //    ⇒ الشاهدُ الأوّلُ هو الملفُّ نفسُه لا الدفتر: ما وُجد صوتُه سليماً لا يُعاد.
  let adopted = 0;
  for (const b of blocks) {
    const f = path.join(OUT, b.id + '.wav');
    if (!state.done[b.id] && fs.existsSync(f) && fs.statSync(f).size > 8000) {
      state.done[b.id] = true; adopted++;
    }
  }
  if (adopted) { save(); console.log(`↻ تُبنّي ${adopted} كتلةً وُجد صوتُها من شوطٍ سابق — لا تُعاد`); }
  const todo = blocks.filter(b => !state.done[b.id]);
  console.log(`متبقٍّ: ${todo.length} | مسارات: ${WORKERS}`);
  let i = 0, ok = 0, fail = 0;
  const failed = [];
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    while (i < todo.length) {
      const blk = todo[i++];
      const r = await genOne(blk);
      if (r === 'ok' || r === 'skip') ok++; else { fail++; failed.push(blk.id + ':' + r); console.log(`✗ ${blk.id}: ${r}`); }
      if ((ok + fail) % 10 === 0) console.log(`… ${ok + fail}/${todo.length} | نجح ${ok} | فشل ${fail} | نداءات ${state.calls}`);
      if (r === 'nokeys') break;   // نفدت الحصّة — لا تطحن (درس 2026-09-12)
    }
  }));
  save();
  const models = {};
  Object.values(state.model_of).forEach(m => { models[m] = (models[m] || 0) + 1; });
  console.log(`انتهى: نجح ${ok} | فشل ${fail} | إجمالي النداءات ${state.calls}`);
  console.log(`النماذج المستعمَلة: ${JSON.stringify(models)}`);
  if (fail) {
    console.log(`⛔ الكتل المتعذّرة: ${failed.join(' · ')}`);
    process.exit(2);            // ⛔ الفشل يُعلَن ولا يُبتلع
  }
})();
