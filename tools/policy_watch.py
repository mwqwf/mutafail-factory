# -*- coding: utf-8 -*-
"""لقطاتٌ من صفحات سياسات يوتيوب الرسمية للمقارنة الدورية (policy-watch.yml). بلا مفاتيح؛ نصٌّ مجرّد من الوسوم.
يكتب ops/policy/snapshots/<اسم>.txt، وإن تغيّرت لقطةٌ كتب ops/policy/CHANGED.md بالفروق المختصرة ليقرأها الفاحص الشهريّ."""
import difflib, html, io, os, re, sys, urllib.request, datetime as dt

PAGES = {
    'community-guidelines': 'https://support.google.com/youtube/answer/9288567?hl=en',
    'violent-graphic': 'https://support.google.com/youtube/answer/2802008?hl=en',
    'harmful-dangerous': 'https://support.google.com/youtube/answer/2801964?hl=en',
    'hate-speech': 'https://support.google.com/youtube/answer/2801939?hl=en',
    'harassment': 'https://support.google.com/youtube/answer/2802268?hl=en',
    'child-safety': 'https://support.google.com/youtube/answer/2801999?hl=en',
    'nudity-sexual': 'https://support.google.com/youtube/answer/2802002?hl=en',
    'suicide-selfharm': 'https://support.google.com/youtube/answer/2802245?hl=en',
    'vulgar-language': 'https://support.google.com/youtube/answer/10072685?hl=en',
    'thumbnails': 'https://support.google.com/youtube/answer/9229980?hl=en',
    'misinformation': 'https://support.google.com/youtube/answer/10834785?hl=en',
    'spam-deceptive': 'https://support.google.com/youtube/answer/2801973?hl=en',
    'edsa': 'https://support.google.com/youtube/answer/6345162?hl=en',
    'policy-updates': 'https://support.google.com/youtube/answer/10008196?hl=en',
    'advertiser-friendly': 'https://support.google.com/youtube/answer/6162278?hl=en',
}
OUT = os.path.join('ops', 'policy', 'snapshots')


def text_of(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (policy-watch; mutafail-factory)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        h = r.read().decode('utf-8', 'ignore')
    h = re.sub(r'(?is)<(script|style|noscript|header|footer|nav)[^>]*>.*?</\1>', ' ', h)
    m = re.search(r'(?is)<article.*?</article>|<main.*?</main>', h)
    h = m.group(0) if m else h
    t = html.unescape(re.sub(r'(?s)<[^>]+>', '\n', h))
    lines = [re.sub(r'\s+', ' ', x).strip() for x in t.split('\n')]
    return '\n'.join(x for x in lines if len(x) > 2)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    changes = []
    for name, url in PAGES.items():
        try:
            new = text_of(url)
        except Exception as e:
            print('⚠️ تعذّر %s: %s' % (name, str(e)[:120])); continue
        if len(new) < 500:
            print('⚠️ %s: صفحة قصيرة (%d) — تُهمل' % (name, len(new))); continue
        p = os.path.join(OUT, name + '.txt')
        old = io.open(p, encoding='utf-8').read() if os.path.exists(p) else ''
        if old and old != new:
            diff = [l for l in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('+++', '---')]
            changes.append((name, url, diff[:80]))
            print('✱ تغيّر %s: %d سطراً' % (name, len(diff)))
        elif not old:
            print('＋ لقطة أولى %s' % name)
        else:
            print('= %s' % name)
        io.open(p, 'w', encoding='utf-8').write(new)
    if changes:
        with io.open(os.path.join('ops', 'policy', 'CHANGED.md'), 'w', encoding='utf-8') as f:
            f.write('# تغيّرت صفحات سياسات يوتيوب — %s\n\nتُراجَع ops/policy/README.md وlexicon.json وPROMPT في tools/policy_gate.py، ثم يُحذف هذا الملفّ.\n\n' % dt.date.today())
            for name, url, diff in changes:
                f.write('## %s\n%s\n\n```diff\n%s\n```\n\n' % (name, url, '\n'.join(diff)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
