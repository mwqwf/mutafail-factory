const assert = require('node:assert/strict');
const {pack, requestParts, parseResponse} = require('./listen_batch');

const item = id => ({block: {id, text: `نص ${id}`}, audio: Buffer.alloc(10)});
assert.deepEqual(pack(['a','b','c','d','e'].map(item), 4).map(x => x.length), [4, 1]);
assert.deepEqual(pack(['a','b','c'].map(item), 9, 20).map(x => x.length), [2, 1]);
assert.equal(requestParts([item('a'), item('b')], 'عدد {COUNT}').length, 5);
assert.deepEqual(Object.keys(parseResponse('{"results":[{"id":"b","ok":false},{"id":"a","ok":true}]}', ['a','b'])).sort(), ['a','b']);
for (const bad of [
  '{"results":[{"id":"a","ok":true}]}',
  '{"results":[{"id":"a","ok":true},{"id":"a","ok":true}]}',
  '{"results":[{"id":"a","ok":"true"},{"id":"b","ok":true}]}',
  '{"results":[{"id":"a","ok":true},{"id":"x","ok":true}]}'
]) assert.throws(() => parseResponse(bad, ['a','b']));
console.log('PASS: strict batched listening invariants');
