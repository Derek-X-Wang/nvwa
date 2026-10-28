"""Loopback receiver. Run and three request identities come from frozen contract."""
import argparse,hashlib,json,re,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from collect_transfer import manifest_identity,verify_bytes,raw_object
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.work/hairline-aba79';SITE=OUT/'retained-r2-site';MAX=32*1024*1024
class Reject(ValueError):pass
def require(ok,msg):
 if not ok:raise Reject(msg)
def contract_valid(c):
 require(c.get('version')==1 and re.fullmatch(r'[A-Za-z0-9_-]{1,40}',c.get('run_id','')) is not None,'run contract identity')
 require(c.get('work_path')=='works/default-arms.nvwa.json' and c.get('source_seconds')==0 and c.get('mode')=='combined' and c.get('palette')=='textured' and c.get('window_ms')==90000,'fixed controls required')
 stages=c.get('stages',[]);require(len(stages)==3,'three stages required')
 for s,(label,wire,typed) in zip(stages,[('A1','a_original','AOriginal'),('B','b_local_alpha','BLocalAlpha'),('A2','a_original','AOriginal')]):require(s.get('label')==label and s.get('variant')==wire and s.get('typed_variant')==typed,'A/B/A required')
 ids=[c.get('hold_id')]+[s.get('request_id') for s in stages];require(len(set(ids))==4 and all(isinstance(i,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',i) for i in ids),'independent unique request IDs required')
 return c
class Receiver:
 def __init__(self,site,output,contract,port):
  c=contract_valid(contract);self.site=site;self.output=output;self.config=dict(c);self.run_id=c['run_id'];self.origin=f'http://127.0.0.1:{port}';self.host=f'127.0.0.1:{port}';self.lock=threading.Lock();self.manifests={};self.received=set();self.current=set();self.closed=set();self.work=json.loads((site/c['work_path']).read_text());self.config.update(expected_work=self.work,work_file_sha256=hashlib.sha256((site/c['work_path']).read_bytes()).hexdigest())
  output.mkdir(parents=True,exist_ok=False);(output/'events').mkdir()
  for s in c['stages']:(output/s['label']).mkdir()
  self.write('SERVER-CONFIG.json',json.dumps(self.config,indent=2).encode())
 def write(self,name,data):
  with (self.output/name).open('xb') as f:f.write(data)
 def guard(self,host,origin,length,transfer_encoding=None):require(host==self.host and origin==self.origin,'Host/Origin rejected');require(transfer_encoding is None,'Transfer-Encoding rejected');require(type(length) is int and 0<length<=MAX,'body length rejected')
 def accept(self,path,data):
  require(len(data)<=MAX,'body too large');prefix='/_aba/'+self.run_id+'/';require(path.startswith(prefix),'path/run rejected');name=path[len(prefix):]
  with self.lock:
   if re.fullmatch(r'event/[1-9][0-9]{0,2}',name):
    n=int(name.split('/')[1]);v=raw_object(data,'event');require(n<=512 and len(data)<=8192 and v.get('seq')==n and isinstance(v.get('name'),str),'event bound/identity');self.write(f'events/{n:03}.json',data);return
   require(re.fullmatch(r'(A1|B|A2)/(manifest|capture|currentness|window-close)\.json',name) is not None,'path rejected');label,kind=name.split('/');stage=next(s for s in self.config['stages'] if s['label']==label);i=self.config['stages'].index(stage);require(i==0 or self.config['stages'][i-1]['label'] in self.closed,'previous screenshot window must close first');rid=stage['request_id'];v=raw_object(data,kind)
   if kind=='manifest.json':
    require(len(data)<=65536,'manifest bound');manifest_identity(v,rid);require(v.get('format')=='nvwa76-raw-transfer-v1' and v.get('encoding')=='utf-8' and type(v.get('bytes')) is int and 0<v['bytes']<=MAX,'manifest format/size');self.write(name,data);self.manifests[label]=v;return
   require(label in self.manifests,'manifest required');m=self.manifests[label]
   if kind=='capture.json':
    verify_bytes(m,data,expected_request_id=rid);r,f=v['report'],v['frame'];require(json.loads(r['work_json'])==self.work,'fixed Work mismatch');require(f.get('candidate',{}).get('variant')==stage['typed_variant'] and f['candidate'].get('pre_visibility_publication_matches') is True,'actual variant/visibility mismatch');require(f['full_base']['sample']['source_seconds']==0 and f['full_base']['sample']['playing'] is False,'held source0 required');require(f['candidate']['generation']==f['full_base']['generation'],'generation mismatch');require(f['diagnostic']['mode']=='Combined' and f['diagnostic']['palette']=='Textured','fixed diagnostic required');self.write(name,data);self.received.add(label);return
   require(label in self.received and len(data)<=131072,'capture required/receipt bound');require(v.get('request_id')==rid,'receipt request mismatch')
   def fence(f):require(f.get('ready') is True and f.get('token')==m['token'] and f.get('exact_report_before_after') is True and f.get('exact_frame_before_after') is True,'currentness fence invalid')
   if kind=='currentness.json':
    require(v.get('run_id')==self.run_id and v.get('manifest')==m,'receipt identity');fences=v.get('fences',[]);required={'after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response'};require(required.issubset({f.get('name') for f in fences}),'six fences required')
    for f in fences:fence(f)
    self.write(name,data);self.current.add(label);return
   require(label in self.current and v.get('token')==m['token'],'currentness required');opening,closing=v.get('open',{}),v.get('close',{});require(opening.get('name')=='SCREENSHOT-WINDOW-OPEN' and opening.get('request_id')==rid and opening.get('token')==m['token'],'window opening identity');fence(closing);require(closing.get('name')=='screenshot-close' and 0<=closing['ms']-opening['ms']<=90000,'bounded closing fence required');require(v.get('reason') in ['button','pace60'],'window close reason');self.write(name,data);self.closed.add(label)
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,request,client_address,server):super().__init__(request,client_address,server,directory=str(server.receiver.site))
 def reply(self,code,text):
  data=text.encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  r=self.server.receiver
  if self.headers.get('Host')!=r.host:return self.reply(403,'{"error":"Host rejected"}')
  if self.path=='/_aba/config':return self.reply(200,json.dumps(r.config))
  if urlsplit(self.path).path.startswith('/_aba/'):return self.reply(404,'{"error":"unknown route"}')
  return super().do_GET()
 def do_HEAD(self):
  if self.headers.get('Host')!=self.server.receiver.host:return self.reply(403,'{"error":"Host rejected"}')
  return super().do_HEAD()
 def do_POST(self):
  try:
   r=self.server.receiver;raw=self.headers.get('Content-Length');length=int(raw) if raw and re.fullmatch(r'[0-9]+',raw) else None;r.guard(self.headers.get('Host'),self.headers.get('Origin'),length,self.headers.get('Transfer-Encoding'));data=self.rfile.read(length);require(len(data)==length,'truncated body');r.accept(self.path,data)
  except (ValueError,KeyError,TypeError,FileExistsError) as e:return self.reply(400,json.dumps({'error':str(e)}))
  return self.reply(201,'{"stored":true,"scope":"bytes/currentness receipt; no quality admission"}')
 def do_OPTIONS(self):return self.reply(405,'{"error":"no CORS"}')
 def list_directory(self,path):return self.reply(403,'{"error":"directory listing disabled"}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--port',type=int,default=9205);a=p.parse_args();from freeze import verify;verify();require(9200<=a.port<=9299,'Nvwa port range');c=contract_valid(json.loads(a.contract.read_text()));s=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
 try:
  s.receiver=Receiver(SITE,OUT/'actual'/c['run_id'],c,a.port);print(json.dumps({'url':s.receiver.origin+'/aba82.html?work=works/default-arms.nvwa.json&benchmark=1&player=1&case=aba&pace=60','request_ids':[x['request_id'] for x in c['stages']],'output':str(s.receiver.output)}),flush=True);s.serve_forever()
 finally:s.server_close()
if __name__=='__main__':main()
