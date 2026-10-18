#!/usr/bin/env python3
"""Isolated appearance preview loopback site and exclusive exact-capture sink."""
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
def empty_runtime(value):
 # Both fixed-runtime representations mean no accessory observations. Reject all residual fields.
 return value is None or (isinstance(value,dict) and set(value)=={'accessories'} and value['accessories'] is None)
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
 if not isinstance(value,dict) or set(value)!={'request','report','frame'}:reject(400,'expected exact appearance capture envelope')
 req=value['request'];report=value['report'];frame=value['frame']
 if not isinstance(req,dict) or req.get('request_id')!=capture_id:reject(400,'capture path/request_id mismatch')
 if not isinstance(report,dict) or report.get('phase')!='captured' or report.get('request')!=req:reject(400,'current captured report/request required')
 mode=report.get('desired')
 if mode not in {'baseline','skin','skin+eyes+hair'} or mode!=report.get('applied'):reject(400,'desired/current applied appearance mismatch')
 if not isinstance(frame,dict) or frame.get('request')!=req or frame.get('geometry_equal') is not True:reject(400,'current frame/request/geometry proof required')
 hashes=[report.get('geometry_before_sha256'),report.get('geometry_after_sha256'),frame.get('geometry_before_sha256'),frame.get('geometry_after_sha256')]
 if any(not isinstance(x,str) or not re.fullmatch('[0-9a-f]{64}',x) for x in hashes) or len(set(hashes))!=1:reject(400,'before/after report/frame geometry hashes must agree')
 snapshot=frame.get('snapshot')
 if not isinstance(snapshot,dict) or snapshot.get('schema_version')!=1 or snapshot.get('profile_id')!='nvwa-mpfb-b1-motion-v1':reject(400,'expected actual motion-profile snapshot')
 if not isinstance(snapshot.get('bones'),list) or len(snapshot['bones'])!=53:reject(400,'snapshot must include53 actual bones')
 parts=snapshot.get('parts')
 if not isinstance(parts,list) or len(parts)!=2 or any(not isinstance(p,dict) for p in parts) or {p.get('name') for p in parts}!={'body','garment'}:reject(400,'snapshot must include actual body and garment')
 appearance=frame.get('appearance');observed=report.get('appearance')
 if not isinstance(appearance,dict) or not isinstance(observed,dict):reject(400,'actual appearance observations required')
 expected_state='plain' if mode=='baseline' else 'skin'
 if appearance.get('state')!=expected_state or observed.get('state')!=expected_state:reject(400,'body appearance state does not match mode')
 if report.get('applied_generation')!=snapshot.get('generation') or report.get('sample')!=snapshot.get('sample') or report.get('parameters')!=snapshot.get('parameters'):reject(400,'report/current snapshot identity mismatch')
 runtime=appearance.get('accessory_runtime');compact=observed.get('accessory_runtime')
 if mode=='skin+eyes+hair':
  if not isinstance(runtime,dict) or not isinstance(compact,dict):reject(400,'accessory runtime observations required')
  for proof in (runtime,compact):
   if proof.get('generation')!=snapshot.get('generation') or proof.get('revision')!=snapshot.get('revision') or proof.get('sample')!=snapshot.get('sample'):reject(400,'accessory/current snapshot identity mismatch')
   rows=proof.get('accessories')
   if not isinstance(rows,list) or len(rows)!=2 or any(not isinstance(row,dict) for row in rows) or {row.get('name') for row in rows}!={'eyes','hair'} or any(row.get('not_saved') is not True for row in rows):reject(400,'exact unsaved eyes/hair observations required')
  if runtime.get('identity')!=compact.get('identity'):reject(400,'report/frame accessory binding mismatch')
 else:
  if 'accessory_runtime' not in appearance or 'accessory_runtime' not in observed or not empty_runtime(runtime) or not empty_runtime(compact):reject(400,'accessory observations present outside accessory mode')
 quality=frame.get('quality')
 if not isinstance(quality,dict) or quality!=report.get('quality'):reject(400,'matching actual quality metadata required')
 selected=quality.get('selected');camera=quality.get('scene_camera')
 if selected not in {'frozen64','hair_coverage','eye_polygon_normals','eyes_unlit_diagnostic'}:reject(400,'unknown quality control')
 if not isinstance(camera,dict) or type(camera.get('msaa_samples')) is not int or camera['msaa_samples'] not in {1,2,4,8} or camera.get('active') is not True:reject(400,'actual active scene camera MSAA required')
 if quality.get('work_appearance')!={'type':'none'}:reject(400,'quality preview requires Work appearance None')
 if quality.get('production_appearance_controller_disabled') is not True:reject(400,'quality comparison requires explicitly disabled production appearance controller')
 if any(field.startswith('production_') and field!='production_appearance_controller_disabled' for field in quality):reject(400,'production appearance status claims are inapplicable to isolated quality comparison')
 base=quality.get('base_binding_identity')
 if not isinstance(base,dict) or base.get('runtime_ready') is not True or base.get('runtime_error') is not None or base.get('revision')!=snapshot['revision']:reject(400,'current base B1 binding identity required')
 if mode=='skin+eyes+hair':
  samples=camera['msaa_samples']
  if selected=='hair_coverage' and samples==1:reject(400,'hair ATC requires multisampling')
  for proof in (runtime,compact):
   if proof.get('quality')!=selected or proof.get('actual_msaa_samples')!=samples:reject(400,'accessory quality/MSAA metadata mismatch')
   for row in proof['accessories']:
    material=row.get('material',{})
    alpha='AlphaToCoverage' if selected=='hair_coverage' and row['name']=='hair' else 'Mask(0.5)'
    unlit=selected=='eyes_unlit_diagnostic' and row['name']=='eyes'
    if material.get('quality')!=selected or material.get('actual_msaa_samples')!=samples or material.get('alpha')!=alpha or material.get('unlit') is not unlit:reject(400,'actual observed material does not match selected control')
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
    if urlsplit(self.path).path.startswith('/__appearance_capture'):reject(404,'capture route accepts POST only')
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
    parsed=urlsplit(self.path);prefix='/__appearance_capture/'
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
  print(f'Isolated B1 appearance site http://127.0.0.1:{a.port}; exclusive captures {a.captures.resolve()}',flush=True)
  server.serve_forever()
if __name__=='__main__':main()
