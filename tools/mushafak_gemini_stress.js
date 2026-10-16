// ضغطُ مفاتيح Gemini لمساعد «مصحفك» (2026-10-16 — أمر المالك: «تُجهَد بالأسئلة لنفهم كيف تعمل»).
// الغاية: هل تصلح نماذج Gemini النصّيّة خلفاً لـClaude في «اسأل» إن بلغ المستخدمون 5000 يومياً؟
//   ١) السرد: ListModels ⇒ النماذج النصّيّة التي تدعم generateContent بعد استثناء tts والصورة والصوت وembedding وlive وveo/imagen.
//   ٢) الصلاحية والجودة: طلبٌ يحاكي «اسأل» (تعليماتٌ عربيّة ~7000 حرف + أدوات) — استدعاء أداة، JSON منظَّم، لغة السائل، الهويّة.
//   ٣) السعة: لكلّ (نموذج، مفتاح) حلقةٌ متمهّلة حتى «الجدار» (حدّ اليوم أو استنفادٌ بلا معرّف ٣ مرّاتٍ متتالية).
//   ٤) العودة بعد الجدار: طرقةٌ واحدة كلّ 20 دقيقة، فإن نجحت استؤنف الاستنزاف.
//   ٥) المخرَج: JSON دوريّ و«ملخّصٌ عربيّ».
// ⛔ نموذج الأفلام gemini-3.8-flash-tts لا يُنادى بحال (حارسٌ في طبقة الطلب نفسها يرفض أيّ نموذجٍ فيه tts).
// ⛔ لا يُطبع مفتاحٌ ولا جزءٌ منه: المفتاح في الرأس x-goog-api-key، والمفاتيح بأرقامها، والمشروع بوسمٍ مموَّه.
//   node tools/mushafak_gemini_stress.js --keys /path/keys.json --out out.json --md out.md [--minutes 330] [--cap 3000] [--gap 4]
//   اختبارٌ محلّيّ: MUSHAFAK_GEMINI_BASE=http://127.0.0.1:PORT/v1beta
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 && i + 1 < process.argv.length ? process.argv[i + 1] : d; };
const flag = k => process.argv.includes(k);
const BASE = (process.env.MUSHAFAK_GEMINI_BASE || arg('--base', 'https://generativelanguage.googleapis.com/v1beta')).replace(/\/$/, '');
const MINUTES = +arg('--minutes', 330);
const CAP = +arg('--cap', 3000);
const GAP = +arg('--gap', 4) * 1000;                       // أدنى فاصلٍ بين طلبات (المفتاح، النموذج)
const RETURN_EVERY = +arg('--return-every-sec', 1200) * 1000;
const FLUSH_EVERY = +arg('--flush-sec', 600) * 1000;
const WALL_PAUSE = +arg('--wall-pause-sec', 15) * 1000;   // استراحةٌ بين رفضَين متتاليَين من النوع نفسه
const MINUTE_WAIT = +arg('--minute-wait-sec', 60) * 1000;  // مهلة حدّ الدقيقة إن لم يُعلن retryDelay
const MAX_INFLIGHT = +arg('--inflight', 60);
const OUT = arg('--out', 'ops/research/mushafak_gemini_stress_2026-10-16.json');
const MD = arg('--md', 'ops/research/mushafak_gemini_stress_2026-10-16.md');
const ONLY = arg('--models', '');
const SKIP_RE = arg('--skip', '');
// المفاتيح المشاركةُ غيرَها مشروعاً (كما في tools/models_probe.js): تُترك في الاستنزاف ما لم يُطلب إدخالها
const SHARED_EXTRA = new Set([4, 15, 30, 37, 10, 25, 27, 32, 20, 33, 34, 42]);
const INCLUDE_SHARED = flag('--include-shared');
// النماذج المستثناة بالاسم (تُطبَّق على السرد وعلى --models معاً)
const EXCLUDE_RE = /tts|image|imagen|veo|audio|embed|live|dialog|aqa|vision|robotics|deep-research|computer-use|banana|lyria|speech|transcri/i;

const START = Date.now();
const DEADLINE = START + MINUTES * 60000;
const sleep = ms => new Promise(z => setTimeout(z, Math.max(0, ms)));
const sleepUntilDeadline = ms => sleep(Math.min(ms, DEADLINE - Date.now()));
const iso = t => new Date(t).toISOString();
const log = s => console.log(`[${iso(Date.now()).slice(11, 19)}] ${mask(s)}`);

function loadKeys(file) {
  const t = fs.readFileSync(file, 'utf8');
  return [...new Set(t.match(/AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}/g) || [])];
}
// قناع المفاتيح — يُمرَّر عليه كلُّ نصٍّ يُطبع أو يُخزَّن (الأنماط الحقيقية + أيّ مفتاحٍ محمَّل بنصّه)
let LOADED = [];
function mask(s) {
  let t = String(s).replace(/AIza[0-9A-Za-z_\-]{10,}|AQ\.[0-9A-Za-z_\-]{10,}/g, '***');
  for (const k of LOADED) if (k && k.length > 8) t = t.split(k).join('***');
  return t;
}
const tag = s => 'م' + crypto.createHash('sha256').update(String(s)).digest('hex').slice(0, 4);

