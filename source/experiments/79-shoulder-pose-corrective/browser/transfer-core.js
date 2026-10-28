// TRANSFER_CORE_BEGIN: tests execute this exact live export seam without Web/GPU.
const CHUNK_BYTES=32768;
async function sha256Text(text){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('')}
function createTransfer(readReport,readFrame,digest=sha256Text){
 let active=null,epoch=0,failure=null;
 function invalidate(error=null){active=null;epoch++;failure=error}
 function readCapture(){
  const reportRaw=readReport(),frameRaw=readFrame();
  const report=JSON.parse(reportRaw),frame=JSON.parse(frameRaw);
  if(report.phase!=='ready'||report.current!==true||report.acknowledged!==true||report.request_succeeded!==true||!report.diagnostic)throw Error('No current successful diagnostic capture');
  if(!report.request_id||report.request_id!==frame.request_id||report.work_sha256!==frame.work_sha256||report.endpoint!==frame.endpoint)throw Error('Capture correlation differs');
  if(!Number.isInteger(frame.stable_updates)||frame.stable_updates<2||!frame.identity||JSON.stringify(report.captured_identity)!==JSON.stringify(frame.identity))throw Error('Capture identity/stability differs');
  return {reportRaw,frameRaw,requestId:report.request_id};
 }
 function requireActive(token){
  if(!active||active.manifest.token!==token)throw Error('Unknown or invalidated transfer token');
  if(readReport()!==active.reportRaw||readFrame()!==active.frameRaw){invalidate('Prepared transfer is stale; prepare the current capture again');throw Error(failure)}
  return active;
 }
 async function prepare(){
  invalidate();const started=epoch,capture=readCapture();
  // Concatenate original strings. Never serialize parsed numeric witnesses.
  const text='{"report":'+capture.reportRaw+',"frame":'+capture.frameRaw+'}';
  const [sha256,reportSha,frameSha]=await Promise.all([digest(text),digest(capture.reportRaw),digest(capture.frameRaw)]);
  if(epoch!==started)throw Error('Transfer preparation superseded');
  if(readReport()!==capture.reportRaw||readFrame()!==capture.frameRaw)throw Error('Capture changed during transfer preparation');
  const bytes=new TextEncoder().encode(text);
  const manifest={format:'nvwa76-raw-transfer-v1',token:'transfer-'+started+'-'+sha256,request_id:capture.requestId,encoding:'utf-8',chars:text.length,bytes:bytes.length,sha256,report_bytes:new TextEncoder().encode(capture.reportRaw).length,report_sha256:reportSha,frame_bytes:new TextEncoder().encode(capture.frameRaw).length,frame_sha256:frameSha,chunk_bytes:CHUNK_BYTES,chunks:Math.ceil(bytes.length/CHUNK_BYTES)};
  active={...capture,text,bytes,manifest};return {...manifest};
 }
 function status(){if(!active)return failure?{ready:false,error:failure}:{ready:false};try{requireActive(active.manifest.token);return {ready:true,...active.manifest}}catch(e){return {ready:false,error:String(e)}}}
 function chunk(token,index){const a=requireActive(token);if(!Number.isInteger(index)||index<0||index>=a.manifest.chunks)throw Error('Chunk index out of range');return {token,index,base64:btoa(String.fromCharCode(...a.bytes.slice(index*CHUNK_BYTES,(index+1)*CHUNK_BYTES)))}}
 function exactText(token){return requireActive(token).text}
 return {prepare,status,chunk,exactText,invalidate};
}
// TRANSFER_CORE_END
