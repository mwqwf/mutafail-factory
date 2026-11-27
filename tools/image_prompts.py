# -*- coding: utf-8 -*-
"""معيار أوامر صور جروك (GenerateImage) — أمر المالك 2026-11-27: «الصور بأعلى احترافية ممكنة».

التوليد نفسه يجريه البوت بأداته؛ هذه الأداة تبني الأمر وتفحصه قبله، وتفحص الصورة بعده:
  • «دليل أسلوب» واحد لكلّ فيلم (`<proj>/style_bible.json`) يثبّت اللون والضوء والعدسة والحبيبة وتفاصيل العصر، فتبدو الصور
    كأنها من فيلمٍ واحد لا من عشرين مولِّداً.
  • قائمة لقطات لكلّ كتلة (`<proj>/shotlist.json`): الحجم، والزاوية، والموضوع، والفعل، والشعور، والتكوين.
  • `compose` يركّب الأمر النهائيّ بترتيبٍ ثابت: الموضوع ⟵ التكوين ⟵ العدسة ⟵ الضوء ⟵ العصر ⟵ الأسلوب ⟵ الموانع ⟵ الجملة الواقية.
  • `lint` يرفض: المحظورات (guard.BANNED_IMG)، إنساناً بلا إخفاء وجه، تصوير نبيّ، صليباً، نصّاً قرآنياً، دماً، مفارقات العصر
    (قبّة، مئذنة، ركاب، سيف معقوف، بارود…)، ونقص أيّ قسم أو الجملة الواقية.
  • `image_gate` بعد التوليد: الدقّة والنسبة، والحدّة، والتعرّض، والاتّساق مع لوحة الفيلم، ومراجعة يدوية إلزامية
    (`<proj>/image_review.json`: اليدان، السلاح، الوجوه، النساء، الصلبان، الكتابة، العصر، التشوّه) — والمرفوض يُعاد توليده
    حتى ثلاث مرّات، ثم تُغيَّر اللقطة نفسها (حجمها أو زاويتها أو موضوعها) لا يُقبل الأقلّ.

    python3 tools/image_prompts.py prompts <proj>          # يطبع الأوامر النهائية ويكتب prompts.json (بعد lint)
    python3 tools/image_prompts.py gate    <proj> <img>... # بوّابة الصور بعد التوليد
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guard import BANNED_IMG, REQUIRED_TAIL  # noqa: E402

DEFAULT_BIBLE = {
    'look': 'cinematic historical documentary still, photoreal, muted earth palette of ochre, sand and deep umber with one '
            'restrained accent colour, soft film grain, gentle halation on highlights, high dynamic range, crisp micro-detail',
    'lens': {'wide': '24mm anamorphic lens, f/5.6, deep focus', 'medium': '35mm lens, f/2.8, shallow depth of field',
             'close': '85mm lens, f/2, creamy background separation', 'detail': '100mm macro lens, f/4'},
    'light': {'day': 'hard low-angle desert sun, long shadows, warm key and cool sky fill',
              'golden': 'golden-hour backlight, rim light on silhouettes, dust glowing in the air',
              'dawn': 'blue pre-dawn light, faint warm horizon line, stars fading',
              'night': 'moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks',
              'interior': 'single shaft of daylight through a doorway, volumetric dust, dark falloff'},
    'era': '7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, '
           'Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather '
           'scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), '
           'clay oil lamps, rolled parchment',
    'figures': 'all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; '
               'adult men only',
    'avoid': 'no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, '
             'no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour',
}
COMPOSITION = {
    'wide': 'wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax',
    'medium': 'medium shot, subject on a third line, layered foreground, midground and background for depth',
    'close': 'close shot on hands, objects or a silhouette, clean negative space on one side of the frame',
    'detail': 'insert detail shot, tactile texture, shallow focus',
}
ANGLES = {'low': 'low camera angle looking up, heroic scale', 'high': 'high angle looking down, sense of vulnerability',
          'eye': 'eye-level camera', 'over': 'over-the-shoulder from behind the figure', 'aerial': 'high aerial view'}
HUMAN = re.compile(r'\b(man|men|rider|riders|warrior|warriors|horseman|horsemen|figure|figures|soldier|soldiers|people|crowd|'
                   r'army|ranks|companion|companions|king|messenger|guard|guards|worshippers|prayer rows)\b', re.I)
HIDDEN = re.compile(r'\b(from behind|silhouett\w*|seen from the back|back view|faces? hidden|in shadow|at distance|distant|'
                    r'litham|veiled|faceless|no visible faces)\b', re.I)
FORBID = {
    'نبيّ': r'\b(prophet|muhammad|mohammed|messenger of god|jesus|moses|angel|halo)\b',
    'صليب': r'\b(cross|crosses|crucifix)\b(?![- ]?(?:roads?|ing|ed|wise|hatch))',
    'نصّ قرآنيّ': r'\b(quran|koran|qur\'an|verse|ayah|surah|calligraph\w*)\b',
    'دم': r'\b(blood\w*|gore|corpse|corpses|severed|decapitat\w*|wound\w*)\b',
    'وجه ظاهر': r'\b(portrait|face of|his face|faces of|facial|eyes|smil\w*|expression|looking at (?:the )?camera)\b',
    'مفارقة عصر': r'\b(dome|domes|minaret\w*|stirrups?|scimitar\w*|gun\w*|cannon\w*|musket\w*|gunpowder|glass windows?|'
                  r'paper books?|printed)\b',
}
NEG_EXEMPT = re.compile(r'\bno [^,.;]+', re.I)


def bible(proj: str | None) -> dict:
    b = json.loads(json.dumps(DEFAULT_BIBLE))
    p = os.path.join(proj, 'style_bible.json') if proj else ''
    if p and os.path.exists(p):
        with open(p, encoding='utf-8') as fh:
            over = json.load(fh)
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(b.get(k), dict):
                b[k].update(v)
            else:
                b[k] = v
    return b


def compose(shot: dict, bb: dict) -> str:
    size = shot.get('size', 'wide')
    parts = [shot['subject'].rstrip('. '),
             COMPOSITION.get(size, COMPOSITION['wide']),
             ANGLES.get(shot.get('angle', 'eye'), shot.get('angle', '')),
             bb['lens'].get(size, bb['lens']['wide']),
             bb['light'].get(shot.get('light', 'day'), shot.get('light', '')),
             'period details: ' + (shot.get('era') or bb['era']),
             bb['look'], bb['figures'], bb['avoid']]
    return '. '.join(p for p in parts if p) + '. ' + REQUIRED_TAIL


def lint(prompt: str, kind: str = 'film') -> list[str]:
    errs = []
    positive = NEG_EXEMPT.sub(' ', prompt)          # «no domes» مانعٌ لا وصف
    for label, pat in BANNED_IMG.items():
        if re.search(pat, positive, re.I):
            errs.append('محظور (%s): «%s»' % (label, re.search(pat, positive, re.I).group(0)))
    for label, pat in FORBID.items():
        m = re.search(pat, positive, re.I)
        if m:
            errs.append('محظور (%s): «%s»' % (label, m.group(0)))
    if HUMAN.search(positive) and not HIDDEN.search(prompt):
        errs.append('إنسانٌ في الصورة بلا إخفاء وجه (from behind / silhouette / faces hidden)')
    if REQUIRED_TAIL.lower() not in prompt.lower():
        errs.append('الجملة الواقية ناقصة: ' + REQUIRED_TAIL)
    for need, rx in (('العدسة', r'\d+mm'), ('الضوء', r'\blight|sun|lamp|firelight|moon'), ('العصر', r'period details|7th-century'),
                     ('التكوين', r'shot\b')):
        if not re.search(rx, prompt, re.I):
            errs.append('قسم ناقص في الأمر: ' + need)
    return errs


def prompts(proj: str) -> tuple[list, list]:
    bb = bible(proj)
    shots = json.load(open(os.path.join(proj, 'shotlist.json'), encoding='utf-8'))
    out, errs = [], []
    for s in shots:
        p = s.get('prompt') or compose(s, bb)
        for e in lint(p):
            errs.append('%s: %s' % (s['id'], e))
        out.append({'id': s['id'], 'blocks': s.get('blocks'), 'prompt': p})
    return out, errs


# ── بوّابة الصور بعد التوليد ─────────────────────────────────────────────────────────────────────
MIN_W, MIN_H = 1280, 720            # أدنى دقّة مقبولة لصورةٍ تدخل المونتاج (تُرفع إلى 1920 بتكبير جيّد لا أقلّ)
ASPECT = 16 / 9
SHARP_MIN = 60.0                    # تباين لابلاس على نسخة 960 — أقلّ منه ضبابية/لطخ
HI_MAX = 0.03                       # حصّة البكسلات المحترقة (≥ 253)
LO_MAX = 0.30                       # حصّة الأسود المطموس (≤ 2) — الظلال الصامتة مقصودة، فالحدّ واسع (معايرة أجنادين)
PALETTE_Z = 3.0                     # بُعد الصورة عن وسيط لوحة الفيلم (بوحدات MAD)
REVIEW_KEYS = ('hands', 'weapons', 'faces_hidden', 'no_women', 'no_crosses', 'no_text', 'era', 'artifacts')
MAX_ATTEMPTS = 3


def stats(path: str) -> dict:
    import cv2
    im = cv2.imread(path)
    if im is None:
        return {'error': 'تعذّرت القراءة'}
    h, w = im.shape[:2]
    small = cv2.resize(im, (960, int(960 * h / w)), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    return {'w': w, 'h': h, 'sharp': float(cv2.Laplacian(g, cv2.CV_64F).var()),
            'hi': float((g >= 253).mean()), 'lo': float((g <= 2).mean()), 'lab': [float(x) for x in lab.mean(0)]}


def image_gate(paths: list[str], review: dict | None = None) -> list[str]:
    errs, st = [], {}
    for p in paths:
        s = st[p] = stats(p)
        n = os.path.basename(p)
        if 'error' in s:
            errs.append('%s: %s' % (n, s['error'])); continue
        if s['w'] < MIN_W or s['h'] < MIN_H:
            errs.append('%s: دقّة %dx%d أقلّ من %dx%d' % (n, s['w'], s['h'], MIN_W, MIN_H))
        if abs(s['w'] / s['h'] - ASPECT) > 0.03:
            errs.append('%s: النسبة %.2f ليست 16:9' % (n, s['w'] / s['h']))
        if s['sharp'] < SHARP_MIN:
            errs.append('%s: ضبابية (لابلاس %.0f < %.0f)' % (n, s['sharp'], SHARP_MIN))
        if s['hi'] > HI_MAX:
            errs.append('%s: إضاءة محترقة %.0f٪' % (n, 100 * s['hi']))
        if s['lo'] > LO_MAX:
            errs.append('%s: سوادٌ مطموس %.0f٪' % (n, 100 * s['lo']))
    ok = [p for p in paths if 'lab' in st[p]]
    if len(ok) >= 5:
        lab = np.array([st[p]['lab'] for p in ok])
        med = np.median(lab, 0); mad = np.median(np.abs(lab - med), 0) + 1.5
        for p, row in zip(ok, lab):
            z = float(np.max(np.abs(row[1:] - med[1:]) / mad[1:]))
            if z > PALETTE_Z:
                errs.append('%s: خارج لوحة الفيلم (بُعد %.1f) — أعِد بدليل الأسلوب أو صحّح اللون' % (os.path.basename(p), z))
    if review is not None:
        for p in paths:
            r = review.get(os.path.basename(p))
            if not r:
                errs.append('%s: بلا مراجعة يدوية (image_review.json) — لا تدخل المونتاج' % os.path.basename(p)); continue
            bad = [k for k in REVIEW_KEYS if r.get(k) != 'pass']
            if bad:
                tries = int(r.get('attempts', 1))
                act = 'أعِد التوليد' if tries < MAX_ATTEMPTS else 'غيّر اللقطة نفسها (حجم/زاوية/موضوع) — استُنفدت المحاولات'
                errs.append('%s: رُفضت (%s) — %s' % (os.path.basename(p), ' '.join(bad), act))
    return errs


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2:
        print(__doc__); return 2
    if a[0] == 'prompts':
        out, errs = prompts(a[1])
        if not errs:
            json.dump(out, open(os.path.join(a[1], 'prompts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            for o in out:
                print('%s\t%s' % (o['id'], o['prompt']))
    else:
        rp = os.path.join(a[1], 'image_review.json')
        errs = image_gate(a[2:], json.load(open(rp, encoding='utf-8')) if os.path.exists(rp) else {})
    for e in errs:
        print('⛔', e)
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
