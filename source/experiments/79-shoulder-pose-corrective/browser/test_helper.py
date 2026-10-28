import subprocess,shutil,unittest,json,tempfile,threading,http.client,hashlib
from pathlib import Path
from server import check_contract,Receiver,Handler,ThreadingHTTPServer,MODES
D=Path(__file__).resolve().parent
NODE=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');global.crypto=require('node:crypto').webcrypto;vm.runInThisContext(fs.readFileSync(process.argv[1]+'/transfer-core.js','utf8'));vm.runInThisContext(fs.readFileSync(process.argv[1]+'/shoulder.js','utf8'));
const modes=['combined','source_body','source_garment'],diagnostic=['Combined','SourceBody','SourceGarment'];
function setup(opts={}){let clock=0,report='',frame='',transfer,callback,posted={},commands=[],digestWait=[],prepareCount=0;const stages=modes.map((mode,i)=>({mode,diagnostic_mode:diagnostic[i],request_id:'proof-'+mode,source_equals:{mode:i?diagnostic[i]:'baseline',target_active:false},required_source_keys:['visibility_prepared']}));
const d={pace:opts.pace,now:()=>clock,interval:f=>(callback=f,1),clearInterval(){},timeout:setTimeout,clearTimeout,pause:async()=>{clock+=10000},warn(){},render(){},readWork:()=>'{"stage":"rear"}',readReport:()=>report,readFrame:()=>frame,invalidate:()=>transfer.invalidate(),prepare:()=>{prepareCount++;return transfer.prepare()},status:()=>transfer.status(),exactText:t=>transfer.exactText(t),fetch:async(path,init)=>{if(path==='/_shoulder/config')return {ok:true,json:async()=>({run_id:'proof',hold_id:'proof-hold2',expected_work:{stage:'rear'},stages})};if(!path.includes('/event/'))posted[path]=init.body;return {ok:true,status:201,text:async()=>''}},send:v=>{transfer.invalidate();commands.push(v);const i=modes.indexOf(v.mode),identity={generation:opts.changedIdentity&&i===1?8:7};const sd={mode:i<=0?'baseline':diagnostic[i],target_active:false,visibility_prepared:true};if(opts.missingSource)delete sd.visibility_prepared;const diag={mode:i>=0?diagnostic[i]:'Combined',palette:'Textured'};const f={endpoint:'web',request_id:v.request_id,work_sha256:'work',stable_updates:2,identity,diagnostic:diag,source_diagnostic:sd,full_base:{generation:7,sample:{source_seconds:2,playing:false},bones:[{id:'bone'}]}};frame=JSON.stringify(f);report=JSON.stringify({endpoint:'web',request_id:v.request_id,work_sha256:'work',work_json:'{"stage":"rear"}',phase:'ready',current:true,acknowledged:true,request_succeeded:true,captured_identity:identity,diagnostic:diag,source_diagnostic:sd})}};
const proofs=createShoulderProofs(d);transfer=createTransfer(d.readReport,d.readFrame,opts.deferDigest?()=>new Promise(r=>digestWait.push(r)):sha256Text);return {proofs,posted,commands,tick(n){clock=n;callback()},stale(){frame+=' '},resolve(){digestWait.forEach(r=>r('a'.repeat(64)))},prepares:()=>prepareCount};}
const settle=()=>new Promise(r=>setImmediate(r));const until=async(fn)=>{const deadline=Date.now()+3000;while(!fn()&&Date.now()<deadline)await settle();assert(fn(),'asynchronous called seam did not reach expected terminal state')};
(async()=>{
 let x=setup();await x.proofs.start();assert.equal(x.proofs.state().index,0);x.tick(999999);await settle();assert.equal(x.proofs.state().index,0,'manual default never advances by time');await x.proofs.next('button');await x.proofs.next('button');assert(x.proofs.state().final);assert.equal(x.proofs.state().phase,'FINAL-AWAITING-SCREENSHOT-CHECK');await assert.rejects(x.proofs.next(),/STOP forever/);assert.equal(x.commands.filter(c=>c.action==='diagnostic').length,3);assert(!x.commands.some(c=>c.action==='author_target'||c.mode==='corrective'));assert(Object.keys(x.posted).some(p=>p.endsWith('combined/pre-next.json')));assert(!Object.keys(x.posted).some(p=>p.endsWith('source_garment/pre-next.json')));
 x.stale();x.tick(999999);await until(()=>x.proofs.state().phase==='FAILED');assert.equal(x.proofs.state().phase,'FAILED','stale final capture must stop qualification');
 x=setup({pace:45});await x.proofs.start();x.tick(44999);await settle();assert.equal(x.proofs.state().index,0);x.tick(45000);await until(()=>x.proofs.state().index===1&&!x.proofs.state().busy);assert.equal(x.proofs.state().index,1);x.tick(90000);await until(()=>x.proofs.state().final&&!x.proofs.state().busy);assert(x.proofs.state().final);await assert.rejects(x.proofs.next(),/STOP forever/);
 // Twelve bounded exact final checks emit create-only receipts, then remove live qualification.
 x.tick(90000);await until(()=>x.proofs.state().lastFinalReceipt===1&&!x.proofs.state().busy);assert.equal(x.proofs.state().lastFinalReceipt,1);for(let i=1;i<12;i++){x.tick(90000+i*5000);await until(()=>x.proofs.state().finalChecks===i+1&&!x.proofs.state().busy)}assert(x.proofs.state().finalClosed);assert.equal(x.proofs.state().finalChecks,12);assert.equal(x.proofs.state().phase,'FINAL-WINDOW-CLOSED-NO-CURRENT-PROOF');assert.equal(Object.keys(x.posted).filter(p=>p.includes('/final-check/')).length,12);await assert.rejects(x.proofs.checkScreenshot(),/no open final/);const closedCount=x.commands.length;x.tick(9999999);await settle();assert.equal(x.commands.length,closedCount);
 // Manual Check emits fences; stale after final cannot retain old qualified STOP/token.
 x=setup();await x.proofs.start();await x.proofs.next();await x.proofs.next();await x.proofs.checkScreenshot();assert.equal(x.proofs.state().lastFinalReceipt,1);x.stale();x.tick(5000);await until(()=>x.proofs.state().phase==='FAILED');assert.equal(x.proofs.state().phase,'FAILED');await assert.rejects(x.proofs.checkScreenshot(),/no open final/);
 x=setup({changedIdentity:true});await x.proofs.start();await assert.rejects(x.proofs.next(),/identity/);assert(!Object.keys(x.posted).some(p=>p.includes('/source_body/capture.json')));
 x=setup();await x.proofs.start();x.stale();await assert.rejects(x.proofs.next(),/token|strings/);assert.equal(x.commands.length,2,'stale previous hold prevents next command');
 x=setup({missingSource:true});await assert.rejects(x.proofs.start(),/source field absent/);assert.equal(Object.keys(x.posted).length,0);
 x=setup({deferDigest:true});const running=x.proofs.start();await settle();assert.equal(x.prepares(),1);await assert.rejects(x.proofs.start(),/overlapping/);await assert.rejects(x.proofs.next(),/overlapping/);x.proofs.cancel();x.resolve();await assert.rejects(running,/superseded|canceled/);assert(!Object.keys(x.posted).some(p=>p.endsWith('/capture.json')));
 console.log('PASS guarded Next manual/pace45 exact timing, finalSTOP, cancellation, changed identity, stale token, missing schema, overlap');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
def contract():return {'root_frozen':True,'stage_rules':{m:{'source_equals':{'mode':('baseline' if i==0 else ['Combined','SourceBody','SourceGarment'][i]),'target_active':False},'required_source_keys':['visibility_prepared']} for i,m in enumerate(MODES)}}
class Helper(unittest.TestCase):
 def test_called_js_sequence_guards(self):
  p=subprocess.run([shutil.which('node'),'-e',NODE,str(D)],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stderr+p.stdout)
 def test_contract_unknown_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'not frozen'):check_contract(json.loads((D/'contract.example.json').read_text()))
  c=contract();c['stage_rules']['source_body']['required_source_keys']=[]
  with self.assertRaisesRegex(ValueError,'unknown source'):check_contract(c)
 def test_real_http_config_events_and_no_cors_or_arbitrary_path(self):
  scratch=D/'test-tmp';scratch.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=scratch) as tmp:
   base=Path(tmp);site=base/'site';(site/'works').mkdir(parents=True);(site/'works/shoulder-rear-baseline-arms.nvwa.json').write_text('{}');server=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=server.server_address[1];server.receiver=Receiver(site,base/'out','proof',port,contract());t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
   def req(method,path,body=None,headers=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:c.request(method,path,body,headers or {});r=c.getresponse();return r.status,r.read()
    finally:c.close()
   try:
    self.assertEqual(req('GET','/helper.html')[0],200);code,body=req('GET','/_shoulder/config');self.assertEqual(code,200);self.assertEqual([s['mode'] for s in json.loads(body)['stages']],MODES);origin=f'http://127.0.0.1:{port}';headers={'Origin':origin};self.assertEqual(req('POST','/_shoulder/proof/event/1',b'{"seq":1}',headers)[0],201);self.assertEqual(req('POST','/_shoulder/proof/event/1',b'{"seq":1}',headers)[0],400);self.assertEqual(req('POST','/_shoulder/proof/author_target',b'{}',headers)[0],400);self.assertEqual(req('POST','/_shoulder/proof/event/2',b'{"seq":2}',{'Origin':'http://evil'})[0],400);self.assertEqual(req('OPTIONS','/')[0],405)
   finally:server.shutdown();server.server_close();t.join(timeout=3)
 def test_receiver_full_three_identity_and_fenced_order(self):
  scratch=D/'test-tmp';scratch.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=scratch) as tmp:
   base=Path(tmp);site=base/'site';(site/'works').mkdir(parents=True);(site/'works/shoulder-rear-baseline-arms.nvwa.json').write_text('{}');r=Receiver(site,base/'out','proof',9205,contract());origin='http://127.0.0.1:9205';r.guard('127.0.0.1:9205',origin,1)
   for mode_index,mode in enumerate(MODES):
    stage=r.stages[mode_index];sd={**stage['source_equals'],'visibility_prepared':True};identity={'generation':3};frame={'endpoint':'web','request_id':stage['request_id'],'work_sha256':'work','stable_updates':2,'identity':identity,'diagnostic':{'mode':stage['diagnostic_mode'],'palette':'Textured'},'source_diagnostic':sd,'full_base':{'generation':3,'sample':{'source_seconds':2,'playing':False},'bones':[{'id':'b'}]}};report={k:frame[k] for k in ['endpoint','request_id','work_sha256','diagnostic','source_diagnostic']};report.update(work_json='{}',phase='ready',current=True,acknowledged=True,request_succeeded=True,captured_identity=identity);rr=json.dumps(report).encode();ff=json.dumps(frame).encode();raw=b'{"report":'+rr+b',"frame":'+ff+b'}';sha=lambda b:hashlib.sha256(b).hexdigest();m={'request_id':stage['request_id'],'format':'nvwa76-raw-transfer-v1','encoding':'utf-8','bytes':len(raw),'chars':len(raw),'sha256':sha(raw),'report_bytes':len(rr),'frame_bytes':len(ff),'report_sha256':sha(rr),'frame_sha256':sha(ff),'token':'transfer-1-'+sha(raw),'chunks':1,'chunk_bytes':32768};prefix='/_shoulder/proof/'+mode+'/'
    r.accept(prefix+'manifest.json',json.dumps(m).encode());r.accept(prefix+'capture.json',raw);fence=lambda name:{'name':name,'ready':True,'token':m['token'],'exact_report_before_after':True,'exact_frame_before_after':True};r.accept(prefix+'currentness.json',json.dumps({'request_id':stage['request_id'],'mode':mode,'manifest':m,'fences':[fence(n) for n in ['after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response']]}).encode());advance={'request_id':stage['request_id'],'mode':mode,'token':m['token'],'reason':'button','fence':fence('pre-next')}
    if mode_index<2:r.accept(prefix+'pre-next.json',json.dumps(advance).encode())
    else:
     with self.assertRaisesRegex(ValueError,'STOP forever'):r.accept(prefix+'pre-next.json',json.dumps(advance).encode())
   # Real final-check HTTP route after the exact three captures above.
   httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=httpd.server_address[1];r.host=f'127.0.0.1:{port}';r.origin='http://'+r.host;httpd.receiver=r;thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
   def final_http(n,value):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:c.request('POST',f'/_shoulder/proof/source_garment/final-check/{n:03}.json',json.dumps(value).encode(),{'Origin':r.origin});res=c.getresponse();return res.status,res.read()
    finally:c.close()
   def check_receipt(n,prev,purpose,elapsed=0):return {'request_id':'proof-source_garment','mode':'source_garment','token':m['token'],'check_index':n,'previous_check_index':prev,'purpose':purpose,'reason':'pace45','elapsed_ms':elapsed,'fence':fence('final-check-'+str(n)+'-before')}
   try:
    opening=check_receipt(1,0,'opening');self.assertEqual(final_http(1,opening)[0],201);self.assertEqual(final_http(1,opening)[0],400)
    for field,value in [('token','wrong'),('mode','source_body'),('previous_check_index',0),('purpose','opening')]:
     bad=check_receipt(2,1,'continuation');bad[field]=value;self.assertEqual(final_http(2,bad)[0],400)
    bad=check_receipt(2,1,'continuation');bad['fence']['exact_frame_before_after']=False;self.assertEqual(final_http(2,bad)[0],400)
    self.assertEqual(final_http(2,check_receipt(2,1,'continuation'))[0],201);self.assertEqual(final_http(3,check_receipt(3,2,'closing'))[0],400);self.assertEqual(final_http(12,check_receipt(12,2,'closing',55000))[0],201);self.assertEqual(final_http(13,check_receipt(13,12,'continuation',60000))[0],400);self.assertTrue(r.final_closed)
    saved=json.loads((r.output/'source_garment/final-check/012.json').read_text());self.assertEqual(saved['previous_check_index'],2);self.assertEqual(saved['purpose'],'closing')
   finally:httpd.shutdown();httpd.server_close();thread.join(timeout=3)
if __name__=='__main__':unittest.main()
