import json,tempfile,unittest,hashlib
from pathlib import Path
from server import Receiver,Reject,MAX
class ReceiverControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);site=self.root/'site';(site/'works').mkdir(parents=True);(site/'works/default-arms.nvwa.json').write_text('{}');self.r=Receiver(site,self.root/'out','run80',9205)
 def test_origin_host_length_transfer_encoding(self):
  self.r.guard('127.0.0.1:9205','http://127.0.0.1:9205',1)
  for args in [('evil','http://127.0.0.1:9205',1),('127.0.0.1:9205','http://evil',1),('127.0.0.1:9205','http://127.0.0.1:9205',MAX+1),('127.0.0.1:9205','http://127.0.0.1:9205',1,'chunked')]:
   with self.assertRaises(Reject):self.r.guard(*args)
 def test_paths_bounds_create_only(self):
  for p in ['/_diag80/other/event/1','/_diag80/run80/../escape','/_diag80/run80/event/513','/_diag80/run80/capture.json']:
   with self.assertRaises((ValueError,KeyError)):self.r.accept(p,b'{}')
  raw=b'{"seq":1,"name":"boot"}';self.r.accept('/_diag80/run80/event/1',raw)
  with self.assertRaises(FileExistsError):self.r.accept('/_diag80/run80/event/1',raw)
  with self.assertRaises(FileExistsError):Receiver(self.r.site,self.r.output,'run80',9205)
 def test_independent_request_id_rejects_manifest(self):
  m={'request_id':'other','token':'transfer-1-'+'a'*64,'sha256':'a'*64}
  with self.assertRaisesRegex(ValueError,'expected request'):self.r.accept('/_diag80/run80/manifest.json',json.dumps(m).encode())
 def test_actual_receiver_accepts_exact_record_then_requires_all_post_network_fences(self):
  identity={'generation':3};frame={'request_id':'run80-A','work_sha256':'work','endpoint':'web','stable_updates':2,'identity':identity,'candidate':{'variant':'AOriginal','pre_visibility_publication_matches':True,'generation':3},'full_base':{'generation':3,'sample':{'source_seconds':0,'playing':False}},'signed_zero':-0.0};report={'request_id':'run80-A','work_sha256':'work','endpoint':'web','phase':'ready','current':True,'acknowledged':True,'request_succeeded':True,'diagnostic':{},'captured_identity':identity,'work_json':'{}'}
  rr=json.dumps(report).encode();ff=json.dumps(frame).encode();raw=b'{"report":'+rr+b',"frame":'+ff+b'}';sha=lambda b:hashlib.sha256(b).hexdigest();m={'request_id':'run80-A','format':'nvwa76-raw-transfer-v1','encoding':'utf-8','bytes':len(raw),'chars':len(raw.decode().encode('utf-16-le'))//2,'sha256':sha(raw),'report_bytes':len(rr),'frame_bytes':len(ff),'report_sha256':sha(rr),'frame_sha256':sha(ff),'token':'transfer-1-'+sha(raw),'chunk_bytes':32768,'chunks':1}
  self.r.accept('/_diag80/run80/manifest.json',json.dumps(m).encode());self.r.accept('/_diag80/run80/capture.json',raw);self.assertEqual((self.r.output/'capture.json').read_bytes(),raw)
  with self.assertRaises(FileExistsError):self.r.accept('/_diag80/run80/capture.json',raw)
  receipt={'run_id':'run80','request_id':'run80-A','manifest':m,'fences':[]}
  with self.assertRaisesRegex(Reject,'fences absent'):self.r.accept('/_diag80/run80/currentness.json',json.dumps(receipt).encode())
  receipt['fences']=[{'name':n,'ready':True,'token':m['token'],'exact_report_before_after':True,'exact_frame_before_after':True} for n in ['after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response']];self.r.accept('/_diag80/run80/currentness.json',json.dumps(receipt).encode());self.assertTrue((self.r.output/'currentness.json').exists())
if __name__=='__main__':unittest.main()
