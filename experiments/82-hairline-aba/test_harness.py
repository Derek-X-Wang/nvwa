"""Called JS/controller + exact unchanged transfer. Synthetic controls, no actual GPU claim."""
import subprocess,shutil,unittest
from pathlib import Path
E=Path(__file__).resolve().parent
NODE=r'''
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');global.crypto=require('node:crypto').webcrypto;const html=fs.readFileSync(process.argv[1]+'/index.html','utf8');vm.runInThisContext(html.split('// TRANSFER_CORE_BEGIN:')[1].split('\n').slice(1).join('\n').split('// TRANSFER_CORE_END')[0]);vm.runInThisContext(fs.readFileSync(process.argv[1]+'/harness.js','utf8'));const c=JSON.parse(fs.readFileSync(process.argv[1]+'/contract.json'));c.expected_work={};
function setup(opts={}){let r='',f='',now=0,transfer,tick,posts={},sends=[];const identity={generation:3};let app;const d={pace:opts.pace,now:()=>now,interval:fn=>(tick=fn,1),clearInterval(){},timeout:setTimeout,clearTimeout,pause:async()=>{now+=10000},render(){},warn(){},readWork:()=>opts.work?'null':'{}',readReport:()=>r,readFrame:()=>f,invalidate:()=>transfer?.invalidate(),status:()=>transfer.status(),prepare:()=>transfer.prepare(),exactText:t=>transfer.exactText(t),send:s=>{sends.push(s);const stage=c.stages.find(x=>x.request_id===s.request_id);const diag={mode:'Combined',palette:'Textured'};f=JSON.stringify({endpoint:'web',request_id:opts.wrong?'wrong':s.request_id,work_sha256:'w',stable_updates:opts.unstable?1:2,identity,candidate:{variant:opts.variant?'AOriginal':(stage?.typed_variant||'AOriginal'),pre_visibility_publication_matches:true,generation:3},full_base:{generation:3,sample:{source_seconds:0,playing:false}},diagnostic:diag,witness:[-0.0]}).replace('\"witness\":[0]','\"witness\":[-0.0]');r=JSON.stringify({endpoint:'web',phase:'ready',current:!opts.stale,acknowledged:true,request_succeeded:true,request_id:opts.wrong?'wrong':s.request_id,work_sha256:'w',work_json:'{}',diagnostic:diag,captured_identity:identity})},fetch:async(path,init)=>{if(path==='/_aba/config')return {ok:true,json:async()=>c};if(!path.includes('/event/')){posts[path]=init.body;if(opts.after===path.split('/').pop())f+=' '}return {ok:true,status:201,text:async()=>''}}};transfer=createTransfer(d.readReport,d.readFrame);app=createHairlineABA(d);return {app,posts,sends,tick:()=>tick(),advance:n=>now+=n,mutate:()=>f+=' '}}
(async()=>{
let x=setup();await x.app.start();assert(x.app.state().held);await assert.rejects(x.app.start(),/overlapping/);for(let i=0;i<3;i++){const p=x.app.next();await assert.rejects(x.app.next(),/overlapping/);await p}assert(x.app.state().terminal);assert.equal(x.sends.length,4);assert.equal(Object.keys(x.posts).length,12);assert(Object.values(x.posts).some(s=>s.includes('-0.0')));await assert.rejects(x.app.next(),/no open/);
for(const opts of [{work:true},{wrong:true},{stale:true},{unstable:true},{after:'manifest.json'},{after:'capture.json'},{after:'currentness.json'}]){x=setup(opts);await assert.rejects(x.app.start());assert(x.app.state().terminal);assert(!Object.keys(x.posts).some(k=>k.includes('window-close')))}
x=setup({variant:true});await x.app.start();await assert.rejects(x.app.next(),/variant mismatch/);assert.equal(x.sends.length,3);
x=setup();await x.app.start();x.mutate();await assert.rejects(x.app.next(),/token|strings/);assert.equal(x.sends.length,2);
x=setup({after:'window-close.json'});await x.app.start();await assert.rejects(x.app.next(),/token|strings/);assert.equal(x.sends.length,2);
x=setup();x.app.cancel();await assert.rejects(x.app.start(),/canceled/);
x=setup();await x.app.start();x.advance(90001);x.tick();assert(x.app.state().terminal);assert.equal(x.sends.length,2);
x=setup({pace:60});await x.app.start();for(let i=0;i<3;i++){x.advance(60000);x.tick();for(let n=0;n<40;n++)await new Promise(r=>setImmediate(r))}assert(x.app.state().terminal);assert.equal(x.sends.length,4);console.log('PASS called A/B/A manual+pace60, exact bytes, initial/work/request/readiness/stability/variant/cancel/overlap/stale/network/window expiry/final stop');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
class Harness(unittest.TestCase):
 def test_called_controller(self):
  r=subprocess.run([shutil.which('node'),'-e',NODE,str(E)],capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_core_and_generated_structure(self):
  from prepare_site import generate,core,CORE_SHA
  import hashlib
  original=(E/'original-index.html').read_text();h=generate(original);self.assertEqual(h,(E/'index.html').read_text());self.assertEqual(hashlib.sha256(core(h).encode()).hexdigest(),CORE_SHA)
  with self.assertRaises(ValueError):generate(original+' ')
if __name__=='__main__':unittest.main()
