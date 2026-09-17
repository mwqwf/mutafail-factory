// تشفير مخرجات Actions الخاصة: AES-256-GCM ومفتاح عابر مغلف بـRSA-OAEP-SHA256.
// لا تتغير حمولة seal.sh القديمة؛ هذا غلاف مستقل للوسائط بعد فكها في العدّاء.
import {createCipheriv, createDecipheriv, randomBytes, publicEncrypt, privateDecrypt, constants} from 'node:crypto';
import {createReadStream, createWriteStream} from 'node:fs';
import {open, readFile, rename, rm, stat} from 'node:fs/promises';
import {pipeline} from 'node:stream/promises';
import {pathToFileURL} from 'node:url';

const MAGIC='mutafail-private-artifact-v1';
const MAX_HEADER=8192;
export async function seal(input, output, publicKey) {
  const key=randomBytes(32), iv=randomBytes(12);
  const wrapped=publicEncrypt({key:publicKey,oaepHash:'sha256',padding:constants.RSA_PKCS1_OAEP_PADDING},key);
  const header=Buffer.from(JSON.stringify({format:MAGIC,iv:iv.toString('base64'),key:wrapped.toString('base64')})+'\n');
  if(header.length>MAX_HEADER) throw new Error('Artifact header too large');
  const cipher=createCipheriv('aes-256-gcm',key,iv);
  cipher.setAAD(header);
  const handle=await open(output,'wx',0o600);
  try {
    await handle.write(header);
    await handle.close();
    await pipeline(createReadStream(input),cipher,createWriteStream(output,{flags:'a',mode:0o600}));
    const tail=await open(output,'a');
    try {await tail.write(cipher.getAuthTag());} finally {await tail.close();}
  } catch(error) {await handle.close().catch(()=>{}); await rm(output,{force:true}); throw error;}
  finally {key.fill(0);}
}

export async function unseal(input, output, privateKey) {
  if(!privateKey) throw new Error('Missing CONTENT_PRIVATE_KEY');
  // لا يُكتب الخرج النهائي قبل اجتياز مصادقة GCM؛ ولا قبول لمخرجات قديمة خامة.
  const size=(await stat(input)).size;
  const source=await open(input,'r');
  let header, tag;
  try {
    const prefix=Buffer.alloc(Math.min(MAX_HEADER,size));
    await source.read(prefix,0,prefix.length,0);
    const end=prefix.indexOf(10);
    if(end<0 || size<end+1+16) throw new Error('Invalid encrypted artifact');
    header=prefix.subarray(0,end+1);
    tag=Buffer.alloc(16);
    await source.read(tag,0,16,size-16);
  } finally {await source.close();}
  const meta=JSON.parse(header.toString('utf8'));
  if(meta.format!==MAGIC) throw new Error('Unsupported artifact format');
  const iv=Buffer.from(meta.iv,'base64');
  if(iv.length!==12) throw new Error('Invalid artifact IV');
  const key=privateDecrypt({key:privateKey,oaepHash:'sha256',padding:constants.RSA_PKCS1_OAEP_PADDING},Buffer.from(meta.key,'base64'));
  if(key.length!==32) throw new Error('Invalid artifact key');
  const decipher=createDecipheriv('aes-256-gcm',key,iv);
  decipher.setAAD(header); decipher.setAuthTag(tag);
  const temporary=output+'.partial-'+randomBytes(8).toString('hex');
  try {
    // لا استبدال صامت لملف موجود.
    const reservation=await open(output,'wx',0o600);
    await reservation.close();
  } catch(error) {key.fill(0); throw error;}
  try {
    await pipeline(createReadStream(input,{start:header.length,end:size-17}),decipher,
      createWriteStream(temporary,{flags:'wx',mode:0o600}));
    await rename(temporary,output);
  } catch(error) {
    await rm(temporary,{force:true}); await rm(output,{force:true}); throw error;
  } finally {key.fill(0);}
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const [action,input,output,pub]=process.argv.slice(2);
  try {
    if(action==='seal' && input && output && pub) await seal(input,output,await readFile(pub));
    else if(action==='unseal' && input && output) await unseal(input,output,process.env.CONTENT_PRIVATE_KEY);
    else throw new Error('Usage: seal input output public.pem | unseal input output');
    console.log('Private artifact '+action+' verified.');
  } catch {console.error('Private artifact operation failed; no plaintext details logged.'); process.exitCode=1;}
}