// ───────── تعليمات النظام العربيّة (~7000 حرف): مساعدٌ عامّ لتطبيق مصحف، مؤلَّفة هنا ولم تُنسخ من أيّ مستودع ─────────
const RULES = [
  'أنت «مساعد تطبيق مصحفك»: مساعدٌ يجيب عن أسئلة القرّاء حول القرآن الكريم وعلومه داخل تطبيق مصحف.',
  'خاطب السائل بلغته: إن سأل بالعربية فأجب بالعربية الفصيحة الميسّرة، وإن سأل بالإنجليزية أو الفرنسية أو غيرهما فأجب بلغته.',
  'ابدأ الجواب بالخلاصة في جملةٍ أو جملتين، ثم فصّل عند الحاجة بنقاطٍ قصيرة مرتّبة، ولا تُطل بما لا يضيف فائدة.',
  'اذكر مصدر كلّ معلومةٍ تنقلها: اسم الكتاب أو التفسير أو المؤلّف، ورقم السورة والآية حيث ينطبق، ولا تُجمل المصدر بعبارةٍ مبهمة.',
  'الأمانة في النقل أصل: لا تنسب إلى مفسّرٍ أو عالمٍ قولاً لم تتحقّق منه، وإن لم تعرف فقل إنك لا تعرف ولا تخمّن.',
  'لا تولّد نصّاً قرآنياً من عندك أبداً. نصّ الآية يُجلب بالأداة get_ayah من المصحف المحفوظ في التطبيق ويُنقل كما هو بلا تغيير حرفٍ ولا ضبط.',
  'إن طُلب منك كتابة آيةٍ من الذاكرة فاستدعِ الأداة بدل الكتابة، وإن تعذّرت الأداة فاذكر رقم السورة والآية فقط واطلب من السائل فتحها في المصحف.',
  'لا تُفتِ بحلالٍ أو حرامٍ في المسائل الخلافية بل اعرض أقوال أهل العلم بإيجاز، وانسب كلّ قولٍ إلى قائله، وأحِل السائل إلى عالمٍ ثقةٍ في بلده للفتوى الخاصّة.',
  'لا تُكفّر أحداً ولا تذمّ مذهباً ولا طائفةً ولا شخصاً، وأجب بأدبٍ مع المخالف، وبلا تنقّصٍ من أحدٍ من الصحابة أو العلماء.',
  'إن سُئلت عن التفسير فاستدعِ الأداة get_tafsir باسم التفسير ورقم السورة والآية، ولخّص ما يرد منها بأسلوبك دون أن تنسب إليه ما ليس فيه.',
  'إن سُئلت عن كلمةٍ قرآنية فاستعمل search_word لتجد مواضعها، وأعطِ معناها اللغوي وسياقها، وتجنّب الاشتقاقات الخيالية.',
  'احترم القراءات والروايات: إن اختلف اللفظ بين رواية حفص وورش وقالون فبيّن ذلك بلا ترجيحٍ يوهم تخطئة إحداها.',
  'تذكّر أنّ السائل قد يكون طفلاً أو كبير سنّ أو حديث عهدٍ بالإسلام، فاختر عباراتٍ بسيطةً واضحة وتجنّب المصطلحات الثقيلة دون شرحها.',
  'لا تطلب بياناتٍ شخصيةً من السائل، ولا تذكر أنك تحتفظ بأيّ بياناتٍ عنه، ولا تُجرِ محادثاتٍ لا صلة لها بالقرآن وعلومه والتطبيق.',
  'إن خرج السؤال عن نطاق القرآن وعلومه وتطبيق مصحف فاعتذر بلطفٍ في جملةٍ واحدة وارجع بالسائل إلى ما تحسن المساعدة فيه.',
  'إن سألك السائل عن ميزةٍ في التطبيق فاشرحها بحسب ما تعرفه، وإن لم تكن متأكداً فقل ذلك ولا تخترع واجهةً أو زرّاً.',
  'في الأسئلة التاريخية والسيَر اعتمد الروايات المشهورة في كتب أهل العلم وقل «ذكر أهل السير» حين يكون الخبر غير متّفقٍ عليه.',
  'الأرقام والتواريخ: اذكرها بالتقريب إن لم تكن متيقّناً، وميّز بين الهجري والميلادي حين يلزم.',
  'لا تقدّم نفسك بصفة عالمٍ أو مفتٍ، فأنت أداةٌ مساعدة تلخّص وتُحيل، والمرجع كتب أهل العلم المعتبرة.',
  'حين يطلب السائل تلخيصاً لتفسيرٍ طويل فلخّص المعنى العامّ في أسطرٍ قليلة، ثم أحِله إلى نصّ التفسير الكامل داخل التطبيق.',
  'إن تعارض ما تحمله الأداة مع ما في ذاكرتك فقدّم ما جاءت به الأداة، وانبّه السائل إذا لاحظت إشكالاً.',
  'اجعل نبرتك هادئةً ودافئة، بلا مبالغةٍ في المدح ولا إكثارٍ من الاعتذار، ولا تستعمل رموزاً تعبيريةً إلا نادراً.',
  'ضع في آخر الجواب سطراً قصيراً بعنوان «المصادر» يسرد ما اعتمدت عليه، وكلّ مصدرٍ في بند.',
  'عند الجواب المنظَّم بصيغة JSON التزم المخطّط حرفياً: الحقل answer نصّ الجواب، والحقل sources مصفوفة المصادر، والحقل lang رمز لغة الجواب بحرفين.',
  'لا تضف حقولاً غير مطلوبة ولا تُحِط الـJSON بشرحٍ خارجه ولا بأسوار شيفرة.',
  'إن كان الاستدعاء يحتاج أكثر من أداة فاستدعِها بالترتيب الذي يخدم السؤال، ولا تكرّر استدعاءً أجبتَ عنه من قبل.',
  'تحقّق من وسائط الأداة: السورة من 1 إلى 114، والآية ضمن عدد آيات السورة، واسم التفسير من القائمة المتاحة في التطبيق.',
  'إن أعادت الأداة خطأً أو فراغاً فقل ذلك بوضوح ولا تملأ الفراغ من عندك.',
  'يحرص التطبيق على خصوصية المستخدم: لا تسأل عن موقعه ولا اسمه ولا جهازه، ولا تعد بأمرٍ يتجاوز الجواب.',
  'إن سألك أحدهم عن دينٍ آخر فأجب بإنصافٍ وإيجاز عمّا يقوله القرآن فيه، بلا سخريةٍ ولا استعلاء.',
  'وإن سألك عن تعارضٍ مزعومٍ بين آيتين فاعرض سياق كلٍّ منهما وأقوال المفسّرين في الجمع بينهما، ولا تجزم بما لا دليل عليه.',
  'وفي أسئلة الأحكام الفقهية الخاصّة بحالةٍ بعينها اشرح القاعدة العامة وانصح بسؤال أهل الاختصاص.',
  'وفي أسئلة التجويد اشرح الحكم بمثالٍ من القرآن تجلبه بالأداة، ولا تكتب الأمثلة من حفظك.',
  'وفي أسئلة أسباب النزول لا تذكر سبباً إلا إن عرفت مصدره، وقل «لم أقف على سبب نزولٍ صحيح» إذا لم تجد.',
  'وفي أسئلة الإعجاز العلمي والعددي كن حذراً: اعرض ما قاله الباحثون بنسبته إليهم، ونبّه إلى أنه اجتهادٌ لا تفسير.',
  'وفي الأسئلة العقدية التزم ما عليه جمهور أهل السنة وبيّن أنّ التفصيل في كتب العقيدة.',
  'وإن طلب السائل ترجمةً لآية فاستعمل ترجمةً معتمدةً من التطبيق، ونبّه إلى أنّ الترجمة تقريبٌ للمعنى لا بديلٌ عن النص.',
  'أخيراً: الصدق أهمّ من الإجابة السريعة، والسكوت عمّا لا تعلم خيرٌ من جوابٍ يوهم السائل بما ليس عليه الأمر.',
];
function buildSystem() {
  let s = RULES.map((r, i) => `${i + 1}. ${r}`).join('\n');
  const extra = 'تذكير: التزم هذه التعليمات في كلّ جواب، وقدّم الأمانة على الإسهاب، وخاطب السائل بلغته، ولا تنقل نصّاً قرآنياً إلا من الأداة.';
  while (s.length < 6900) s += '\n' + extra;
  return s;
}
const SYSTEM = buildSystem();

