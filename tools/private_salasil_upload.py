"""Private-only salasil uploader. No action occurs on import.

Integration contract: supply a Store backed ONLY by an authenticated GitHub draft
release (not git, logs, artifacts, or a published release). Store.exclusive() must
hold a distributed exclusive lease for the entire call. load/save must recheck
that release.draft is True, and save must synchronously persist. A store adapter
is deliberately required; no unsafe local/default persistence is provided.
Review evidence and file hashes belong in that same private draft release.
"""
import contextlib
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

PRIVATE_AUTHORIZATION = {
    'slug': 'salasil', 'private_only': True, 'allow_incomplete_review': True,
    'revision': 1,
    'review_archive_sha256': 'b7068d6571d036b3cc7c88a9b9cf52d7ec21da9e67cf4c08dd41d0e105b4c83e',
}

class Stop(RuntimeError):
    pass

def require(ok, code):
    if not ok:
        raise Stop(code)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def load_legacy(repo, proj):
    """Use the existing auth/media/shape helpers, never its publishing main."""
    path = Path(repo).resolve() / 'tools/publish_youtube.py'
    require(path.is_file(), 'legacy_module_missing')
    argv = sys.argv[:]
    try:
        sys.argv = [str(path), str(proj)]
        spec = importlib.util.spec_from_file_location('_salasil_legacy', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.argv = argv

def inventory(proj, legacy):
    proj = Path(proj).resolve()
    meta = json.loads((proj / 'publish.json').read_text(encoding='utf-8'))
    require(meta.get('slug') == 'salasil', 'wrong_slug')
    reels = meta.get('reels', [])
    require(len(reels) == 3 and {r.get('file') for r in reels} == {'r1.mp4','r2.mp4','r3.mp4'}, 'wrong_reels')
    entries = [('film.mp4', copy.deepcopy(meta['film']))] + [('reels/'+r['file'], copy.deepcopy(r)) for r in sorted(reels, key=lambda r:r['file'])]
    chapters = proj / 'الفصول.txt'
    titles = []
    out = []
    for name, m in entries:
        p = proj / name
        require(p.is_file() and p.stat().st_size > 0 and p.resolve().is_relative_to(proj), 'missing_or_unsafe_media')
        require(isinstance(m.get('title'), str) and 0 < len(m['title'].strip()) <= 100, 'invalid_title')
        m['title'] = m['title'].strip()
        require(re.search(r'[\u0600-\u06ff]', m['title']), 'arabic_title_required')
        require(isinstance(m.get('description'), str), 'missing_description')
        if '{CHAPTERS}' in m['description']:
            require(chapters.is_file(), 'chapters_missing')
            ch = chapters.read_text(encoding='utf-8').strip()
            require(bool(ch), 'chapters_empty')
            m['description'] = m['description'].replace('{CHAPTERS}', ch)
        if name.startswith('reels/'):
            ok, _ = legacy.reel_shape(str(p))
            require(ok, 'reel_shape_failed')
        titles.append(m['title'])
        out.append((name, p, m, digest(p)))
    require(len(set(titles)) == 4, 'duplicate_titles')
    thumb = proj / 'thumb-a.jpg'
    require(thumb.is_file() and thumb.stat().st_size > 0 and thumb.resolve().is_relative_to(proj), 'thumbnail_missing_or_unsafe')
    return out, thumb

def marker(name, sha):
    return '[salasil-private:' + hashlib.sha256((name+':'+sha).encode()).hexdigest() + ']'

def recent(svc):
    ch = svc.channels().list(part='contentDetails', mine=True).execute()
    require(len(ch.get('items', [])) == 1, 'channel_ambiguous')
    channel = ch['items'][0]
    playlist = channel['contentDetails']['relatedPlaylists']['uploads']
    result, token, seen = [], None, set()
    # Read only the channel's system uploads playlist; no playlist mutation.
    for _ in range(200):
        args = dict(part='snippet', playlistId=playlist, maxResults=50)
        if token:
            args['pageToken'] = token
        r = svc.playlistItems().list(**args).execute()
        result.extend(r.get('items', []))
        token = r.get('nextPageToken')
        if not token:
            return result
        require(token not in seen, 'pagination_loop')
        seen.add(token)
    raise Stop('channel_scan_incomplete')

def read_video(svc, vid):
    require(isinstance(vid,str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', vid), 'invalid_video_id')
    items = svc.videos().list(part='snippet,status', id=vid).execute().get('items', [])
    require(len(items) == 1 and items[0]['id'] == vid, 'video_unreadable')
    return items[0]

def private(svc, vid, tag):
    v = read_video(svc, vid)
    require(tag in v['snippet'].get('description', ''), 'video_identity_mismatch')
    s = v['status']
    if s.get('privacyStatus') != 'private' or s.get('publishAt'):
        # Omitting publishAt in a full status update clears the schedule.
        svc.videos().update(part='status', body={'id':vid, 'status':{
            'privacyStatus':'private', 'selfDeclaredMadeForKids':False,
            'containsSyntheticMedia':True}}).execute()
        s = read_video(svc, vid)['status']
    require(s.get('privacyStatus') == 'private' and not s.get('publishAt'), 'privacy_verification_failed')
    require(s.get('madeForKids') is not True and s.get('selfDeclaredMadeForKids') is not True, 'children_classification')
    return s

def persist(store, state):
    store.save(copy.deepcopy(state))
    require(store.load() == state, 'checkpoint_readback_failed')

def run(repo, proj, store, *, legacy=None):
    """Adapter must validate private-draft storage and provide exclusive locking.

    Initial state must contain review={approved:True, sha256:{filename:hash,...},
    evidence:...}. A previous pending upload with no positively identified video
    blocks forever rather than retrying a possibly successful upload.
    """
    require(store is not None, 'private_draft_store_required')
    with store.exclusive():
        require(store.is_private_draft() is True, 'private_draft_required')
        legacy = legacy or load_legacy(repo, proj)
        entries, thumb = inventory(proj, legacy)
        state = store.load()
        require(isinstance(state, dict) and state.get('slug') == 'salasil', 'checkpoint_slug_mismatch')
        review = state.get('review', {})
        require((review.get('approved') is True or (review.get('private_upload_authorized') is True and review.get('authorization') == PRIVATE_AUTHORIZATION)) and bool(review.get('evidence')), 'review_not_approved')
        hashes = {name:sha for name, _, _, sha in entries}
        hashes['thumb-a.jpg'] = digest(thumb)
        require(review.get('sha256') == hashes, 'review_hash_mismatch')
        state.setdefault('videos', {})
        require(set(state['videos']).issubset({e[0] for e in entries}), 'unexpected_checkpoint_items')
        svc = legacy.yt()
        for name, path, meta, sha in entries:
            require(store.is_private_draft() is True, 'draft_no_longer_private')
            require(digest(path) == sha, 'media_changed')
            tag = marker(name, sha)
            rec = state['videos'].get(name)
            if rec:
                require(rec.get('sha256') == sha and rec.get('title') == meta['title'], 'checkpoint_identity_changed')
            # Fail closed on any read failure. Preserve all title collisions.
            hits = [i for i in recent(svc) if i['snippet']['title'].strip() == meta['title']]
            require(len(hits) <= 1, 'ambiguous_title_matches')
            vid = rec.get('id') if rec else None
            if hits:
                found = hits[0]['snippet']['resourceId']['videoId']
                require(not vid or vid == found, 'checkpoint_channel_conflict')
                require(tag in read_video(svc, found)['snippet'].get('description',''), 'unproven_title_match')
                vid = found
            if not vid:
                require(not rec, 'previous_upload_uncertain')
                description = meta['description']
                if '{FILM_URL}' in description:
                    require(name != 'film.mp4', 'invalid_film_placeholder')
                    description = description.replace('{FILM_URL}', 'https://youtu.be/'+state['videos']['film.mp4']['id'])
                if name.startswith('reels/') and '#Shorts' not in description:
                    description += '\n\n#Shorts'
                description += '\n\n'+tag
                require(len(description) <= 5000 and not re.search(r'\{[A-Z_]+\}', description), 'invalid_description')
                rec = {'sha256':sha, 'title':meta['title'], 'phase':'pending'}
                state['videos'][name] = rec
                persist(store, state)  # Intent precedes any irreversible request.
                req = svc.videos().insert(part='snippet,status', notifySubscribers=False,
                    body={'snippet':{'title':meta['title'], 'description':description,
                        'tags':meta.get('tags', []), 'categoryId':str(meta.get('categoryId','27')),
                        'defaultLanguage':'ar', 'defaultAudioLanguage':'ar'},
                        'status':{'privacyStatus':'private', 'selfDeclaredMadeForKids':False,
                                  'containsSyntheticMedia':True}},
                    media_body=legacy.MediaFileUpload(str(path), chunksize=8*1024*1024, resumable=True, mimetype='video/mp4'))
                response = None
                while response is None:
                    _, response = req.next_chunk(num_retries=0)
                vid = response['id']
                rec['id'], rec['phase'] = vid, 'uploaded'
                persist(store, state)  # First operation after the returned ID.
            else:
                rec = {'sha256':sha, 'title':meta['title'], 'id':vid, 'phase':'recovered'}
                state['videos'][name] = rec
                persist(store, state)
            rec['verified_status'] = private(svc, vid, tag)
            rec['phase'] = 'private_verified'
            persist(store, state)
            if name == 'film.mp4':
                require(digest(thumb) == hashes['thumb-a.jpg'], 'thumbnail_changed')
                svc.thumbnails().set(videoId=vid, media_body=legacy.MediaFileUpload(str(thumb))).execute()
                rec['thumbnail_set'] = True
                persist(store, state)
            print(json.dumps({'id':vid, 'status':'private_verified'}), flush=True)
        # Re-read all four after completing the batch.
        for name, _, _, sha in entries:
            private(svc, state['videos'][name]['id'], marker(name,sha))
        state['complete'] = True
        persist(store, state)
        return {name:state['videos'][name]['id'] for name, _, _, _ in entries}

class DraftReleaseStore:
    """Run ONLY in the workflow-wide mutafail-sealed-publish concurrency group.

    Immutable revision assets survive --clobber's delete/create gap. The fixed
    checkpoint filename is a convenience mirror, never the authoritative copy.
    No subprocess stdout/stderr (including titles or credentials) is forwarded.
    """
    PREFIX = 'salasil-private-upload-state.'
    FIXED = 'salasil-private-upload-state.json'

    def __init__(self, release, review):
        import os
        self.release, self.review = release, review
        self.repo = os.environ.get('GITHUB_REPOSITORY', '')
        require(release == 'salasil-out' and bool(self.repo), 'invalid_release_context')
        self.version = 0

    def gh(self, *args):
        import subprocess
        result = subprocess.run(['gh', *args], capture_output=True, text=True)
        require(result.returncode == 0, 'private_checkpoint_command_failed')
        return result.stdout

    def detail(self):
        d = json.loads(self.gh('api', 'repos/'+self.repo+'/releases/tags/'+self.release))
        require(d.get('draft') is True and d.get('tag_name') == self.release, 'release_not_draft')
        return d

    def is_private_draft(self):
        self.detail()
        return True

    @contextlib.contextmanager
    def exclusive(self):
        import os
        # Workflow integration MUST set job/workflow concurrency to this exact
        # group with cancel-in-progress:false. This is an explicit attestation,
        # not an independent GitHub concurrency inspector.
        require(os.environ.get('GITHUB_ACTIONS') == 'true' and
                os.environ.get('SALASIL_PRIVATE_LOCK') == 'mutafail-sealed-publish',
                'workflow_exclusive_lock_required')
        self.detail()
        yield

    def load(self):
        import tempfile
        assets = self.detail().get('assets')
        require(isinstance(assets, list), 'release_asset_listing_missing')
        names = [a['name'] for a in assets]
        require(len(names) == len(set(names)), 'duplicate_checkpoint_assets')
        revisions = []
        for n in names:
            m = re.fullmatch(re.escape(self.PREFIX)+r'(\d{8})\.json', n)
            if m:
                revisions.append((int(m[1]), n))
        if revisions:
            self.version, selected = max(revisions)
        elif self.FIXED in names:
            # Never assume a legacy fixed checkpoint is absent or safe to reset.
            selected = self.FIXED
        else:
            require(not any(n.startswith('salasil-private-upload-state') for n in names), 'unrecognized_checkpoint_asset')
            return {'slug':'salasil', 'review':copy.deepcopy(self.review)}
        with tempfile.TemporaryDirectory(prefix='private-checkpoint-') as d:
            self.gh('release','download',self.release,'--repo',self.repo,'--pattern',selected,'--dir',d)
            data = json.loads((Path(d)/selected).read_text(encoding='utf-8'))
        require(isinstance(data, dict), 'invalid_checkpoint')
        return data

    def save(self, state):
        import tempfile
        self.detail()
        self.version += 1
        name = self.PREFIX+f'{self.version:08d}'+'.json'
        with tempfile.TemporaryDirectory(prefix='private-checkpoint-') as d:
            path = Path(d)/name
            path.write_text(json.dumps(state, ensure_ascii=False),encoding='utf-8')
            path.chmod(0o600)
            # No clobber: existing revision collision aborts, never overwrites.
            self.gh('release','upload',self.release,str(path),'--repo',self.repo)
            self.detail()
            fixed = Path(d)/self.FIXED
            fixed.write_text(path.read_text(encoding='utf-8'),encoding='utf-8')
            fixed.chmod(0o600)
            self.gh('release','upload',self.release,str(fixed),'--repo',self.repo,'--clobber')
        self.detail()


def review_for_upload(report, authorization=None):
    require(report.get('slug') == 'salasil' and report.get('review_kind') == 'automated', 'wrong_review_identity')
    passed = report.get('status') == 'passed' and all(report.get('checks', {}).get(k) is True for k in
        ('audio','clips','technical','final_audio','policy','opening'))
    waived = authorization == PRIVATE_AUTHORIZATION
    require(passed or waived, 'review_not_approved')
    hashes = dict(report.get('files', {}))
    hashes['thumb-a.jpg'] = report.get('thumbnail_sha256')
    require(set(hashes) == {'film.mp4','reels/r1.mp4','reels/r2.mp4','reels/r3.mp4','thumb-a.jpg'}, 'invalid_review_inventory')
    require(all(isinstance(v,str) and re.fullmatch(r'[0-9a-f]{64}',v) for v in hashes.values()), 'invalid_review_hash')
    return {'approved':passed, 'private_upload_authorized':waived,
        'authorization':authorization if waived else None, 'sha256':hashes, 'evidence':report}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--proj',required=True)
    parser.add_argument('--review',required=True)
    parser.add_argument('--private-authorization-file')
    parser.add_argument('--state-release',default='salasil-out',choices=['salasil-out'])
    parser.add_argument('--repo-root',default='.')
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.review).read_text(encoding='utf-8'))
        authorization = None
        if args.private_authorization_file:
            auth_path = Path(args.private_authorization_file).resolve()
            require(auth_path == (Path(args.repo_root).resolve()/'ops/salasil-private-authorized.json'), 'wrong_authorization_path')
            authorization = json.loads(auth_path.read_text(encoding='utf-8'))
            require(authorization == PRIVATE_AUTHORIZATION, 'wrong_private_authorization')
        review = review_for_upload(report, authorization)
        print(json.dumps({'review_complete':review['approved'], 'upload_authorized_private_only':True}),flush=True)
        run(args.repo_root,args.proj,DraftReleaseStore(args.state_release,review))
    except Exception as exc:
        # Only our static error codes or an exception class, never SDK payloads.
        code = str(exc) if isinstance(exc, Stop) else type(exc).__name__
        print(json.dumps({'status':'blocked','code':code}),flush=True)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())

