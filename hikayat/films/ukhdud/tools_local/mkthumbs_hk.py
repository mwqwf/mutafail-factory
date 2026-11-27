"""مصغّرتا الفيلم 1: النص يُضاف بالكود (لا نص مولَّد). 1280x720."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
B='/workspace/hikayat-factory/film1/images/'
FONT='/usr/share/fonts/truetype/sand-box/google/Cairo/Cairo-VariableFont_slnt,wght.ttf'
def font(sz):
    f=ImageFont.truetype(FONT,sz,layout_engine=ImageFont.Layout.RAQM)
    try: f.set_variation_by_name('Black')
    except Exception: pass
    return f
def make(bg,out,lines,side,accent):
    im=Image.open(B+bg).convert('RGB').resize((1280,720),Image.LANCZOS)
    im=ImageEnhance.Contrast(im).enhance(1.15)
    # تعتيم جانب النص
    grad=Image.new('L',(1280,720),0); g=ImageDraw.Draw(grad)
    for x in range(1280):
        t = (x-640)/640 if side=='right' else (640-x)/640
        g.line([(x,0),(x,720)],fill=int(max(0,min(1,t))*170))
    im=Image.composite(Image.new('RGB',(1280,720),(5,8,12)),im,grad)
    d=ImageDraw.Draw(im)
    y=170
    for txt,sz,col in lines:
        f=font(sz)
        w=d.textlength(txt,font=f,direction='rtl',language='ar')
        x = 1280-70-w if side=='right' else 70
        for dx,dy in [(-4,4),(4,4),(0,6),(-3,-3),(3,-3)]:
            d.text((x+dx,y+dy),txt,font=f,fill=(0,0,0),direction='rtl',language='ar')
        d.text((x,y),txt,font=f,fill=col,direction='rtl',language='ar',stroke_width=2,stroke_fill=(0,0,0))
        y+=int(sz*1.25)
    # خط ذهبي رفيع تحت النص
    x0 = 1280-70-380 if side=='right' else 70
    d.rectangle([x0,y+40,x0+380,y+48],fill=accent)
    im.save(B+out,quality=92)
make('TA_bg.jpg','thumb-a.jpg',[('رب',150,(255,214,120)),('الغلام',150,(255,255,255))],'right',(212,160,60))
make('I41.jpg','thumb-b.jpg',[('لم',150,(255,255,255)),('يرجعوا',150,(255,140,40))],'left',(255,120,30))
print('ok')