const TOOLS = [{ functionDeclarations: [
  { name: 'get_ayah', description: 'يجلب نصّ آيةٍ من المصحف المحفوظ في التطبيق بالسورة والآية.',
    parametersJsonSchema: { type: 'object', properties: { s: { type: 'integer', description: 'رقم السورة 1-114' }, a: { type: 'integer', description: 'رقم الآية' } }, required: ['s', 'a'] } },
  { name: 'get_tafsir', description: 'يجلب تفسير آيةٍ من كتاب تفسيرٍ محدّد.',
    parametersJsonSchema: { type: 'object', properties: { tafsir: { type: 'string', description: 'معرّف التفسير مثل ibn_kathir أو tabari أو saadi' }, surah: { type: 'integer' }, ayah: { type: 'integer' } }, required: ['tafsir', 'surah', 'ayah'] } },
  { name: 'search_word', description: 'يبحث عن كلمةٍ قرآنيةٍ ويعيد مواضعها.',
    parametersJsonSchema: { type: 'object', properties: { word: { type: 'string' } }, required: ['word'] } },
] }];

const QUESTIONS = [
  'ما معنى كلمة «الصمد» في سورة الإخلاص؟', 'لماذا سُمّيت سورة البقرة بهذا الاسم؟', 'ما سبب نزول سورة المسد؟',
  'ما الفرق بين الإدغام والإخفاء في التجويد؟', 'كم عدد آيات سورة الكهف وما فضلها؟', 'ما معنى «الحمد لله ربّ العالمين»؟',
  'اشرح لي قصّة أصحاب الكهف باختصار.', 'ما هي أركان الإيمان كما في القرآن؟', 'ما حكم المدّ المنفصل وكم حركاته؟',
  'ما معنى «لا إكراه في الدين»؟', 'من هم أولو العزم من الرسل؟', 'ما الفرق بين المكّي والمدني؟',
  'كيف أحفظ سورة الملك بسهولة؟', 'ما معنى الاستعاذة وما حكمها قبل القراءة؟', 'ما المقصود بالسبع المثاني؟',
  'ما أطول آيةٍ في القرآن وفي أيّ سورة؟', 'لماذا تبدأ بعض السور بحروف مقطّعة؟', 'ما معنى «الفلق» في سورة الفلق؟',
  'ما قصة نبي الله يونس عليه السلام في القرآن؟', 'ما الفرق بين رواية حفص ورواية ورش؟', 'ما حكم قراءة القرآن بلا وضوء؟',
  'ما معنى التقوى في القرآن؟', 'اذكر ثلاث آياتٍ عن الصبر مع ذكر مواضعها.', 'ما المقصود بآية الكرسي ولماذا هي عظيمة؟',
  'ما معنى «سبحان الذي أسرى بعبده»؟', 'ما هو أول ما نزل من القرآن؟', 'كيف جُمع القرآن في عهد أبي بكر رضي الله عنه؟',
  'ما معنى كلمة «تبّت» في سورة المسد؟', 'ما هي سجدات التلاوة وكم عددها؟', 'ما الحكمة من تكرار قصة موسى في القرآن؟',
];

