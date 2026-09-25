"""تدقيق الحمولتين بلا توليد، ونقل نسخة مشفرة إلى جلسة المالك دون نقل سر المستودع."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def sealed_digest(directory: Path) -> str:
    """احسب بصمة الحمولة الواحدة أو أجزائها بالترتيب نفسه عند التجميع."""
    parts = sorted(directory.glob('payload.part.*.enc'))
    files = parts or [directory / 'payload.enc']
    digest = hashlib.sha256()
    for path in files:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
    return digest.hexdigest()


def main():
    repo = Path(__file__).resolve().parents[1]
    out = repo / 'ops/audit/2026-09-25'
    report = {'run_id': os.environ.get('GITHUB_RUN_ID'), 'head': os.environ.get('GITHUB_SHA'),
              'films': {}, 'generation_calls': 0, 'artifact_uploads': 0}
    for slug in ('waraq', 'nahl'):
        sealed = repo / 'ops/staged' / slug
        trigger = json.loads((sealed / 'trigger.json').read_text())
        digest = sealed_digest(sealed)
        if digest != trigger['payload_sha256']:
            raise SystemExit('بصمة الحمولة لا تطابق الزناد: ' + slug)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / slug
            subprocess.run(['bash', 'tools/unseal.sh', str(sealed), str(root)], check=True,
                           stdout=subprocess.DEVNULL)
            # المخرجات التفصيلية خاصة، ولا تُطبع نصوص السيناريو في السجل العام.
            check = subprocess.run([sys.executable, 'tools/precheck.py', str(root)],
                                   capture_output=True)
            (root / 'audit-precheck.log').write_bytes(check.stdout + check.stderr)
            def read(name):
                path = root / name
                return json.loads(path.read_text()) if path.exists() else []
            blocks = read('blocks.json')
            images = read('images.json')
            report['films'][slug] = {
                'payload_sha256': digest, 'precheck_exit': check.returncode,
                'blocks': len(blocks), 'images_required': len(images),
                'audio_present': sum((root / 'audio' / (b['id'] + '.wav')).is_file() for b in blocks),
                'images_present': sum((root / 'img' / (i['id'] + '.jpg')).is_file() for i in images),
                'openai_manifest_present': (root / 'image_sources.json').is_file(),
                'film_rendered': (root / 'film.mp4').is_file(),
                'listen_report_present': (root / 'listen_report.json').is_file(),
                'files': sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()),
            }
            archive = Path(temp) / 'review.tgz'
            with tarfile.open(archive, 'w:gz') as tar:
                tar.add(root, arcname=slug)
            destination = out / (slug + '-review.enc')
            if destination.exists():
                destination.unlink()
            subprocess.run(['node', 'tools/artifact_crypto.mjs', 'seal', str(archive),
                            str(destination), str(out / 'session-public.pem')], check=True,
                           stdout=subprocess.DEVNULL)
    logo = repo / 'assets/logo.png'
    report['logo_sha256'] = hashlib.sha256(logo.read_bytes()).hexdigest()
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('اكتمل التدقيق بلا توليد؛ التقرير العددي محفوظ والحمولتان مشفرتان.')


if __name__ == '__main__':
    main()
