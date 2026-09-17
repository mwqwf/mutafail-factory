"""حارس اكتمال الفحص السمعي والتحكيم الموثّق، لا شهادة عصمة لغوية."""
import hashlib
import json
from pathlib import Path
import sys


def audit(project):
    project = Path(project)
    blocks = json.loads((project / 'blocks.json').read_text(encoding='utf-8'))
    if not blocks:
        return ['empty-blocks']
    results = {}
    reviews = {}
    for review_file in sorted(project.glob('listen_reviews*.json')):
        for key, value in json.loads(review_file.read_text(encoding='utf-8')).items():
            if key in reviews:
                raise ValueError('duplicate-review: ' + key)
            reviews[key] = value
    for file in sorted(project.glob('listen_results*.json')):
        data = json.loads(file.read_text(encoding='utf-8'))
        for key, value in data.items():
            if key in results:
                raise ValueError('duplicate-result: ' + key)
            results[key] = value
    errors = []
    seen = set()
    for block in blocks:
        ident = block['id']
        if ident in seen:
            errors.append(ident + ': duplicate-block')
        seen.add(ident)
        if not isinstance(ident, str) or Path(ident).name != ident or '/' in ident or '\\' in ident:
            raise ValueError('invalid block id')
        audio = project / 'audio' / (ident + '.wav')
        if not audio.is_file():
            errors.append(ident + ': missing-audio')
            continue
        digest = hashlib.sha256(block['text'].encode('utf-8') + b'\0' + audio.read_bytes()).hexdigest()
        result = results.get(ident)
        review = reviews.get(ident, {})
        review_kind = review.get('review_kind')
        honest_reviewer = (review_kind == 'human' or
                           (review_kind == 'automated_independent' and
                            str(review.get('reviewer', '')).startswith('automated-independent-review:')))
        adjudicated = (isinstance(result, dict) and result.get('ok') is False
                       and isinstance(review, dict) and review.get('decision') == 'false_positive'
                       and review.get('input_sha256') == digest
                       and isinstance(review.get('reason'), str) and bool(review['reason'].strip())
                       and isinstance(review.get('reviewer'), str) and bool(review['reviewer'].strip())
                       and honest_reviewer)
        if not isinstance(result, dict) or (result.get('ok') is not True and not adjudicated):
            errors.append(ident + ': unchecked-or-flagged')
        elif result.get('input_sha256') != digest:
            errors.append(ident + ': stale-result')
    return errors


if __name__ == '__main__':
    try:
        errors = audit(sys.argv[1])
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print('FAIL: malformed or missing audit inputs (' + type(exc).__name__ + ')')
        raise SystemExit(1)
    print('PASS: complete, current listening results' if not errors else '\n'.join(errors))
    raise SystemExit(bool(errors))
