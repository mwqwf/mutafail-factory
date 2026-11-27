# -*- coding: utf-8 -*-
"""اشتقاق المؤثّر الصوتيّ من مضمون اللقطة آلياً — أمر المالك 2026-10-14.

كانت جداول لقطات مؤتة واليمامة (المولَّدة من `_src/mk_codex.py`) تخرج بلا حقل `sfx`، فلم تدخل الفيلمَ إلا الرياح
وصوتُ Kling في ثلاثة مقاطع. هنا يُشتقّ المؤثّر من كلمات نصّ الكتلة العربيّ ومن وصف الحركة الإنجليزيّ (`move`)،
ثمّ من فصل اللقطة (`phase`) إن لم تدلّ الكلمات على شيء. ⛔ لا موسيقى ولا آلات: الطبول والأبواق الحربية النغمية وأيّ فراش لحني ممنوعة.
أمر المالك 2026-11-22: طبقة المحيط والمؤثّرات إلزامية في كل فيلم حيث يناسب المشهد.
الأصناف كلّها أصواتٌ طبيعية في `assets/sfx/<صنف>_*.ogg` (CC0).

يستعمله `mont_hybrid.py` للقطةٍ بلا `sfx`، و`thrill_gate.py` ليقيس تنوّع مؤثّرات المعركة (≥ 60٪ بغير «wind»)،
ومولِّدات الجداول (`mk_codex.py`) لتكتب `sfx` من البداية.

    python3 tools/sfx_auto.py <مجلد_المشروع>     # يطبع المؤثّر المشتقّ لكلّ لقطة، ولا يكتب شيئاً
"""
from __future__ import annotations

import json
import os
import re
import sys

HARAKAT = re.compile(r"[ً-ْٰـ]")
# الأصناف المتاحة في المكتبة (assets/sfx) — الموجودة من Freesound CC0؛ وما لا ملفّ له بعد يقع على بديله في FALLBACK
CATEGORIES = ('swords', 'armor', 'bowstring', 'hooves', 'footsteps', 'breath', 'shout', 'horses', 'arrows', 'battle', 'crowd',
              'fire', 'night', 'marching', 'elephants', 'wind')
