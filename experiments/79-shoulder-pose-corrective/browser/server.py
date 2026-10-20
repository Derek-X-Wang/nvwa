"""Draft standalone same-origin receiver. Read-only compiled site; fixed three-mode sequence."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
import argparse,json,re,threading,hashlib
from decimal import Decimal
from collect_transfer import manifest_identity,verify_bytes,raw_object
DRAFT=Path(__file__).resolve().parent;MAX=32*1024*1024;MODES=['combined','source_body','source_garment'];DIAGNOSTIC=['Combined','SourceBody','SourceGarment']
def require(ok,message):
 if not ok:raise ValueError(message)
def check_contract(c):
 require(isinstance(c,dict),'root contract object required');require(c.get('root_frozen') is True,'root final source contract is not frozen');rules=c.get('stage_rules');require(isinstance(rules,dict) and set(rules)==set(MODES),'fixed three-mode contract required')
 for mode in MODES:
  rule=rules[mode];equals=rule.get('source_equals');keys=rule.get('required_source_keys');require(isinstance(equals,dict) and isinstance(equals.get('mode'),str) and equals['mode'] not in ['Corrective','corrective'] and equals.get('target_active') is False,'root-fixed source mode/no-target contract required');require(isinstance(keys,list) and len(keys)>0 and all(isinstance(k,str) and k and not k.startswith('__') for k in keys),'unknown source previsibility fields; fail closed')
class Receiver:
 def __init__(self,site,output,run_id,port,contract):
  check_contract(contract);require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}',run_id) is not None,'run ID invalid');self.site=site;self.output=output;self.run_id=run_id;self.host=f'127.0.0.1:{port}';self.origin='http://'+self.host;self.lock=threading.Lock();self.manifests={};self.captures={};self.anchor=None;self.contract=contract;self.last_final_check=0;self.final_closed=False
  output.mkdir(parents=True,exist_ok=False);(output/'events').mkdir();self.work=json.loads((site/'works/shoulder-rear-baseline-arms.nvwa.json').read_text());self.stages=[{'mode':mode,'diagnostic_mode':DIAGNOSTIC[i],'request_id':run_id+'-'+mode,**contract['stage_rules'][mode]} for i,mode in enumerate(MODES)];self.config={'run_id':run_id,'hold_id':run_id+'-hold2','expected_work':self.work,'stages':self.stages,'contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()};self.write('SERVER-CONFIG.json',json.dumps(self.config,indent=2).encode())
 def write(self,name,data):
  p=self.output/name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
 def guard(self,host,origin,length,encoding=None):require(host==self.host and origin==self.origin,'Host/Origin rejected');require(encoding is None and type(length) is int and 0<length<=MAX,'bounded Content-Length required')
 def accept(self,path,data):
  require(len(data)<=MAX,'body exceeds32MiB');prefix='/_shoulder/'+self.run_id+'/';require(path.startswith(prefix),'run/path rejected');name=path[len(prefix):]
  with self.lock:
   if re.fullmatch(r'event/[1-9][0-9]{0,2}',name):
    seq=int(name.split('/')[1]);require(seq<=512 and len(data)<=8192,'event bound');v=raw_object(data,'event');require(v.get('seq')==seq,'event identity');self.write(f'events/{seq:03}.json',data);return
   final_match=re.fullmatch(r'source_garment/final-check/([0-9]{3})\.json',name)
   if final_match:
    require(not self.final_closed,'final screenshot window already closed');n=int(final_match.group(1));require(1<=n<=12 and len(data)<=16384,'bounded final check required');mode='source_garment';stage=self.stages[2];require(self.captures.get(mode) and (self.output/mode/'currentness.json').exists(),'qualified final raw/currentness required');manifest=self.manifests[mode];v=raw_object(data,'final screenshot check');require(v.get('request_id')==stage['request_id'] and v.get('mode')==mode and v.get('token')==manifest['token'],'final check request/mode/token mismatch');require(type(v.get('check_index')) is int and v['check_index']==n and n>self.last_final_check and type(v.get('previous_check_index')) is int and v['previous_check_index']==self.last_final_check,'final check sequence mismatch');purpose=v.get('purpose');reason=v.get('reason');require(purpose in ['opening','continuation','closing'] and reason in ['button','pace45','watch'],'final check kind/source mismatch');require((purpose=='closing' or reason!='watch') and (purpose!='opening' or self.last_final_check==0),'manual watch cannot open screenshot receipt');require(purpose!='continuation' or self.last_final_check>0,'continuation requires an opening receipt');elapsed=v.get('elapsed_ms');require(isinstance(elapsed,(int,float,Decimal)) and elapsed>=0,'final elapsed time absent');require(purpose!='closing' or n==12 or elapsed>=55000,'premature final window closure');require(n<12 or purpose=='closing','last bounded check must close');f=v.get('fence',{});require(f.get('name')=='final-check-'+str(n)+'-before' and f.get('ready') is True and f.get('token')==manifest['token'] and f.get('exact_report_before_after') is True and f.get('exact_frame_before_after') is True,'final exact-string fence absent');self.write(name,data);self.last_final_check=n;self.final_closed=purpose=='closing';return
   fields=name.split('/');require(len(fields)==2 and fields[0] in MODES and fields[1] in ['manifest.json','capture.json','currentness.json','pre-next.json'],'fixed capture path required');mode,file=fields;i=MODES.index(mode);stage=self.stages[i]
   if file=='manifest.json':
    if i:require((self.output/MODES[i-1]/'pre-next.json').exists(),'previous qualified pre-next fence required')
    require(len(data)<=65536,'manifest bound');v=raw_object(data,'manifest');manifest_identity(v,stage['request_id']);require(v.get('format')=='nvwa76-raw-transfer-v1' and v.get('encoding')=='utf-8' and type(v.get('bytes')) is int and 0<v['bytes']<=MAX,'manifest format/bound');self.write(name,data);self.manifests[mode]=v;return
   require(mode in self.manifests,'manifest required');manifest=self.manifests[mode]
   if file=='capture.json':
    verify_bytes(manifest,data,expected_request_id=stage['request_id']);v=raw_object(data,'record');r,f=v['report'],v['frame'];require(r['endpoint']==f['endpoint']=='web','actual Web required');require(json.loads(r['work_json'])==self.work,'pinned Work mismatch');require(r['diagnostic']['mode']==f['diagnostic']['mode']==stage['diagnostic_mode'] and r['diagnostic']['palette']==f['diagnostic']['palette']=='Textured','exact mode/palette mismatch');source=f.get('source_diagnostic');require(isinstance(source,dict) and source==r.get('source_diagnostic'),'source report/frame mismatch');require(source.get('target_active') is False and source.get('target_authored') is None,'no target allowed')
    for k,value in stage['source_equals'].items():require(k in source and source[k]==value,'root-fixed source field mismatch '+k)
    for k in stage['required_source_keys']:require(k in source and source[k] is not None,'unknown source field '+k)
    base=f['full_base'];require(base['sample']['source_seconds']==2 and base['sample']['playing'] is False and isinstance(base['bones'],list) and len(base['bones'])>0,'actual held2/bones required');anchor={'work_json':r['work_json'],'work_sha256':r['work_sha256'],'identity':r['captured_identity'],'generation':base['generation'],'sample':base['sample'],'bones':base['bones']};require(self.anchor is None or self.anchor==anchor,'three-proof identity changed');self.write(name,data);self.anchor=anchor;self.captures[mode]=True;return
   require(self.captures.get(mode),'raw required');require(len(data)<=131072,'receipt bound');v=raw_object(data,'receipt');require(v.get('request_id')==stage['request_id'] and v.get('mode')==mode,'receipt identity')
   if file=='currentness.json':
    require(v.get('manifest')==manifest,'currentness manifest');required={'after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response'};fences=v.get('fences',[]);require(required.issubset({f.get('name') for f in fences}),'missing currentness fences');require(all(f.get('ready') is True and f.get('token')==manifest['token'] and f.get('exact_report_before_after') is True and f.get('exact_frame_before_after') is True for f in fences),'invalid currentness fence')
   else:
    require(i<2,'source_garment STOP forever');require((self.output/mode/'currentness.json').exists(),'qualified receipt required');f=v.get('fence',{});require(v.get('token')==manifest['token'] and f.get('name')=='pre-next' and f.get('ready') is True and f.get('token')==manifest['token'] and f.get('exact_report_before_after') is True and f.get('exact_frame_before_after') is True,'pre-next exact fence required');require(v.get('reason') in ['button','pace45'],'guarded Next source required')
   self.write(name,data)
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,request,client_address,server):super().__init__(request,client_address,server,directory=str(server.receiver.site))
 def reply(self,status,text):
  data=text.encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def translate_path(self,path):
  clean=unquote(urlsplit(path).path);draft={'/helper.html','/shoulder.js','/transfer-core.js'}
  if clean in draft:return str(DRAFT/clean[1:])
  return super().translate_path(path)
 def do_GET(self):
  r=self.server.receiver
  if self.headers.get('Host')!=r.host:return self.reply(403,'{"error":"Host rejected"}')
  if self.path=='/_shoulder/config':return self.reply(200,json.dumps(r.config))
  if urlsplit(self.path).path.startswith('/_shoulder/'):return self.reply(404,'{"error":"unknown path"}')
  return super().do_GET()
 def do_POST(self):
  try:
   r=self.server.receiver;length=self.headers.get('Content-Length');length=int(length) if length and re.fullmatch(r'[0-9]+',length) else None;r.guard(self.headers.get('Host'),self.headers.get('Origin'),length,self.headers.get('Transfer-Encoding'));data=self.rfile.read(length);require(len(data)==length,'truncated body');r.accept(self.path,data)
  except (ValueError,KeyError,TypeError,FileExistsError) as e:return self.reply(400,json.dumps({'error':str(e)}))
  return self.reply(201,'{"stored":true,"scope":"exact snapshot only; screenshot must be separately matched"}')
 def do_OPTIONS(self):return self.reply(405,'{"error":"no CORS"}')
 def list_directory(self,path):return self.reply(403,'{"error":"listing disabled"}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--site',required=True,type=Path);p.add_argument('--contract',required=True,type=Path);p.add_argument('--run-id',required=True);p.add_argument('--port',type=int,default=9205);a=p.parse_args();require(9200<=a.port<=9299,'Nvwa port range');require((a.site/'pkg/b1_shoulder_source_corrective.js').is_file(),'compiled b1_79 package required');r=Receiver(a.site,DRAFT/'actual'/a.run_id,a.run_id,a.port,json.loads(a.contract.read_text()));http=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);http.receiver=r;print(json.dumps({'url':r.origin+'/helper.html?work=works/shoulder-rear-baseline-arms.nvwa.json&player=1&case=proofs','explicit_pace45_suffix':'&pace=45','expected_ids':[s['request_id'] for s in r.stages],'output':str(r.output)}),flush=True);http.serve_forever()
if __name__=='__main__':main()
