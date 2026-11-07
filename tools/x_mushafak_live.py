# مونتاج فيديو «مصحفك يعمل أمامك»: تسجيلٌ حقيقيٌّ من المحاكي في إطار هاتف، وتعليقٌ صوتيّ، وعناوين أعلى.
import subprocess, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = os.path.dirname(os.path.abspath(__file__)); os.chdir(D)
W, H, FPS = 1080, 1920, 30
F = '/home/claude/quranrafiq/app/src/main/res/font/'
PB, PM = F + 'ibm_plex_sans_arabic_bold.ttf', F + 'ibm_plex_sans_arabic_medium.ttf'
LOGO = '/tmp/claude-0/-home-claude/715dbec7-c2c1-5122-b1c3-4198a6c466d4/scratchpad/mk/logo.png'
VO = 'vo/mushafak-live-voice-B.mp3'
DUR = [7.24, 6.44, 6.40, 4.84, 4.36, 3.00]; PAD = 0.6
# بدايات الجمل داخل ملفّ الصوت المضموم
OFF = []; t = 0
for d in DUR: OFF.append(t); t += d + PAD
os.makedirs('b', exist_ok=True)

def ar(s): return s
def run(a): subprocess.run(a, check=True)

# مقاطع الصورة: (المصدر، البداية، النهاية، مدّة الإخراج، العنوان، جملة الصوت أو None)
PW = 900; PH = int(PW * 1920 / 1080)   # 900×1600
SEG = [
    ('rec_mushaf', 0.0, 1.95, 7.84, 'تسجيلٌ حقيقيّ… لا تصاميم', 0),
    ('rec_mushaf', 2.3, 9.34, 7.04, 'حفص · ورش · قالون', 1),
    ('rec_tabs', 1.4, 21.0, 7.00, 'تدرّب: حفظي · وِردي · اختبرني', 2),
    ('rec_tabs', 21.4, 27.85, 5.44, 'يومي: المواقيت · القبلة · الأذكار', 3),
    ('rec_ask', 5.5, 13.5, 2.80, 'اسأل في دينك…', 4),
    ('rec_ask', 37.0, 57.0, 6.80, 'اسأل في دينك… بالمصادر', None),
]

def bg():
    im = Image.new('RGB', (W, H), (10, 46, 38)); dr = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H; dr.line([(0, y), (W, y)], fill=(int(8 + 10 * k), int(40 + 22 * (1 - k)), int(34 + 14 * (1 - k))))
    return im

def frame_png(path, title):
    im = bg().convert('RGBA'); dr = ImageDraw.Draw(im)
    # ظلّ الهاتف وإطاره
    x0, y0 = (W - PW) // 2, 290
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle([x0 - 14, y0 - 6, x0 + PW + 14, y0 + PH + 22], 56, fill=(0, 0, 0, 150))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(18))); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([x0 - 12, y0 - 12, x0 + PW + 12, y0 + PH + 12], 52, fill=(22, 24, 26))
    # الشارة: نقطة تسجيلٍ حمراء
    fb = ImageFont.truetype(PM, 36); s = ar('تسجيلٌ حقيقيّ من التطبيق')
    tw = dr.textlength(s, font=fb, direction='rtl', language='ar'); bx = (W - tw - 60) // 2
    dr.rounded_rectangle([bx - 18, 40, bx + tw + 60, 100], 30, fill=(0, 0, 0, 110))
    dr.ellipse([bx + tw + 22, 58, bx + tw + 46, 82], fill=(232, 64, 56))
    dr.text((bx, 70), s, font=fb, fill=(240, 240, 236), anchor='lm', direction='rtl', language='ar')
    # العنوان
    ft = ImageFont.truetype(PB, 64 if len(title) < 24 else 54); s = ar(title)
    dr.text((W // 2, 190), s, font=ft, fill=(247, 218, 146), anchor='mm', direction='rtl', language='ar', stroke_width=2, stroke_fill=(6, 30, 24))
    im.save(path)
    return x0, y0

segs = []
mk = Image.new('L', (PW, PH), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, PW - 1, PH - 1], 42, fill=255); mk.save('b/mask.png')
for i, (src, a, b, d, title, _) in enumerate(SEG):
    x0, y0 = frame_png('b/f%d.png' % i, title)
    k = d / (b - a)
    # مسارٌ واحد: الخلفية ثمّ الشاشة المسجّلة بزوايا مدوّرة
    fc = ("[1:v]trim=%.3f:%.3f,setpts=PTS-STARTPTS,setpts=%.4f*PTS,fps=%d,scale=%d:%d:flags=lanczos,format=rgba[r];"
          "[2:v]format=gray[m];[r][m]alphamerge[s];"
          "[0:v][s]overlay=%d:%d,trim=duration=%.3f,setpts=PTS-STARTPTS,format=yuv420p[v]") % (a, b, k, FPS, PW, PH, x0, y0, d)
    run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', str(FPS), '-i', 'b/f%d.png' % i, '-i', 'src/%s.mp4' % src, '-loop', '1', '-framerate', str(FPS), '-i', 'b/mask.png',
         '-filter_complex', fc, '-map', '[v]', '-t', '%.3f' % d, '-r', str(FPS), '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', 'b/s%d.mp4' % i])
    segs.append('b/s%d.mp4' % i)

# بطاقة الختام
END = 4.2
im = bg().convert('RGBA'); dr = ImageDraw.Draw(im)
lg = Image.open(LOGO).convert('RGBA').resize((300, 300), Image.LANCZOS)
m = Image.new('L', (300, 300), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 299, 299], 66, fill=255)
im.paste(lg, ((W - 300) // 2, 560), m)
dr.text((W // 2, 990), ar('مُصحفك'), font=ImageFont.truetype(PB, 120), fill=(247, 218, 146), anchor='mm', direction='rtl', language='ar')
dr.text((W // 2, 1130), ar('جرّبه بنفسك'), font=ImageFont.truetype(PM, 60), fill=(240, 240, 236), anchor='mm', direction='rtl', language='ar')
dr.text((W // 2, 1260), ar('على Google Play · الرابط في الردّ'), font=ImageFont.truetype(PM, 44), fill=(196, 214, 206), anchor='mm', direction='rtl', language='ar')
im.save('b/end.png')
run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', str(FPS), '-i', 'b/end.png', '-t', str(END),
     '-vf', "fade=in:st=0:d=0.4,format=yuv420p", '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', 'b/end.mp4'])
segs.append('b/end.mp4')
open('b/list.txt', 'w').write(''.join("file '%s'\n" % os.path.basename(s) for s in segs))
run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'b/list.txt', '-c', 'copy', 'b/video.mp4'])

# الصوت: كلّ جملةٍ في موضع مقطعها، والأخيرة على بطاقة الختام
starts = []; t = 0
for (_, a, b, d, _, vi) in SEG:
    if vi is not None: starts.append((vi, t + 0.25))
    t += d
starts.append((5, t + 0.3))
total = t + END
inp = []; fl = []
for j, (vi, st) in enumerate(starts):
    inp += ['-i', VO]
    fl.append("[%d:a]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[a%d]" % (j, OFF[vi], OFF[vi] + DUR[vi] + 0.1, st * 1000, st * 1000, j))
fl.append(''.join('[a%d]' % j for j in range(len(starts))) + "amix=inputs=%d:normalize=0,loudnorm=I=-15:TP=-1.5,apad,atrim=0:%.3f[a]" % (len(starts), total))
run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-i', 'b/video.mp4', '-filter_complex', ';'.join(fl),
     '-map', '%d:v' % len(starts), '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'mushafak_live.mp4'])
print('ok', total)
