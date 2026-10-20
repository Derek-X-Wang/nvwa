/* Isolated diagnostic80: orchestration/observations only. Original transfer core is unchanged. */
(function(scope){
'use strict';
function createDiagnostic80(d){
 let events=[],phase='boot',tick=0,maxLag=0,lastTick=d.now(),started=false,canceled=false,terminal=false,seq=0;
 let configPromise=d.fetch('/_diag80/config',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('config HTTP '+r.status);return r.json()});
 const event=(name,detail={})=>{
  const row={seq:++seq,name,ms:d.now(),wall_utc:new Date().toISOString(),...detail};events.push(row);d.render({phase,tick,maxLag,last:row,events:events.slice(-12)});
  // Breadcrumb delivery is observational; its failure never creates a successful capture.
  void configPromise.then(c=>d.fetch('/_diag80/'+c.run_id+'/event/'+row.seq,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(row)})).then(r=>{if(!r.ok)d.warn('event HTTP '+r.status)}).catch(e=>d.warn(String(e)));
 };
 const timer=d.interval(()=>{const now=d.now();maxLag=Math.max(maxLag,now-lastTick-250);lastTick=now;tick++;if(tick%4===0&&!terminal)event('heartbeat',{max_lag_ms:maxLag});},250);
 event('boot');
 function ensure(ok,message){if(!ok)throw Error(message)}
 function checkCancel(){ensure(!canceled,'diagnostic canceled')}
 function same(a,b){if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return a===b;if(Array.isArray(a)!==Array.isArray(b))return false;const keys=Object.keys(a).sort();return JSON.stringify(keys)===JSON.stringify(Object.keys(b).sort())&&keys.every(k=>same(a[k],b[k]));}
 async function limited(p,label,ms=60000){let t;try{return await Promise.race([p,new Promise((_,reject)=>{t=d.timeout(()=>{d.invalidate();reject(Error(label+' timeout'));},ms)})]);}finally{d.clearTimeout(t)}}
 async function waitReady(id){const begin=d.now();for(;;){checkCancel();const raw=d.readReport();let r;try{r=JSON.parse(raw)}catch{}if(r?.request_id===id&&r.phase==='error')throw Error('Rust rejected '+id+': '+r.error);if(r?.request_id===id&&r.phase==='ready'&&r.current===true&&r.acknowledged===true&&r.request_succeeded===true)return r;ensure(d.now()-begin<60000,'ready timeout '+id);await d.pause(250);}}
 async function digest(text){event('digest-enter',{chars:text.length});const begin=d.now();try{const hash=await d.sha256Text(text);event('digest-exit',{chars:text.length,elapsed_ms:d.now()-begin,sha256:hash});return hash}catch(e){event('digest-error',{message:String(e)});throw e}}
 async function run(){
  ensure(!started,'overlapping diagnostic run rejected');started=true;
  try{
   const c=await configPromise;checkCancel();event('config-ready',{run_id:c.run_id,expected_request_id:c.request_id});
   phase='initial-work';event('initial-work-wait-enter');const initialStart=d.now();let initialWorkRaw;
   for(;;){checkCancel();const wr=d.readWork();let actual;try{actual=JSON.parse(wr)}catch{}if(actual&&same(actual,c.expected_work)){initialWorkRaw=wr;break}let status;try{status=JSON.parse(d.readReport())}catch{}ensure(status?.phase!=='error','Rust initial Work error: '+status?.error);ensure(d.now()-initialStart<60000,'initial committed Work timeout');await d.pause(250);}
   const initialWorkSha=await d.sha256Text(initialWorkRaw);event('initial-work-wait-exit',{actual_work_sha256:initialWorkSha,pinned_work_file_sha256:c.work_file_sha256});
   phase='hold';event('send-hold-enter');d.send({request_id:c.hold_id,action:'playback',seek_seconds:0,playing:false});event('send-hold-exit');await waitReady(c.hold_id);event('hold-ready');
   phase='diagnostic';event('send-A-enter');d.send({request_id:c.request_id,action:'diagnostic',mode:'combined',palette:'textured',variant:'a_original'});event('send-A-exit');const report=await waitReady(c.request_id);ensure(report.work_sha256===initialWorkSha,'committed initial Work changed before A');event('A-ready');
   // Additional fixed-case correlation. Original prepare still repeats every original gate.
   ensure(same(JSON.parse(report.work_json),c.expected_work),'actual Work differs from independently pinned config');
   const reportRaw=d.readReport(),frameRaw=d.readFrame(),frame=JSON.parse(frameRaw);
   ensure(frame.request_id===c.request_id&&frame.stable_updates>=2,'actual frame request/stability mismatch');
   ensure(frame.candidate?.variant==='AOriginal'&&frame.candidate.pre_visibility_publication_matches===true,'actual original A visibility publication absent');
   ensure(frame.full_base?.sample?.source_seconds===0&&frame.full_base.sample.playing===false,'actual held source0 absent');
   ensure(frame.candidate.generation===frame.full_base.generation,'actual generation mismatch');
   event('fixed-frame-qualified',{stable_updates:frame.stable_updates,generation:frame.full_base.generation,work_sha256:frame.work_sha256});
   phase='prepare';event('prepare-enter');const manifest=await limited(d.prepare(),'prepare');event('prepare-exit',{token:manifest.token,bytes:manifest.bytes,sha256:manifest.sha256});checkCancel();
   const fences=[];
   function fence(name){checkCancel();const status=d.status();ensure(status.ready===true&&status.token===manifest.token,'current transfer token differs at '+name);ensure(d.readReport()===reportRaw&&d.readFrame()===frameRaw,'exact report/frame changed at '+name);const f={name,ms:d.now(),ready:true,token:status.token,exact_report_before_after:true,exact_frame_before_after:true};fences.push(f);event('currentness-'+name,{token:status.token});}
   fence('after-prepare');event('exactText-enter');const exact=d.exactText(manifest.token);event('exactText-exit',{chars:exact.length});fence('after-exactText');
   const post=async(name,body)=>{const res=await limited(d.fetch('/_diag80/'+c.run_id+'/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body}),'upload '+name);ensure(res.ok,'receiver '+name+' HTTP '+res.status+': '+await res.text());return res;};
   phase='upload';fence('pre-manifest-upload');await post('manifest.json',JSON.stringify(manifest));fence('post-manifest-response');
   fence('pre-raw-upload');event('raw-upload-enter');await post('capture.json',exact);event('raw-upload-exit');fence('post-raw-response');
   const receipt={run_id:c.run_id,request_id:c.request_id,manifest,scope:'exact captured bytes and explicit currentness fences; no quality/GPU source admission',fences};await post('currentness.json',JSON.stringify(receipt));fence('post-currentness-response');
   phase='done';terminal=true;event('DONE',{request_id:c.request_id,token:manifest.token,sha256:manifest.sha256,post_response_current:true});return receipt;
  }catch(e){phase='failed';terminal=true;d.invalidate();event('FAILED',{message:String(e),post_response_current:'NOT-RUN unless already recorded by a named successful fence'});throw e;}
 }
 async function observePrepare(fn){event('manual-prepare-enter');try{const value=await fn();event('manual-prepare-exit',{token:value?.token,bytes:value?.bytes});return value}catch(e){event('manual-prepare-error',{message:String(e)});throw e}}
 return {run,digest,observePrepare,cancel(){canceled=true;d.invalidate();event('cancel')},events:()=>events.slice(),state:()=>({phase,tick,maxLag}),stopHeartbeat(){d.clearInterval(timer)}};
}
scope.createDiagnostic80=createDiagnostic80;
})(typeof window==='undefined'?globalThis:window);
