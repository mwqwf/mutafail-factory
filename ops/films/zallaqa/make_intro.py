# يبني ملفات الافتتاحية (zallaqa-intro): كتل الراوي ولقطاته بإيماءةٍ مكتوبة لكل جملة (أمر المالك 2026-09-28)
# دليل OmniHuman 1.5: [الكاميرا] ثم [الانفعال] ثم [الكلام] ثم [الأفعال بالتسلسل First… then… finally]
import json, os, shutil

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intro')
os.makedirs(OUT, exist_ok=True)
STYLE = 'Read aloud in a lively, energetic, slightly brisk pace'   # السرعة من النموذج نفسه لا بتسريعٍ ظاهر (يُختبر هنا أولاً)
SAME = ' Same face, same clothes and same background throughout; natural five-finger hands; no one else appears.'

# (المعرّف، النص المشكول، الكاميرا والانفعال والأفعال)
N = [
 ('n_01', 'السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ، أَهْلًا بِكُمْ يَا أَصْدِقَائِي!',
  'A static medium shot. The man smiles warmly and greets the viewers, talking directly to the camera. First he raises his right hand to shoulder height with the open palm toward the camera in a greeting and gives a small respectful nod; then he places his right hand on his chest over his heart in welcome; finally he opens both hands slightly toward the viewer.'),
 ('n_02', 'هَلْ تُرِيدُونَ أَنْ نُسَافِرَ بِكُمْ عَبْرَ الزَّمَنِ، لِنَحْشُرَكُمْ فِي وَاحِدَةٍ مِنْ أَعْظَمِ مَعَارِكِ الْمُسْلِمِينَ فِي الْأَنْدَلُسْ؟',
  'The camera slowly dollies in toward his face. He is playful and full of suspense, leaning toward the lens and talking directly to the camera. First he points his index finger at the viewer; then he rolls his hand backward over his shoulder as if pointing back through time; finally he raises his eyebrows and holds an open palm up, asking a question.'),
 ('n_03', 'مَعْرَكَةٌ وَاحِدَةٌ، فِي يَوْمٍ وَاحِدٍ، أَنْقَذَتِ الْأَنْدَلُسَ مِنْ سُقُوطٍ كَانَ وَشِيكًا!',
  'A tracking medium-wide shot as he walks slowly along the hilltop toward the camera. He speaks with rising excitement. First he holds up one finger; then he holds up one finger again, stressing it; finally he sweeps both arms wide open to the landscape as if embracing the whole land.'),
 ('n_04', 'مَلِكُ قَشْتَالَةَ أَسْقَطَ طُلَيْطِلَةَ، وَفَرَضَ الْجِزْيَةَ عَلَى مُلُوكِ الْمُسْلِمِينَ، وَأَقْبَلَ بِجَيْشٍ جَرَّارٍ يُرِيدُ الْأَنْدَلُسَ كُلَّهَا!',
  'A static medium shot from his side. His face turns serious and stern as he speaks. First he points his whole arm far into the distance toward the north; then he turns his head back to the camera and tightens his fist at his chest; finally he shakes the fist slightly with a grave expression.'),
 ('n_05', 'وَفِي الْمُقَابِلِ… رِجَالٌ مُلَثَّمُونَ جَاؤُوا مِنْ صَحْرَاءِ الْمَغْرِبِ، عَبَرُوا الْبَحْرَ نُصْرَةً لِإِخْوَانِهِمْ!',
  'A static medium close shot. His expression changes to admiration and pride as he talks to the camera. First he passes his open hand horizontally across the lower half of his face as if drawing a veil; then he moves one hand in a flowing wave motion like the sea; finally he places his hand firmly on his heart.'),
 ('n_06', 'يَقُودُهُمْ شَيْخٌ جَاوَزَ السِّتِّينَ، أَسْمَرُ نَحِيفٌ، كَثِيرُ الْعَفْوِ، مُقَرِّبٌ لِلْعُلَمَاءِ… اسْمُهُ: يُوسُفُ بْنُ تَاشْفِينْ!',
  'A static low-angle medium shot. He speaks with deep respect that grows into pride. First he gently strokes his beard; then he opens his palm softly as if describing a humble man; finally he raises his clenched fist proudly and his eyes widen as he says the name.'),
 ('n_07', 'فَكَيْفَ هَزَمَ هَذَا الشَّيْخُ أَقْوَى مُلُوكِ النَّصَارَى فِي الْأَنْدَلُسْ؟',
  'A static close-up. He speaks slowly like someone asking a riddle, with a knowing half-smile. First he taps his index finger on his temple; then he narrows his eyes and leans slightly toward the camera; finally he lifts one eyebrow and holds the look.'),
 ('n_08', 'هَيَّا بِنَا! سَنَعُودُ قُرَابَةَ تِسْعِمِئَةٍ وَأَرْبَعِينَ سَنَةً إِلَى الْوَرَاءِ… تَعَالَوْا مَعِي!',
  'A static medium-full shot, the wind rising and dust swirling. He is excited and in a hurry, like someone about to leave. First he waves his right arm quickly toward himself again and again, beckoning the viewer to follow; then he half turns his body away as if starting to walk off; finally he looks back at the camera over his shoulder and beckons once more, urgently.'),
 ('n_09', 'انْظُرُوا! هَا نَحْنُ فِي سَهْلِ الزَّلَّاقَةِ، قُرْبَ بَطَلْيُوسَ، سَنَةَ أَرْبَعِمِئَةٍ وَتِسْعٍ وَسَبْعِينَ لِلْهِجْرَةْ!',
  'A static medium-full shot. He is amazed and delighted. First he looks down at his own robe and touches the fabric of his sleeve with surprise; then he touches his turban and laughs softly; finally he turns toward the camera and sweeps his arm wide to present the army camp behind him.'),
 ('n_10', 'وَقَبْلَ أَنْ تَبْدَأَ الْمَعْرَكَةُ: اشْتَرِكُوا فِي الْقَنَاةِ، وَفَعِّلُوا الْجَرَسَ، حَتَّى لَا تَفُوتَكُمْ حَلْقَةٌ مِنْ هَذِهِ السِّلْسِلَةْ!',
  'A static medium-wide shot of him seated on the standing camel, which stays calm and only breathes and shifts its head a little. He talks to the camera warmly and energetically. First he points his right index finger down toward the lower right corner of the frame and glances at it; then he makes a quick pressing gesture in the air with his finger as if pressing a button; then he points again slightly higher and wiggles his fingers like ringing a small bell; finally he gives a friendly thumbs-up to the viewer.'),
 ('n_11', 'وَالْآنَ… نَتْرُكُكُمْ مَعَ الْقِصَّةِ، وَنَتَمَنَّى لَكُمْ مُشَاهَدَةً شَيِّقَةْ!',
  'A static medium shot of him seated on the camel. He smiles broadly, warm and friendly. First he raises his right hand high and waves goodbye; then he places his hand on his chest and nods respectfully; finally he pulls the reins gently and the camel begins to turn toward the army.'),
]
blocks = [{'id': b, 'voice': 'Charon', 'text': t, 'style': STYLE} for b, t, _ in N]
IMG = {'n_%02d' % i: 'N%02d' % i for i in range(1, 12)}
shots = []
for b, t, act in N:
    sid = IMG[b]
    s = {'id': sid, 'file': sid + '.jpg', 'blocks': [b], 'kind': 'حيّة', 'sfx': 'wind', 'sfx_vol': 0.12,
         'avatar': True, 'lipsync': b, 'avatar_prompt': act + SAME}
    if sid == 'N10':
        s['overlays'] = [
            {'png': 'ui/subscribe.png', 'word': 'اشْتَرِكُوا', 'x': 1400, 'y': 860, 'w': 440},
            {'png': 'ui/bell.png', 'word': 'الْجَرَسَ', 'x': 1245, 'y': 845, 'w': 140, 'shake': True}]
    shots.append(s)
    if sid == 'N08':   # التحوّل بلا كلام بين N08 وN09: Kling v3 يرسم ما بين الصورتين
        shots.append({'id': 'TR1', 'file': 'TR1.jpg', 'blocks': [], 'hold': 8, 'kind': 'حيّة', 'duration': 8,
                      'end_image': 'N09', 'sfx': 'wind', 'sfx_vol': 0.55,
                      'move': ('A static camera. A powerful swirling sandstorm rises around the man on the hilltop. Gradually and clearly visible, '
                               'from the shoulders downward, his olive jacket and scarf ripple and transform piece by piece into a long loose cream wool robe '
                               'and a dark indigo cloak, the scarf winds itself up around his head into a dark indigo turban with its tail lowered under his chin; '
                               'at the same time, behind him, the highway, pylons and modern town dissolve into drifting sand and the ancient plain with an army camp '
                               'of dark tents and camels appears as the dust settles. His face stays exactly the same the whole time')})
shots.append({'id': 'K01', 'file': 'K01.jpg', 'blocks': [], 'hold': 4.5, 'kind': 'حيّة', 'duration': 5, 'sfx': 'marching', 'sfx_vol': 0.3,
              'move': 'The rider on the camel moves steadily away from the camera down the slope toward the army, the camel walking with natural gait, '
                      'his cloak moving in the wind, dust in the golden light; he never turns around; the camera holds still'})
pub = {'slug': 'zallaqa-intro', 'budget_usd': 14, 'film': {'title': 'الزلاقة — افتتاحية الراوي (معاينة خاصة)'}, 'reels': []}
for name, obj in (('blocks.json', blocks), ('shots.json', shots), ('publish.json', pub), ('reels.json', []),
                  ('sections.json', [{'id': 'n_01', 'title': 'الافتتاحية'}])):
    json.dump(obj, open(os.path.join(OUT, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(blocks), 'كتلة ·', len(shots), 'لقطة')
