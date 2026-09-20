# ✅ رُفع هذا الإيقاف — أمرُ المالك 2026-09-20

**هذه الوثيقةُ صارت تأريخاً.** رفع المالكُ بأمرٍ صريحٍ إيقافَ الفهرسة والإيقافَ الماليَّ معاً،
والشرطُ الباقي: **استنفادُ جميع الطرق المجّانيّة استنفاداً موثَّقاً قبل أيّ إنفاق، فإذا استُنفدت
فالمالُ لا يمنع العمل** — وتُسمَّى التكلفةُ في التقرير. وتبقى حُرّاسُ سلامة النصّ وعتبةُ 5% ملزمةً.

**تنفيذُ الرفع:** رقعةٌ جاهزةٌ ومُختبَرة في `ops/LIFT_STOP_2026-09-20.patch` تُزيل `if: ${{ false }}`
وتُعيد الشروطَ الأصليّةَ المحفوظةَ في التعليقات. تُطبَّق هكذا:

```
git apply ops/LIFT_STOP_2026-09-20.patch
```

تحقُّقٌ سابقٌ عليها: `git apply --check` نجح، و**كلُّ** ملفّات سير العمل تُحلَّل YAML بلا خطأ بعدها.
⛔ ولم تُطبَّق في الجلسة السحابيّة لأنّ حارسَ صلاحيّات الجلسة منع الكتابةَ في `.github/workflows`
(`[CI Bypass]` و`[Modify Shared Resources]`) — وهو منعٌ من الأداة لا من المالك.

---

# Owner financial stop — 2026-09-18

No new charges are authorized. Before any push, PR, workflow dispatch, rerun, schedule, deployment, storage write or external API use, establish that the entire operation is free within available quotas. `ubuntu-latest`, a public repository, or an available budget alone is not sufficient proof. Do not re-enable Actions or use old branch snapshots to bypass the stop. Paid work requires NEW explicit owner approval of the necessity, estimated cost and hard cap. Never make private repositories public or disclose private code/secrets to obtain free compute. Prefer verified free cloud, then the session environment, then lightweight local work. Continue read-only analysis and small offline checks; do not repeat rejected candidates or tests without a material reason. Existing Quran accuracy gates and the 5% threshold remain mandatory. Use existing follow-up cycles only.

All default-branch workflow jobs have a reversible `if: ${{ false }}` stop. This does NOT cancel already running jobs or disable GitHub schedules at the API level. See `ops/FINANCIAL_STOP_2026-09-18.md` for rollback and outstanding cancellation.

## Recorded intervention

21 workflows; 40 jobs. All YAML files were parsed locally and every job condition checked before committing. No Actions test or cancellation workflow was launched. Commits use [skip ci]. Triggers (push, PR, schedule and workflow chains where present) remain declared, but jobs on the modified version cannot allocate runners. Old branch/PR versions remain a risk; do not run them.

## Cancellation result

