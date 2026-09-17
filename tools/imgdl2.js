// تنزيل صور بوليناشنز — ⛔ عامل واحد فقط (max queue 1 للطبقة المجانية)
// الاستعمال: node imgdl2.js <projectDir1> [projectDir2 ...]
// يقرأ <proj>/images.json = [{id, prompt}] ويكتب <proj>/img/<id>.jpg
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const CURL = 'curl';
const TIMEOUT = 180;
const GAP = 1200;

function verify(f) {
  try {
    execFileSync('python', ['-c', `from PIL import Image;im=Image.open(r"${f}");im.verify();im2=Image.open(r"${f}");im2.load()`], { stdio: 'pipe' });
    return fs.statSync(f).size >= 25000;
  } catch (e) { return false; }
}

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  const projs = process.argv.slice(2);
  if (!projs.length) { console.error('usage: node imgdl2.js <projectDir>...'); process.exit(1); }
  for (const proj of projs) {
    const list = JSON.parse(fs.readFileSync(path.join(proj, 'images.json'), 'utf8'));
    const dir = path.join(proj, 'img'); fs.mkdirSync(dir, { recursive: true });
    console.log(`\n=== ${path.basename(proj)}: ${list.length} صورة ===`);
    let ok = 0, fail = 0;
    for (const it of list) {
      const out = path.join(dir, it.id + '.jpg');
      if (fs.existsSync(out) && verify(out)) { ok++; continue; }
      let got = false;
      for (let attempt = 1; attempt <= 6 && !got; attempt++) {
        const seed = 1000 + attempt * 137 + it.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
        const url = `https://image.pollinations.ai/prompt/${encodeURIComponent(it.prompt)}?width=1920&height=1080&model=flux&nologo=true&seed=${seed}`;
        try {
          execFileSync(CURL, ['-s', '-L', '-m', String(TIMEOUT), '-o', out, url], { stdio: 'pipe' });
          if (verify(out)) { got = true; break; }
        } catch (e) {}
        try { if (fs.existsSync(out)) fs.unlinkSync(out); } catch (e) {}
        await sleep(4000);
      }
      if (got) { ok++; process.stdout.write(`✓${it.id} `); } else { fail++; console.log(`\n✗ فشل ${it.id}`); }
      await sleep(GAP);
    }
    console.log(`\n${path.basename(proj)}: نجح ${ok} | فشل ${fail}`);
  }
})();