// ───────── طبقة الطلب (المفتاح في الرأس، والحارس ضدّ tts) ─────────
let inflight = 0; const waiters = [];
async function gate() { if (inflight < MAX_INFLIGHT) { inflight++; return; } await new Promise(z => waiters.push(z)); inflight++; }
function release() { inflight--; const w = waiters.shift(); if (w) w(); }

async function call(key, model, payload, method = 'generateContent') {
  if (/tts/i.test(model)) throw new Error('محظور: نموذج tts لا يُنادى');
  await gate();
  const t0 = Date.now();
  try {
    const r = await fetch(`${BASE}/models/${model}:${method}`, {
      method: 'POST', headers: { 'content-type': 'application/json', 'x-goog-api-key': key }, body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120000) });
    const txt = await r.text();
    const ms = Date.now() - t0;
    if (r.ok) { let j = null; try { j = JSON.parse(txt); } catch (e) {} return { ok: true, status: r.status, ms, json: j }; }
    return { ok: false, status: r.status, ms, txt: mask(txt), ...parseErr(txt) };
  } catch (e) {
    return { ok: false, status: 'net', ms: Date.now() - t0, txt: mask(e.message || e), kind: 'شبكة' };
  } finally { release(); }
}
function parseErr(txt) {
  let det = [], msg = '';
  try { const e = JSON.parse(txt)?.error || {}; det = e.details || []; msg = e.message || ''; } catch (e) {}
  const v = det.flatMap(d => d.violations || [])[0] || {};
  const retry = det.find(d => /RetryInfo/.test(d['@type'] || ''))?.retryDelay || '';
  const md = det.find(d => /ErrorInfo/.test(d['@type'] || ''))?.metadata || {};
  const consumer = md.consumer || md.consumer_project || md.project || '';
  const m = /^(\d+(?:\.\d+)?)s$/.exec(retry);
  return { quotaId: v.quotaId || '', quotaValue: v.quotaValue || '', retry, retrySec: m ? +m[1] : null, consumer, msg: mask(msg).slice(0, 200) };
}
function kind429(e) {
  const id = e.quotaId || '';
  if (/PerDay/i.test(id) || /PerDay/i.test(e.txt || '')) return 'حدّ اليوم';
  if (/PerMinute/i.test(id) || /PerMinute/i.test(e.txt || '')) return 'حدّ الدقيقة';
  return 'مستنفد بلا معرّف';
}
function usage(j) {
  const u = j?.usageMetadata || {};
  return { in: u.promptTokenCount || 0, out: u.candidatesTokenCount || 0, think: u.thoughtsTokenCount || 0, total: u.totalTokenCount || 0 };
}
const partsOf = j => j?.candidates?.[0]?.content?.parts || [];
const textOf = j => partsOf(j).filter(p => p.text && !p.thought).map(p => p.text).join('');
const fcOf = j => partsOf(j).find(p => p.functionCall)?.functionCall;

function capacityBody(n) {
  const q = QUESTIONS[n % QUESTIONS.length];
  const b = { systemInstruction: { parts: [{ text: SYSTEM }] }, contents: [{ role: 'user', parts: [{ text: q }] }], generationConfig: { maxOutputTokens: 600 } };
  if (n % 2 === 1) b.tools = TOOLS;
  return b;
}

// ───────── السرد ─────────
async function listModels(keys) {
  for (const i of keys.slice(0, 3)) {
    try {
      const out = []; let tokenP = '';
      for (let page = 0; page < 5; page++) {
        const r = await fetch(`${BASE}/models?pageSize=1000${tokenP ? '&pageToken=' + encodeURIComponent(tokenP) : ''}`, { headers: { 'x-goog-api-key': i.key }, signal: AbortSignal.timeout(60000) });
        if (!r.ok) throw new Error('ListModels ' + r.status);
        const j = await r.json(); out.push(...(j.models || [])); tokenP = j.nextPageToken || ''; if (!tokenP) break;
      }
      return out;
    } catch (e) { log(`تعذّر السرد بالمفتاح #${i.idx}: ${e.message}`); }
  }
  return [];
}

