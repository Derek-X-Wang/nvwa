"""New page only; retained original HTML, Wasm, assets and transfer core stay exact."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent;OUT=ROOT/'.work/hairline-aba79';SITE=OUT/'retained-r2-site'
CORE_SHA='44698bd8f212ae656ccf6561b277ceb3bb4e9f01bbf9d51d1ceb3f318dbeab9a'
def require(ok,msg):
 if not ok:raise ValueError(msg)
def core(s):return s.split('// TRANSFER_CORE_BEGIN:')[1].split('// TRANSFER_CORE_END')[0]
def generate(original):
 require(hashlib.sha256(original.encode()).hexdigest()=='26c07697d0792c124537e2b8b8d91e9c06005c88b56523726083ba251d004b2e','original HTML drift')
 h=original.replace('<script type="module">','<script src="./aba82-harness.js"></script>\n<div style="position:fixed;left:4px;bottom:4px;z-index:110;background:#111e;color:#aff;font:11px monospace;padding:5px;max-width:550px"><pre id="aba-status" style="margin:0;max-height:100px"></pre><button id="aba-next" disabled>Next hairline case</button><button id="aba-cancel">Cancel A/B/A</button></div>\n<script type="module">',1)
 injection="""
const aba82=window.createHairlineABA({pace:new URLSearchParams(location.search).get('pace')==='60'?60:undefined,fetch:(...a)=>fetch(...a),now:()=>performance.now(),interval:(f,n)=>setInterval(f,n),timeout:(f,n)=>setTimeout(f,n),clearTimeout:t=>clearTimeout(t),clearInterval:t=>clearInterval(t),pause:n=>new Promise(r=>setTimeout(r,n)),readWork:()=>api.b1_76_work(),readReport:()=>api.b1_76_report(),readFrame:()=>api.b1_76_frame(),send:v=>send(v),prepare:()=>transfer.prepare(),status:()=>transfer.status(),exactText:t=>transfer.exactText(t),invalidate:()=>transfer?.invalidate(),warn:m=>console.warn('[ABA82]',m),render:s=>{$('aba-status').textContent=s.phase+'\\n'+(s.request_id||'')+' '+(s.token||'')+'\\n'+(s.remaining_ms===null?'':Math.ceil(s.remaining_ms/1000)+'s remaining');$('aba-next').disabled=!s.next_enabled}});
$('aba-next').onclick=()=>aba82.next().catch(e=>console.error('[ABA82]',e));$('aba-cancel').onclick=()=>aba82.cancel();
"""
 needle='try{api=await import(';require(h.count(needle)==1,'injection marker drift');h=h.replace(needle,injection+needle)
 needle='},150)}catch(e)';require(h.count(needle)==1,'startup marker drift');h=h.replace(needle,"},150);if(new URLSearchParams(location.search).get('case')==='aba')void aba82.start().catch(e=>console.error('[ABA82]',e));}catch(e)")
 require(core(original)==core(h) and hashlib.sha256(core(h).encode()).hexdigest()==CORE_SHA,'core drift');return h
if __name__=='__main__':
 h=generate((SITE/'index.html').read_text());(EXP/'index.html').write_text(h);(SITE/'aba82.html').write_text(h);shutil.copy2(EXP/'harness.js',SITE/'aba82-harness.js');print('core exact',CORE_SHA)
