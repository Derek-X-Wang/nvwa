#!/usr/bin/env python3
"""Test-only root-launched loopback static site and exclusive exact-capture sink."""
import argparse
import hashlib
import http.server
import json
import math
from pathlib import Path
import re
import threading
from urllib.parse import unquote,urlsplit

MAX_BYTES=64*1024*1024
MAX_CAPTURES=32
SAFE_ID=re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
CLIPS={'b1_arm_rehearsal_v1','b1_knee_flex_v1'}
class CaptureError(ValueError):
 def __init__(self,status,message):self.status=status;super().__init__(message)
def reject(status,message):raise CaptureError(status,message)
def finite_number(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def duplicate_free(pairs):
 obj={}
 for key,value in pairs:
  if key in obj:reject(400,'duplicate JSON field: '+key)
  obj[key]=value
 return obj
def parse_record(raw,capture_id):
 if not SAFE_ID.fullmatch(capture_id):reject(400,'unsafe capture ID')
 if not 0<len(raw)<=MAX_BYTES:reject(413,'capture body must be1..64MiB')
 try:
  value=json.loads(raw.decode('utf-8'),object_pairs_hook=duplicate_free,parse_constant=lambda x:reject(400,'nonfinite JSON constant'))
 except (UnicodeError,json.JSONDecodeError,RecursionError) as error:reject(400,'invalid UTF-8/JSON capture: '+str(error))
 stack=[value]
 while stack:
  item=stack.pop()
  if isinstance(item,dict):stack.extend(item.values())
  elif isinstance(item,list):stack.extend(item)
  elif isinstance(item,(int,float)) and not isinstance(item,bool):
   if not math.isfinite(item):reject(400,'nonfinite JSON number')
 if not isinstance(value,dict) or set(value)!={'kind','request','snapshot','evidence'} or value['kind']!='studio':reject(400,'expected exact Studio probe capture envelope')
 req=value['request'];frame=value['snapshot']
 if not isinstance(req,dict) or req.get('request_id')!=capture_id:reject(400,'capture path/request_id mismatch')
 if set(req)-{'request_id','action','clip_id','seconds','torso_length','jaw_drop'}:reject(400,'unknown capture request field')
 if req.get('action') not in {'sample','play','pause','snapshot'}:reject(400,'invalid capture action')
 if not isinstance(frame,dict) or frame.get('schema_version')!=1 or frame.get('profile_id')!='nvwa-mpfb-b1-motion-v1':reject(400,'expected actual motion-profile snapshot')
 sample=frame.get('sample');parameters=frame.get('parameters')
 if not isinstance(sample,dict) or not isinstance(parameters,dict):reject(400,'snapshot sample/parameters missing')
 if not all(finite_number(sample.get(k)) for k in ('position_seconds','source_seconds')):reject(400,'snapshot finite time missing')
 if req['action']=='sample':
  if req.get('clip_id') not in CLIPS:reject(400,'invalid sample clip')
  for key in ('seconds','torso_length','jaw_drop'):
   n=req.get(key);low,high=(0.,4.) if key=='seconds' else (-1.,1.)
   if not finite_number(n) or not low<=n<=high:reject(400,'invalid sample '+key)
  if sample.get('clip_id')!=req['clip_id'] or sample.get('timeline_id')!='probe-entry':reject(400,'snapshot clip/timeline request mismatch')
  if any(abs(sample[k]-req['seconds'])>1e-6 for k in ('position_seconds','source_seconds')):reject(400,'snapshot time/request mismatch')
  if any(not finite_number(parameters.get(k)) or abs(parameters[k]-req[k])>1e-6 for k in ('torso_length','jaw_drop')):reject(400,'snapshot shape/request mismatch')
 if not isinstance(frame.get('bones'),list) or len(frame['bones'])!=53:reject(400,'snapshot must include53 actual bones')
 parts=frame.get('parts')
 if not isinstance(parts,list) or len(parts)!=2 or any(not isinstance(p,dict) for p in parts) or {p.get('name') for p in parts}!={'body','garment'}:reject(400,'snapshot must include actual body and garment')
 return value

class CaptureStore:
 def __init__(self,root):
  self.root=Path(root).resolve(strict=True)
  if not self.root.is_dir():raise ValueError('captures must be an existing owned directory')
  self.lock=threading.Lock()
 def save(self,capture_id,raw):
  parse_record(raw,capture_id)
  with self.lock:
   if len(list(self.root.glob('*.json')))>=MAX_CAPTURES:reject(409,'capture limit32 reached')
   destination=self.root/(capture_id+'.json')
   try:
    with destination.open('xb') as output:output.write(raw);output.flush()
   except FileExistsError:reject(409,'capture already exists; no overwrite')
   except OSError as error:reject(500,'capture write failed: '+str(error))
  return {'stored':True,'request_id':capture_id,'file':destination.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def make_handler(site,captures,port):
 site=Path(site).resolve(strict=True)
 if not site.is_dir():raise ValueError('site must be an existing owned directory')
 store=CaptureStore(captures);authority=f'127.0.0.1:{port}';origin='http://'+authority
 class ProbeHandler(http.server.SimpleHTTPRequestHandler):
  def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(site),**kwargs)
  def end_headers(self):
   self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
  def json_response(self,status,value):
   body=(json.dumps(value,allow_nan=False)+'\n').encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def valid_authority(self):
   if self.headers.get_all('Host')!=[authority]:reject(403,'Host must match exact loopback authority')
  def translate_path(self,path):
   decoded=unquote(urlsplit(path).path,errors='strict');parts=decoded.split('/')
   if '\\' in decoded or any(p in {'.','..'} or p.startswith('.') for p in parts if p):raise ValueError('unsafe static path')
   target=(site/decoded.lstrip('/')).resolve()
   if not target.is_relative_to(site):raise ValueError('static path escapes owned site')
   return str(target)
  def send_head(self):
   try:
    self.valid_authority()
    if urlsplit(self.path).path.startswith('/__b1_capture'):reject(404,'capture route accepts POST only')
    self.translate_path(self.path)
   except (CaptureError,ValueError,UnicodeError) as error:
    self.send_error(getattr(error,'status',403),str(error));return None
   if 'If-Modified-Since' in self.headers:del self.headers['If-Modified-Since']
   return super().send_head()
  def list_directory(self,path):self.send_error(403,'directory listing disabled');return None
  def do_POST(self):
   try:
    self.valid_authority()
    if self.headers.get_all('Origin')!=[origin]:reject(403,'Origin must match exact loopback site')
    parsed=urlsplit(self.path);prefix='/__b1_capture/'
    if not parsed.path.startswith(prefix) or parsed.query or parsed.fragment:reject(404,'unknown capture route')
    capture_id=parsed.path[len(prefix):]
    if not SAFE_ID.fullmatch(capture_id):reject(400,'unsafe capture ID')
    if self.headers.get('Transfer-Encoding') is not None:reject(400,'chunked capture requests are unsupported')
    if self.headers.get_content_type()!='application/json':reject(415,'capture Content-Type must be application/json')
    lengths=self.headers.get_all('Content-Length')
    if not lengths or len(lengths)!=1 or not lengths[0].isdigit():reject(411,'one exact Content-Length is required')
    length=int(lengths[0])
    if not 0<length<=MAX_BYTES:reject(413,'capture Content-Length exceeds64MiB or is empty')
    raw=self.rfile.read(length)
    if len(raw)!=length:reject(400,'truncated capture body')
    result=store.save(capture_id,raw);self.json_response(201,result)
   except CaptureError as error:self.json_response(error.status,{'stored':False,'error':str(error)})
   except (OSError,ValueError,RecursionError,OverflowError) as error:self.json_response(400,{'stored':False,'error':str(error)})
 return ProbeHandler

def main():
 p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--captures',type=Path,required=True);p.add_argument('--port',type=int,required=True);a=p.parse_args()
 if not 9203<=a.port<=9299:p.error('use an assigned free Nvwa probe port9203..9299; preserve9201/9202')
 handler=make_handler(a.site,a.captures,a.port)
 with http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler) as server:
  server.daemon_threads=True
  print(f'Test-only B1 Studio site http://127.0.0.1:{a.port}; exclusive captures {a.captures.resolve()}',flush=True)
  server.serve_forever()
if __name__=='__main__':main()