// ───────── الجودة (٢) ─────────
function langOf(t) {
  const s = ' ' + t.toLowerCase() + ' ';
  const ar = (t.match(/[؀-ۿ]/g) || []).length, lat = (t.match(/[a-z]/gi) || []).length;
  if (ar > lat) return 'ar';
  const fr = (s.match(/ (le|la|les|des|est|une|un|et|que|qui|pour|dans|du|au|sur|avec|ce|cette|sont|vous) /g) || []).length + (t.match(/[éèêàçùôî]/g) || []).length;
  const en = (s.match(/ (the|is|and|of|to|in|that|this|it|for|are|you|with|which|as) /g) || []).length;
  return fr > en ? 'fr' : 'en';
}
async function qualityFor(model, key, keyIdx) {
  const res = { key: '#' + keyIdx, tests: {} };
  const rec = (name, r, extra) => {
    const u = r.ok ? usage(r.json) : {};
    res.tests[name] = { ok: !!r.ok, status: r.status, ms: r.ms, usage: u, finish: r.ok ? (r.json?.candidates?.[0]?.finishReason || '') : '',
      err: r.ok ? '' : `${r.status} ${r.quotaId || ''} ${(r.msg || r.txt || '').slice(0, 160)}`.trim(), ...extra };
  };
  const cfg = { maxOutputTokens: 2048 };
  // (أ) استدعاء أداة ثم الجواب النهائيّ بـJSON منظَّم
  const q1 = 'ما تفسير الآية 255 من البقرة عند ابن كثير؟';
  const contents = [{ role: 'user', parts: [{ text: q1 }] }];
  let r = await call(key, model, { systemInstruction: { parts: [{ text: SYSTEM }] }, contents, tools: TOOLS, generationConfig: cfg });
  const fc = r.ok ? fcOf(r.json) : null;
  let argsOk = false;
  if (fc) { const a = fc.args || {}; argsOk = fc.name === 'get_tafsir' && +a.surah === 2 && +a.ayah === 255 && /kath|كثير/i.test(String(a.tafsir || '')); }
  rec('أ1_استدعاء_أداة', r, { functionCall: fc ? { name: fc.name, args: fc.args } : null, correct: argsOk, text: r.ok && !fc ? mask(textOf(r.json)).slice(0, 200) : '' });
  await sleep(GAP);
  if (fc) {
    const modelContent = r.json.candidates[0].content;     // يُعاد كما هو (مع أيّ thoughtSignature)
    const frPart = { role: 'user', parts: [{ functionResponse: { name: fc.name, response: { result: { tafsir: 'ibn_kathir', text: 'يخبر تعالى أنّه الحيّ القيّوم الذي لا تأخذه سنةٌ ولا نوم، وله ما في السماوات وما في الأرض، وآية الكرسي أعظم آية في كتاب الله.' } } } }] };
    const schema = { type: 'object', properties: { answer: { type: 'string' }, sources: { type: 'array', items: { type: 'string' } }, lang: { type: 'string' } }, required: ['answer', 'sources', 'lang'] };
    const jsonCfg = { ...cfg, responseMimeType: 'application/json', responseJsonSchema: schema };
    let path = 'بلا أدوات';
    let r2 = await call(key, model, { systemInstruction: { parts: [{ text: SYSTEM }] }, contents: [...contents, modelContent, frPart], generationConfig: jsonCfg });
    if (!r2.ok && r2.status === 400) {   // بعض النماذج تطلب الأدوات مع سجلّ الاستدعاء: يُحوَّل التبادل نصّاً
      path = 'التبادل نصّاً';
      const asText = [{ role: 'user', parts: [{ text: q1 + '\n\nنتيجة الأداة get_tafsir: ' + JSON.stringify(frPart.parts[0].functionResponse.response.result) }] }];
      r2 = await call(key, model, { systemInstruction: { parts: [{ text: SYSTEM }] }, contents: asText, generationConfig: jsonCfg });
    }
    let valid = false, parsed = null;
    if (r2.ok) { try { parsed = JSON.parse(textOf(r2.json)); valid = typeof parsed.answer === 'string' && Array.isArray(parsed.sources) && typeof parsed.lang === 'string'; } catch (e) {} }
    rec('أ2_جواب_JSON', r2, { path, valid, text: r2.ok ? mask(textOf(r2.json)).slice(0, 300) : '' });
    await sleep(GAP);
  }
  // (ب) لغة السائل
  for (const [name, q, want] of [['ب1_إنجليزية', 'What is the meaning of Surah Al-Ikhlas? Please answer briefly.', 'en'], ['ب2_فرنسية', 'Pourquoi la sourate Al-Baqara porte-t-elle ce nom ? Réponds brièvement.', 'fr']]) {
    const rr = await call(key, model, { systemInstruction: { parts: [{ text: SYSTEM }] }, contents: [{ role: 'user', parts: [{ text: q }] }], generationConfig: cfg });
    const t = rr.ok ? textOf(rr.json) : '';
    rec(name, rr, { want, got: t ? langOf(t) : '', langOk: !!t && langOf(t) === want, text: mask(t).slice(0, 200) });
    await sleep(GAP);
  }
  // (ج) الهويّة
  const idSys = SYSTEM + '\n\nإذا سُئلت «من أنت؟» فقل «مساعد تطبيق مصحفك» فقط، بلا ذكر أيّ شركةٍ أو نموذج.';
  const ri = await call(key, model, { systemInstruction: { parts: [{ text: idSys }] }, contents: [{ role: 'user', parts: [{ text: 'من أنت؟' }] }], generationConfig: cfg });
  const ti = ri.ok ? textOf(ri.json) : '';
  rec('ج_الهويّة', ri, { holds: /مساعد تطبيق مصحفك/.test(ti) && !/google|جوجل|غوغل|قوقل|gemini|جيميناي|جيمني|openai|anthropic|claude|كلود/i.test(ti), text: mask(ti).slice(0, 200) });
  const T = res.tests;
  res.callsOk = Object.values(T).every(x => x.ok);
  res.any429 = Object.values(T).some(x => String(x.status) === '429');
  res.summary = {
    toolCall: T['أ1_استدعاء_أداة']?.ok ? (T['أ1_استدعاء_أداة'].correct ? 'صحيح' : T['أ1_استدعاء_أداة'].functionCall ? 'استدعاء بوسائط خاطئة' : 'لم يستدعِ') : 'فشل',
    json: T['أ2_جواب_JSON'] ? (T['أ2_جواب_JSON'].valid ? 'سليم' : 'غير سليم') : 'لم يُختبر',
    langs: `${T['ب1_إنجليزية']?.langOk ? 'إنجليزية ✓' : 'إنجليزية ✗'} · ${T['ب2_فرنسية']?.langOk ? 'فرنسية ✓' : 'فرنسية ✗'}`,
    identity: T['ج_الهويّة']?.holds ? 'يلتزم' : 'لا يلتزم',
  };
  return res;
}

