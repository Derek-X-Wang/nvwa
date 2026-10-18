#!/usr/bin/env python3
"""Socket-free parser/handler controls for the test-only capture adapter."""
import copy
from email.message import Message
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from serve import CaptureError,CaptureStore,MAX_BYTES,MAX_CAPTURES,make_handler,parse_record

class CaptureControls(unittest.TestCase):
 def record(self,request_id='sample-1'):
  return {'kind':'studio','request':{'request_id':request_id,'action':'sample','clip_id':'b1_knee_flex_v1','seconds':2.,'torso_length':0.,'jaw_drop':0.},'snapshot':{'schema_version':1,'profile_id':'nvwa-mpfb-b1-motion-v1','sample':{'clip_id':'b1_knee_flex_v1','timeline_id':'probe-entry','source_seconds':2.,'position_seconds':2.},'parameters':{'torso_length':0.,'jaw_drop':0.},'bones':[{} for _ in range(53)],'parts':[{'name':'body'},{'name':'garment'}]},'evidence':'comparator-only handler fixture; not actual runtime'}
 def raw(self,record=None):return json.dumps(record or self.record()).encode()
 def test_exact_record_and_exclusive_no_overwrite(self):
  with tempfile.TemporaryDirectory() as folder:
   store=CaptureStore(folder);raw=self.raw();receipt=store.save('sample-1',raw);self.assertTrue(receipt['stored']);self.assertEqual((Path(folder)/'sample-1.json').read_bytes(),raw)
   with self.assertRaisesRegex(CaptureError,'no overwrite'):store.save('sample-1',raw)
   self.assertEqual((Path(folder)/'sample-1.json').read_bytes(),raw)
 def test_safe_path_and_request_id_binding(self):
  for identity in ['../sample-1','sample/1','%2e%2e','', 'x'*65,'different-id']:
   with self.assertRaises(CaptureError):parse_record(self.raw(),identity)
 def test_duplicate_and_nonfinite_json_rejected(self):
  for raw in [b'{"kind":"studio","kind":"studio"}',self.raw().replace(b'2.0',b'NaN',1),self.raw().replace(b'2.0',b'1e999',1)]:
   with self.assertRaises(CaptureError):parse_record(raw,'sample-1')
 def test_sample_time_shape_and_timeline_binding(self):
  mutations=[('source_seconds',1.),('position_seconds',0.),('timeline_id','wrong-entry'),('clip_id','b1_arm_rehearsal_v1')]
  for key,value in mutations:
   record=self.record();record['snapshot']['sample'][key]=value
   with self.assertRaises(CaptureError):parse_record(self.raw(record),'sample-1')
  record=self.record();record['snapshot']['parameters']['torso_length']=1.
  with self.assertRaises(CaptureError):parse_record(self.raw(record),'sample-1')
 def test_count_cap_preserves_existing_files(self):
  with tempfile.TemporaryDirectory() as folder:
   for k in range(MAX_CAPTURES):(Path(folder)/f'old-{k}.json').write_text('{}')
   with self.assertRaisesRegex(CaptureError,'limit32'):CaptureStore(folder).save('sample-1',self.raw())
   self.assertEqual(len(list(Path(folder).glob('*.json'))),32)
 def handler(self,site,captures,headers=None,path='/__b1_capture/sample-1',raw=None):
  cls=make_handler(site,captures,9209);handler=cls.__new__(cls);handler.path=path;handler.headers=Message();body=self.raw() if raw is None else raw
  values={'Host':'127.0.0.1:9209','Origin':'http://127.0.0.1:9209','Content-Type':'application/json','Content-Length':str(len(body))}
  values.update(headers or {})
  for key,value in values.items():
   if value is not None:handler.headers[key]=value
  handler.rfile=BytesIO(body);responses=[];handler.json_response=lambda status,value:responses.append((status,value));handler.do_POST();return responses
 def test_handler_exact_origin_and_host_enforcement(self):
  for bad in [{'Origin':None},{'Origin':'http://localhost:9209'},{'Origin':'http://127.0.0.1:9210'},{'Host':'localhost:9209'}]:
   with tempfile.TemporaryDirectory() as site,tempfile.TemporaryDirectory() as captures:
    responses=self.handler(site,captures,bad);self.assertEqual(responses[0][0],403);self.assertFalse(list(Path(captures).iterdir()))
 def test_handler_declared_size_type_and_transfer_controls(self):
  cases=[({'Content-Length':str(MAX_BYTES+1)},413),({'Content-Length':None},411),({'Content-Type':'text/plain'},415),({'Transfer-Encoding':'chunked'},400),({'Content-Length':'999'},400)]
  for headers,status in cases:
   with tempfile.TemporaryDirectory() as site,tempfile.TemporaryDirectory() as captures:
    self.assertEqual(self.handler(site,captures,headers)[0][0],status);self.assertFalse(list(Path(captures).iterdir()))
 def test_handler_success_and_route_rejection(self):
  with tempfile.TemporaryDirectory() as site,tempfile.TemporaryDirectory() as captures:
   self.assertEqual(self.handler(site,captures)[0][0],201)
   self.assertEqual(self.handler(site,captures,path='/__b1_capture/sample-1?overwrite=1')[0][0],404)
   self.assertEqual(self.handler(site,captures,path='/__b1_capture/../escape')[0][0],400)
 def test_static_path_cannot_escape_owned_site(self):
  with tempfile.TemporaryDirectory() as site,tempfile.TemporaryDirectory() as captures,tempfile.TemporaryDirectory() as outside:
   cls=make_handler(site,captures,9209);handler=cls.__new__(cls)
   for path in ['/../outside','/%2e%2e/outside','/.hidden','/a\\b']:
    with self.assertRaises(ValueError):handler.translate_path(path)
   (Path(site)/'escape').symlink_to(outside,target_is_directory=True)
   with self.assertRaises(ValueError):handler.translate_path('/escape/file.json')
   self.assertEqual(handler.translate_path('/pkg/module.js?x=1'),str(Path(site).resolve()/'pkg/module.js'))
if __name__=='__main__':unittest.main()
