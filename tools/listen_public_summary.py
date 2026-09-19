# -*- coding: utf-8 -*-
"""ملخصٌ آمن لسجل Actions: أعداد فقط، بلا نص أو منطوق غير منشور."""
import glob
import io
import json
import os
import sys

project = sys.argv[1]
results = {}
reviews = {}
for name in glob.glob(os.path.join(project, "listen_results*.json")):
    results.update(json.load(io.open(name, encoding="utf-8")))
for name in glob.glob(os.path.join(project, "listen_reviews*.json")):
    reviews.update(json.load(io.open(name, encoding="utf-8")))
checked = sum(type(v.get("ok")) is bool for v in results.values() if isinstance(v, dict))
flags = sum(v.get("ok") is False for v in results.values() if isinstance(v, dict))
pending = sum(type(v.get("ok")) is not bool for v in results.values() if isinstance(v, dict))
false_positive = sum(v.get("decision") == "false_positive" for v in reviews.values())
true_error = sum(v.get("decision") == "true_error" for v in reviews.values())
print("listen-summary checked=%d flags=%d pending=%d false_positive=%d true_error=%d" %
      (checked, flags, pending, false_positive, true_error))
reasons = {}
for value in results.values():
    if isinstance(value, dict) and type(value.get("ok")) is not bool:
        reason = str(value.get("why") or "no-result")[:80].replace("\n", " ")
        reasons[reason] = reasons.get(reason, 0) + 1
for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0])):
    print("listen-pending-reason count=%d reason=%s" % (count, reason))
