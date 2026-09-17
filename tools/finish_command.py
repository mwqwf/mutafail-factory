"""اختيار أمر إتمام محدد والتحقق منه قبل تمريره إلى خطوات النشر."""
import json
import re
from pathlib import Path


def read_command(root, filename):
    root = Path(root).resolve()
    if not re.fullmatch(r"ops/finish/[a-z0-9][a-z0-9_-]*\.json", filename):
        raise ValueError("مسار أمر الإتمام غير صالح")
    path = (root / filename).resolve()
    if not path.is_relative_to(root / "ops" / "finish"):
        raise ValueError("مسار خارج دليل الإتمام")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("تمّ"):
        return None
    patterns = {"runId": r"[0-9]+", "videoId": r"[A-Za-z0-9_-]{11}",
                "command": r"[a-z0-9][a-z0-9_-]*"}
    for key, pattern in patterns.items():
        if not isinstance(data.get(key), str) or not re.fullmatch(pattern, data[key]):
            raise ValueError("حقل أمر الإتمام غير صالح: " + key)
    if path.stem != data["command"]:
        raise ValueError("اسم ملف الإتمام لا يطابق الأمر")
    return data


if __name__ == "__main__":
    import sys
    data = read_command(Path.cwd(), sys.argv[1])
    print("execute=" + ("true" if data else "false"))
    if data:
        for key in ("runId", "videoId", "command"):
            print(key + "=" + data[key])