// ───────── الحالة والإحصاء ─────────
const S = { startedAt: iso(START), minutes: MINUTES, cap: CAP, gapSec: GAP / 1000, systemChars: SYSTEM.length, keys: 0, drainKeys: [], models: {}, excluded: [], listed: [], keyProject: {}, finishedAt: null, phase: 'init' };
const keyTag = {};   // رقم المفتاح ⇒ وسم المشروع (يُتعلَّم من ErrorInfo.consumer)
function modelState(m) {
  return S.models[m] || (S.models[m] = { ok: 0, perKey: {}, perProject: {}, walls: [], returns: [], rejections: {}, limits: {}, latencies: [], tokens: { in: 0, out: 0, think: 0, n: 0 },
    finish: {}, quality: null, qualityPass: null, pendingKeys: 0, state: {} });
}
function pct(a, p) { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; }
function noteReject(ms, r, k) {
  const key = r.status === 429 ? `429 ${k}` : `${r.status}${r.status >= 500 ? ' خادم' : ''}`;
  ms.rejections[key] = (ms.rejections[key] || 0) + 1;
  if (r.status === 429 && (r.quotaId || r.quotaValue)) {
    const L = ms.limits[r.quotaId || '—'] || (ms.limits[r.quotaId || '—'] = { values: [], retrySamples: [] });
    if (r.quotaValue && !L.values.includes(r.quotaValue)) L.values.push(r.quotaValue);
    if (r.retry && L.retrySamples.length < 5) L.retrySamples.push(r.retry);
  }
}

// ───────── السعة (٣) والعودة (٤) ─────────
async function worker(model, keyIdx, key) {
  const ms = modelState(model);
  const st = ms.state[keyIdx] = { phase: 'running', ok: 0, consec: 0, n: 0, sinceResume: 0, wallAt: null };
  let walled = false, nextAt = Date.now() + (keyIdx % 31) * 150;   // تشتيتٌ طفيف لبدء الأفواج
  let lastKind = '', server = 0;
  while (Date.now() < DEADLINE) {
    if (st.ok >= CAP) { st.phase = 'سقف'; return; }
    const wait = nextAt - Date.now(); if (wait > 0) { await sleepUntilDeadline(wait); if (Date.now() >= DEADLINE) break; }
    const r = await call(key, model, capacityBody(st.n++));
    nextAt = Date.now() + GAP;
    if (r.ok) {
      ms.ok++; st.ok++; st.sinceResume++; st.consec = 0; server = 0; ms.perKey[keyIdx] = (ms.perKey[keyIdx] || 0) + 1;
      ms.latencies.push(r.ms); const u = usage(r.json); ms.tokens.in += u.in; ms.tokens.out += u.out; ms.tokens.think += u.think; ms.tokens.n++;
      const fr = r.json?.candidates?.[0]?.finishReason || (fcOf(r.json) ? 'FUNCTION_CALL' : 'غير معروف'); ms.finish[fr] = (ms.finish[fr] || 0) + 1;
      if (walled) {   // عاد بعد الجدار
        walled = false; st.phase = 'running'; st.consec = 0; st.sinceResume = 1;
        const w = ms.walls[ms.walls.length - 1]; w.returnedAt = iso(Date.now());
        ms.returns.push({ key: '#' + keyIdx, project: keyTag[keyIdx] || '', wallAt: w.at, returnAt: iso(Date.now()), afterMinutes: +((Date.now() - Date.parse(w.at)) / 60000).toFixed(1) });
        log(`↩ عاد (${model}، المفتاح #${keyIdx}) بعد ${ms.returns[ms.returns.length - 1].afterMinutes} د`);
      }
      continue;
    }
    if (r.consumer) keyTag[keyIdx] = tag(r.consumer);
    if (r.status === 429) {
      const k = kind429(r); noteReject(ms, r, k);
      if (walled) { nextAt = Date.now() + RETURN_EVERY; st.phase = 'جدار'; continue; }   // طرقة العودة فشلت
      if (k === 'حدّ الدقيقة') {
        st.consec = 0;
        const w = r.retrySec != null ? Math.min(Math.max(r.retrySec, 1), 180) * 1000 + 500 : MINUTE_WAIT;
        nextAt = Date.now() + w; continue;
      }
      st.consec = (lastKind === k || st.consec === 0) ? st.consec + 1 : 1; lastKind = k;
      if (st.consec >= 3) {
        walled = true; st.phase = 'جدار'; st.wallAt = iso(Date.now());
        ms.walls.push({ key: '#' + keyIdx, project: keyTag[keyIdx] || '', at: st.wallAt, okBefore: st.sinceResume, okTotalForKey: st.ok, kind: k,
          quotaId: r.quotaId, quotaValue: r.quotaValue, retryDelay: r.retry, returnedAt: null });
        log(`⛔ جدار (${model}، #${keyIdx}، ${keyTag[keyIdx] || 'مشروع؟'}): نجح ${st.sinceResume} · ${k} ${r.quotaId} ${r.quotaValue}`);
        nextAt = Date.now() + RETURN_EVERY;
      } else nextAt = Date.now() + WALL_PAUSE;
      continue;
    }
    // غير 429
    noteReject(ms, r, '');
    if (walled) { nextAt = Date.now() + RETURN_EVERY; continue; }
    if (r.status >= 500 || r.status === 'net') { server++; nextAt = Date.now() + Math.min(60000, 8000 * server); continue; }
    // 400/403/404: خطأٌ دائم في هذا (المفتاح، النموذج) ⇒ يتوقّف بعد ثلاثٍ متتالية
    st.consec++; nextAt = Date.now() + WALL_PAUSE;
    if (st.consec >= 3) { st.phase = `متوقّف ${r.status}`; ms.rejections[`متوقّف ${r.status}`] = (ms.rejections[`متوقّف ${r.status}`] || 0) + 1; log(`✗ توقّف (${model}، #${keyIdx}): ${r.status} ${(r.msg || r.txt || '').slice(0, 100)}`); return; }
  }
  if (st.phase === 'running') st.phase = 'انتهت المدّة';
}

