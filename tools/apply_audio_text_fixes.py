# -*- coding: utf-8 -*-
"""يطبق إصلاحات نصية صوتية مستهدفة ويُبطل كاش المقطع وحده."""
import glob
import io
import json
import os
import sys


def save_json(path, data):
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    )
    os.replace(tmp, path)


def main(project, fixes_file, output_file):
    if not os.path.isfile(fixes_file):
        save_json(output_file, {"ids": []})
        print("لا إصلاحات نصية صوتية مستهدفة")
        return

    spec = json.load(io.open(fixes_file, encoding="utf-8"))
    replacements = spec.get("replacements", spec)
    blocks_path = os.path.join(project, "blocks.json")
    blocks = json.load(io.open(blocks_path, encoding="utf-8"))
    by_id = {b.get("id"): b for b in blocks}
    changed = []

    for ident, text in replacements.items():
        if ident not in by_id:
            raise SystemExit("معرّف إصلاح غير موجود: " + ident)
        if not isinstance(text, str) or not text.strip():
            raise SystemExit("نص إصلاح غير صالح: " + ident)
        if by_id[ident].get("text") == text:
            continue
        by_id[ident]["text"] = text
        changed.append(ident)

    if not changed:
        save_json(output_file, {"ids": []})
        print("الإصلاحات النصية مطبقة سلفاً")
        return

    save_json(blocks_path, blocks)
    for ident in changed:
        audio = os.path.join(project, "audio", ident + ".wav")
        if os.path.isfile(audio):
            os.remove(audio)

    for state_name in glob.glob(os.path.join(project, "gen_state*.json")):
        try:
            state = json.load(io.open(state_name, encoding="utf-8"))
        except Exception:
            continue
        for ident in changed:
            if isinstance(state.get("done"), dict):
                state["done"].pop(ident, None)
            if isinstance(state.get("model_of"), dict):
                state["model_of"].pop(ident, None)
        save_json(state_name, state)

    for pattern in ("listen_results*.json", "listen_reviews*.json"):
        for name in glob.glob(os.path.join(project, pattern)):
            try:
                data = json.load(io.open(name, encoding="utf-8"))
            except Exception:
                continue
            for ident in changed:
                data.pop(ident, None)
            save_json(name, data)

    save_json(output_file, {"ids": changed})
    print("إصلاحات النص الصوتي المستهدفة:", ",".join(changed))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
