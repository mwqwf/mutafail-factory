import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {test} from 'node:test';

for (const scenario of ['success', 'wrong-channel', 'update-fails']) {
  test(`حماية تطبيق الهوية: ${scenario}`, () => {
    const code = `
      import assert from 'node:assert/strict';
      const scenario = ${JSON.stringify(scenario)};
      let writes=0, watermark=false, updated=false;
      const fields={title:'المتفائل',description:'وصف محفوظ',keywords:'وثائقي',defaultLanguage:'ar',country:'DZ'};
      const channel={id:scenario==='wrong-channel'?'wrong':'UCda-VgyvZwAH5_Pl1elVEnw',
        snippet:{title:'المتفائل',description:'وصف محفوظ',thumbnails:{}},
        brandingSettings:{channel:fields,image:{bannerExternalUrl:'https://example.invalid/old'}}};
      process.argv[2]='--apply';
      process.env.YT_OAUTH_JSON=JSON.stringify({client_id:'fake',client_secret:'fake',refresh_token:'fake'});
      delete process.env.GITHUB_STEP_SUMMARY;
      globalThis.fetch=async(url,opts={})=>{
        const method=opts.method||'GET';
        if(url==='https://oauth2.googleapis.com/token') return Response.json({access_token:'fake'});
        if(method!=='GET') writes++;
        if(url.includes('channels?')&&method==='GET') return Response.json({items:[channel]});
        if(url.includes('channelBanners/insert')) return Response.json({url:'https://example.invalid/new'});
        if(url.includes('channels?')&&method==='PUT'){
          const body=JSON.parse(opts.body);
          assert.deepEqual(body.brandingSettings.channel,fields);
          assert.equal(body.id,'UCda-VgyvZwAH5_Pl1elVEnw');
          if(scenario==='update-fails') return Response.json({error:{errors:[{reason:'forbidden'}]}},{status:403});
          channel.brandingSettings=body.brandingSettings;updated=true;return Response.json(channel);
        }
        if(url.includes('watermarks/set')){
          assert.ok(updated);assert.ok(opts.body.includes(Buffer.from('offsetFromStart')));
          watermark=true;return new Response(null,{status:204});
        }
        throw new Error('Unexpected network call: '+url);
      };
      let failed=false;
      try{await import('./channel_branding.mjs')}catch(e){failed=true}
      if(scenario==='success'){assert.equal(failed,false);assert.equal(watermark,true);assert.equal(writes,3)}
      else{assert.equal(failed,true);assert.equal(watermark,false);if(scenario==='wrong-channel')assert.equal(writes,0)}
    `;
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
      cwd: new URL('.', import.meta.url), encoding: 'utf8'});
    assert.equal(result.status, 0, result.stdout + result.stderr);
  });
}
