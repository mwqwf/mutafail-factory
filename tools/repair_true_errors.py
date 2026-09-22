# -*- coding: utf-8 -*-
"""يحدّد أخطاء الصوت المؤكدة ويُبطل آثارها وحدها لإعادة توليدها وفحصها."""
import glob
import hashlib
import io
import json
import os
import sys


def load_many(pattern):
    out = {}
    for name in glob.glob(pattern):
        try:
            out.update(json.load(io.open(name, encoding="utf-8")))
        except Exception:
            pass
    return out


def digest(text, audio_path):
    h = hashlib.sha256()
    h.update(text.encode("utf-8")); h.update(b"\0")
    with open(audio_path, "rb") as handle:
        h.update(handle.read())
    return h.hexdigest()


def stuck_unverified(project):
    """كتلٌ تردّها بوّابةُ الاستماع بـ«غير مفحوصة أو مرفوعةُ راية» بعد تمام الفحص.

    ⛔ الثقبُ المقيس (شوط 35705031085 · 2026-09-22): كتلةُ `r_002` لم يرجع لها
    نتيجةُ فحصٍ أصلاً، فلم تكن «خطأً مؤكَّداً» فلم يُعِد العاملُ توليدَها، فدارت
    دورةُ الإصلاح في محلّها ثلاثَ إعاداتٍ ثمّ سقط الشوط. والعلاجُ أنّ ما تردّه
    البوّابةُ بعد الفحص **يُعاد توليدُه**، فلا يبقى في المنتَج صوتٌ لم يُتحقَّق منه.
    ⭐ وهذا يزيد الحارسَ إحكاماً لا ليناً: لا يمرّ شيءٌ بلا نتيجةٍ مطابقةِ البصمة.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import listen_gate
    ids = []
    for problem in listen_gate.audit(project):
        ident, _, kind = str(problem).partition(": ")
        if kind == "unchecked-or-flagged" and os.path.isfile(
                os.path.join(project, "audio", ident + ".wav")):
            ids.append(ident)
    return ids


def main(project, output_file):
    blocks = {b["id"]: b for b in json.load(io.open(os.path.join(project, "blocks.json"), encoding="utf-8"))}
    reviews = load_many(os.path.join(project, "listen_reviews*.json"))
    repair = [i for i in stuck_unverified(project) if i in blocks]
    for ident, review in reviews.items():
        if review.get("decision") != "true_error" or ident not in blocks:
            continue
        audio = os.path.join(project, "audio", ident + ".wav")
        if not os.path.isfile(audio):
            raise SystemExit("true_error بلا ملف صوت: " + ident)
        current = digest(blocks[ident]["text"], audio)
        if review.get("input_sha256") != current:
            continue
        repair.append(ident)

    repair = sorted(set(repair))
    json.dump({"ids": repair}, io.open(output_file, "w", encoding="utf-8"), ensure_ascii=False)
    if not repair:
        print("لا أخطاء صوت مؤكدة تحتاج إصلاحاً")
        return

    for ident in repair:
        os.remove(os.path.join(project, "audio", ident + ".wav"))

    # لا يكفي حذف الملف: gen25 يتخطى كل معرّف موسوم done حتى لو بقيت
    # حالته من محاولة سابقة. أسقط حالة المقطع كي تكون إعادة التوليد حقيقية.
    for state_name in glob.glob(os.path.join(project, "gen_state*.json")):
        try:
            state = json.load(io.open(state_name, encoding="utf-8"))
        except Exception:
            continue
        for ident in repair:
            if isinstance(state.get("done"), dict):
                state["done"].pop(ident, None)
            if isinstance(state.get("model_of"), dict):
                state["model_of"].pop(ident, None)
        io.open(state_name, "w", encoding="utf-8").write(
            json.dumps(state, ensure_ascii=False, indent=1)
        )

    for pattern in ("listen_results*.json", "listen_reviews*.json"):
        for name in glob.glob(os.path.join(project, pattern)):
            data = json.load(io.open(name, encoding="utf-8"))
            for ident in repair:
                data.pop(ident, None)
            io.open(name, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("كتل الإصلاح المستهدف:", len(repair), "· المعرّفات:", ",".join(repair))
    for ident in repair:
        reason = str(reviews.get(ident, {}).get("reason", "")).replace("\n", " ").strip()
        print("سبب الحكم", ident + ":", reason[:240] or "غير مسجل")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
