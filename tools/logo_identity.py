"""مرجع بصري لهوية الشعار، مشترك بين التصيير والفحص الفعلي للإطارات."""
from PIL import Image, ImageDraw, ImageFilter


def badge(path, layout='film'):
    size = 118 if layout == 'reel' else 120
    logo = Image.open(path).convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new('L', (size * 4, size * 4), 0)
    inset, blur = (6, 4) if layout == 'reel' else (4, 3)
    ImageDraw.Draw(mask).ellipse([inset, inset, size * 4 - inset, size * 4 - inset], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur)).resize((size, size), Image.Resampling.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(logo, (0, 0), mask)
    if layout == 'film':
        out.putalpha(out.getchannel('A').point(lambda value: int(value * .72)))
    return out


def expected_frame(base, path, layout):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    mark = badge(path, layout)
    width, height = base.size
    xy = ((width - 118) // 2, height - 158) if layout == 'reel' else (width - 166, 46)
    # لصق مباشر يحفظ ألفا العلامة ولا يضاعف شفافيّتها.
    layer.paste(mark, xy)
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')
