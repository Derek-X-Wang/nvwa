"""Actual unchanged transfer core + called diagnostic wrapper; CPU only."""
import hashlib,json,subprocess,shutil,unittest
from pathlib import Path
E=Path(__file__).resolve().parent
NODE=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');global.crypto=require('node:crypto').webcrypto;
const old=fs.readFileSync(process.argv[1]+'/original-index.html','utf8'),html=fs.readFileSync(process.argv[1]+'/index.html','utf8');
const core=s=>s.split('// TRANSFER_CORE_BEGIN:')[1].split('\n').slice(1).join('\n').split('// TRANSFER_CORE_END')[0];assert.equal(core(old),core(html));vm.runInThisContext(core(html));vm.runInThisContext(fs.readFileSync(process.argv[1]+'/harness.js','utf8'));
const work={character:{parameters:{torso_length:0,jaw_drop:0}},stage:{camera:{fov_degrees:30}}};
async function setup(opts={}){
 let report='',frame='',clock=0,transfer,diag,posted={},reads=[];
 const base=id=>({request_id:id,work_sha256:require('node:crypto').createHash('sha256').update(JSON.stringify(work)).digest('hex'),endpoint:'web',stable_updates:2,identity:{generation:3},candidate:{variant:'AOriginal',pre_visibility_publication_matches:true,generation:3},full_base:{generation:3,sample:{source_seconds:0,playing:false}},witness:[-0.0]});
 const d={now:()=>++clock,interval(){return 1},timeout:setTimeout,clearTimeout,clearInterval(){},pause:async()=>{clock+=10000},warn(){},render(){},invalidate:()=>transfer.invalidate(),sha256Text,
 readWork:()=>opts.initialWorkWrong?'{}':JSON.stringify(work),readReport:()=>{reads.push('read-report');return report},readFrame:()=>frame,status:()=>transfer.status(),exactText:t=>transfer.exactText(t),prepare:()=>transfer.prepare(),
 send:v=>{const id=opts.wrongId?'wrong':v.request_id;const f=base(id);frame=JSON.stringify(f).replace('"witness":[0]','"witness":[-0.0]');report=JSON.stringify({phase:'ready',current:!opts.stale,acknowledged:true,request_succeeded:true,request_id:id,work_sha256:require('node:crypto').createHash('sha256').update(JSON.stringify(work)).digest('hex'),endpoint:'web',diagnostic:{},captured_identity:f.identity,work_json:JSON.stringify(work)})},
 fetch:async(path,init)=>{if(path==='/_diag80/config')return {ok:true,json:async()=>({run_id:'run80',hold_id:'run80-hold0',request_id:'run80-A',expected_work:work})};if(!path.includes('/event/'))posted[path.split('/').pop()]=init.body;if(path.endsWith('/capture.json')&&opts.changeAfterRaw)frame+=' ';return {ok:true,status:201,text:async()=>''}}};
 diag=createDiagnostic80(d);transfer=createTransfer(d.readReport,d.readFrame,t=>diag.digest(t));return {diag,posted,reads,setInvalid(){report='{}'},d};
}
(async()=>{
 let a=await setup();await a.diag.run();assert.equal(a.diag.state().phase,'done');assert(a.posted['capture.json'].includes('-0.0'));assert(a.posted['manifest.json']);assert(a.posted['currentness.json']);const es=a.diag.events().map(e=>e.name);assert(es.indexOf('prepare-enter')<es.indexOf('digest-enter'));assert(es.includes('currentness-post-raw-response'));assert(es.includes('currentness-post-currentness-response'));await assert.rejects(a.diag.run(),/overlapping/);
 a=await setup({initialWorkWrong:true});await assert.rejects(a.diag.run(),/initial committed Work timeout/);assert(!a.posted['capture.json']);assert(!a.diag.events().some(e=>e.name==='send-hold-enter'));
 a=await setup({stale:true});await assert.rejects(a.diag.run(),/ready timeout/);assert(!a.posted['capture.json']);
 a=await setup({wrongId:true});await assert.rejects(a.diag.run(),/ready timeout/);assert(!a.posted['capture.json']);
 a=await setup({changeAfterRaw:true});await assert.rejects(a.diag.run(),/token differs|stale/);assert(a.posted['capture.json']);assert(!a.posted['currentness.json']);assert.equal(a.diag.state().phase,'failed');
 a=await setup();a.diag.cancel();await assert.rejects(a.diag.run(),/canceled/);assert(!a.posted['capture.json']);
 // Generated actual Prepare handler enters observer before the original prepare/readCapture.
 a=await setup();a.setInvalid();const button={};const wrapper=html.match(/\$\('prepare'\)\.onclick=([^;]+);/)[0];new Function('$','diag80','prepareTransfer',wrapper)(()=>button,a.diag,()=>a.d.prepare());await button.onclick();const e=a.diag.events().map(e=>e.name);assert(e.includes('manual-prepare-enter'));assert(e.includes('manual-prepare-error'));assert(!e.includes('digest-enter'),'readCapture rejection precedes digest');
 // Original transfer overlap: superseded first prepare rejects; only latest may publish.
 const identity={generation:3};let rr=JSON.stringify({phase:'ready',current:true,acknowledged:true,request_succeeded:true,request_id:'overlap',endpoint:'web',work_sha256:'w',diagnostic:{},captured_identity:identity}),ff=JSON.stringify({request_id:'overlap',endpoint:'web',work_sha256:'w',stable_updates:2,identity});let resolves=[];const t=createTransfer(()=>rr,()=>ff,()=>new Promise(r=>resolves.push(r)));const p1=t.prepare(),p2=t.prepare();resolves.slice(0,3).forEach(r=>r('a'.repeat(64)));await assert.rejects(p1,/superseded/);resolves.slice(3).forEach(r=>r('b'.repeat(64)));const m=await p2;assert(t.status().ready);t.invalidate();assert.throws(()=>t.exactText(m.token),/token/);
 console.log('PASS diagnostic fixed A, exact negative-zero bytes, ready/request/cancel/overlap/stale/post-network/manual-entry controls');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
class Harness(unittest.TestCase):
 def test_actual_called_core_and_wrapper(self):
  p=subprocess.run([shutil.which('node'),'-e',NODE,str(E)],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
 def test_original_core_exact(self):
  core=lambda s:s.split('// TRANSFER_CORE_BEGIN:')[1].split('// TRANSFER_CORE_END')[0]
  self.assertEqual(core((E/'original-index.html').read_text()),core((E/'index.html').read_text()))
  self.assertIn("get('case')==='fixed-auto'",(E/'index.html').read_text())
if __name__=='__main__':unittest.main()
