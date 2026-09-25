// الهوية المعتمدة: الغلاف والعلامة المائية فقط، دون تغيير بيانات الأفلام أو وصف القناة.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'assets/branding/manifest.json'), 'utf8'));
const expectedChannel = 'UCda-VgyvZwAH5_Pl1elVEnw';
const mode = process.argv[2];
if (!['--verify-local', '--apply'].includes(mode)) throw new Error('اختر --verify-local أو --apply');
if (manifest.channelId !== expectedChannel) throw new Error('معرّف القناة لا يطابق الهوية');
for (const [name, spec] of Object.entries(manifest.assets)) {
  const resolved = path.resolve(root, name);
  if (!resolved.startsWith(root + path.sep)) throw new Error('مسار أصل غير صالح');
  const bytes = fs.readFileSync(resolved);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== spec.sha256) throw new Error(`بصمة مختلفة: ${name}`);
  if (bytes.length > spec.maxBytes) throw new Error(`حجم غير صالح: ${name}`);
}
console.log('✅ أصول الهوية تطابق بصمات الاعتماد وحدود الحجم');

function report(value) {
  const out = JSON.stringify(value, null, 2);
  console.log(out);
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, '\n```json\n' + out + '\n```\n');
}

if (mode === '--apply') {
  const auth = JSON.parse(process.env.YT_OAUTH_JSON || '{}');
  if (!auth.client_id || !auth.client_secret || !auth.refresh_token) throw new Error('إذن يوتيوب غير متاح');
  const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', signal: AbortSignal.timeout(30000),
    body: new URLSearchParams({client_id: auth.client_id, client_secret: auth.client_secret,
      refresh_token: auth.refresh_token, grant_type: 'refresh_token'})
  });
  const token = await tokenResponse.json();
  if (!tokenResponse.ok || !token.access_token) throw new Error(`تجديد إذن يوتيوب فشل: ${token.error || tokenResponse.status}`);
  async function api(route, {method = 'GET', body, contentType = 'application/json', upload = false} = {}) {
    const base = upload ? 'https://www.googleapis.com/upload/youtube/v3/' : 'https://www.googleapis.com/youtube/v3/';
    const response = await fetch(base + route, {method, body, signal: AbortSignal.timeout(60000),
      headers: {Authorization: 'Bearer ' + token.access_token, 'Content-Type': contentType}});
    const raw = await response.text();
    let data = {}; try { data = raw ? JSON.parse(raw) : {}; } catch {}
    if (!response.ok) throw new Error(`يوتيوب ${response.status}: ${data.error?.errors?.[0]?.reason || 'فشل الطلب'}`);
    return {data, status: response.status};
  }
  async function readChannel() {
    const {data} = await api('channels?part=snippet,brandingSettings&mine=true');
    const channel = data.items?.find(c => c.id === expectedChannel);
    if (!channel) throw new Error('الحساب المأذون لا يحتوي قناة المتفائل المطلوبة؛ أوقف التغيير');
    return channel;
  }
  const before = await readChannel();
  report({مرحلة: 'قبل التطبيق', channelId: before.id, title: before.snippet.title,
    previousBanner: before.brandingSettings?.image?.bannerExternalUrl || null,
    previousAvatar: before.snippet.thumbnails?.high?.url || null});

  const bannerBytes = fs.readFileSync(path.join(root, 'assets/branding/banner.jpg'));
  const {data: uploaded} = await api('channelBanners/insert?uploadType=media', {
    method: 'POST', upload: true, contentType: 'image/jpeg', body: bannerBytes});
  if (!uploaded.url) throw new Error('لم ترجع واجهة رفع الغلاف رابطاً');
  // نحفظ جميع حقول brandingSettings الحالية؛ تعديل الجزء يستبدل حقوله القابلة للكتابة.
  const brandingSettings = structuredClone(before.brandingSettings || {});
  brandingSettings.image = {...brandingSettings.image, bannerExternalUrl: uploaded.url};
  await api('channels?part=brandingSettings', {method: 'PUT',
    body: JSON.stringify({id: expectedChannel, brandingSettings})});
  report({مرحلة: 'حفظ الغلاف', uploadedBanner: uploaded.url});
  const after = await readChannel();
  if (after.brandingSettings?.image?.bannerExternalUrl !== uploaded.url) throw new Error('قراءة الغلاف من الخادم لا تطابق الرفع');
  if (JSON.stringify(after.brandingSettings?.channel) !== JSON.stringify(before.brandingSettings?.channel)
      || after.snippet.title !== before.snippet.title || after.snippet.description !== before.snippet.description) {
    throw new Error('تغيّرت بيانات أخرى في القناة؛ يلزم فحص قبل أي خطوة أخرى');
  }
  report({مرحلة: 'تحقق الغلاف من الخادم', verified: true, bannerUrl: uploaded.url,
    channelMetadataUnchanged: true, avatarChanged: false});

  const boundary = 'mutafail-' + crypto.randomUUID();
  const metadata = {timing: {type: 'offsetFromStart', offsetMs: '0'}, targetChannelId: expectedChannel};
  const watermark = fs.readFileSync(path.join(root, 'assets/branding/watermark.png'));
  const body = Buffer.concat([
    Buffer.from(`--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${JSON.stringify(metadata)}\r\n`),
    Buffer.from(`--${boundary}\r\nContent-Type: image/png\r\n\r\n`), watermark,
    Buffer.from(`\r\n--${boundary}--\r\n`)
  ]);
  const accepted = await api(`watermarks/set?channelId=${expectedChannel}&uploadType=multipart`, {
    method: 'POST', upload: true, contentType: `multipart/related; boundary=${boundary}`, body});
  report({مرحلة: 'تطبيق العلامة المائية', accepted: true, httpStatus: accepted.status,
    timing: metadata.timing, visualPlaybackVerified: false,
    ملاحظة: 'صورة حساب القناة تحتاج واجهة الاستوديو؛ هذه الأداة لا تغيّرها'});
}
