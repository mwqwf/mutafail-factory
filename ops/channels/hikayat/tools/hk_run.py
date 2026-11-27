# -*- coding: utf-8 -*-
"""تشغيل أيّ أداة من tools/ (أداة التاريخ نفسها) لقناة الحكايات، بشعار الحكايات، بلا تعديل tools/.

لماذا: كل أدوات المخرَجات تأخذ الشعار من envpaths.logo() ⇐ <جذر المستودع>/assets/logo.png (شعار التاريخ)،
وجذر المستودع يُحسب من موضع الملف (os.path.abspath بلا حلّ للروابط). فنبني «جذراً ظلّياً» مؤقتاً:
كل ما في المستودع روابط رمزية إليه، إلا assets/logo.png فهو شعار الحكايات من channel.json.
النتيجة: mont_hybrid وmkthumb وmkreel3d وlogocheck تعمل كما هي حرفياً، بالموضع والحجم والشفافية نفسها.

الاستعمال (من جذر المستودع):
  python3 ops/channels/hikayat/tools/hk_run.py mont_hybrid.py <proj> [GAP]
  python3 ops/channels/hikayat/tools/hk_run.py mkthumb.py <bg.jpg> <out.jpg> "سطر" "سطر"
  python3 ops/channels/hikayat/tools/hk_run.py logocheck.py <film.mp4> <baseline.mp4>
يزول هذا الغلاف حين يُقبل طلب TOOLS_CHANGE_REQUESTS.md §١ (MUTAFAIL_CHANNEL في envpaths.logo).
"""
import json, os, shutil, subprocess as sp, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CFG = json.load(open(os.path.join(HERE, '..', 'channel.json'), encoding='utf-8'))


def shadow_root():
    logo = os.path.join(REPO, CFG['logo']['asset'])
    if not os.path.isfile(logo):
        raise SystemExit('⛔ شعار الحكايات غير موجود: %s — لا يخرج مخرَج بلا شعار' % logo)
    root = tempfile.mkdtemp(prefix='hk_root_')
    for name in os.listdir(REPO):
        if name in ('assets', '.git'):
            continue
        os.symlink(os.path.join(REPO, name), os.path.join(root, name))
    os.mkdir(os.path.join(root, 'assets'))
    for name in os.listdir(os.path.join(REPO, 'assets')):
        if name == 'logo.png':
            continue
        os.symlink(os.path.join(REPO, 'assets', name), os.path.join(root, 'assets', name))
    shutil.copyfile(logo, os.path.join(root, 'assets', 'logo.png'))
    return root


def main(argv):
    if not argv:
        print(__doc__); return 2
    tool, args = argv[0], argv[1:]
    if os.sep in tool or not tool.endswith('.py') or not os.path.isfile(os.path.join(REPO, 'tools', tool)):
        raise SystemExit('⛔ أداة غير معروفة في tools/: %s' % tool)
    root = shadow_root()
    try:
        env = dict(os.environ, MUTAFAIL_CHANNEL='hikayat', PYTHONDONTWRITEBYTECODE='1')
        # المسارات النسبية في الوسائط تبقى نسبةً إلى مجلّد التشغيل الحاليّ
        return sp.call([sys.executable, os.path.join(root, 'tools', tool)] + args, env=env)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
