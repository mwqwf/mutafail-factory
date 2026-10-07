# -*- coding: utf-8 -*-
"""مسار خريطة عمق الصورة — منفصلٌ عن kb3d (بلا numpy) ليُختبر في كلّ بيئة، ومنها عدّاء الاختبارات."""
import os


def depth_of(src):
    """خريطة عمق الصورة: بجانبها، وإلا في <proj>/img حيث يكتبها kb3d.depth_maps.
    ⛔ درس الأرك 2026-10-04: المونتاج يأخذ الصورة من images/ والعمق في img/، فكان كلّ مشهدٍ مجسَّم يسقط إلى التدرّج
    الرأسيّ (كين-بيرنز) منذ الأفلام الهجينة — والعمق محسوبٌ في كلّ شوطٍ بلا فائدة."""
    d = src.rsplit('.', 1)[0] + "_depth.png"
    if os.path.exists(d):
        return d
    alt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(src))), 'img', os.path.basename(d))
    return alt if os.path.exists(alt) else d