# الترتيب مهمّ: الأخصّ أوّلاً (صليل قبل معركة عامّة)، والكلمات العربيّة بلا تشكيل، والإنجليزيّة من وصف الحركة
RULES: list[tuple[str, re.Pattern, re.Pattern]] = [
    ('swords', re.compile(r"(صليل|سيف|سيوف|السيوف|انكسر|تكسر|تكسّر|انقطع|نصل|حدّ |ضرب|يضرب|طعن|رمح|رماح|الرماح)"),
     re.compile(r"(sword|blade|steel|snap|shatter|spear|slash|clash|stab|thrust)")),
    ('armor', re.compile(r"(درع|دروع|زرد|ترس|تروس|التروس|خوذة|خوذ)"),
     re.compile(r"(shield|armou?r|mail|helmet|lamellar)")),
    ('bowstring', re.compile(r"(قوس|أقواس|وتر|سهم|سهام|السهام|نبل|نبال|رمى|رموا|رشق)"),
     re.compile(r"(bow\b|bowstring|arrow|archer|shoot|volley|loose)")),
    ('hooves', re.compile(r"(حوافر|حافر|غارة|أغار|انقض|انقضّ|اقتحم|عدا|عدوا|ركض)"),
     re.compile(r"(hooves|hoof|gallop|charge|charging|rider|riders|stampede)")),
    ('horses', re.compile(r"(خيل|الخيل|فرس|الفرس|فرسان|الفرسان|حصان|خيول|جواد|مهر|صهيل)"),
     re.compile(r"(horse|mare|stallion|cavalry|mount|neigh)")),
    ('elephants', re.compile(r"(فيل|فيلة|الفيلة|أفيال)"), re.compile(r"(elephant)")),
    ('fire', re.compile(r"(نار|النار|نيران|حريق|لهب|اشتعل|مشاعل|شعلة|يحترق|جمر)"),
     re.compile(r"(fire|flame|torch|burn|ember|blaze|smithy|anvil|spark)")),
    ('breath', re.compile(r"(لهث|يلهث|أنفاس|الأنفاس|نفس |تنفّس|تنفس|جريح|ينزف|يحتضر|يتلو)"),
     re.compile(r"(breath|panting|gasp|exhaust|wounded|dying|kneel|whisper|speaking to himself)")),
    ('shout', re.compile(r"(صاح|صرخ|صرخة|نادى|ينادي|هتف|زأر|صيحة|يصيح|ناداه)"),
     re.compile(r"(shout|shouts|cry|cries|yell|roar|calls out|bellow)")),
    ('crowd', re.compile(r"(الله أكبر|كبّروا|كبروا|تكبير|هتاف|جموع|الجموع|صفوف|الصفوف|جيش|الجيش|جيوش|الحشد|حشد|آلاف|ألف)"),
     re.compile(r"(army|ranks|crowd|host|thousands|men raise|raise their|assembl|council|gather)")),
    ('footsteps', re.compile(r"(قدم|أقدام|خطوات|خطوة|مشى|يمشي|مشي |وطء|يسير على)"),
     re.compile(r"(footstep|footsteps|boots|steps|walking)")),
    ('marching', re.compile(r"(مسير|المسير|زحف|يزحف|سار |ساروا|طريق|الطريق|رحل|الركب|قافلة)"),
     re.compile(r"(march|column|walk|road|leav|depart|withdraw|retreat|procession)")),
    ('night', re.compile(r"(ليل|الليل|ليلة|نجوم|النجوم|فجر|الفجر|سحر|ظلام|معسكر)"),
     re.compile(r"(night|stars|starry|campfire|camp at|dusk|dawn|tent)")),
    ('battle', re.compile(r"(معركة|المعركة|التحم|الالتحام|قتال|القتال|اشتبك|هجوم|حمل |حملوا|اقتتل|الميدان|صدام)"),
     re.compile(r"(battle|melee|fight|collide|crash|clash|combat|front line|dust explodes)")),
    ('wind', re.compile(r"(ريح|الريح|رياح|عاصفة|صحراء|الصحراء|غبار|سكون|صمت)"),
     re.compile(r"(wind|dust drifts|desert|silence|still|calm|lonely|empty)")),
]
# صنفٌ ليس له ملفّ في المكتبة بعد يقع على أقرب صنفٍ حقيقيّ موجود (لا يُسقط المؤثّر إلى الريح)
FALLBACK = {'swords': 'battle', 'armor': 'battle', 'bowstring': 'arrows', 'hooves': 'horses', 'footsteps': 'marching',
            'breath': 'wind', 'shout': 'crowd'}
PHASE_DEFAULT = {'battle': 'battle', 'buildup': 'crowd', 'setup': 'wind', 'aftermath': 'wind', None: 'wind'}


def files(sfx_dir: str, cat: str) -> list:
    """ملفّات الصنف، أو ملفّات بديله الأقرب إن لم يكن له ملفّ."""
    import glob
    for c in (cat, FALLBACK.get(cat)):
        got = sorted(glob.glob(os.path.join(sfx_dir, '%s_*.ogg' % c))) if c else []
        if got:
            return got
    return []


def resolved(sfx_dir: str, cat: str) -> str:
    f = files(sfx_dir, cat)
    return os.path.basename(f[0]).rsplit('_', 1)[0] if f else 'none'


def plain(t: str) -> str:
    return HARAKAT.sub('', t or '')


