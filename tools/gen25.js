// مولّد الصوت — gemini-2.5-flash-preview-tts
// الاستعمال: node gen31.js <projectDir> [workers]
const fs = require('fs'), path = require('path'), os = require('os');

const PROJ = process.argv[2];
const WORKERS = parseInt(process.argv[3] || '8', 10);
if (!PROJ) { console.error('usage: node gen31.js <projectDir> [workers]'); process.exit(1); }

const KEYFILES = [
  path.join(os.homedir(), '.claude', 'skills', 'video-factory', 'keys.txt'),
  path.join(os.homedir(), 'Desktop', 'claude-media', 'muw', 'مفاتيح-جديدة.txt'),
  path.join(os.homedir(), 'Downloads', 'مفاتيح-جيميناي-نسخة-احتياطية.txt'),
];
function loadKeys() {
  const s = new Set();
  for (const f of KEYFILES) {
    try { fs.readFileSync(f, 'utf8').split(/\r?\n/).forEach(l => { l = l.trim(); if ((l.startsWith('AIza') || l.startsWith('AQ.'))) s.add(l); }); } catch (e) {}
  }
  return [...s];
}

const MODEL = 'gemini-2.5-flash-preview-tts';
const OUT = path.join(PROJ, 'audio');
fs.mkdirSync(OUT, { recursive: true });
const STATE = path.join(PROJ, 'gen_state.json');
let state = {};
try { state = JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch (e) { state = { done: {}, calls: 0, dead: {} }; }
state.done = state.done || {}; state.dead = state.dead || {}; state.calls = state.calls || 0;
// ⭐ إحياء المفاتيح بعد تجديد الحصّة اليوميّ (07:00 UTC / 08:00 الجزائر).
// بلا هذا تبقى المفاتيح «ميتة» إلى الأبد فيتعذّر التوليد ولو تجدّدت الحصّة.
{
  const now = new Date();
  const qd = new Date(now.getTime() - 7 * 3600 * 1000).toISOString().slice(0, 10); // يوم الحصّة
  if (state.quotaDay !== qd) {
    const n = Object.keys(state.dead).length;
    state.dead = {}; state.quotaDay = qd;
    if (n) console.log(`♻️ يومُ حصّةٍ جديد (${qd}) — أُحييت ${n} مفتاحًا`);
  }
}
function save() { fs.writeFileSync(STATE, JSON.stringify(state, null, 1)); }

// blocks.json: [{id, voice, text}]
const blocks = JSON.parse(fs.readFileSync(path.join(PROJ, 'blocks.json'), 'utf8'));

let keys = loadKeys();
let ki = 0;
function nextKey() {
  for (let n = 0; n < keys.length; n++) {
    const k = keys[(ki + n) % keys.length];
    if (!state.dead[k]) { ki = (ki + n + 1) % keys.length; return k; }
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

async function genOne(blk) {
  const outFile = path.join(OUT, blk.id + '.wav');
  if (state.done[blk.id] && fs.existsSync(outFile) && fs.statSync(outFile).size > 8000) return 'skip';
  const deadline = Date.now() + 4 * 60 * 1000; // مهلة زمنية لا عدّ محاولات
  while (Date.now() < deadline) {
    const key = nextKey();
    if (!key) return 'nokeys';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
    const body = {
      contents: [{ parts: [{ text: blk.text }] }],
      generationConfig: {
        responseModalities: ['AUDIO'],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: blk.voice || 'Charon' } } },
      },
    };
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 90000);
      const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal });
      clearTimeout(t);
      state.calls++;
      if (r.status === 429) {
        const txt = await r.text();
        // ⭐ اقرأ جسم الخطأ: ميّز حدّ اليوم من حدّ الدقيقة
        if (/PerDay/i.test(txt)) { state.dead[key] = 'daily'; save(); continue; }
        await new Promise(z => setTimeout(z, 3000)); continue;
      }
      if (!r.ok) { await new Promise(z => setTimeout(z, 2000)); continue; }
      const j = await r.json();
      const p = j?.candidates?.[0]?.content?.parts?.find(x => x.inlineData);
      if (!p) { await new Promise(z => setTimeout(z, 1500)); continue; }
      const pcm = Buffer.from(p.inlineData.data, 'base64');
      fs.writeFileSync(outFile, Buffer.concat([wavHeader(pcm.length), pcm]));
      state.done[blk.id] = true; save();
      return 'ok';
    } catch (e) { await new Promise(z => setTimeout(z, 2000)); }
  }
  return 'timeout';
}

(async () => {
  const todo = blocks.filter(b => !state.done[b.id]);
  console.log(`مفاتيح: ${keys.length} | كتل: ${blocks.length} | متبقٍّ: ${todo.length} | مسارات: ${WORKERS}`);
  let i = 0, ok = 0, fail = 0;
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    while (i < todo.length) {
      const blk = todo[i++];
      const r = await genOne(blk);
      if (r === 'ok' || r === 'skip') ok++; else { fail++; console.log(`✗ ${blk.id}: ${r}`); }
      if ((ok + fail) % 10 === 0) console.log(`… ${ok + fail}/${todo.length} | نجح ${ok} | فشل ${fail} | نداءات ${state.calls}`);
      if (r === 'nokeys') break;
    }
  }));
  save();
  console.log(`انتهى: نجح ${ok} | فشل ${fail} | إجمالي النداءات ${state.calls}`);
})();
