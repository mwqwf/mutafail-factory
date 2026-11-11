import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('uploader', Path(__file__).with_name('private_salasil_upload.py'))
u=importlib.util.module_from_spec(spec); spec.loader.exec_module(u)

class Store:
    def __init__(self,state): self.state=state; self.writes=[]; self.draft=True
    def exclusive(self): return contextlib.nullcontext()
    def is_private_draft(self): return self.draft
    def load(self): return copy.deepcopy(self.state)
    def save(self,s): self.state=copy.deepcopy(s); self.writes.append(copy.deepcopy(s))

class Request:
    def __init__(self,fn): self.fn=fn
    def execute(self): return self.fn()
    def next_chunk(self,**kwargs): return None,self.fn()

class Service:
    def __init__(self,store): self.store=store; self.data={}; self.inserts=[]; self.updates=[]; self.thumbs=[]; self.fail_upload=False; self.fail_read=False
    def videos(self): return SimpleNamespace(list=self.vlist,insert=self.insert,update=self.update)
    def vlist(self,**kw): return Request(lambda:{'items':[copy.deepcopy(self.data[kw['id']])] if kw['id'] in self.data else []})
    def insert(self,**kw):
        assert any(v['phase']=='pending' for v in self.store.state['videos'].values())
        assert kw['notifySubscribers'] is False
        assert kw['body']['status']=={'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':True}
        self.inserts.append(kw)
        def finish():
            vid='abcdefghij'+str(len(self.inserts))
            self.data[vid]={'id':vid,**copy.deepcopy(kw['body'])}
            if self.fail_upload: raise OSError('uncertain')
            return {'id':vid}
        return Request(finish)
    def update(self,**kw):
        self.updates.append(kw)
        def finish(): self.data[kw['body']['id']]['status']=copy.deepcopy(kw['body']['status']); return {}
        return Request(finish)
    def channels(self): return SimpleNamespace(list=lambda **kw:Request(lambda:{'items':[{'contentDetails':{'relatedPlaylists':{'uploads':'channel_uploads'}}}]}))
    def playlistItems(self): return SimpleNamespace(list=self.plist)
    def plist(self,**kw):
        def finish():
            if self.fail_read: raise OSError('read_failed')
            return {'items':[{'snippet':{'title':v['snippet']['title'],'resourceId':{'videoId':k}}} for k,v in self.data.items()]}
        return Request(finish)
    def thumbnails(self): return SimpleNamespace(set=self.thumb)
    def thumb(self,**kw):
        assert self.data[kw['videoId']]['status']['privacyStatus']=='private'
        self.thumbs.append(kw)
        return Request(lambda:{})

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.p=Path(self.tmp.name); (self.p/'reels').mkdir()
        for n in ['film.mp4','reels/r1.mp4','reels/r2.mp4','reels/r3.mp4','thumb-a.jpg']: (self.p/n).write_bytes(n.encode())
        self.meta={'slug':'salasil','publicNow':True,'publishAt':'2099-01-01T00:00:00Z','film':{'title':'الفيلم','description':'وصف'},'reels':[{'file':f'r{i}.mp4','title':f'ريلز {i}','description':'وصف {FILM_URL}'} for i in range(1,4)]}
        self.write_meta()
        self.store=Store({'slug':'salasil','review':{'approved':True,'evidence':'private-review-report','sha256':{n:u.digest(self.p/n) for n in ['film.mp4','reels/r1.mp4','reels/r2.mp4','reels/r3.mp4','thumb-a.jpg']}}})
        self.svc=Service(self.store)
        self.legacy=SimpleNamespace(yt=lambda:self.svc, reel_shape=lambda p:(True,'ok'), MediaFileUpload=lambda *a,**k:('media',a,k))
    def tearDown(self): self.tmp.cleanup()
    def write_meta(self): (self.p/'publish.json').write_text(json.dumps(self.meta))
    def run_it(self):
        with contextlib.redirect_stdout(io.StringIO()): return u.run('.',self.p,self.store,legacy=self.legacy)
    def test_all_private_and_resume(self):
        ids=self.run_it(); self.assertEqual(len(ids),4); self.assertEqual(len(self.svc.inserts),4)
        self.run_it(); self.assertEqual(len(self.svc.inserts),4)
        self.assertTrue(self.store.state['complete'])
        for r in self.svc.inserts: self.assertNotIn('publishAt',r['body']['status'])
    def test_explicit_incomplete_review_keeps_every_upload_private(self):
        self.store.state['review'].update(approved=False,private_upload_authorized=True,authorization=copy.deepcopy(u.PRIVATE_AUTHORIZATION))
        ids=self.run_it();self.assertEqual(len(ids),4);self.assertFalse(self.store.state['review']['approved'])
        self.assertTrue(all(x['body']['status']['privacyStatus']=='private' and 'publishAt' not in x['body']['status'] for x in self.svc.inserts))
    def test_incomplete_review_wrong_authorization_blocks_run(self):
        self.store.state['review'].update(approved=False,private_upload_authorized=True,authorization={'private_only':True})
        with self.assertRaisesRegex(u.Stop,'review_not_approved'):self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_wrong_slug(self):
        self.meta['slug']='other'; self.write_meta()
        with self.assertRaisesRegex(u.Stop,'wrong_slug'): self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_extra_reel(self):
        self.meta['reels'].append({'file':'r4.mp4'}); self.write_meta()
        with self.assertRaisesRegex(u.Stop,'wrong_reels'): self.run_it()
    def test_review_hash_mismatch(self):
        (self.p/'film.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(u.Stop,'review_hash_mismatch'): self.run_it()
    def test_not_draft(self):
        self.store.draft=False
        with self.assertRaisesRegex(u.Stop,'private_draft_required'): self.run_it()
    def test_channel_read_failure_no_insert(self):
        self.svc.fail_read=True
        with self.assertRaises(OSError): self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_pending_unknown_blocks(self):
        self.store.state['videos']={'film.mp4':{'title':'الفيلم','sha256':u.digest(self.p/'film.mp4'),'phase':'pending'}}
        with self.assertRaisesRegex(u.Stop,'previous_upload_uncertain'): self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_uncertain_success_recovers(self):
        self.svc.fail_upload=True
        with self.assertRaises(OSError): self.run_it()
        self.assertEqual(self.store.state['videos']['film.mp4']['phase'],'pending')
        self.svc.fail_upload=False; self.run_it()
        self.assertEqual(len(self.svc.inserts),4)
    def test_title_only_refused(self):
        self.svc.data['abcdefghij0']={'id':'abcdefghij0','snippet':{'title':'الفيلم','description':'other'},'status':{'privacyStatus':'private'}}
        with self.assertRaisesRegex(u.Stop,'unproven_title_match'): self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_ambiguous_title_refused(self):
        for x in ['0','1']: self.svc.data['abcdefghij'+x]={'id':'abcdefghij'+x,'snippet':{'title':'الفيلم','description':'other'},'status':{'privacyStatus':'private'}}
        with self.assertRaisesRegex(u.Stop,'ambiguous_title_matches'): self.run_it()
    def test_schedule_removed_on_exact_video(self):
        self.run_it(); vid=self.store.state['videos']['film.mp4']['id']
        self.svc.data[vid]['status']['publishAt']='2099-01-01T00:00:00Z'
        self.run_it(); self.assertEqual(len(self.svc.updates),1)
        self.assertNotIn('publishAt',self.svc.data[vid]['status'])
    def test_bad_shape_prevents_all_uploads(self):
        self.legacy.reel_shape=lambda p:(False,'bad')
        with self.assertRaisesRegex(u.Stop,'reel_shape_failed'): self.run_it()
        self.assertFalse(self.svc.inserts)
    def test_checkpoint_immediate_before_verification(self):
        with patch.object(u,'private',side_effect=u.Stop('verify_failed')):
            with self.assertRaisesRegex(u.Stop,'verify_failed'): self.run_it()
        self.assertEqual(self.store.state['videos']['film.mp4']['id'],'abcdefghij1')
        self.assertEqual(len(self.svc.inserts),1)
    def test_output_only_id_and_status(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): u.run('.',self.p,self.store,legacy=self.legacy)
        for line in out.getvalue().splitlines(): self.assertEqual(set(json.loads(line)),{'id','status'})

class AdapterTests(unittest.TestCase):
    def make(self):
        with patch.dict('os.environ', {'GITHUB_REPOSITORY':'owner/repo'}):
            return u.DraftReleaseStore('salasil-out', {'approved':True})
    def test_absence_requires_successful_asset_listing(self):
        store=self.make()
        with patch.object(store,'detail',return_value={'assets':[]}):
            self.assertEqual(store.load()['slug'],'salasil')
        with patch.object(store,'detail',side_effect=u.Stop('denied')):
            with self.assertRaises(u.Stop): store.load()
        with patch.object(store,'detail',return_value={}):
            with self.assertRaisesRegex(u.Stop,'asset_listing'): store.load()
    def test_draft_read_uses_verified_release_id_not_unpublished_tag(self):
        store=self.make()
        with patch.object(store,'gh',return_value=json.dumps({'draft':True,'tag_name':'salasil-out'})) as call:
            self.assertTrue(store.is_private_draft())
            call.assert_called_once_with('api','repos/owner/repo/releases/441521130')
    def test_published_release_rejected(self):
        store=self.make()
        with patch.object(store,'gh',return_value=json.dumps({'draft':False,'tag_name':'salasil-out'})):
            with self.assertRaisesRegex(u.Stop,'release_not_draft'): store.is_private_draft()
    def test_missing_lock_rejected(self):
        store=self.make()
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaisesRegex(u.Stop,'workflow_exclusive_lock_required'):
                with store.exclusive(): pass
    def test_newest_immutable_revision_wins_over_mirror(self):
        store=self.make()
        names=[store.FIXED,store.PREFIX+'00000001.json',store.PREFIX+'00000002.json']
        def gh(*args):
            name=args[args.index('--pattern')+1]
            directory=args[args.index('--dir')+1]
            self.assertEqual(name,names[-1])
            (Path(directory)/name).write_text(json.dumps({'slug':'salasil','revision':2}))
            return ''
        with patch.object(store,'detail',return_value={'assets':[{'name':n} for n in names]}),patch.object(store,'gh',side_effect=gh):
            self.assertEqual(store.load()['revision'],2)
    def test_journal_written_before_clobber_mirror(self):
        store=self.make(); calls=[]
        with patch.object(store,'detail',return_value={'assets':[]}),patch.object(store,'gh',side_effect=lambda *args:calls.append(args) or ''):
            store.save({'slug':'salasil'})
        self.assertEqual(len(calls),2)
        self.assertNotIn('--clobber',calls[0]); self.assertIn('--clobber',calls[1])

class AuthorizationTests(unittest.TestCase):
    def report(self):
        return {'slug':'salasil','review_kind':'automated','status':'failed','checks':{'technical':True},
            'files':{k:'a'*64 for k in ('film.mp4','reels/r1.mp4','reels/r2.mp4','reels/r3.mp4')},'thumbnail_sha256':'b'*64}
    def test_incomplete_still_requires_explicit_private_authorization(self):
        with self.assertRaisesRegex(u.Stop,'review_not_approved'):u.review_for_upload(self.report())
    def test_authorization_does_not_mark_review_passed(self):
        r=u.review_for_upload(self.report(),copy.deepcopy(u.PRIVATE_AUTHORIZATION))
        self.assertFalse(r['approved']);self.assertTrue(r['private_upload_authorized']);self.assertEqual(r['evidence']['status'],'failed')
    def test_wrong_scope_and_hashes_rejected(self):
        a=copy.deepcopy(u.PRIVATE_AUTHORIZATION);a['private_only']=False
        with self.assertRaises(u.Stop):u.review_for_upload(self.report(),a)
        r=self.report();r['files']['film.mp4']='bad'
        with self.assertRaisesRegex(u.Stop,'invalid_review_hash'):u.review_for_upload(r,u.PRIVATE_AUTHORIZATION)
    def test_missing_file_rejected_even_with_authorization(self):
        r=self.report();del r['files']['reels/r3.mp4']
        with self.assertRaisesRegex(u.Stop,'invalid_review_inventory'):u.review_for_upload(r,u.PRIVATE_AUTHORIZATION)

if __name__=='__main__': unittest.main()

