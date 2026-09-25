"""يربط إثبات الشعار ببايتات الفيديو والشعار، كي لا يعبر تصيير قديم مسار الاستئناف."""
import hashlib
import json
from pathlib import Path
import envpaths


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(video, layout):
    video = Path(video)
    receipt = json.loads(Path(str(video) + '.logo.json').read_text(encoding='utf-8'))
    return (receipt.get('passed') is True and receipt.get('layout') == layout
            and receipt.get('video_sha256') == digest(video)
            and receipt.get('logo_sha256') == digest(envpaths.logo()))
