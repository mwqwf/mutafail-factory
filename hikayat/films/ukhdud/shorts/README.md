# شورتات فيلم 1 «أصحاب الأخدود»

- الدراسة: `shorts_study_and_plan.md`
- المواصفة المعتمدة (المصدر للتركيب): `shorts_spec.json`
- المراجعة اللغوية: `linguistic_review.md`
- الصور العمودية: `images/` ومراجعتها `images/_reports/review.md`

التصوير والرفع لم يبدأ بعد.

```bash
python3 tools_local/mk_shorts.py status
python3 tools_local/mk_shorts.py gates
# بعد إعلان اكتمال صوت الفيلم، وتوليد shorts/work/sh_cta.wav بصوت الفيلم:
python3 tools_local/mk_shorts.py render --ids S1,S2,S3
```