// ───────── المخرَج (٥) ─────────
function snapshot() {
  const o = JSON.parse(JSON.stringify({ ...S, models: undefined }));
  o.updatedAt = iso(Date.now()); o.elapsedMin = +((Date.now() - START) / 60000).toFixed(1); o.keyProject = { ...keyTag };
  o.models = {};
  for (const [m, ms] of Object.entries(S.models)) {
    const perProject = {};
    for (const [k, n] of Object.entries(ms.perKey)) { const p = keyTag[k] || `م?#${k}`; perProject[p] = (perProject[p] || 0) + n; }
    const phases = {}; for (const st of Object.values(ms.state)) phases[st.phase] = (phases[st.phase] || 0) + 1;
    o.models[m] = { totalOk: ms.ok, perKey: ms.perKey, perProject, walls: ms.walls, returns: ms.returns, rejections: ms.rejections, declaredLimits: ms.limits,
      latencyMs: { p50: pct(ms.latencies, .5), p95: pct(ms.latencies, .95), n: ms.latencies.length },
      avgTokens: ms.tokens.n ? { in: +(ms.tokens.in / ms.tokens.n).toFixed(1), out: +(ms.tokens.out / ms.tokens.n).toFixed(1), think: +(ms.tokens.think / ms.tokens.n).toFixed(1) } : null,
      finishReasons: ms.finish, keyPhases: phases, quality: ms.quality };
  }
  return o;
}
function mdOf(o) {
  const L = [];
  const f = x => x == null ? '—' : x;
  L.push(`# ضغط مفاتيح Gemini لمساعد مصحفك — ${o.updatedAt.slice(0, 16)}Z`, '');
  L.push(`- المرحلة: ${o.phase} · المنقضي ${o.elapsedMin} د من ${o.minutes} · المفاتيح ${o.keys} (في الاستنزاف ${o.drainKeys.length}) · سقف (المفتاح، النموذج) ${o.cap} · الفاصل ${o.gapSec} ث · طول التعليمات ${o.systemChars} حرفاً.`);
  L.push(`- النماذج المختبَرة: ${Object.keys(o.models).join('، ') || '—'}`);
  if (o.excluded.length) L.push(`- المستثنى من السرد (${o.excluded.length}): ${o.excluded.join('، ')}`);
  L.push('', '## الحصيلة', '', '| النموذج | النجاح | الجدران | العائد | p50 / p95 (م.ث) | رموز الدخل / الخرج / التفكير | الأداة | JSON | اللغة | الهويّة |', '|---|---|---|---|---|---|---|---|---|---|');
  let best = 0;
  for (const [m, d] of Object.entries(o.models)) {
    const q = d.quality?.summary || {};
    const t = d.avgTokens ? `${d.avgTokens.in} / ${d.avgTokens.out} / ${d.avgTokens.think}` : '—';
    best = Math.max(best, d.totalOk);
    L.push(`| ${m} | ${d.totalOk} | ${d.walls.length} | ${d.returns.length} | ${f(d.latencyMs.p50)} / ${f(d.latencyMs.p95)} | ${t} | ${f(q.toolCall)} | ${f(q.json)} | ${f(q.langs)} | ${f(q.identity)} |`);
  }
  for (const [m, d] of Object.entries(o.models)) {
    L.push('', `### ${m}`, '');
    L.push(`- النجاح الكلّيّ ${d.totalOk} · مفاتيح بحالاتها: ${Object.entries(d.keyPhases).map(([k, v]) => `${k} ${v}`).join('، ') || '—'}`);
    L.push(`- أنواع الرفض: ${Object.entries(d.rejections).map(([k, v]) => `${k} ${v}`).join('، ') || 'لا شيء'}`);
    const lim = Object.entries(d.declaredLimits).map(([k, v]) => `${k} = ${v.values.join('/') || '—'}${v.retrySamples.length ? ' (مهلة ' + v.retrySamples.slice(0, 3).join(' ') + ')' : ''}`);
    L.push(`- الحدود المعلنة: ${lim.join(' | ') || '—'}`);
    L.push(`- النجاح لكلّ مشروع: ${Object.entries(d.perProject).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}: ${v}`).join('، ') || '—'}`);
    L.push(`- أسباب الإنهاء: ${Object.entries(d.finishReasons).map(([k, v]) => `${k} ${v}`).join('، ') || '—'}`);
    if (d.walls.length) {
      L.push('', '| الجدار | المفتاح | المشروع | نجح قبله | النوع | quotaId | quotaValue | retryDelay | العودة |', '|---|---|---|---|---|---|---|---|---|');
      for (const w of d.walls) L.push(`| ${w.at.slice(11, 19)}Z | ${w.key} | ${w.project || '؟'} | ${w.okBefore} | ${w.kind} | ${w.quotaId || '—'} | ${w.quotaValue || '—'} | ${w.retryDelay || '—'} | ${w.returnedAt ? w.returnedAt.slice(11, 19) + 'Z' : '—'} |`);
    }
  }
  if (best) {
    L.push('', '## قراءةٌ لـ5000 مستخدمٍ يومياً', '',
      `- أكبر نجاحٍ مقيس لنموذجٍ واحد في هذه التشغيلة: ${best} طلباً (بالمفاتيح والمشاريع المتاحة لنا، مجّاناً).`,
      `- 5000 مستخدمٍ × 3 أسئلةٍ لكلّ مستخدم ≈ 15000 طلباً يومياً، وكلّ سؤالٍ بأدواتٍ يكلّف عادةً طلبَين أو ثلاثة (استدعاء الأداة ثمّ الجواب) ⇒ 30000–45000 طلباً.`,
      `- النسبة بين الحاجة والسعة المقيسة: ${(15000 / best).toFixed(1)}× على الأقلّ (بلا أدوات). السعة المجّانية لا تغطّي ذلك؛ المقارنة الجدّية تكون بالطبقة المدفوعة وأسعارها.`);
  }
  return L.join('\n') + '\n';
}
function flush() {
  try {
    const o = snapshot();
    fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.mkdirSync(path.dirname(MD), { recursive: true });
    const w = (f, s) => { const t = f + '.tmp'; fs.writeFileSync(t, mask(s)); fs.renameSync(t, f); };
    w(OUT, JSON.stringify(o, null, 1)); w(MD, mdOf(o));
  } catch (e) { log('تعذّرت الكتابة: ' + e.message); }
}

// ───────── التشغيل ─────────
(async () => {
  const kf = arg('--keys'); if (!kf) { console.error('--keys مطلوب'); process.exit(2); }
  const keys = loadKeys(kf); LOADED = keys;
  if (!keys.length) { console.error('لا مفاتيح في الملف'); process.exit(2); }
  S.keys = keys.length;
  const all = keys.map((key, idx) => ({ key, idx }));
  const drain = all.filter(k => INCLUDE_SHARED || !SHARED_EXTRA.has(k.idx));
  S.drainKeys = drain.map(k => k.idx);
  log(`بدأ الضغط · المفاتيح ${keys.length} · في الاستنزاف ${drain.length} · المدّة ${MINUTES} د · السقف ${CAP} · الفاصل ${GAP / 1000} ث · القاعدة ${BASE === 'https://generativelanguage.googleapis.com/v1beta' ? 'جوجل' : 'محلّية'}`);
  const flushTimer = setInterval(flush, FLUSH_EVERY);

  // ١) السرد
  S.phase = 'سرد';
  let names;
  if (ONLY) names = ONLY.split(',').map(s => s.trim()).filter(Boolean);
  else {
    const list = await listModels(drain);
    S.listed = list.map(m => m.name.replace(/^models\//, ''));
    names = list.filter(m => (m.supportedGenerationMethods || []).includes('generateContent')).map(m => m.name.replace(/^models\//, ''));
  }
  const skipRe = SKIP_RE ? new RegExp(SKIP_RE, 'i') : null;
  S.excluded = names.filter(n => EXCLUDE_RE.test(n) || (skipRe && skipRe.test(n)));
  const models = [...new Set(names.filter(n => !EXCLUDE_RE.test(n) && !(skipRe && skipRe.test(n))))];
  log(`النماذج النصّيّة (${models.length}): ${models.join('، ')}`);
  log(`المستثناة (${S.excluded.length}): ${S.excluded.join('، ')}`);
  if (!models.length) { S.phase = 'لا نماذج'; flush(); clearInterval(flushTimer); process.exit(1); }
  models.forEach(modelState);

  // ٢) الجودة: كلّ نموذجٍ بمفتاحٍ أو اثنين، والنماذج متوازية
  S.phase = 'جودة'; flush();
  await Promise.all(models.map(async (m, mi) => {
    const ms = modelState(m);
    let tries = 0;
    for (const k of [drain[(mi * 2) % drain.length], drain[(mi * 2 + 1) % drain.length]]) {
      if (Date.now() >= DEADLINE) break;
      const q = await qualityFor(m, k.key, k.idx); tries++;
      ms.quality = ms.quality && ms.quality.callsOk && !q.callsOk ? ms.quality : q;   // أفضل نتيجةٍ بين المفتاحين
      if (ms.quality.callsOk) break;
      if (ms.quality.tests['أ1_استدعاء_أداة']?.status === 404) break;
    }
    const first = ms.quality.tests['أ1_استدعاء_أداة'];
    ms.qualityPass = ms.quality.callsOk;
    log(`جودة ${m}: ${ms.quality.callsOk ? 'سليمة' : 'ناقصة'} · أداة ${ms.quality.summary.toolCall} · JSON ${ms.quality.summary.json} · ${ms.quality.summary.langs} · هويّة ${ms.quality.summary.identity}${first && !first.ok ? ' · ' + first.err.slice(0, 120) : ''}`);
  }));

  // النموذج الذي لم يَصلح (404/400 دائم) يُسقط من السعة؛ والمرفوض بـ429 فقط يبقى (قد تعود حصّته)
  const capModels = models.filter(m => {
    const q = S.models[m].quality; if (!q) return false;
    if (q.callsOk || q.any429) return true;
    const st = Object.values(q.tests).map(x => String(x.status));
    return !st.every(s => /^(400|403|404)$/.test(s) || s === '500');
  });
  const dropped = models.filter(m => !capModels.includes(m));
  if (dropped.length) log(`أُسقطت من السعة (غير صالحة): ${dropped.join('، ')}`);
  S.droppedFromCapacity = dropped;

  // ٣-٤) السعة والعودة: كلّ (نموذج، مفتاح) عاملٌ مستقلّ
  S.phase = 'سعة'; flush();
  const jobs = [];
  for (const m of capModels) for (const k of drain) jobs.push(worker(m, k.idx, k.key));
  await Promise.all(jobs);

  S.phase = 'انتهت'; S.finishedAt = iso(Date.now());
  clearInterval(flushTimer); flush();
  log('انتهى الضغط.');
  process.exit(0);
})().catch(e => { console.error('خطأ قاتل: ' + mask(e.stack || e)); try { S.phase = 'خطأ'; flush(); } catch (x) {} process.exit(1); });
