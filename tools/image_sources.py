"""صور OpenAI المعتمدة أولاً لكل فيلم جديد؛ وimgdl3.py احتياط نهائي موثّق فقط.

لا ينادي API ولا يستهلك رصيداً، ولا يعد بأن توليد الصور متاح داخل GitHub Actions.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
from PIL import Image


def _image_policy(root):
    try:
        slug = json.loads((root / 'meta.json').read_text(encoding='utf-8')).get('slug', '')
    except (OSError, ValueError, AttributeError):
        raise RuntimeError('missing or invalid meta.json; image policy cannot be selected safely')
    if not isinstance(slug, str) or not slug:
        raise RuntimeError('missing project slug; image policy fails closed')
    # الاستثناء التاريخي للحلقتين المنشورتين فقط؛ كل اسم جديد يخضع للحارس.
    return slug, slug not in {'amal-1', 'amal-2'}


def _documented_fallback(root, command):
    record = root / 'image_fallback_exception.json'
    if not record.exists():
        return False
    try:
        data = json.loads(record.read_text(encoding='utf-8'))
        if data.get('provider') != 'openai-chatgpt-imagegen':
            return False
        if data.get('command') != command:
            return False
        if data.get('status') != 'unavailable-after-authorized-attempts':
            return False
        if data.get('authorizedAlternativesExhausted') is not True:
            return False
        if not isinstance(data.get('reason'), str) or len(data['reason'].strip()) < 20:
            return False
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', data.get('checkedAt', '')):
            return False
        evidence = (root / data['evidenceFile']).resolve()
        if root not in evidence.parents:
            return False
        raw = evidence.read_bytes()
        if hashlib.sha256(raw).hexdigest() != data.get('evidenceSha256'):
            return False
        proof = json.loads(raw.decode('utf-8'))
        return (
            proof.get('tool') == 'image_gen.imagegen'
            and proof.get('command') == command
            and proof.get('executionEnvironment') == 'chatgpt-cloud'
            and proof.get('resultKind') == 'tool-error'
            and proof.get('runStatus') == 'failed-terminal'
            and isinstance(proof.get('attemptCount'), int) and proof['attemptCount'] >= 1
            and proof.get('outputCount') == 0
            and proof.get('attemptedAt') == data.get('checkedAt')
            and bool(re.fullmatch(r'[0-9a-f]{64}', proof.get('promptSha256', '')))
            and bool(re.fullmatch(r'[0-9a-f]{64}', proof.get('errorMessageSha256', '')))
            and isinstance(proof.get('errorClass'), str) and len(proof['errorClass']) >= 3
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def import_primary(project):
    root = Path(project).resolve()
    command, strict = _image_policy(root)
    exception = _documented_fallback(root, command) if strict else False
    manifest = root / 'image_sources.json'
    if not manifest.exists():
        if strict and not exception:
            raise RuntimeError('يلزم صور OpenAI معتمدة أو دليل تعذر نهائي مختوم لكل فيلم جديد')
        if strict:
            images = json.loads((root / 'images.json').read_text(encoding='utf-8'))
            report = {'primary': [], 'fallback': [
                {'id': item['id'], 'reason': 'documented-exception'} for item in images
            ], 'mode': 'documented-original-fallback'}
            (root / 'image_source_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            return report
        return {'primary': [], 'fallback': [], 'mode': 'original-only'}
    config = json.loads(manifest.read_text(encoding='utf-8'))
    images = json.loads((root / 'images.json').read_text(encoding='utf-8'))
    preferred = config.get('primary', {})
    accepted = {'codex-imagegen'} if not strict else {'openai-chatgpt-imagegen'}
    if config.get('provider') not in accepted or not isinstance(preferred, dict):
        raise ValueError('invalid image source manifest')
    report = {'primary': [], 'fallback': [],
              'mode': 'openai-required' if strict else 'codex-first-original-fallback'}
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
                # «vertical» قد تصف جسماً داخل صورة أفقية (مثل جذع شجرة)،
                # فلا تُحوِّل اتجاه الصورة إلا صيغة أبعاد صريحة.
                vertical = '9:16' in item['prompt']
                expected_ratio = 9 / 16 if vertical else 16 / 9
                if min(width, height) < 576 or max(width, height) < 1024 or abs(width / height - expected_ratio) > .02:
                    raise ValueError('size-or-aspect-ratio')
                target = root / 'img' / (ident + '.jpg')
                # نسخة مشتقة؛ المصدر يبقى بلا مساس. لا ندعي أن التكبير يزيد التفاصيل.
                target_size = (1080, 1920) if vertical else (1920, 1080)
                image.convert('RGB').resize(target_size, Image.Resampling.LANCZOS).save(
                    target.with_suffix('.tmp'), format='JPEG', quality=94, subsampling=0)
                target.with_suffix('.tmp').replace(target)
            report['primary'].append({'id': ident, 'native_dimensions': [width, height],
                                      'sha256': entry['sha256']})
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            # لا نطبع مساراً خاصاً أو وصف الصورة في سجلات المستودع العام.
            report['fallback'].append({'id': ident, 'reason': type(exc).__name__})
    (root / 'image_source_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if strict and report['fallback'] and not exception:
        raise RuntimeError('صور OpenAI ناقصة أو مرفوضة؛ المسار البديل مقفل')
    if strict and report['fallback']:
        report['mode'] = 'openai-first-documented-original-fallback'
        (root / 'image_source_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    report = import_primary(sys.argv[1])
    print('primary=%d fallback=%d mode=%s' % (len(report['primary']), len(report['fallback']), report['mode']))
