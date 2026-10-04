# -*- coding: utf-8 -*-
"""التدريج السينمائيّ بحسب الفصل — طلب المالك 2026-10-04 بعد عيّنة المحرّك الثاني: «أريده أقوى وأكثر إبهاراً واستثنائية».

لكلّ فصلٍ «نظرةٌ» تُطبَّق على كلّ إطارٍ من لقطاته في المُجمِّع (transitions.assemble) قبل مزج الانتقالات:
  منحنى تباينٍ ناعم (S)، وتلوينٌ منفصل للظلال والإضاءات (الظلال إلى الأزرق المخضرّ والإضاءات إلى البرتقاليّ في المعركة،
  والبنّيّ الدافئ في التمهيد، والبارد الباهت فيما بعد الهزيمة)، وتشبّعٌ، ووهجٌ خفيف من مواضع الضوء (bloom)،
  وتعتيمٌ للأطراف (vignette)، وحبيباتُ فيلمٍ أحادية اللون.
⛔ مؤثّراتٌ على صور كوديكس لا رسم. وكلّها جداول وعمليات cv2 مشبعة فتكلّف ~10 م.ث للإطار.
"""
from __future__ import annotations

import numpy as np

# (تباين، تشبّع، ظلال RGB، إضاءات RGB، رفع الأسود، تعتيم الأطراف، حبيبات، وهج)
LOOKS = {
    None:        (1.12, 0.93, (-4, 2, 8), (10, 4, -8), 0, 0.30, 4.0, 0.16),     # الافتتاحية: سينمائيّ دافئ الضوء بارد الظلّ
    'setup':     (1.06, 0.86, (4, 1, -6), (12, 6, -10), 4, 0.26, 3.5, 0.10),    # التمهيد: دفءُ الرقّ والتاريخ
    'buildup':   (1.10, 0.90, (-6, 0, 10), (6, 3, -4), 0, 0.32, 4.0, 0.10),     # التوتّر: برودةٌ في الظلال
    'battle':    (1.18, 1.02, (-8, 3, 12), (16, 6, -12), 0, 0.36, 6.0, 0.22),   # المعركة: برتقاليٌّ وأزرقُ مخضرّ وأسودٌ عميق
    'aftermath': (1.04, 0.74, (-2, 2, 10), (2, 2, 4), 8, 0.30, 4.5, 0.08),      # ما بعدها: باهتٌ بارد
}


class Look:
    def __init__(self, section, size=(1920, 1080), seed=0):
        import cv2
        c, sat, sh, hi, lift, vig, grain, bloom = LOOKS.get(section, LOOKS[None])
        x = np.arange(256, dtype=np.float32) / 255.0
        s_curve = 0.5 + (x - 0.5) * c                       # تباينٌ حول المنتصف مع انحناءٍ ناعم عند الطرفين
        s_curve = s_curve + (x - s_curve) * (np.abs(x - 0.5) * 2) ** 3 * 0.6
        lut = []
        for ch in range(3):
            y = s_curve + (sh[ch] / 255.0) * (1 - x) ** 2 + (hi[ch] / 255.0) * x ** 2
            y = lift / 255.0 + y * (1 - lift / 255.0)
            lut.append(np.clip(y * 255.0, 0, 255).astype(np.uint8))
        self.lut = np.dstack(lut).reshape(1, 256, 3)
        self.sat, self.bloom = sat, bloom
        w, h = size
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 1.414
        v = 1 - vig * np.clip((r - 0.35) / 0.65, 0, 1) ** 1.8
        self.vig = cv2.merge([(v * 255).astype(np.uint8)] * 3)
        rng = np.random.default_rng(seed)
        self.grain = []
        for _ in range(6):                                  # حبيباتٌ أحادية اللون: ستّ لوحاتٍ تتبدّل عشوائياً كلّ إطار
            n = cv2.GaussianBlur(rng.normal(0, grain, (h, w)).astype(np.float32), (0, 0), 0.7)
            pos = cv2.merge([np.clip(n, 0, 255).astype(np.uint8)] * 3)
            neg = cv2.merge([np.clip(-n, 0, 255).astype(np.uint8)] * 3)
            self.grain.append((pos, neg))
        self.rng = rng
        self.i = 0

    def __call__(self, fr):
        import cv2
        out = cv2.LUT(fr, self.lut)
        if abs(self.sat - 1) > 0.01:
            g = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            out = cv2.addWeighted(out, self.sat, g, 1 - self.sat, 0)
        if self.bloom > 0.01:
            h, w = out.shape[:2]
            sm = cv2.resize(out, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
            hi = cv2.GaussianBlur(cv2.subtract(sm, np.full_like(sm, 165)), (0, 0), 10)
            out = cv2.add(out, cv2.resize(cv2.convertScaleAbs(hi, alpha=self.bloom * 2.0), (w, h), interpolation=cv2.INTER_LINEAR))
        out = cv2.multiply(out, self.vig, scale=1 / 255.0)
        j = int(self.rng.integers(0, len(self.grain) - 1))
        j = j + 1 if j >= self.i else j                     # لا تتكرّر اللوحة نفسها في إطارين متتاليين
        self.i = j
        pos, neg = self.grain[j]
        return cv2.subtract(cv2.add(out, pos), neg)
