# إعدادُ الأذونات الدائمة لمصنع المتفائل — يُطبِّقه المالك بنفسه

طلب المالك 2026-09-24: «فعِّل طريقةً تعطي هذا النوع من الأذونات دائماً». محاولةُ الجلسة كتابةَ
`.claude/settings.json` بنفسها **رفضها حارسُ الأمان** (وكيلٌ لا يمنح نفسه أذوناتٍ)، فهذا نصُّه جاهزاً.
**الطريقة:** أنشئ في الفرع `claude/film-today-bull-c51x48` ملفّ `.claude/settings.json` بهذا المحتوى
(من واجهة GitHub: Add file ← Create new file). وأوّلُ سطرٍ فيه يُصلح أيضاً سقوطَ إعداد العربيّة على هذا الفرع.

```json
{
  "language": "arabic",
  "permissions": {
    "allow": [
      "WebFetch(domain:api.quran.com)", "WebFetch(domain:quran.com)", "WebFetch(domain:sunnah.com)",
      "WebFetch(domain:dorar.net)", "WebFetch(domain:shamela.ws)", "WebFetch(domain:ar.wikisource.org)",
      "WebFetch(domain:ar.wikipedia.org)", "WebFetch(domain:en.wikipedia.org)", "WebFetch(domain:archive.org)",
      "WebFetch(domain:api.github.com)", "WebFetch(domain:raw.githubusercontent.com)", "WebSearch",
      "Bash(git status:*)", "Bash(git log:*)", "Bash(git diff:*)", "Bash(git show:*)", "Bash(git fetch:*)",
      "Bash(git pull:*)", "Bash(git checkout:*)", "Bash(git mv:*)", "Bash(git commit:*)",
      "Bash(git add ops/:*)", "Bash(git add tools/:*)", "Bash(git add skill/:*)", "Bash(git add assets/:*)",
      "Bash(git add .github/:*)", "Bash(git push origin claude/film-today-bull-c51x48:*)",
      "Bash(python3:*)", "Bash(node:*)", "Bash(bash tools/seal.sh:*)", "Bash(jq:*)", "Bash(sha256sum:*)"
    ],
    "deny": [
      "Bash(git add -A:*)", "Bash(git add .:*)", "Bash(git add --all:*)",
      "Bash(git push --force:*)", "Bash(git push -f:*)", "Bash(*rafiq-align-ci*)"
    ]
  }
}
```

⛔ قائمةُ `deny` تُبقي الممنوعات ممنوعةً ولو سُمح بما عداها.
