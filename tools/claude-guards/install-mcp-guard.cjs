#!/usr/bin/env node
/**
 * مثبّت حارس خوادم MCP المؤرشفة على مستوى المستخدم — يسري على كلّ مشروعٍ ومستودع وجلسة على هذا الجهاز.
 * أمر المالك 2026-11-04: «أضفه لجميع المشاريع والمستودعات… طبّق حلّاً عامّاً».
 * يكتب الحارس في ~/.claude/hooks/ ويضيفه إلى ~/.claude/settings.json (PreToolUse) دون مساس بما فيه.
 * تشغيلٌ متكرّر آمن: لا يكرّر المدخل، ويحدّث نصّ الحارس.
 * الاستعمال:  node install-mcp-guard.cjs        (أو عبر curl في سكربت إعداد البيئة السحابية)
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const HOOK = "#!/usr/bin/env node\n/**\n * حارس خوادم MCP المهجورة — PreToolUse على Bash وWrite وEdit.\n *\n * بحث MCPhantom (Glow Labs، 2026-11-03): وكلاء البرمجة يختارون اسم خادم MCP من ذاكرة\n * تدريبهم، فيثبّتون خادماً مرجعياً مؤرشفاً من `@modelcontextprotocol` بدل الخادم الرسميّ.\n * في هذه الخوادم ثغراتٌ لن تُصلح (أخطرها تنفيذ أوامر عن بُعد في Puppeteer)، ولا تكشفها\n * أدوات الأمن لأنّها خارج ملفّات الاعتماديات. يرفض الحارس تشغيلها أو تثبيتها أو كتابتها في\n * إعداد MCP، ويسمّي البديل الرسميّ. يرفض برسالة («deny») ولا يسأل، كي لا تتعلّق جلسةٌ سحابيّة.\n * أمر المالك 2026-11-04: «طبّق منها ما يفيدنا».\n */\n// الخوادم المرجعية المؤرشفة (modelcontextprotocol/servers-archived) وبدائلها الرسمية\nconst ARCHIVED = {\n  'aws-kb-retrieval-server': 'خادم AWS الرسميّ (awslabs/mcp)',\n  'brave-search': 'خادم Brave الرسميّ (@brave/brave-search-mcp-server)',\n  everart: 'لا بديل؛ لا يُستعمل',\n  gdrive: 'موصل Google Drive الرسميّ',\n  github: 'خادم GitHub الرسميّ (github/github-mcp-server) أو موصل GitHub',\n  gitlab: 'خادم GitLab الرسميّ',\n  'google-maps': 'لا بديل معتمد؛ لا يُستعمل',\n  postgres: 'خادم قاعدة البيانات الرسميّ لمزوّدها',\n  puppeteer: 'Playwright المثبّت في البيئة أو @playwright/mcp',\n  redis: 'خادم Redis الرسميّ (redis/mcp-redis)',\n  sentry: 'خادم Sentry الرسميّ (getsentry/sentry-mcp)',\n  slack: 'موصل Slack الرسميّ',\n  sqlite: 'لا بديل معتمد؛ تُقرأ القاعدة بأداةٍ محلية',\n};\nconst RE = new RegExp('@modelcontextprotocol/server-(' + Object.keys(ARCHIVED).map((k) => k.replace(/-/g, '\\\\-')).join('|') + ')(?![\\\\w-])', 'g');\n\nfunction hits(text) {\n  const out = new Set();\n  for (const m of String(text || '').matchAll(RE)) out.add(m[1]);\n  return [...out];\n}\n\nlet input = '';\nprocess.stdin.on('data', (c) => (input += c));\nprocess.stdin.on('end', () => {\n  try {\n    const p = JSON.parse(input || '{}');\n    const ti = p.tool_input || {};\n    const text = [ti.command, ti.content, ti.new_string].filter(Boolean).join('\\n');\n    const found = hits(text);\n    if (!found.length) process.exit(0);\n    const alt = found.map((k) => `@modelcontextprotocol/server-${k} ← ${ARCHIVED[k]}`).join('؛ ');\n    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny',\n      permissionDecisionReason: `حارس MCP: خادمٌ مرجعيّ مؤرشف لن تُصلح ثغراته (بحث MCPhantom). استعمل البديل الرسميّ: ${alt}.` } }));\n  } catch { /* لا يعطّل العمل إن تعذّر التحليل */ }\n  process.exit(0);\n});\n\nmodule.exports = { hits };\n";

const dir = path.join(os.homedir(), '.claude');
const hooks = path.join(dir, 'hooks');
fs.mkdirSync(hooks, { recursive: true });
const file = path.join(hooks, 'guard-mcp-deprecated.cjs');
fs.writeFileSync(file, HOOK);

const sp = path.join(dir, 'settings.json');
let s = {};
if (fs.existsSync(sp)) {
  try { s = JSON.parse(fs.readFileSync(sp, 'utf8') || '{}'); } catch (e) {
    console.error('⛔ ~/.claude/settings.json ليس JSON صالحاً؛ لم يُعدَّل: ' + e.message); process.exit(1);
  }
}
s.hooks = s.hooks || {};
const pre = (s.hooks.PreToolUse = s.hooks.PreToolUse || []);
const cmd = 'node "' + file.replace(/\\/g, '/') + '"';
const has = pre.some((e) => (e.hooks || []).some((h) => String(h.command || '').includes('guard-mcp-deprecated')));
if (!has) pre.push({ matcher: 'Bash|PowerShell|Write|Edit', hooks: [{ type: 'command', command: cmd }] });
fs.writeFileSync(sp, JSON.stringify(s, null, 2) + '\n');
console.log((has ? '✅ الحارس مثبّت سابقاً، وحُدّث نصّه: ' : '✅ ثُبّت الحارس: ') + file);
