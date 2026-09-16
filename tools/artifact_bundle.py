"""تجميع المسارات المحددة وفك أرشيف مصادق، دون اتباع روابط أو خروج من الوجهة."""
import glob
import os
from pathlib import Path
import sys
import tarfile


def pack(patterns, output):
    root = Path.cwd().resolve()
    found = sorted({Path(p).absolute() for line in patterns.splitlines() if line.strip()
                    for p in glob.glob(line.strip(), recursive=True)})
    if not found:
        return False
    for p in found:
        if not p.resolve().is_relative_to(root) or p.is_symlink():
            raise ValueError('Unsafe artifact source')
    base = found[0] if len(found) == 1 and found[0].is_dir() else Path(os.path.commonpath([str(p.parent) for p in found]))
    def safe(info):
        if not (info.isfile() or info.isdir()):
            raise ValueError('Artifact links/special files are forbidden')
        return info
    with tarfile.open(output, 'w:gz') as archive:
        for path in found:
            archive.add(path, arcname=path.relative_to(base).as_posix(), filter=safe)
    return True


def unpack(source, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source, 'r:gz') as archive:
        members = archive.getmembers()
        if len(members) > 100000:
            raise ValueError('Artifact contains too many entries')
        # تحقّق من الأرشيف كله قبل استخراج أي بايت؛ حتى الرابط الداخلي مرفوض.
        for member in members:
            if not (member.isfile() or member.isdir()) or Path(member.name).is_absolute():
                raise ValueError('Unsafe artifact member')
            if not (destination / member.name).resolve().is_relative_to(destination):
                raise ValueError('Artifact path escapes destination')
        archive.extractall(destination, members=members, filter='data')


if __name__ == '__main__':
    try:
        action, source, output = sys.argv[1:]
        if action == 'pack':
            if not pack(os.environ.get('ARTIFACT_PATHS', source), output):
                sys.exit(3)
        elif action == 'unpack':
            unpack(source, output)
        else:
            raise ValueError('Unknown operation')
    except Exception:
        print('Artifact bundle failed; no private paths logged.', file=sys.stderr)
        sys.exit(1)
