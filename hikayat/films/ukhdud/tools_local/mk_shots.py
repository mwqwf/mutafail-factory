import json,re
STYLE=("cinematic painterly matte painting, ancient Near-Eastern desert kingdom before Islam, mud-brick and stone architecture, "
"earth tones with deep shadows and warm low-key light, volumetric haze, subtle film grain, documentary realism, 16:9 composition")
NEG=("no clear human face, no front-facing people; any person only seen from behind, as a dark silhouette, or as a tiny distant figure; "
"no women; no blood, no wounds, no injury, no violence on screen; no crosses, no churches, no religious symbols; "
"no text, no letters, no writing, no calligraphy, no logos, no watermark")
I={
"I01":("d_001","vast flat plain at misty dawn, a huge crowd of people seen strictly from behind in the foreground, far ahead a single bare wooden tree trunk standing upright with nobody on it, silent tense atmosphere"),
"I02":("d_002","close still life: a simple worn leather quiver full of arrows hanging on a rough wooden post, one arrow lifted halfway out, dust in a shaft of morning light, no hands, no people"),
"I03":("d_002","an ornate gilded royal bow with a single arrow resting at the middle of its grip, mounted on a carved stand, a blurred crowd far behind, dramatic rim light, no people near"),
"I04":("d_003","a golden royal crown resting on an empty carved throne in a dark stone hall, one narrow shaft of light from a high window, ominous mood"),
"I05":("d_004","wide aerial view of an ancient walled desert city at dusk, palm groves, winding streets, smoke from rooftops, distant mountains and a dark sea on the horizon"),
"I06":("d_006","dim chamber of an old court sorcerer: hanging dried herbs, clay jars, smoking incense, a hunched old man seen only from behind in a dark robe, candlelight"),
"I07":("d_007","a small boy seen from behind walking alone on a dusty lane between mud-brick houses toward a dark tower, long morning shadows"),
"I08":("d_008","a humble stone hermitage by a desert path, an old man in a plain undyed hooded robe sitting at its door seen from behind, a small boy sitting near him also seen from behind, warm late light, simple and peaceful"),
"I09":("d_010","a lonely dusty path that forks in two: one branch leads to a dark tower with smoke, the other to a small lit stone hut; a small boy seen from behind standing at the fork, tiny in frame"),
"I10":("d_012","night view from outside: a small stone hut with a glowing doorway, two dark silhouettes inside seen from behind, starry sky"),
"I11":("d_013","a road blocked by a gigantic dark shadow of an unseen beast cast across dust and walls, a crowd of tiny people seen from behind halted in fear, haze, the beast itself never visible"),
"I12":("d_016","over-the-shoulder view from behind of a small boy holding a rough stone in his hand, facing a dusty road with a looming dark shadow ahead, shallow depth of field"),
"I13":("d_018","the same road now open, dust settling in sunlight, people seen from behind walking onward through the road, relief, wide shot"),
"I14":("d_019","a small boy seen from behind approaching a humble stone hermitage at dusk, lamp light in the doorway"),
"I15":("d_022","a modest courtyard where many people wait, all seen from behind, some leaning on staffs, warm hopeful light falling into the courtyard"),
"I16":("d_023","a richly dressed courtier seen strictly from behind, led by a servant, arriving at a modest house with servants carrying wooden chests of gifts, late afternoon"),
"I17":("d_027","golden sunlight breaking through dark clouds over the desert city, rays falling on rooftops, sense of grace and healing"),
"I18":("d_028","a grand palace hall with tall columns, the throne seen from the side with a crown resting on it, a courtier in fine robes seated near it seen strictly from behind"),
"I19":("d_031","a long dark palace corridor lit by torches, armored guards seen from behind as silhouettes walking away, heavy menace"),
"I20":("d_035","a heavy wooden door closed in a bare stone chamber, a single torch on the wall burning low, smoke curling, somber"),
"I21":("d_036","a second closed door in a dark stone corridor, an extinguished torch with a thin trail of smoke, silence"),
"I22":("d_039","a steep rocky mountain at dusk with a narrow path, a group of tiny distant figures climbing it, seen from far below, storm clouds gathering"),
"I23":("d_040","mountain summit against a stormy sky, a few tiny dark silhouettes standing at the edge seen from far away behind them, wind and dust"),
"I24":("d_042","the mountain shaking: rockfall and a huge dust cloud pouring down the slope, boulders tumbling, dramatic lightning, no people visible"),
"I25":("d_043","a single small figure seen from behind walking calmly along a road toward huge palace gates, dust settling behind, late light"),
"I26":("d_044","peaceful wide desert landscape at golden hour with an ancient road winding toward a distant city, calm and inviting"),
"I27":("d_046","a small wooden boat on a dark open sea, tiny figures aboard seen from far away, heavy clouds, growing waves"),
"I28":("d_049","far wide shot of a small wooden boat overturning in a large dark wave at sea, spray and foam, no people detail visible"),
"I29":("d_050","a calm shoreline at dawn, a single small figure seen from behind walking from the sea toward the distant city"),
"I30":("d_052","huge closed palace doors of carved wood and bronze, a very small figure seen from behind standing before them, dramatic scale"),
"I31":("d_054","a throne room seen from behind an empty throne with a golden crown on its seat, far across the hall a small figure seen from behind standing, torches, tension"),
"I32":("d_056","close still life of arrows in a leather quiver resting on a stone ledge, sharp light and deep shadow, no people"),
"I33":("d_057","aerial view of crowds streaming from all city streets toward one vast open plain, all tiny figures, morning haze"),
"I34":("d_059","a golden crown on a dark throne, half in shadow, half lit by a cold window light, brooding"),
"I35":("d_061","enormous crowd on a flat plain seen from behind and above, far in the distance a lone wooden trunk, a royal canopy with banners at one side, held-breath silence"),
"I36":("d_062","a single arrow in flight against a pale bright sky, motion blur, birds scattering, nothing else visible"),
"I37":("d_064","a vast crowd seen from behind raising their hands toward the sky at sunrise, golden light flooding the plain"),
"I38":("d_066","first light of sunrise spreading across the plain and the crowd seen from behind, long shadows, solemn hope"),
"I39":("d_069","inside the palace a court official seen from behind bowing before an empty throne with a crown on it, cold blue light, alarm"),
"I40":("d_070","far wide shot at dusk: many tiny silhouettes digging long deep trenches across the entrances of narrow city streets, piles of earth"),
"I41":("d_071","night aerial view of an ancient city with long trenches of fire glowing orange at the mouths of its streets, smoke rising, dark blue surroundings, no people visible in the fire"),
"I42":("d_073","the edge of a glowing fire trench at night seen from a distance, a crowd of dark silhouettes standing far back seen from behind, smoke and embers"),
"I43":("d_075","embers and sparks rising from a trench of fire into a dark night sky, only smoke and light, no people"),
"I44":("d_078","a starry night sky over the silent desert city, a faint glow fading on the horizon, stillness"),
"I45":("d_080","peaceful dawn over the desert city and plain, soft light, a gentle breeze moving the palm trees, serene ending"),
}
THUMBS={
"TA":"high-contrast dramatic thumbnail composition: an ornate gilded royal bow with a single arrow nocked at its grip, pointed toward a lone bare wooden trunk on a misty plain far away, silhouettes of a crowd seen from behind at the bottom edge, deep dark-teal sky with golden rim light, empty negative space on the right third for text",
"TB":"high-contrast dramatic thumbnail composition: night aerial view of long trenches of fire glowing intense orange across the entrances of dark city streets, deep navy blue surroundings, smoke rising, no people visible in the fire, empty negative space on the left third for text",
}
shots=[]
for k,(b,d) in I.items():
    shots.append({"image":k,"block":b,"prompt":f"{d}. Style: {STYLE}. Constraints: {NEG}.","aspect":"16:9"})
for k,d in THUMBS.items():
    shots.append({"image":k,"block":"thumbnail","prompt":f"{d}. Style: {STYLE}. Constraints: {NEG}.","aspect":"16:9"})
json.dump({"style":STYLE,"negative":NEG,"shots":shots},open('image_prompts.json','w'),ensure_ascii=False,indent=1)
print(len(shots))
