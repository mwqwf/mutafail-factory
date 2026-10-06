// مولّد الصوت — يعمل على جهاز المالك وعلى عدّاء أكشنز معاً.
//
// الاستعمال:
//   node gen25.js <projectDir> [workers] [--keys keys.json] [--shard i --shards n] [--model m]
//
// ⛔⛔ عطبان مقيسان أُصلحا في 2026-09-14 (الشوط الثامن: «نجح 0 | فشل 6» في كل سهم):
//   ١) الأداة كانت تقرأ المفاتيح من مسارات وندوز وحدها، فترد `nokeys` في السحاب
//      مهما كان السرّ مضبوطاً — لأنّ `--keys` لم يكن يُقرأ أصلاً.
//   ٢) `--shard` لم يكن يُقرأ كذلك، فكانت الأسهم الستّة تولّد **الكتل كلّها ستّ مرّات**
//      ⇒ إحراقُ ستّة أضعاف الحصّة. والحصّة عندنا ٦٠٠ توليدة في اليوم كلّه (قياس 2026-09-14 لنماذج يومها).
//   ⛔ قياس الأرك 2026-10-04 لـgemini-3.8-flash-tts بالمفاتيح الـ43: نفدت حصّة اليوم بعد نحو ٣٥٠ توليدة
//      (فيلمٌ كامل 173 + إعادة 8 + مختبر الأصوات 104 + 47) ⇒ فيلمان في اليوم لا أكثر؛ احسب الباقي قبل أيّ توليدٍ كامل،
//      و«حدود 429 المضروبة» آخر السجلّ تكشف الحدّ الفعليّ لكلّ مفتاح.
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
state.strikes = state.strikes || {}; state.revived = state.revived || 0;
// أين تذهب النداءات: صوتٌ، أو ردٌّ بلا صوت (يُحسب على الحصّة)، أو رفضٌ بنوعه، أو خطأ خادمٍ أو شبكة
state.out = Object.assign({ ok: 0, noaudio: 0, noaudio_why: {}, day: 0, min: 0, other429: 0, http5xx: 0, http4xx: 0, net: 0 }, state.out || {});   // استراحات «حدّ اليوم» ومن عاد بعدها فولّد
// تشخيص الحصّة (الأرك 2026-10-04): أعلنت المفاتيح كلّها «حدّ اليوم» ثم ولّد الشوط التالي بعد دقيقتين 16 كتلة
// ⇒ تُعدّ معرّفات الحدود (quotaId) في أجسام 429 مع عيّنةٍ مقنّعة من رسالتها، لنعرف أيّ حدٍّ يُضرب فعلاً. لا مفاتيح في السجلّ.
state.q429 = state.q429 || {};
// ⭐ سعة الحصّة الحقيقية (مؤتة 2026-10-06: ردّت المفاتيح الـ43 كلّها بحدّ اليوم بعد نحو 60 توليدة، وكانت تكفي أفلاماً فوق الساعة):
//    الحدّ المعلن لكلّ مشروع (quotaValue في جسم 429)، ونتاجُ كلّ مفتاحٍ برقمه لا بقيمته — فيُعرف كم مشروعاً خلف المفاتيح فعلاً.
state.keys = state.keys || {};
function keyStat(key) { const i = keys.indexOf(key); return state.keys[i] || (state.keys[i] = { ok: 0, day: 0, min: 0 }); }
function note429(txt, key) {
  const ids = [...new Set((txt.match(/"quotaId"\s*:\s*"[^"]+"/g) || []).map(x => x.replace(/^.*"([^"]+)"$/, '$1')))];
  let det = [];
  try { det = JSON.parse(txt)?.error?.details || []; } catch (err) {}
  const viol = det.flatMap(d => d.violations || []);
  for (const q of (ids.length ? ids : ['بلا_معرّف'])) {
    const e = state.q429[q] || (state.q429[q] = { n: 0, sample: '' });
    e.n++;
    const v = viol.find(x => x.quotaId === q);
    if (v && v.quotaValue) e.limit = v.quotaValue;
    if (!e.sample) {
      let m = txt; try { m = JSON.parse(txt)?.error?.message || txt; } catch (err) {}
      e.sample = String(m).replace(/AIza[0-9A-Za-z_\-]{10,}|AQ\.[0-9A-Za-z_\-]{10,}/g, '***').replace(/\s+/g, ' ').slice(0, 220);
    }
  }
  const retry = det.find(d => /RetryInfo/.test(d['@type'] || ''))?.retryDelay;
  if (retry && /PerDay/i.test(txt)) state.dayRetry = retry;
  if (key) { const k = keyStat(key); if (/PerDay/i.test(txt)) k.day++; else k.min++; }
}
// ⭐ إحياء المفاتيح بعد تجديد الحصّة اليوميّ: منتصف الليل UTC (01:00 الجزائر) — مقيس 2026-10-06 بمهلة الرفع في جسم 429
//    (retryDelay ≈ 54064 ث عند 08:58:46Z ⇒ 23:59:50Z، للمفاتيح الـ43 كلّها). وكان 07:00 UTC في قياسٍ قديم.
{
  const now = new Date();
  const qd = now.toISOString().slice(0, 10);
  if (state.quotaDay !== qd) {
    const n = Object.keys(state.dead).length;
    state.dead = {}; state.strikes = {}; state.quotaDay = qd;
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
// ⭐⭐ لا إغراق (مؤتة 2026-10-06، والمالك: «المشكلة من جهتنا»): أرسل الشوط 90 في ثلاث دقائق 752 طلباً ليُخرج 16 صوتاً —
//    409 ردّاً بحدّ الدقيقة و282 «المورد مستنفد» و45 بحدّ اليوم — لأنّ المسار يعود بعد 3–7 ث إلى المفتاح التالي، والرفض يرجع فوراً.
//    ثم رُفضت المفاتيح كلّها بـ«حدّ اليوم» 07:37Z و08:58Z (والشوط 91 يطحن)، وولّد 34 منها 09:35Z: فالرفض عقوبة إغراقٍ تُرفع بعد دقائق، لا نفاد.
//    ⇒ ① إيقاعٌ لكلّ مفتاح: طلبٌ كلّ PACE_MS على الأكثر (دون حدّ الدقيقة المجّانيّ)، محفوظٌ في ملفٍّ مشترك بين الأشواط المتتالية في العدّاء؛
//      ② حدّ الدقيقة و«المورد مستنفد» يُريحان المفتاح دقيقةً أو مهلة جوجل أيّهما أطول، لا ثوانيَ؛
//      ③ «حدّ اليوم» يُريح COOL_MS ثم ضعفها، ولا يُسقط المفتاح نهائياً إلا بعد DAY_STRIKES ردودٍ متتالية.
const COOL_MS = +(process.env.GEN_COOL_MS || 20 * 60 * 1000);
const DAY_STRIKES = +(process.env.GEN_DAY_STRIKES || 3);
const PACE_MS = +(process.env.GEN_PACE_MS || 31000);
const MIN_COOL_MS = +(process.env.GEN_MIN_COOL_MS || 60000);
const PACE_FILE = process.env.GEN_PACE_FILE || path.join(os.tmpdir(), 'gen25_pace.json');
// ميزانية الشوط: إلى متى يُنتظر عودة المفاتيح المستريحة قبل «nokeys» (حدّ مهمّة الفيلم 350 د)
const RUN_END = Date.now() + (+(process.env.GEN_MAX_MIN || 150)) * 60 * 1000;
let pace = {};
try { pace = JSON.parse(fs.readFileSync(PACE_FILE, 'utf8')); } catch (e) { pace = {}; }
const kid = k => require('crypto').createHash('sha256').update(k).digest('hex').slice(0, 12);   // لا مفتاح في الملفّ
function savePace() { try { fs.writeFileSync(PACE_FILE, JSON.stringify(pace)); } catch (e) {} }
function readyAt(model, k) {
  const d = deadOf(model)[k];
  if (d === 'daily') return Infinity;
  return Math.max(typeof d === 'number' ? d : 0, (pace[kid(k)] || 0) + PACE_MS);
}
function soonest(model) {
  const now = Date.now();
  let m = Infinity;
  for (const k of keys) m = Math.min(m, readyAt(model, k) - now);
  return Math.max(0, m);
}
function nextKey(model) {
  const now = Date.now();
  for (let n = 0; n < keys.length; n++) {
    const k = keys[(ki + n) % keys.length];
    if (readyAt(model, k) <= now) { ki = (ki + n + 1) % keys.length; pace[kid(k)] = now; savePace(); return k; }
  }
  return null;
}
function retrySec(txt) {
  try {
    const det = JSON.parse(txt)?.error?.details || [];
    const m = /^(\d+(?:\.\d+)?)s$/.exec(det.find(d => /RetryInfo/.test(d['@type'] || ''))?.retryDelay || '');
    return m ? +m[1] : 0;
  } catch (e) { return 0; }
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
  // المهلة تحدّ محاولات الكتلة لا انتظارَ عودة المفاتيح: كانت 15 د أقصر من استراحة «حدّ اليوم» (20 د) فاستسلمت الأداة
  // والمفاتيح على وشك العودة (الشوط 92، مؤتة 2026-10-06). الانتظار يمدّها، وحدُّه ميزانية الشوط كلّه RUN_END.
  let deadline = Date.now() + (+(process.env.GEN_BLOCK_MS || 15 * 60 * 1000));
  while (Date.now() < deadline) {
    const key = nextKey(model);
    if (!key) {
      const w = soonest(model);
      if (!isFinite(w) || Date.now() + w > RUN_END) return 'nokeys';
      await new Promise(z => setTimeout(z, w + 200 + Math.random() * 800));
      deadline = Math.max(deadline, Date.now() + (+(process.env.GEN_BLOCK_MS || 15 * 60 * 1000)));
      continue;
    }
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
    const body = {
      // توجيه الأداء (style) يسبق النصّ بصيغة «Say …: نص» الموثّقة؛ والفاحص السمعي يمسك أيّ نطقٍ له
      // director: صيغة «ملاحظات المخرج ثم TRANSCRIPT» — يُقرأ ما بعد العنوان وحده (systemInstruction مرفوضٌ في 3.8: «Developer instruction is not enabled»)
      contents: [{ parts: [{ text: blk.director ? blk.director + '\n\n#### TRANSCRIPT\n' + blk.text : (blk.style ? blk.style + ': ' : '') + blk.text }] }],
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
        note429(txt, key);
        // ⭐ اقرأ جسم الخطأ: ميّز حدّ اليوم من حدّ الدقيقة
        if (/PerDay/i.test(txt)) {
          state.out.day++;
          // ردٌّ واحدٌ يصل من مسارين حملا المفتاح نفسه معاً: لا يُعدّ ضربتين (وإلا مات المفتاح قبل استراحتيه)
          const dk = deadOf(model)[key];
          if (dk !== 'daily' && !(typeof dk === 'number' && dk > Date.now())) {
            const sk = model + '#' + keys.indexOf(key);
            const s = (state.strikes[sk] = (state.strikes[sk] || 0) + 1);
            deadOf(model)[key] = s >= DAY_STRIKES ? 'daily' : Date.now() + COOL_MS * s;
          }
          save(); continue;
        }
        // حدّ الدقيقة أو «المورد مستنفد» بلا معرّف: المفتاح يستريح دقيقةً أو مهلة جوجل، والمسار يأخذ مفتاحاً جاهزاً بإيقاعه
        if (/PerMinute/i.test(txt)) state.out.min++; else state.out.other429++;
        const dk = deadOf(model)[key];
        if (dk !== 'daily') deadOf(model)[key] = Math.max(typeof dk === 'number' ? dk : 0, Date.now() + Math.max(MIN_COOL_MS, retrySec(txt) * 1000));
        save(); continue;
      }
      if (r.status === 404 || r.status === 400) {
        // النموذج غير متاحٍ لهذا المفتاح أصلاً — لا تطحن عليه
        const txt = await r.text();
        console.log(`  ⚠ ${model}: ${r.status} — ${txt.slice(0, 160).replace(/\s+/g, ' ')}`);
        return 'nomodel';
      }
      if (!r.ok) { state.out[r.status >= 500 ? 'http5xx' : 'http4xx']++; await new Promise(z => setTimeout(z, 2000 + Math.random() * 3000)); continue; }
      const j = await r.json();
      const p = j?.candidates?.[0]?.content?.parts?.find(x => x.inlineData);
      if (!p) {
        // ⛔ ردٌّ ناجح بلا صوت يُحسب على الحصّة ولا يُخرج شيئاً: يُعدّ ويُسمّى سببه
        state.out.noaudio++;
        const fr = j?.candidates?.[0]?.finishReason || (j?.promptFeedback?.blockReason ? 'حجب:' + j.promptFeedback.blockReason : 'بلا_سبب');
        state.out.noaudio_why[fr] = (state.out.noaudio_why[fr] || 0) + 1;
        save(); await new Promise(z => setTimeout(z, 1500)); continue;
      }
      const pcm = Buffer.from(p.inlineData.data, 'base64');
      // ⛔⛔ gemini-3.8 يُرجع WAV كاملاً بترويسته؛ فإضافةُ ترويسةٍ فوقه تُسمَع طقطقةً في أوّل كل كتلة
      //    (وقع في «اليرموك» 2026-09-27: 175 كتلة). ⇒ إن كان المُرجَع RIFF يُحفظ كما هو.
      const isWav = pcm.length > 12 && pcm.toString('ascii', 0, 4) === 'RIFF';
      fs.writeFileSync(outFile, isWav ? pcm : Buffer.concat([wavHeader(pcm.length), pcm]));
      state.out.ok++;
      state.done[blk.id] = true; state.model_of[blk.id] = model; keyStat(key).ok++;
      { const sk = model + '#' + keys.indexOf(key); if (state.strikes[sk]) { state.revived++; delete state.strikes[sk]; } }
      save();
      return 'ok';
    } catch (e) { state.out.net++; await new Promise(z => setTimeout(z, 2000 + Math.random() * 3000)); }
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
  // ⛔ درس القادسية 2026-09-27: audio_checks يحذف الملفّ المعيب ليُعاد، والدفترُ يقول «تمّ»
  //    فكانت الجولتان الثانية والثالثة لا تولّدان شيئاً (متبقٍّ: 0). ⇒ «تمّ» بلا ملفٍّ ليس تمّاً.
  for (const b of blocks) {
    if (state.done[b.id] && !fs.existsSync(path.join(OUT, b.id + '.wav'))) delete state.done[b.id];
  }
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
  if (Object.keys(state.q429).length) console.log(`حدود 429 المضروبة: ${JSON.stringify(state.q429)}`);
  { const o = state.out;
    console.log(`نتائج النداءات: صوت ${o.ok} · بلا صوت ${o.noaudio}${o.noaudio ? ' ' + JSON.stringify(o.noaudio_why) : ''} · حدّ اليوم ${o.day} · حدّ الدقيقة ${o.min} · مستنفدٌ بلا معرّف ${o.other429} · خادم ${o.http5xx} · طلبٌ مرفوض ${o.http4xx} · شبكة ${o.net} · الإيقاع ${PACE_MS / 1000} ث لكلّ مفتاح`); }
  {
    const ks = Object.entries(state.keys);
    const prod = ks.filter(([, v]) => v.ok > 0).sort((a, b) => b[1].ok - a[1].ok);
    const dry = ks.filter(([, v]) => !v.ok && v.day).length;
    if (ks.length) console.log(`نتاج المفاتيح: أنتج ${prod.length} من ${keys.length} (${prod.map(([i, v]) => '#' + i + '×' + v.ok).join(' ')}) · ردّ ${dry} بحدّ اليوم بلا إنتاجٍ في هذا الشوط${state.dayRetry ? ' · مهلة حدّ اليوم ' + state.dayRetry : ''} · عاد بعد الاستراحة فولّد ${state.revived} مرّة`);
  }
  if (fail) {
    console.log(`⛔ الكتل المتعذّرة: ${failed.join(' · ')}`);
    process.exit(2);            // ⛔ الفشل يُعلَن ولا يُبتلع
  }
})();