The earlier paid-capable run [35327242621](https://github.com/mwqwf/mutafail-factory/actions/runs/35327242621) completed with `conclusion=cancelled` at 2026-09-18T09:20:27Z. A zero-runner concurrency interlock created [35328969582](https://github.com/mwqwf/mutafail-factory/actions/runs/35328969582); it completed `skipped`, with no job or runner allocation. A subsequent repository scan found no run in `active`, `queued`, `waiting`, `pending`, or `requested` state. Do not recreate either run. No claim is made about the source of the reported charges.

## Free fallback

Use the existing session environment for static analysis, YAML validation and small offline diagnostic samples. Do not dispatch cloud compute or write new artifacts to billable storage until account quota/cost verification. No new cloud provider or API has been provisioned. Existing monitoring may read status, but must not dispatch or restore stopped jobs.

## Reversal

Only restore after verified zero cost for all resources or NEW explicit financial approval. Each previous blob below is retained in Git history. Restore individual job conditions from that blob after reviewing intervening edits; do not blindly revert the repository. Existing conditions are also preserved as comments alongside the stop.

| Workflow | Previous blob | Stop commit |
|---|---|---|
| .github/workflows/admin.yml | 6a997154ebeaf3cde12f197dad0cfc375c842602 | 9cbfe03b4ac4cac574fd66998c05a9edb796b598 |
| .github/workflows/artifact-roundtrip.yml | 801a2e7cc7725b75887025970fc4c6c071635fc5 | ca1dee45e0eafb1b0c8e47675c10d64316f29cd3 |
| .github/workflows/audit.yml | fb3926d2e16696becd507692d5e69fca55d304e4 | f038f2bbac8ae586ec0dfda932ef1d92358f710f |
| .github/workflows/cancel-run.yml | ab6e145d246f819d4ff136b90e43c05e3096d018 | da12fa904b9a4400c205a4df483d5fc28234503b |
| .github/workflows/daily-production.yml | c8da3a69364abd2ff999a27fad4eb85a00873f99 | b827424f64adc9d197093aaa82ffa02d4c4313ef |
| .github/workflows/export-amal4-prompts.yml | b1549358dc7d5588734dedb4ec25f2e2dc0e2e3d | 0cd252b8771ee0a86cd44efd82f72a25f659829c |
| .github/workflows/film.yml | ff420c126ed1f24bc6843413baef9e106a5b6c8a | 287a62fa9bd4142f381a62f044a8361e731e0cea |
| .github/workflows/finalize-amal4.yml | 0126e53a236efbf5dfd9b2aa9256f04bfc63a8e8 | 71adbb902dac3bf3cbd2994c61c3d03326175c18 |
| .github/workflows/finish.yml | 46d8a76e7771c673ffd2068f1974a27dadfb2775 | bdb6a74125dd12f542b613529ca0350edbbf6dd8 |
| .github/workflows/inspect-amal4-layout.yml | f78c03fd86bcdfedc48fabafbd8ffe96ac5adabf | 8cc6f1b07ce4101e76d61e33d5bb16b682081188 |
| .github/workflows/inspect-listen-probe.yml | 8efd70548463900616c7a157aeab41371266b7ff | 7761747fb1fd48bc68175ff616aeb1cf48f8e6f0 |
| .github/workflows/listen-model-probe.yml | 0a6fd17c6547b79ec122f12f05b772ca97c27623 | ae7d07568b4f9b6bb485ebfdaf79d66e45148c3c |
| .github/workflows/logo.yml | 7103e98dddf02f82115628f264e9b538d871a8d5 | 0bf400421562073e8f7a60db196c088e2510eeb8 |
| .github/workflows/owner-dispatch.yml | 6c6f9d8775982c71373ef33e32f7ab34d31b538d | fae8be2827a5a2b5d563f9832aacc96b737732b4 |
| .github/workflows/publish-amal2-exception.yml | 16642bd6f244233dd9b2c1f554259238ce793c37 | 4030a87b4616151035679e152b2945df8202f67c |
| .github/workflows/publish-amal3-exception.yml | 84abbb93ae4d3860e0527703a5f88892852af1cf | b8bc23ce7353dcb8b78675aba7a7522e4caf4e07 |
| .github/workflows/pulse.yml | f436c0beb0e320b7d6aa83da61d31a61c95b913f | 86a9aa55d3cd9864498b6a88ef8198766c0de0d6 |
| .github/workflows/quality-tests.yml | b6ab5bd3286956b90781c5268edfffdea8b116d6 | 005f5f83b70e0764dd8011edbf8aec4a551f212d |
| .github/workflows/resume-listen.yml | 230abaed12f24d950d462120922c64ebea4700b9 | 683bcd7634eb67032d308b8070d87c17e6f064ee |
| .github/workflows/retry.yml | 18a8b5a94e427f434e3f4675c7d67187e5bc5969 | 54353d53a38089cfefe08e066393c07182ded3c0 |
| .github/workflows/selftest.yml | 89cec1d3cbc8aaf54c9583b02cc8f8d9f4b09932 | 2d0a01be3142f47c9d6030131796ccf7b9636707 |