# ⛔ درس أجنادين (تدقيق 2026-11-27): كانت الكلمات تُطابَق جزءاً من كلمة، فـ«فيلم» و«فيلقي» أسمعتا فيلةً في معركةٍ
#    بلا فيلة، و«قليل/دليل» ليلاً، و«منارة/دينار» ناراً. ⇒ المطابقة على الكلمة كاملةً مع السوابق (و ف ب ل ك ال)
#    واللواحق الضميرية فقط.
_AR = '\u0621-\u064a'
_PRE = '(?:[وفبلك]?(?:ال|لل)?)'
_SUF = '(?:ه|ها|هم|هما|هن|ي|ك|كم|نا|ات|ون|ين|ان)?'


def _wordwise(rx: re.Pattern) -> re.Pattern:
    alts = [a.strip() for a in rx.pattern.strip('()').split('|') if a.strip()]
    return re.compile('(?<![%s])%s(?:%s)%s(?![%s])' % (_AR, _PRE, '|'.join(alts), _SUF, _AR))


RULES = [(c, _wordwise(ra), re_) for c, ra, re_ in RULES]


def derive(shot: dict, texts: dict | None = None, phase: str | None = None) -> str:
    """صنف المؤثّر للّقطة: من نصّ كتلها العربيّ أوّلاً (ما يُسمع)، ثمّ من وصف حركتها الإنجليزيّ، ثمّ من فصلها."""
    if shot.get('sfx'):
        return shot['sfx']
    ar = ' '.join(plain((texts or {}).get(b, '')) for b in shot.get('blocks') or [])
    en = ' '.join(str(shot.get(k) or '') for k in ('move', 'prompt', 'desc')).lower()
    for cat, rx_ar, rx_en in RULES:
        if ar and rx_ar.search(ar):
            return cat
    for cat, rx_ar, rx_en in RULES:
        if en and rx_en.search(en):
            return cat
    return PHASE_DEFAULT.get(phase, 'wind')


def phases_of(shots: list, sections: list) -> list:
    """فصل كلّ لقطة (phase) من sections.json — كما في transitions.sections_of لكن بالـphase وحده."""
    first = {x['id']: x.get('phase') for x in sections}
    cur, out = None, []
    for s in shots:
        b = (s.get('blocks') or [None])[0]
        if b in first:
            cur = first[b]
        out.append(cur)
    return out



IMPACT_CATS = ('swords', 'battle', 'armor', 'hooves')


def is_impact(shot: dict, texts: dict | None = None, phase: str | None = None) -> bool:
    """هل اللقطة ضربة/التحام تستحق ارتطاماً (ثقيل أو متوسط)؟"""
    if shot.get('slam') or shot.get('title'):
        return True
    return derive(shot, texts, phase) in IMPACT_CATS


def impact_times(shot: dict, span: float, texts: dict | None = None, phase: str | None = None, tier: str = 'medium') -> list:
    """أزمنة ارتطام داخل اللقطة إن لم يكتبها kinetic. قائمة (ثانية، طبقة)."""
    if not is_impact(shot, texts, phase) or span <= 0.3:
        return []
    t = min(max(0.35, span * 0.42), max(0.2, span - 0.15))
    return [(round(t, 3), tier)]


def require_layers(cats: list[str], n_shots: int) -> list[str]:
    """موانع إن غابت طبقة المحيط/المؤثّرات عن الفيلم."""
    errs = []
    real = [c for c in cats if c and c != 'none']
    if n_shots and not real:
        errs.append("لا مؤثّر صوت في أي لقطة — الطبقة إلزامية (أمر المالك 2026-11-22)")
    return errs


def main() -> int:
    proj = sys.argv[1]
    rd = lambda n: json.load(open(os.path.join(proj, n), encoding='utf-8')) if os.path.exists(os.path.join(proj, n)) else []
    shots, secs = rd('shots.json'), rd('sections.json')
    texts = {b['id']: b['text'] for b in rd('blocks.json')}
    ph = phases_of(shots, secs)
    for s, p in zip(shots, ph):
        print('%s\t%s\t%s%s' % (s['id'], p or '-', derive(s, texts, p), '' if s.get('sfx') else ' (مشتقّ)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
