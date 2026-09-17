const MAX_INLINE_RAW_BYTES = 12 * 1024 * 1024;

function pack(items, maxItems = 4, maxRawBytes = MAX_INLINE_RAW_BYTES) {
  const groups = [];
  let group = [], bytes = 0;
  for (const item of items) {
    const size = item.audio.length;
    if (size > maxRawBytes) throw new Error(`audio-too-large:${item.block.id}`);
    if (group.length && (group.length >= maxItems || bytes + size > maxRawBytes)) {
      groups.push(group); group = []; bytes = 0;
    }
    group.push(item); bytes += size;
  }
  if (group.length) groups.push(group);
  return groups;
}

function requestParts(group, prompt) {
  const parts = [{text: prompt.replace('{COUNT}', String(group.length))}];
  group.forEach((item, index) => {
    parts.push({text: `\nالمقطع ${index + 1} — المعرّف ${item.block.id}\nالنص المشكول: ${item.block.text}`});
    parts.push({inlineData: {mimeType: 'audio/wav', data: item.audio.toString('base64')}});
  });
  return parts;
}

function parseResponse(text, expectedIds) {
  const parsed = JSON.parse(text);
  if (!parsed || !Array.isArray(parsed.results)) throw new Error('missing-results');
  const expected = new Set(expectedIds), found = new Map();
  for (const row of parsed.results) {
    if (!row || typeof row.id !== 'string' || !expected.has(row.id)) throw new Error('unexpected-id');
    if (found.has(row.id)) throw new Error('duplicate-id');
    if (typeof row.ok !== 'boolean') throw new Error('invalid-verdict');
    found.set(row.id, row);
  }
  if (found.size !== expected.size) throw new Error('missing-id');
  return Object.fromEntries(found);
}

module.exports = {MAX_INLINE_RAW_BYTES, pack, requestParts, parseResponse};
