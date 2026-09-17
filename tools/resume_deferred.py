"""نبضة صريحة؛ لا تعتمد على إشعال push بواسطة GITHUB_TOKEN."""
import json
import os
import subprocess
from pathlib import Path
from finish_command import read_command


def next_deferred(root):
    for path in sorted((Path(root) / "ops" / "finish").glob("*.json")):
        name = "ops/finish/" + path.name
        data = read_command(root, name)
        if data and data.get("مؤجَّل"):
            return name
    return None


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    # جميع الأشواط غير المكتملة، بما فيها queued/waiting، لا in_progress وحدها.
    raw = subprocess.check_output([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{repo}/actions/runs?per_page=100"], text=True, timeout=120)
    pages = json.loads(raw)
    busy = any(run["status"] != "completed" and
               run.get("path", "").split("/")[-1] in ("film.yml", "finish.yml")
               for page in pages for run in page["workflow_runs"])
    if busy:
        print("يوجد إنتاج أو إتمام غير مكتمل؛ لا إطلاق مكرر")
        return
    name = next_deferred(Path.cwd())
    if not name:
        print("لا أمر مؤجل غير مكتمل")
        return
    subprocess.run(["gh", "workflow", "run", "finish.yml", "--repo", repo,
                    "--ref", "master", "-f", "command_file=" + name],
                   check=True, timeout=60)
    print("قُبل طلب الاستئناف: " + name + "؛ قبول الطلب ليس إثبات نجاح النشر")


if __name__ == "__main__":
    main()
