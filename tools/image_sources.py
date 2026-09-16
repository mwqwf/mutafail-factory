"""صور Codex المعتمدة أولاً؛ يبقى imgdl3.py الأصلي مسؤولاً عن الصور الناقصة.

لا ينادي API ولا يستهلك رصيداً، ولا يعد بأن توليد الصور متاح داخل GitHub Actions.
"""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image


def import_primary(project):
    root = Path(project).resolve()
    manifest = root / 'image_sources.json'
    if not manifest.exists():
        return {'primary': [], 'fallback': [], 'mode': 'original-only'}
    config = json.loads(manifest.read_text(encoding='utf-8'))
    images = json.loads((root / 'images.json').read_text(encoding='utf-8'))
    preferred = config.get('primary', {})
    if config.get('provider') != 'codex-imagegen' or not isinstance(preferred, dict):
        raise ValueError('invalid image source manifest')
    report = {'primary': [], 'fallback': [], 'mode': 'codex-first-original-fallback'}
    (root / 'img').mkdir(exist_ok=True)
    for item in images:
        ident = item['id']
        if not isinstance(ident, str) or Path(ident).name != ident or '/' in ident or '\\' in ident:
            raise ValueError('invalid image id')
        entry = preferred.get(ident)
        if entry is None:
            report['fallback'].append({'id': ident, 'reason': 'no-primary'})
            continue
        try:
            if entry.get('approved') is not True:
                raise ValueError('not-visually-approved')
            source = (root / entry['file']).resolve()
            if root not in source.parents:
                raise ValueError('outside-payload')
            raw = source.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('source-hash-mismatch')
            if hashlib.sha256(item['prompt'].encode('utf-8')).hexdigest() != entry['prompt_sha256']:
                raise ValueError('prompt-hash-mismatch')
            with Image.open(source) as check:
                check.verify()
            with Image.open(source) as image:
                image.load()
                width, height = image.size
                if width < 1024 or height < 576 or abs(width / height - 16 / 9) > .02:
                    raise ValueError('size-or-aspect-ratio')
                target = root / 'img' / (ident + '.jpg')
                # نسخة مشتقة؛ المصدر يبقى بلا مساس. لا ندعي أن التكبير يزيد التفاصيل.
                image.convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS).save(
                    target.with_suffix('.tmp'), format='JPEG', quality=94, subsampling=0)
                target.with_suffix('.tmp').replace(target)
            report['primary'].append({'id': ident, 'native_dimensions': [width, height],
                                      'sha256': entry['sha256']})
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            # لا نطبع مساراً خاصاً أو وصف الصورة في سجلات المستودع العام.
            report['fallback'].append({'id': ident, 'reason': type(exc).__name__})
    (root / 'image_source_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    report = import_primary(sys.argv[1])
    print('primary=%d fallback=%d mode=%s' % (len(report['primary']), len(report['fallback']), report['mode']))
