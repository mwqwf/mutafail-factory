"""فحص الصيغ الإنشائية في كل النصوص الموجّهة للمشاهد، دون تعديل الاقتباسات."""
import json
from pathlib import Path
import re
import sys
from humanlint import _norm

BANNED = ('في عالم مليء', 'دعونا نغوص', 'رحلة مذهلة', 'رحلة عبر الزمن',
          'منذ فجر التاريخ', 'وخلاصة القول', 'وفي الختام', 'في هذا الفيديو سنتعرف')


def audit(root):
    root = Path(root)
    texts = []
    for line in (root / 'script.md').read_text(encoding='utf-8').splitlines():
        match = re.match(r'^((?:d|m|r)_\d+)\|\w\|(.+)$', line)
        if match:
            texts.append((match[1], match[2]))
    pub = json.loads((root / 'publish.json').read_text(encoding='utf-8'))
    for section, values in [('film', [pub.get('film', {})]), ('reels', pub.get('reels', [])),
                            ('thumbs', pub.get('thumbs', []))]:
        for index, obj in enumerate(values):
            for key in ('title', 'description', 'l1', 'l2', 'badge'):
                if isinstance(obj.get(key), str):
                    texts.append((f'{section}.{index}.{key}', obj[key]))
    problems = []
    for location, text in texts:
        normalized = _norm(text)
        for phrase in BANNED:
            if _norm(phrase) in normalized:
                problems.append(f'صيغة إنشائية في {location}: «{phrase}»')
    return problems


if __name__ == '__main__':
    problems = audit(sys.argv[1])
    print('\n'.join(problems) if problems else '✅ فحص الإنشاء في السرد والنشر والمصغّرات والشورتين')
    raise SystemExit(bool(problems))
