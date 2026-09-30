# -*- coding: utf-8 -*-
"""رفع النسخة المراجعة مرة واحدة خاصة ثم إتاحتها بعد نجاح المعالجة."""
import json,os,pathlib,hashlib,datetime,time,re,subprocess as sp,base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
P=pathlib.Path('repaired'); STATE=pathlib.Path('ops/state/published/series-promo.json')
config=json.loads(pathlib.Path('ops/review/publish-repaired.json').read_text())
report=json.loads((P/'repair_report.json').read_text()); digest=hashlib.sha256((P/'r1.mp4').read_bytes()).hexdigest()
assert digest==report['video_sha256']==config['approved_sha256']
asr=json.loads((P/'ending_asr.json').read_text())
verdict=json.loads(asr['response']['candidates'][0]['content']['parts'][0]['text'])
v=next(x for x in verdict if x['id']=='repaired_tail')
assert v['cut_off'] is False and all(v[k] is True for k in ['subscription_heard','series_heard','description_heard'])
assert 58<report['actual_duration']<61
meta=json.loads(pathlib.Path('proj/publish.json').read_text())['reels'][0]
c=json.loads(os.environ['YT_OAUTH_JSON'])
creds=Credentials(None,refresh_token=c['refresh_token'],client_id=c['client_id'],client_secret=c['client_secret'],token_uri='https://oauth2.googleapis.com/token',scopes=['https://www.googleapis.com/auth/youtube'])
yt=build('youtube','v3',credentials=creds,cache_discovery=False)
channel=yt.channels().list(part='contentDetails',mine=True).execute()['items'][0]
assert channel['id']=='UCda-VgyvZwAH5_Pl1elVEnw'
old=json.loads(STATE.read_text())
record={'slug':'series-promo','title':meta['title'],'previous_publication':old,'release_tag':'series-promo-v2-out','publish_run':os.environ.get('GITHUB_RUN_ID'),'status':'repair_verified','replaces_deleted_video_id':'RLFp0DMlEHU','repair_report':report,'do_not_reupload':True}
def persist():
    record['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    STATE.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    # حفظ مباشر فور الأثر، حتى لو سقطت الخطوة التالية.
    endpoint='repos/'+os.environ['GITHUB_REPOSITORY']+'/contents/'+str(STATE)
    current=json.loads(sp.check_output(['gh','api',endpoint+'?ref=master']))
    body={'message':'تسجيل أثر النسخة المصححة من ريلز السلسلة [skip ci]','branch':'master','sha':current['sha'],'content':base64.b64encode(STATE.read_bytes()).decode()}
    pathlib.Path('/tmp/promo-state.json').write_text(json.dumps(body))
    sp.run(['gh','api','--method','PUT',endpoint,'--input','/tmp/promo-state.json'],stdout=sp.DEVNULL,check=True)
# القناة حارس التكرار أيضاً عند انقطاع بعد الرفع وقبل حفظ المعرّف.
uploads=yt.playlistItems().list(part='snippet',playlistId=channel['contentDetails']['relatedPlaylists']['uploads'],maxResults=50).execute()['items']
candidates=[x['snippet']['resourceId']['videoId'] for x in uploads if x['snippet']['title'].strip()==meta['title'].strip() and x['snippet']['resourceId']['videoId']!='RLFp0DMlEHU']
assert len(candidates)<=1,'عناوين مكررة تحتاج مراجعة، لن يرفع شيئاً'
vid=candidates[0] if candidates else None
if not vid:
    # وثائق videos.insert الحالية: 100 عملية رفع في حصة منفصلة يومياً.
    # https://developers.google.com/youtube/v3/docs/videos/insert
    q=json.loads(pathlib.Path('ops/state/quota_usage.json').read_text())['يوتيوب']
    assert sum(x['ما']=='upload' for x in q['عمليات'])<98
    assert q['وحدات']+200<9600  # هامش محافظ لقراءات الحالة وتحديث الخصوصية
    body={'snippet':{'title':meta['title'],'description':meta['description']+'\n\n#Shorts','tags':meta.get('tags',[]),'categoryId':'27','defaultLanguage':'ar','defaultAudioLanguage':'ar'},'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':True}}
    req=yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(P/'r1.mp4'),chunksize=8*1024*1024,resumable=True,mimetype='video/mp4'))
    response=None
    while response is None:
        _,response=req.next_chunk()
    vid=response['id'];record.update(video_id=vid,url='https://youtube.com/shorts/'+vid,status='uploaded_private_processing')
    persist()
else:
    record.update(video_id=vid,url='https://youtube.com/shorts/'+vid,status='resuming_existing_upload');persist()
for _ in range(40):
    items=yt.videos().list(part='status,contentDetails,processingDetails',id=vid).execute()['items']
    assert items,'تعذرت قراءة الرفع'
    item=items[0];st=item['status'];ps=item.get('processingDetails',{}).get('processingStatus')
    assert st.get('uploadStatus') not in ('failed','rejected','deleted')
    assert ps not in ('failed','terminated')
    if ps=='succeeded' and st.get('uploadStatus')=='processed':break
    time.sleep(15)
else: raise RuntimeError('لم تكتمل معالجة يوتيوب؛ النسخة باقية خاصة، يُستأنف المعرّف نفسه')
m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?',item['contentDetails']['duration']);assert m
seconds=float(m[1] or 0)*3600+float(m[2] or 0)*60+float(m[3] or 0)
assert abs(seconds-report['actual_duration'])<1.1
assert not st.get('madeForKids',False) and not st.get('selfDeclaredMadeForKids',False)
if st['privacyStatus']!='public':
    yt.videos().update(part='status',body={'id':vid,'status':{'privacyStatus':'public','selfDeclaredMadeForKids':False,'containsSyntheticMedia':True}}).execute()
final=yt.videos().list(part='status,contentDetails,processingDetails',id=vid).execute()['items'][0]
assert final['status']['privacyStatus']=='public' and final['status']['uploadStatus']=='processed'
record.update(status='published',published_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),youtube_verified=final,note='نُشرت النسخة المكتملة بإذن المالك بعد حذفه النسخة القديمة. لا تعِد رفعها. الخاتمة أُعيد تركيبها من الصوت الكامل ثم بطاقة 6 ثوان باسم السلسلة.')
persist();print(json.dumps({'video_id':vid,'url':record['url'],'status':'published','duration':seconds},ensure_ascii=False))
