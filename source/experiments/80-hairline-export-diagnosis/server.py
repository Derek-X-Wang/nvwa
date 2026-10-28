"""Task-owned loopback-only static site + bounded create-only exact-record receiver."""
import argparse,hashlib,json,re,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from collect_transfer import manifest_identity,verify_bytes,raw_object
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.work/hairline-export79';SITE=OUT/'retained-r2-site';MAX=32*1024*1024
class Reject(ValueError):pass
def require(ok,why):
 if not ok:raise Reject(why)
class Receiver:
 def __init__(self,site,output,run_id,port):
  require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}',run_id) is not None,'invalid run ID');self.site=site;self.output=output;self.run_id=run_id;self.origin=f'http://127.0.0.1:{port}';self.host=f'127.0.0.1:{port}';self.lock=threading.Lock();self.manifest=None;self.received=False
  output.mkdir(parents=True,exist_ok=False);(output/'events').mkdir();self.work=json.loads((site/'works/default-arms.nvwa.json').read_text());self.config={'run_id':run_id,'hold_id':run_id+'-hold0','request_id':run_id+'-A','expected_work':self.work,'work_file_sha256':hashlib.sha256((site/'works/default-arms.nvwa.json').read_bytes()).hexdigest()}
  self.write('SERVER-CONFIG.json',json.dumps({'origin':self.origin,**self.config,'scope':'exact bytes plus explicitly fenced snapshot; receiver arrival is not current render or quality admission'},indent=2).encode())
 def write(self,name,data):
  with (self.output/name).open('xb') as f:f.write(data)
 def guard(self,host,origin,length,transfer_encoding=None):
  require(host==self.host,'Host rejected');require(origin==self.origin,'Origin rejected');require(transfer_encoding is None,'Transfer-Encoding rejected');require(type(length) is int and 0<length<=MAX,'body length rejected')
 def accept(self,path,data):
  require(len(data)<=MAX,'body too large');prefix='/_diag80/'+self.run_id+'/';require(path.startswith(prefix),'path/run ID rejected');name=path[len(prefix):]
  with self.lock:
   if re.fullmatch(r'event/[1-9][0-9]{0,2}',name):
    n=int(name.split('/')[1]);require(n<=512 and len(data)<=8192,'event bound');v=raw_object(data,'event');require(v.get('seq')==n and isinstance(v.get('name'),str),'event identity');self.write(f'events/{n:03}.json',data);return
   require(name in ['manifest.json','capture.json','currentness.json'],'path rejected')
   if name=='manifest.json':
    require(len(data)<=65536,'manifest too large');v=raw_object(data,'manifest');manifest_identity(v,self.config['request_id']);require(v.get('format')=='nvwa76-raw-transfer-v1' and v.get('encoding')=='utf-8','manifest format');require(type(v.get('bytes')) is int and 0<v['bytes']<=MAX,'manifest body size');self.write(name,data);self.manifest=v;return
   require(self.manifest is not None,'manifest required first')
   if name=='capture.json':
    verify_bytes(self.manifest,data,expected_request_id=self.config['request_id']);v=raw_object(data,'envelope');r,f=v['report'],v['frame'];require(json.loads(r['work_json'])==self.work,'fixed Work mismatch');require(f.get('candidate',{}).get('variant')=='AOriginal' and f['candidate'].get('pre_visibility_publication_matches') is True,'original A visibility witness');require(f['full_base']['sample']['source_seconds']==0 and f['full_base']['sample']['playing'] is False,'source0 held');require(f['candidate']['generation']==f['full_base']['generation'],'generation mismatch');self.write(name,data);self.received=True;return
   require(self.received,'raw capture required first');require(len(data)<=131072,'currentness too large');v=raw_object(data,'currentness');require(v.get('run_id')==self.run_id and v.get('request_id')==self.config['request_id'],'currentness identity');require(v.get('manifest')==self.manifest,'currentness manifest mismatch');fences=v.get('fences',[]);required={'after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response'};require(required.issubset({f.get('name') for f in fences}),'required currentness fences absent');require(all(f.get('ready') is True and f.get('token')==self.manifest['token'] and f.get('exact_report_before_after') is True and f.get('exact_frame_before_after') is True for f in fences),'currentness fence failed');self.write(name,data)
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,request,client_address,server):super().__init__(request,client_address,server,directory=str(server.receiver.site))
 def reply(self,code,text):
  data=text.encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  r=self.server.receiver
  if self.headers.get('Host')!=r.host:return self.reply(403,'{"error":"Host rejected"}')
  if self.path=='/_diag80/config':return self.reply(200,json.dumps(r.config))
  parts=urlsplit(self.path)
  if parts.path.startswith('/_diag80/'):return self.reply(404,'{"error":"unknown route"}')
  return super().do_GET()
 def do_POST(self):
  r=self.server.receiver
  try:
   raw=self.headers.get('Content-Length');length=int(raw) if raw is not None and re.fullmatch(r'[0-9]+',raw) else None;r.guard(self.headers.get('Host'),self.headers.get('Origin'),length,self.headers.get('Transfer-Encoding'));data=self.rfile.read(length);require(len(data)==length,'truncated body');r.accept(self.path,data)
  except (ValueError,KeyError,TypeError,FileExistsError) as e:return self.reply(400,json.dumps({'error':str(e)}))
  return self.reply(201,'{"stored":true,"scope":"bytes receipt; not current render or quality"}')
 def do_OPTIONS(self):return self.reply(405,'{"error":"no CORS"}')
 def list_directory(self,path):return self.reply(403,'{"error":"directory listing disabled"}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--port',type=int,default=9205);a=p.parse_args();require(9200<=a.port<=9299,'Nvwa port range required');r=Receiver(SITE,OUT/'actual'/a.run_id,a.run_id,a.port);s=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);s.receiver=r
 print(json.dumps({'manual_url':r.origin+'/diagnostic80.html?work=works/default-arms.nvwa.json&benchmark=1&player=1&case=manual','auto_url':r.origin+'/diagnostic80.html?work=works/default-arms.nvwa.json&benchmark=1&player=1&case=fixed-auto','expected_hold_id':r.config['hold_id'],'expected_A_id':r.config['request_id'],'output':str(r.output)}),flush=True);s.serve_forever()
if __name__=='__main__':main()
