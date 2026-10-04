#!/usr/bin/env python3
"""🃏 بطاقات الكتابة يصنعها كوديكس — أمر المالك 2026-10-04: «الصور ممنوعة عليك اتركها لكوديكس… حتى البطاقات المكتوبة».

كلُّ نصٍّ مصمَّمٍ يظهر على الشاشة (ضربةٌ مكتوبة، بطاقةُ اسم، ختمٌ زمنيّ، قولٌ مأثور، سطرُ رسالة، شطرُ بيت، بندُ قائمة،
عنوانُ فصل، تسميةٌ على خريطة، عنوانُ الريلز وخطّافه وسؤاله الأخير) صار **بنداً في طابور كوديكس**: صورة PNG بخلفيةٍ شفّافة
فيها النصّ وحده بتصميمٍ موحّد. وClaude لا يرسم حرفاً: `tools/kinetic.py` و`tools/mkreel_film.py` يقصّان البطاقة ويحجّمانها
ويحرّكانها فقط (كشفٌ من اليمين متزامنٌ مع النطق «كأنّ الكتابة تُكتب أثناء الإلقاء»، وتكبيرٌ، وانزلاق).

المفتاح حتميّ من النوع والنصّ (نصٌّ واحد ⇒ بطاقةٌ واحدة تُستعمل حيث تكرّر، وتغيّر النصّ ⇒ بطاقةٌ جديدة).
والأسطر تُقسَم هنا من كلمات الكتلة المنطوقة نفسها، فيُعرف زمن كلّ سطرٍ من صوته.

    python3 tools/cards.py <مجلد_الفيلم> <مستودع_الصور> <المجلد>   # يكتب film/cards.json ويُلحق الناقص بطابور كوديكس
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HARAKAT = re.compile('[ً-ْٰـ]')
LINE_WORDS = {'center': 5, 'lower': 7, 'quote': 6, 'letter': 6}
WIDE, TALL = [1536, 384], [1536, 512]

COMMON = ('Output a PNG with a REAL transparent background (alpha channel): no checkerboard pattern, no backdrop, no frame '
          'unless one is described. Write the Arabic text EXACTLY as given, letter by letter, correctly joined, right-to-left, '
          'without diacritics, adding no other words, letters, numbers, logos or watermark. The text must be crisp, fully legible, '
          'centred, and must not touch the edges.')
DISPLAY = 'a bold modern Kufi-style Arabic typeface (like Noto Kufi Arabic Black)'
NASKH = 'elegant classical Arabic Naskh calligraphy (like Amiri)'
GOLDC = 'golden yellow (#F7C74A)'
STYLE = {
    'slam': f'Huge cinematic Arabic display lettering in {DISPLAY}, {GOLDC} letters with a thick near-black outline and a soft dark drop shadow',
    'slam_sub': 'below it, a second line much smaller in bold white with a thin dark outline',
    'name': ('A sleek documentary lower-third name plate: a dark charcoal, slightly translucent rounded rectangle with a vertical gold bar '
             f'along its right edge; inside it, right-aligned, the first line in bold white {DISPLAY}'),
    'name_sub': 'and the second line smaller in golden yellow; everything outside the plate fully transparent',
    'date': ('A small historical date stamp: a dark charcoal, slightly translucent rounded rectangle; inside it, right-aligned, '
             'the first line in bold white Kufi-style Arabic'),
    'date_sub': 'and the second line smaller in golden yellow; everything outside the plate fully transparent',
    'title': f'A large documentary title in {DISPLAY}, warm gold (#F4D68C) with a soft dark shadow',
    'title_sub': 'below it, a smaller second line in white',
    'quote': f'One line of {NASKH} in warm cream (#F5ECD6) with a soft dark shadow',
    'letter': 'One line of Arabic Naskh handwriting in dark brown ink, as if written with a reed pen; no paper at all, only the ink on transparency',
    'center': f'One line of large bold white Arabic display text in {DISPLAY} with a thin dark outline and a soft shadow',
    'lower': f'One line of bold white Arabic subtitle text in {DISPLAY} with a thin dark outline and a soft shadow',
    'poem': f'One hemistich of classical Arabic poetry in {GOLDC} Thuluth-Naskh calligraphy with a soft dark shadow',
    'item': ('A dark charcoal, slightly translucent rounded strip; inside it, right-aligned, a small gold dot followed by bold white '
             'Kufi-style Arabic text; everything outside the strip fully transparent'),
    'src': f'A short source line in small bold {GOLDC} Kufi-style Arabic with a thin dark outline',
    'label': ('A dark charcoal, slightly translucent pill-shaped tag; inside it a small gold dot on the right followed by bold white '
              'Kufi-style Arabic text; everything outside the tag fully transparent'),
    'clabel': f'A short label in bold {GOLDC} Kufi-style Arabic with a thin dark outline',
    'chapter': f'A chapter title in {GOLDC} Kufi-style Arabic display lettering with a thin ornamental gold line underneath it',
    'rtitle': f'A headline for the top of a vertical video, up to three centred lines in bold white {DISPLAY} with a thick black outline; the last line in golden yellow',
    'rhook': f'A shocking hook headline for the first second of a vertical video: bold white {DISPLAY} with a thick black outline on a bright red rounded band, up to three centred lines',
    'rend': f'A cliff-hanger question for the end of a vertical video: up to three centred lines in bold {GOLDC} {DISPLAY} with a thick dark outline',
    'rcta1': f'Bold white {DISPLAY} text on a bright red rounded band',
    'rcta2': f'Bold white {DISPLAY} text with a thick black outline',
}
PARCHMENT = ('An empty sheet of aged parchment seen straight on, warm beige with darker brown edges and soft paper texture, '
             'slightly irregular torn borders, completely blank: no writing, no letters, no marks; the area outside the sheet fully transparent. '
             'Output a PNG with a real transparent background.')


def plain(t: str) -> str:
    return HARAKAT.sub('', t or '')


def bare(w: str) -> str:
    return plain(w).strip('…،,.؟?!:؛«»"“”()-— ').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')


def words_of(text: str) -> list[str]:
    """كلمات الكتلة المعروضة بترتيب نطقها — هي نفسها كلمات أزمنة kinetic.block_word_times."""
    import kinetic
    return [w.rstrip('.،,:؛') for w, p in kinetic.tokens(text) if not p]


def breaks_of(text: str, offset: int = 0) -> set[int]:
    """أرقام الكلمات التي يعقبها وقف (… ، . ؟ !) — مواضع كسر السطر الطبيعية كما يُنطق."""
    import kinetic
    br, i = set(), offset - 1
    for _, p in kinetic.tokens(text):
        if p:
            if i >= offset:
                br.add(i)
        else:
            i += 1
    if i >= offset:
        br.add(i)                                  # آخر الكتلة وقفٌ أيضاً
    return br


def shot_words(s: dict, texts: dict) -> tuple[list[str], set[int]]:
    out: list[str] = []
    br: set[int] = set()
    for bid in s.get('blocks', []):
        if bid in texts:
            br |= breaks_of(texts[bid], len(out))
            out += words_of(texts[bid])
    return out, br


def lines_of(words: list[str], maxw: int, breaks: set[int] | None = None) -> list[list[int]]:
    """أسطرٌ تُكسر عند الوقف (كما يُنطق)، والعبارةُ الأطول من maxw تُقسَم أقساماً متوازنة، والكلمةُ اليتيمة تُضمّ إلى جارتها."""
    breaks = breaks or set()
    phrases: list[list[int]] = []
    cur: list[int] = []
    for i in range(len(words)):
        cur.append(i)
        if i in breaks:
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    chunks: list[list[int]] = []
    for ph in phrases:
        k = max(1, math.ceil(len(ph) / maxw))
        size = math.ceil(len(ph) / k)
        chunks += [ph[j:j + size] for j in range(0, len(ph), size)]
    lines: list[list[int]] = []
    for ch in chunks:
        if lines and (len(ch) == 1 or len(lines[-1]) == 1) and len(lines[-1]) + len(ch) <= maxw:
            lines[-1] += ch
        else:
            lines.append(ch)
    return lines


def key(kind: str, payload) -> str:
    h = hashlib.sha1(json.dumps([kind, payload], ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:10]
    return f'{kind}_{h}'


def _spec(kind, role, text, size, sub=None, hl=None, **extra) -> dict:
    payload = {'t': text, 's': sub, 'h': sorted(hl) if hl else None}
    return {'key': key(kind, payload), 'kind': kind, 'role': role, 'text': text, 'sub': sub,
            'hl': hl or [], 'size': size, **extra}


def shot_cards(s: dict, texts: dict, chapter: str | None = None) -> list[dict]:
    """بطاقات اللقطة بترتيب ظهورها. لكلّ سطرٍ منطوق idx = أرقام كلماته في كلمات اللقطة (للتوقيت)."""
    out: list[dict] = []
    kt = s.get('kt')
    if kt:
        style = kt.get('style', 'lower')
        txt = kt.get('text')
        if style == 'list':
            for it in (txt if isinstance(txt, list) else [txt or '']):
                out.append(_spec('item', 'item', plain(it), WIDE))
        elif style == 'poem':
            hs = txt if isinstance(txt, list) else [txt or '']
            for i, h in enumerate(hs[:2]):
                out.append(_spec('poem', 'line', plain(h), WIDE, half=i))
        else:
            spoken = not isinstance(txt, str)
            if spoken:
                words, br = shot_words(s, texts)
            else:
                words, br = words_of(txt), breaks_of(txt)
            hlb = {bare(h) for h in kt.get('hl', [])}
            for idx in lines_of(words, LINE_WORDS.get(style, 6), br):
                line = ' '.join(words[i] for i in idx)
                hl = [words[i] for i in idx if bare(words[i]) in hlb]
                out.append(_spec(style, 'line', line, WIDE, hl=hl, idx=idx, spoken=spoken))
            if style == 'letter':
                out.insert(0, {'key': 'letter_bg', 'kind': 'bg', 'role': 'bg', 'text': '', 'size': [1536, 1024]})
        if kt.get('src'):
            out.append(_spec('src', 'src', '— ' + plain(kt['src']), [1536, 256]))
    sl = s.get('slam')
    if sl:
        out.append(_spec('slam', 'slam', plain(sl['text']), TALL if sl.get('sub') else WIDE, sub=plain(sl.get('sub') or '') or None))
    nm = s.get('name')
    if nm:
        out.append(_spec('name', 'name', plain(nm['text']), WIDE, sub=plain(nm.get('sub') or '') or None))
    dt = s.get('date')
    if dt:
        out.append(_spec('date', 'date', plain(dt['text']), WIDE, sub=plain(dt.get('sub') or '') or None))
    for lb in s.get('labels') or []:
        out.append(_spec('label', 'label', plain(lb['text']), [1024, 256], x=lb['x'], y=lb['y'], word=lb.get('word')))
    for i, c in enumerate(s.get('cards') or []):
        out.append(_spec('clabel', 'clabel', plain(c['label']), [1024, 256], n=i))
    ti = s.get('title')
    if ti:
        out.append(_spec('title', 'title', plain(ti['text']), TALL if ti.get('sub') else WIDE, sub=plain(ti.get('sub') or '') or None))
    if chapter:
        out.append(_spec('chapter', 'chapter', plain(chapter), WIDE))
    return out


CTA1, CTA2 = 'الجواب في الفيلم الكامل', 'اكتب جوابك في التعليقات'   # التفاعل السريع (أمر المالك 2026-10-04) بدل «اشترك وفعّل الجرس»


def reel_cards(r: dict) -> dict[str, dict]:
    sq = [1024, 640]
    return {'title': _spec('rtitle', 'rtitle', plain(r['title']), sq),
            'hook': _spec('rhook', 'rhook', plain(r.get('hook') or r['title']), sq),
            'end': _spec('rend', 'rend', plain(r.get('end_q') or 'ماذا حدث بعد ذلك؟'), sq),
            'cta1': _spec('rcta1', 'rcta1', CTA1, [1024, 256]),
            'cta2': _spec('rcta2', 'rcta2', CTA2, [1024, 256])}


def prompt(c: dict) -> str:
    if c['kind'] == 'bg':
        return PARCHMENT
    k = c['kind'] if c['kind'] in STYLE else c['role']
    p = STYLE[k] + ': «%s»' % c['text']
    if c.get('sub'):
        p += '; ' + STYLE.get(k + '_sub', 'below it a smaller second line in white') + ': «%s»' % c['sub']
    if c.get('hl'):
        p += '. The word(s) %s in %s, all the other words as described' % ('، '.join('«%s»' % h for h in c['hl']), GOLDC)
    return p + '. ' + COMMON


def manifest(film: Path) -> dict[str, dict]:
    shots = json.loads((film / 'shots.json').read_text(encoding='utf-8'))
    texts = {b['id']: b['text'] for b in json.loads((film / 'blocks.json').read_text(encoding='utf-8'))}
    secs = json.loads((film / 'sections.json').read_text(encoding='utf-8')) if (film / 'sections.json').exists() else []
    first = {x['id']: x['title'] for x in secs[1:]}
    man: dict[str, dict] = {}
    for s in shots:
        ch = None
        if s.get('blocks') and s['blocks'][0] in first:
            ch = first.pop(s['blocks'][0])
        for c in shot_cards(s, texts, ch):
            man.setdefault(c['key'], {k: v for k, v in c.items() if k not in ('idx', 'x', 'y', 'word', 'n', 'half', 'spoken')})
    if (film / 'reels.json').exists():
        for r in json.loads((film / 'reels.json').read_text(encoding='utf-8')):
            for c in reel_cards(r).values():
                man.setdefault(c['key'], c)
    for c in man.values():
        c['file'] = 'cards/%s.png' % c['key']
        c['prompt'] = prompt(c)
    return man


CARD_RULE = ('بنود cards/: بطاقاتُ كتابةٍ مطلوبٌ نصُّها صراحةً (يغلب منعَ الكتابة في الصور). PNG بخلفيةٍ شفّافة حقيقية (قناة ألفا) لا رقعة شطرنج، '
             'والنصّ العربيّ حرفياً كما بين «» دون زيادةٍ أو نقصٍ ولا تشكيل، والحروف متّصلة صحيحة من اليمين إلى اليسار، '
             'وتصميمٌ موحّد بين البطاقات من النوع نفسه. افحص كلّ بطاقةٍ بعينك: كلمةٌ ناقصة أو حرفٌ مقلوب أو منفصل ⇒ أعدها.')


def queue(media: Path, folder: str, man: dict[str, dict]) -> int:
    jf = media / folder / 'codex_job.json'
    job = json.loads(jf.read_text(encoding='utf-8'))
    have = {it['file'] for it in job['items']}
    add = [{'file': c['file'], 'prompt': c['prompt'], 'size': c['size']} for c in man.values() if c['file'] not in have]
    if add:
        job['items'].extend(add)                     # في الآخر: لا يتغيّر تقسيم الأجزاء الجارية
        job['status'] = 'pending'
    if CARD_RULE not in job.get('rules', ''):
        job['rules'] = (job.get('rules', '').rstrip() + '\n' + CARD_RULE).strip()
    jf.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding='utf-8')
    return len(add)


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    film, media, folder = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    man = manifest(film)
    (film / 'cards.json').write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    n = queue(media, folder, man)
    kinds: dict[str, int] = {}
    for c in man.values():
        kinds[c['kind']] = kinds.get(c['kind'], 0) + 1
    print('البطاقات:', len(man), kinds, '· أُلحق بالطابور:', n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
