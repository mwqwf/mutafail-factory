import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,randomBytes} from 'node:crypto';
import {mkdtemp,writeFile,readFile,unlink,rmdir,readdir,access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {seal,unseal} from './artifact_crypto.mjs';
const pair=generateKeyPairSync('rsa',{modulusLength:2048,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});
async function fixture(fn) {
  const dir=await mkdtemp(join(tmpdir(),'mutafail-artifact-test-'));
  try {await fn(dir);} finally {
    // ملفات اصطناعية في مجلد الاختبار الذي أُنشئ هنا فقط؛ لا حذف متكرر.
    for(const name of await readdir(dir)) await unlink(join(dir,name));
    await rmdir(dir);
  }
}
test('streamed artifact round-trips without disclosing its contents',async()=>fixture(async d=>{
  const input=join(d,'input'),sealed=join(d,'payload.enc'),output=join(d,'out');
  const data=Buffer.concat([Buffer.from('PRIVATE TEST ONLY'),randomBytes(200000)]);
  await writeFile(input,data); await seal(input,sealed,pair.publicKey);
  assert.equal((await readFile(sealed)).includes(Buffer.from('PRIVATE TEST ONLY')),false);
  await unseal(sealed,output,pair.privateKey);
  assert.deepEqual(await readFile(output),data);
}));
test('tampering is rejected and plaintext output removed',async()=>fixture(async d=>{
  const input=join(d,'input'),sealed=join(d,'payload.enc'),output=join(d,'out');
  await writeFile(input,randomBytes(65536)); await seal(input,sealed,pair.publicKey);
  const bad=await readFile(sealed); bad[bad.length-20]^=1; await writeFile(sealed,bad);
  await assert.rejects(unseal(sealed,output,pair.privateKey));
  await assert.rejects(access(output));
  assert.equal((await readdir(d)).some(x=>x.includes('.partial-')),false);
}));
test('wrong key and missing key fail closed',async()=>fixture(async d=>{
  const input=join(d,'input'),sealed=join(d,'payload.enc'),output=join(d,'out');
  await writeFile(input,'synthetic'); await seal(input,sealed,pair.publicKey);
  await assert.rejects(unseal(sealed,output,''));
  await assert.rejects(unseal(sealed,output,'not a private key'));
  await assert.rejects(access(output));
}));
test('existing output is never overwritten',async()=>fixture(async d=>{
  const input=join(d,'input'),sealed=join(d,'payload.enc'),output=join(d,'out');
  await writeFile(input,'new'); await seal(input,sealed,pair.publicKey); await writeFile(output,'keep');
  await assert.rejects(unseal(sealed,output,pair.privateKey));
  assert.equal(await readFile(output,'utf8'),'keep');
  await assert.rejects(seal(input,sealed,pair.publicKey));
}));
