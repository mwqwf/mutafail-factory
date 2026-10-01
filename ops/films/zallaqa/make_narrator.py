# يبني shots_narrator.json: صور الراوي والتحوّل لكوديكس (الدفعة الأولى — تُعرض على المالك قبل الإنفاق)
import json

FACE = ("the channel narrator EXACTLY as in the reference photo narrator/narrator_ref.jpg (open it and match it): "
        "the same contemporary Muslim man about 40, the same face and features, the same short dark wavy hair, "
        "the same medium-length well-groomed dark beard with grey at the chin, the same skin tone")
MODERN = "wearing the same dark olive field jacket over a plain black t-shirt and the same light sand-coloured loose scarf as in the reference"
ALMOR = ("now dressed as an 11th-century Almoravid warrior of the Sahara: a dark indigo-blue turban wound around his head, "
         "its long tail (the litham veil) lowered and gathered loosely UNDER his chin and around his neck so his whole face is visible; "
         "a long, very loose ankle-length undyed cream wool robe that hangs straight and never shows the shape of the body; "
         "over it a loose dark indigo wool burnous cloak; a plain leather belt with a sheathed straight sword; "
         "a round tan leather shield of oryx hide slung on his back. No jewellery")
HANDS = "BOTH HANDS fully visible with five natural fingers each, no hands in pockets"
NOW = ("He stands on top of a low rocky hill near Badajoz in Extremadura, Spain, in golden morning light; behind him the wide flat plain "
       "of the Guadiana valley TODAY: olive groves and green irrigated fields, a modern highway with a few cars, power-line pylons, "
       "and the distant white modern town of Badajoz")
THEN = ("He stands on the SAME low rocky hill, but the plain behind him is now the year 1086: no roads, no pylons, no buildings; "
        "open grassland with scattered holm oaks, a small river lined with trees, and a vast Almoravid army camp of dark wool tents, "
        "rows of warriors whose faces are covered by dark litham veils holding long spears and round tan leather shields, "
        "and many dromedary camels, dust glowing in the golden morning light")
TAIL = ("Cinematic documentary photograph, photorealistic, sharp focus on face and hands, soft natural background blur, 16:9 widescreen. "
        "Only adult men; no women, no text, no letters, no logos, no watermark, no crosses, no musical instruments.")

def sh(i, pose, clothes, place):
    return {"id": i, "file": i + ".jpg", "prompt": "%s, %s. %s. %s. %s. %s" % (FACE, clothes, pose, HANDS, place, TAIL)}

S = [
    sh("N01", "Framing like a YouTube documentary presenter: medium shot from the waist up, centred, eye level, facing the camera. "
              "He greets the viewers: his right hand raised at shoulder height with the open palm toward the camera, left hand relaxed in front of his waist, "
              "a warm genuine smile, mouth slightly open as if saying hello", MODERN, NOW),
    sh("N02", "Closer framing from the chest up, the camera slightly lower and nearer than a normal presenter shot. He leans toward the lens "
              "with raised eyebrows and a playful, inviting smile, his right index finger pointing straight at the viewer, left hand open at chest height",
       MODERN, NOW + ", the landscape softly out of focus"),
    sh("N03", "Medium-wide shot from the knees up, three-quarter angle from his left side: he walks slowly along the ridge of the hill toward the camera, "
              "holding up ONE finger of his right hand to make a point, left hand open, mouth open mid-sentence, excited eyes", MODERN, NOW),
    sh("N04", "Medium shot from his right side, three-quarter view: he stretches his whole right arm and points into the far distance toward the north, "
              "his face serious and determined, left hand clenched into a fist at his chest, still turned enough that his face and both hands are clearly seen",
       MODERN, NOW),
    sh("N05", "Medium close shot, frontal, eye level: both hands raised in front of his chest, palms slightly open, fingers apart, in the middle of an "
              "energetic storytelling gesture, eyebrows lifted, intense admiring eyes, mouth open mid-sentence", MODERN, NOW),
    sh("N06", "Low-angle medium shot, the sky wide behind him: his right hand gently strokes his beard in respect and admiration, "
              "left hand open at waist height, a proud respectful expression as if speaking of a great man", MODERN, NOW),
    sh("N07", "Close-up of head, shoulders and his right hand, shallow depth of field: his right index finger touches his temple, "
              "eyes narrowed with a knowing half-smile, as if asking a riddle; left hand visible lower in the frame", MODERN, NOW),
    sh("N08", "Medium-full shot from the thighs up, frontal, the SAME camera position as a presenter shot: the wind is rising and dust swirls around his legs, "
              "his scarf blowing; his right arm raised high beckoning energetically toward the camera as if saying 'come on, hurry!', "
              "his body already half turned to his left as if about to leave, an excited urgent expression, left hand visible", MODERN, NOW),
    sh("N09", "Medium-full shot from the thighs up, frontal, EXACTLY the same camera position, framing and hill as N08.jpg: he holds his arms slightly out "
              "from his sides, palms up, looking down at his new robe in delighted amazement with a wide smile, dust settling around him", ALMOR, THEN),
    sh("N10", "Medium-wide shot from a low camera at front three-quarter: he sits on a saddle on a tall standing dromedary camel (one hump, natural camel head, "
              "neck, face and four legs, anatomically perfect); the reins in his left hand, his right arm extended pointing DOWN toward the lower right corner "
              "of the frame, looking at the camera with an enthusiastic smile. Keep the lower right quarter of the frame calm and uncluttered",
       ALMOR, "Behind him on the plain of 1086: rows of veiled Almoravid warriors with spears and round leather shields and more camels, softly blurred, "
              "golden morning light and dust; no modern structures"),
    sh("N11", "Medium shot, slightly closer, from the front: he sits on the same dromedary camel, raising his right hand high in a warm farewell wave, "
              "big smile, reins in his left hand, the camel's head turning slightly toward the army", ALMOR,
       "Behind him on the plain of 1086: rows of veiled Almoravid warriors and camels softly blurred, golden light and dust; no modern structures"),
    {"id": "K01", "file": "K01.jpg", "prompt": "Wide shot FROM BEHIND: a man in a dark indigo turban and a loose dark indigo burnous cloak with a round tan leather shield on his back "
     "rides a dromedary camel away from the camera, down a gentle slope toward a vast Almoravid army of veiled warriors with long spears and round leather shields "
     "and many camels on an open plain with scattered holm oaks in the year 1086, dust glowing in golden morning light. His face is NOT visible. "
     "Camel anatomically perfect. " + TAIL},
]
json.dump(S, open('shots_narrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(S))
