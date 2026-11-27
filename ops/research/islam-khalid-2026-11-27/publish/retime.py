"""يعيد أوقات النشر بعد الجمل الجديدة ونقل d_003 (proj/real_timing_split.json): الفصول، البطاقة، النداء، شاشة النهاية،
الشورتات (proj/reels.json لـthrill_gate)، والترجمة. يكتب publish/timing.json ويحدّث package.md وcaptions_ar.srt."""
import json, os, re
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(D, 'proj')
old = json.load(open(os.path.join(P, 'real_timing.json')))['bt']
S = json.load(open(os.path.join(P, 'real_timing_split.json'))); bt, sub = S['bt'], S['split_from']
B = json.load(open(os.path.join(P, 'blocks.json'), encoding='utf-8')); ids = [b['id'] for b in B]
total = max(v[1] for v in bt.values())
f = lambda t: '%d:%02d' % (int(t) // 60, int(t) % 60)
ff = lambda t: '%02d:%02d' % (int(t) // 60, int(t) % 60)
pk = open(os.path.join(D, 'publish', 'package.md'), encoding='utf-8').read()
# الفصول: كلّ فصلٍ يبدأ بالكتلة التي كان يبدأ عندها
def at_old(sec):
    return min(old, key=lambda k: abs(old[k][0] - sec))
lines = []
for m in re.finditer(r'^(\d\d):(\d\d) (.+)$', pk, re.M):
    sec = int(m.group(1)) * 60 + int(m.group(2)); k = 'd_001' if sec == 0 else at_old(sec)
    lines.append((m.group(0), '%s %s' % (ff(0 if sec == 0 else int(bt[k][0])), m.group(3))))
for a, b in lines: pk = pk.replace(a, b)
card, cta = bt['d_027'][0], bt['d_038'][0]; es0 = int(total) - 19
span = lambda a, b: (max(0.0, bt[a][0] - 0.3), bt[sub[b][-1]][1] + 0.6)
reels = [('r1', 'd_001', 'd_003', 'عُسفان', '«لو حملنا عليهم!» لماذا لم يحمل خالد بن الوليد؟'),
         ('r2', 'd_016', 'd_017', 'مفترق الطرق', '«أين المذهب؟» حيرة خالد بن الوليد بعد الحديبية'),
         ('r3', 'd_102', 'd_029', 'عمرو والنجاشي', 'عمرو بن العاص عند النجاشي… قبل أن يلقى خالد بن الوليد')]
R = []
for rid, a, b, lab, title in reels:
    s0, s1 = span(a, b); blk = [x for x in ids[ids.index(a):ids.index(sub[b][-1]) + 1]]
    R.append({'id': rid, 'title': title, 'blocks': blk, 'from': round(s0, 2), 'to': round(s1, 2), 'label': lab})
json.dump([{k: r[k] for k in ('id', 'title', 'blocks')} for r in R], open(os.path.join(P, 'reels.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
pk = re.sub(r'المدة [^\n]*?\(538\.7 ث\)|المدة 8:58 \([^)]*\)', 'المدة %s (%.1f ث)' % (f(total), total), pk)
pk = re.sub(r'\| بطاقة فيديو \(الجسر\) \| \*\*[\d:]+\*\* \([\d.]+٪\)', '| بطاقة فيديو (الجسر) | **%s** (%.1f٪)' % (f(card), 100 * card / total), pk)
pk = re.sub(r'\| نداء الاشتراك الوحيد \(في الصوت\) \| [\d:]+ \([\d.]+٪\)', '| نداء الاشتراك الوحيد (في الصوت) | %s (%.0f٪)' % (f(cta), 100 * cta / total), pk)
pk = re.sub(r'\| شاشة النهاية \| \*\*[^*]+\*\* \([^)]*\)', '| شاشة النهاية | **%s–%s** (آخر 20 ث من فيلم مدته %s)' % (f(es0), f(total), f(total)), pk)
tab = '\n'.join('| %d | %s–%s (%s) | %s | القصة كاملة في الفيلم المرتبط ⬇️ |' % (i + 1, f(r['from']), f(r['to']), r['label'], r['title']) for i, r in enumerate(R))
pk = re.sub(r'(\|---\|---\|---\|---\|\n)(\| 1 \|.*\n\| 2 \|.*\n\| 3 \|.*)', lambda m: m.group(1) + tab, pk)
open(os.path.join(D, 'publish', 'package.md'), 'w', encoding='utf-8').write(pk)
T = {'total': round(total, 2), 'card': f(card), 'cta': f(cta), 'endscreen': '%s-%s' % (f(es0), f(total)), 'reels': R}
json.dump(T, open(os.path.join(D, 'publish', 'timing.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
srt = lambda t: '%02d:%02d:%02d,%03d' % (t // 3600, t % 3600 // 60, t % 60, round((t % 1) * 1000) % 1000)
o = ['%d\n%s --> %s\n%s\n' % (i + 1, srt(bt[b['id']][0]), srt(bt[b['id']][1]), b['text']) for i, b in enumerate(B)]
open(os.path.join(D, 'publish', 'captions_ar.srt'), 'w', encoding='utf-8').write('\n'.join(o))
print(json.dumps({k: v for k, v in T.items() if k != 'reels'}, ensure_ascii=False), [(r['id'], f(r['from']), f(r['to'])) for r in R])
print('\n'.join(b for a, b in lines))
