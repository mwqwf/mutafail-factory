#!/usr/bin/env node
/**
 * حارس خوادم MCP المهجورة — PreToolUse على Bash وWrite وEdit.
 *
 * بحث MCPhantom (Glow Labs، 2026-11-03): وكلاء البرمجة يختارون اسم خادم MCP من ذاكرة
 * تدريبهم، فيثبّتون خادماً مرجعياً مؤرشفاً من `@modelcontextprotocol` بدل الخادم الرسميّ.
 * في هذه الخوادم ثغراتٌ لن تُصلح (أخطرها تنفيذ أوامر عن بُعد في Puppeteer)، ولا تكشفها
 * أدوات الأمن لأنّها خارج ملفّات الاعتماديات. يرفض الحارس تشغيلها أو تثبيتها أو كتابتها في
 * إعداد MCP، ويسمّي البديل الرسميّ. يرفض برسالة («deny») ولا يسأل، كي لا تتعلّق جلسةٌ سحابيّة.
 * أمر المالك 2026-11-04: «طبّق منها ما يفيدنا».
 */
// الخوادم المرجعية المؤرشفة (modelcontextprotocol/servers-archived) وبدائلها الرسمية
const ARCHIVED = {
  'aws-kb-retrieval-server': 'خادم AWS الرسميّ (awslabs/mcp)',
  'brave-search': 'خادم Brave الرسميّ (@brave/brave-search-mcp-server)',
  everart: 'لا بديل؛ لا يُستعمل',
  gdrive: 'موصل Google Drive الرسميّ',
  github: 'خادم GitHub الرسميّ (github/github-mcp-server) أو موصل GitHub',
  gitlab: 'خادم GitLab الرسميّ',
  'google-maps': 'لا بديل معتمد؛ لا يُستعمل',
  postgres: 'خادم قاعدة البيانات الرسميّ لمزوّدها',
  puppeteer: 'Playwright المثبّت في البيئة أو @playwright/mcp',
  redis: 'خادم Redis الرسميّ (redis/mcp-redis)',
  sentry: 'خادم Sentry الرسميّ (getsentry/sentry-mcp)',
  slack: 'موصل Slack الرسميّ',
  sqlite: 'لا بديل معتمد؛ تُقرأ القاعدة بأداةٍ محلية',
};
const RE = new RegExp('@modelcontextprotocol/server-(' + Object.keys(ARCHIVED).map((k) => k.replace(/-/g, '\\-')).join('|') + ')(?![\\w-])', 'g');

function hits(text) {
  const out = new Set();
  for (const m of String(text || '').matchAll(RE)) out.add(m[1]);
  return [...out];
}

let input = '';
process.stdin.on('data', (c) => (input += c));
process.stdin.on('end', () => {
  try {
    const p = JSON.parse(input || '{}');
    const ti = p.tool_input || {};
    const text = [ti.command, ti.content, ti.new_string].filter(Boolean).join('\n');
    const found = hits(text);
    if (!found.length) process.exit(0);
    const alt = found.map((k) => `@modelcontextprotocol/server-${k} ← ${ARCHIVED[k]}`).join('؛ ');
    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny',
      permissionDecisionReason: `حارس MCP: خادمٌ مرجعيّ مؤرشف لن تُصلح ثغراته (بحث MCPhantom). استعمل البديل الرسميّ: ${alt}.` } }));
  } catch { /* لا يعطّل العمل إن تعذّر التحليل */ }
  process.exit(0);
});

module.exports = { hits };
