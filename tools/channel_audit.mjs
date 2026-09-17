// جرد قناة المتفائل، وتنظيف عناوين محددة اختيارياً مع نسخة استرجاع وتحقق.
import fs from 'node:fs';
import crypto from 'node:crypto';
const mode = process.argv[2];
function seal(data,path){
  const key=crypto.randomBytes(32),iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',key,iv);
  const body=Buffer.concat([cipher.update(JSON.stringify(data)),cipher.final()]);
  const wrapped=crypto.publicEncrypt({key:fs.readFileSync('ops/audit-public.pem'),oaepHash:'sha256'},key);
  fs.writeFileSync(path,JSON.stringify({key:wrapped.toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),body:body.toString('base64')}));
}
if (mode === 'keygen') {
  const pair = crypto.generateKeyPairSync('rsa', {modulusLength: 3072,
    publicKeyEncoding: {type:'spki', format:'pem'},
    privateKeyEncoding: {type:'pkcs8', format:'pem'}});
  fs.writeFileSync('audit-private.pem', pair.privateKey, {mode:0o600, flag:'wx'});
  fs.writeFileSync('audit-public.pem', pair.publicKey, {flag:'wx'});
  console.log('Generated local audit key; private key stays local.');
} else if (mode === 'decrypt') {
  const e=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
  const key=crypto.privateDecrypt({key:fs.readFileSync('audit-private.pem'),oaepHash:'sha256'},Buffer.from(e.key,'base64'));
  const dec=crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(e.iv,'base64'));
  dec.setAuthTag(Buffer.from(e.tag,'base64'));
  const plain=Buffer.concat([dec.update(Buffer.from(e.body,'base64')),dec.final()]);
  fs.writeFileSync('channel-data.json',plain);
  console.log('Decrypted audit locally.');
} else if (mode === 'collect') {
  const oauth=JSON.parse(process.env.YT_OAUTH_JSON || '{}');
  const tr=await fetch('https://oauth2.googleapis.com/token',{method:'POST',body:new URLSearchParams({
    client_id:oauth.client_id,client_secret:oauth.client_secret,refresh_token:oauth.refresh_token,grant_type:'refresh_token'
  }),signal:AbortSignal.timeout(30000)});
  if(!tr.ok) throw new Error('OAuth refresh failed: HTTP '+tr.status);
  const auth=await tr.json();
  async function get(base,params){
    const url=new URL(base); for(const [k,v] of Object.entries(params)) if(v!==undefined)url.searchParams.set(k,v);
    const r=await fetch(url,{headers:{Authorization:'Bearer '+auth.access_token},signal:AbortSignal.timeout(30000)});
    const d=await r.json();
    if(!r.ok) return {error:{status:r.status,reasons:d.error?.errors?.map(e=>e.reason),message:d.error?.message}};
    return d;
  }
  const yt=(path,p)=>get('https://www.googleapis.com/youtube/v3/'+path,p);
  const channel=await yt('channels',{part:'snippet,statistics,contentDetails',id:'UCda-VgyvZwAH5_Pl1elVEnw'});
  if(!channel.items?.length)throw new Error('Channel lookup failed');
  const ch=channel.items[0];
  const ids=[];let page;
  do{
    const p=await yt('playlistItems',{part:'contentDetails',playlistId:ch.contentDetails.relatedPlaylists.uploads,maxResults:50,pageToken:page});
    if(p.error)throw new Error('Uploads lookup failed');
    ids.push(...p.items.map(i=>i.contentDetails.videoId));page=p.nextPageToken;
  }while(page);
  // مصدر ثان للجرد يعالج تكرار فيديو في قائمة الرفعات عند عبور الصفحات.
  page=undefined;
  do{
    const p=await yt('search',{part:'id',channelId:ch.id,type:'video',order:'date',maxResults:50,pageToken:page});
    if(p.error)break;ids.push(...p.items.map(i=>i.id.videoId));page=p.nextPageToken;
  }while(page);
  const uniqueIds=[...new Set(ids)];
  const videos=[];
  for(let i=0;i<uniqueIds.length;i+=50){
    const r=await yt('videos',{part:'snippet,contentDetails,statistics,status',id:uniqueIds.slice(i,i+50).join(',')});
    if(r.error)throw new Error('Video lookup failed');
    videos.push(...r.items);
  }
  const playlists=[];page=undefined;
  do{
    const p=await yt('playlists',{part:'snippet,contentDetails',channelId:ch.id,maxResults:50,pageToken:page});
    if(p.error)break;playlists.push(...p.items);page=p.nextPageToken;
  }while(page);
  const comments={};
  const seconds=s=>{const m=s.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);return m?(+(m[1]||0)*3600+ +(m[2]||0)*60+ +(m[3]||0)):0;};
  for(const v of videos.filter(v=>v.status.privacyStatus==='public'&&seconds(v.contentDetails.duration)>180)){
    const r=await yt('commentThreads',{part:'snippet',videoId:v.id,maxResults:10,order:'relevance',textFormat:'plainText'});
    comments[v.id]=r.error?{error:r.error}:r.items.map(i=>({text:i.snippet.topLevelComment.snippet.textOriginal,likes:i.snippet.topLevelComment.snippet.likeCount,replies:i.snippet.totalReplyCount}));
    if(r.error?.reasons?.includes('insufficientPermissions'))break;
  }
  const end=new Date(Date.now()-86400000).toISOString().slice(0,10);
  const start=new Date(Date.now()-29*86400000).toISOString().slice(0,10);
  const analytics=await get('https://youtubeanalytics.googleapis.com/v2/reports',{
    ids:'channel==MINE',startDate:start,endDate:end,dimensions:'video',maxResults:200,
    metrics:'views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares',sort:'-views'
  });
  const data={fetchedAt:new Date().toISOString(),channel:ch,videos,playlists,comments,analytics,analyticsPeriod:{start,end},oauthScopes:auth.scope};
  seal(data,'channel-audit.enc.json');
  data.reportingDiscovery={types:await get('https://youtubereporting.googleapis.com/v1/reportTypes',{}),jobs:await get('https://youtubereporting.googleapis.com/v1/jobs',{})};
  seal(data,'channel-audit.enc.json');
  if(!analytics.error){
    data.analyticsReports={};
    const yearStart=new Date(Date.now()-365*86400000).toISOString().slice(0,10);
    const base={ids:'channel=='+ch.id,startDate:yearStart,endDate:end};
    const reports={
      yearTotal:{metrics:'views,estimatedMinutesWatched,subscribersGained,subscribersLost'},
      yearContentType:{dimensions:'creatorContentType',metrics:'views,estimatedMinutesWatched,subscribersGained,subscribersLost'},
      daily:{startDate:start,dimensions:'day',metrics:'views,estimatedMinutesWatched,subscribersGained,subscribersLost',sort:'day'},
      traffic:{startDate:start,dimensions:'insightTrafficSourceType',metrics:'views,estimatedMinutesWatched',sort:'-views'},
      countries:{startDate:start,dimensions:'country',metrics:'views,estimatedMinutesWatched',sort:'-views',maxResults:25},
      devices:{startDate:start,dimensions:'deviceType',metrics:'views,estimatedMinutesWatched'},
      engagement:{startDate:start,dimensions:'video',metrics:'engagedViews,views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage',sort:'-views',maxResults:200}
    };
    for(const [name,params] of Object.entries(reports)){
      data.analyticsReports[name]=await get('https://youtubeanalytics.googleapis.com/v2/reports',{...base,...params});
      seal(data,'channel-audit.enc.json');
    }
    data.retention={};data.videoTraffic={};
    for(const id of ['ncvHqTIW5zA','snaggx_3Mpo','inQNv8vjv-U','KiXoeCfbdX0','BjqSe2z9Y3Q','hBXUglsWwE0','m2wEErDQmvo','kE4zt39LmGk']){
      data.retention[id]=await get('https://youtubeanalytics.googleapis.com/v2/reports',{...base,startDate:start,dimensions:'elapsedVideoTimeRatio',metrics:'audienceWatchRatio,relativeRetentionPerformance',filters:'video=='+id});
      data.videoTraffic[id]=await get('https://youtubeanalytics.googleapis.com/v2/reports',{...base,startDate:start,dimensions:'insightTrafficSourceType',metrics:'views,estimatedMinutesWatched',filters:'video=='+id});
      seal(data,'channel-audit.enc.json');
    }
  }
  if(process.env.AUDIT_APPLY_PLAN){
    const plan=JSON.parse(fs.readFileSync(process.env.AUDIT_APPLY_PLAN,'utf8'));
    data.changes=[];
    for(const item of plan){
      const current=await yt('videos',{part:'snippet',id:item.id});
      const v=current.items?.[0];
      if(!v||v.snippet.channelId!==ch.id||![item.before,item.title].includes(v.snippet.title))throw new Error('Metadata precondition changed: '+item.id);
      if(v.snippet.title===item.title){data.changes.push({id:item.id,state:'already_verified_title',plannedTitle:item.title});seal(data,'channel-audit.enc.json');continue;}
      const snippet={};
      for(const field of ['title','description','tags','categoryId','defaultLanguage','defaultAudioLanguage'])if(v.snippet[field]!==undefined)snippet[field]=v.snippet[field];
      data.changes.push({id:item.id,before:snippet,plannedTitle:item.title,state:'pending'});
      seal(data,'channel-audit.enc.json');
      const next={...snippet,title:item.title};
      const r=await fetch('https://www.googleapis.com/youtube/v3/videos?part=snippet',{method:'PUT',headers:{Authorization:'Bearer '+auth.access_token,'Content-Type':'application/json'},body:JSON.stringify({id:item.id,snippet:next}),signal:AbortSignal.timeout(30000)});
      if(!r.ok)throw new Error('Metadata write failed: '+item.id+' HTTP '+r.status);
      let got;
      // قد تتأخر نسخة القراءة بعد نجاح الكتابة؛ نكرر القراءة فقط، لا الكتابة.
      for(let attempt=0;attempt<12;attempt++){
        const verify=await yt('videos',{part:'snippet',id:item.id});
        got=verify.items?.[0]?.snippet;
        if(got?.title===item.title)break;
        if(attempt<11)await new Promise(resolve=>setTimeout(resolve,5000));
      }
      data.changes.at(-1).observedAfter=got;
      seal(data,'channel-audit.enc.json');
      if(!got||got.title!==item.title||(got.description||'')!==(snippet.description||'')||JSON.stringify([...(got.tags||[])].sort())!==JSON.stringify([...(snippet.tags||[])].sort()))throw new Error('Metadata verification failed: '+item.id);
      data.changes.at(-1).state='verified';
      seal(data,'channel-audit.enc.json');
    }
    console.log('Verified title cleanups:',data.changes.length);
  }
  console.log('Channel audit completed. Videos:',videos.length,'Analytics available:',!analytics.error);
} else {throw new Error('Expected keygen, collect or decrypt');}
