"""Generate an instrumented page beside, never over, exact retained R2 files."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent;OUT=ROOT/'.work/hairline-export79';SITE=OUT/'retained-r2-site'
def require(ok,message):
 if not ok:raise ValueError(message)
def core(s):
 require(s.count('// TRANSFER_CORE_BEGIN:')==1 and s.count('// TRANSFER_CORE_END')==1,'exact transfer markers required')
 return s.split('// TRANSFER_CORE_BEGIN:')[1].split('// TRANSFER_CORE_END')[0]
def generate(original):
 original;require(hashlib.sha256(original.encode()).hexdigest()=='26c07697d0792c124537e2b8b8d91e9c06005c88b56523726083ba251d004b2e','original sealed HTML identity drift');h=original
 h=h.replace('<script type="module">','<script src="./diagnostic80-harness.js"></script>\n<pre id="diagnostic80-status" style="position:fixed;left:4px;bottom:4px;z-index:110;margin:0;padding:5px;max-width:560px;max-height:160px;overflow:auto;background:#111e;color:#aff;font:11px monospace">diagnostic80 boot</pre>\n<script type="module">',1)
 injection="""
const diag80=window.createDiagnostic80({
 fetch:(...args)=>fetch(...args), now:()=>performance.now(), interval:(f,n)=>setInterval(f,n), timeout:(f,n)=>setTimeout(f,n), clearTimeout:t=>clearTimeout(t), clearInterval:t=>clearInterval(t), pause:n=>new Promise(r=>setTimeout(r,n)),
 readWork:()=>api.b1_76_work(),readReport:()=>api.b1_76_report(),readFrame:()=>api.b1_76_frame(),send:v=>send(v),prepare:()=>transfer.prepare(),status:()=>transfer.status(),exactText:t=>transfer.exactText(t),invalidate:()=>transfer?.invalidate(),sha256Text:t=>sha256Text(t),warn:m=>console.warn('[DIAG80]',m),
 render:s=>{$('diagnostic80-status').textContent='DIAG80 '+s.phase+' heartbeat='+s.tick+' maxLagMs='+s.maxLag.toFixed(1)+'\\n'+s.events.map(e=>e.ms.toFixed(1)+' '+e.name+(e.message?' '+e.message:'')).join('\\n')}
});
"""
 needle="try{api=await import(";require(h.count(needle)==1,'unique structural injection marker required');h=h.replace(needle,injection+needle)
 needle="transfer=createTransfer(()=>api.b1_76_report(),()=>api.b1_76_frame());";require(h.count(needle)==1,'unique structural injection marker required');h=h.replace(needle,"transfer=createTransfer(()=>api.b1_76_report(),()=>api.b1_76_frame(),text=>diag80.digest(text));")
 needle="},150)}catch(e)";require(h.count(needle)==1,'unique structural injection marker required');h=h.replace(needle,"},150);if(new URLSearchParams(location.search).get('case')==='fixed-auto')void diag80.run().catch(e=>console.error('[DIAG80]',e));}catch(e)")
 h=h.replace("$('prepare').onclick=()=>prepareTransfer().catch(()=>{});","$('prepare').onclick=()=>diag80.observePrepare(()=>prepareTransfer()).catch(()=>{});")
 require(core(original)==core(h),'transfer core changed');require(hashlib.sha256(core(h).encode()).hexdigest()=='44698bd8f212ae656ccf6561b277ceb3bb4e9f01bbf9d51d1ceb3f318dbeab9a','original core identity drift');require(hashlib.sha256(h.encode()).hexdigest()=='72d9ea853ef73cf8f2b93fd8d4a6bb4da53e7e73256c0c4b189627265d0c7a94','v2 runtime HTML identity drift')
 return h
def main():
 original=(SITE/'index.html').read_text();h=generate(original)
 (EXP/'index.html').write_text(h);(SITE/'diagnostic80.html').write_text(h);shutil.copy2(EXP/'harness.js',SITE/'diagnostic80-harness.js')
 sha=lambda b:hashlib.sha256(b).hexdigest();(OUT/'HTML-PROVENANCE.json').write_text(json.dumps({'original_index_sha256':sha(original.encode()),'diagnostic_index_sha256':sha(h.encode()),'transfer_core_sha256':sha(core(original).encode()),'transfer_core_byte_exact':True,'harness_sha256':sha((EXP/'harness.js').read_bytes()),'new_files_only':['diagnostic80.html','diagnostic80-harness.js'],'original_site_modified':False},indent=2)+'\n')
 print('TRANSFER_CORE_EXACT',sha(core(original).encode()))
if __name__=='__main__':main()
