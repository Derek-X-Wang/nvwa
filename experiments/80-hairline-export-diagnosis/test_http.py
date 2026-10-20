"""Real loopback HTTP handler lifecycle, static/config GET and bounded exact POST."""
import http.client,json,tempfile,threading,unittest,hashlib
from pathlib import Path
from server import Handler,Receiver,ThreadingHTTPServer
class ActualHTTP(unittest.TestCase):
 def test_real_get_head_and_post(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);site=base/'site';(site/'works').mkdir(parents=True);(site/'works/default-arms.nvwa.json').write_text('{}');(site/'diagnostic80.html').write_text('<html>DIAG80 lifecycle probe</html>')
   httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=httpd.server_address[1];httpd.receiver=Receiver(site,base/'out','http80',port);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
   def request(method,path,body=None,headers=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:c.request(method,path,body=body,headers=headers or {});res=c.getresponse();return res.status,res.read()
    finally:c.close()
   try:
    status,body=request('GET','/diagnostic80.html?case=manual');self.assertEqual(status,200);self.assertIn(b'DIAG80',body)
    status,_=request('HEAD','/diagnostic80.html');self.assertEqual(status,200)
    status,body=request('GET','/_diag80/config');self.assertEqual(status,200);self.assertEqual(json.loads(body)['request_id'],'http80-A')
    origin=f'http://127.0.0.1:{port}';headers={'Origin':origin,'Content-Type':'application/json'}
    status,_=request('POST','/_diag80/http80/event/1',b'{"seq":1,"name":"boot"}',headers);self.assertEqual(status,201)
    status,_=request('POST','/_diag80/http80/event/1',b'{"seq":1,"name":"boot"}',headers);self.assertEqual(status,400)
    for head in [{'Origin':'http://evil'},{'Origin':origin,'Host':'evil'}]:
     status,_=request('POST','/_diag80/http80/event/2',b'{"seq":2,"name":"boot"}',head);self.assertEqual(status,400)
    status,_=request('GET','/_diag80/config',headers={'Host':'evil'});self.assertEqual(status,403)
    # Entire real HTTP manifest -> exact-byte envelope -> currentness branch.
    identity={'generation':3};frame={'request_id':'http80-A','work_sha256':'w','endpoint':'web','stable_updates':2,'identity':identity,'candidate':{'variant':'AOriginal','pre_visibility_publication_matches':True,'generation':3},'full_base':{'generation':3,'sample':{'source_seconds':0,'playing':False}},'witness':[-0.0]};report={'request_id':'http80-A','work_sha256':'w','endpoint':'web','phase':'ready','current':True,'acknowledged':True,'request_succeeded':True,'diagnostic':{},'captured_identity':identity,'work_json':'{}'}
    rr=json.dumps(report).encode();ff=json.dumps(frame).encode();raw=b'{"report":'+rr+b',"frame":'+ff+b'}';sha=lambda b:hashlib.sha256(b).hexdigest();m={'request_id':'http80-A','format':'nvwa76-raw-transfer-v1','encoding':'utf-8','bytes':len(raw),'chars':len(raw.decode().encode('utf-16-le'))//2,'sha256':sha(raw),'report_bytes':len(rr),'frame_bytes':len(ff),'report_sha256':sha(rr),'frame_sha256':sha(ff),'token':'transfer-1-'+sha(raw),'chunk_bytes':32768,'chunks':1}
    self.assertEqual(request('POST','/_diag80/http80/manifest.json',json.dumps(m).encode(),headers)[0],201);self.assertEqual(request('POST','/_diag80/http80/capture.json',raw,headers)[0],201);self.assertEqual((base/'out/capture.json').read_bytes(),raw)
    receipt={'run_id':'http80','request_id':'http80-A','manifest':m,'fences':[{'name':n,'ready':True,'token':m['token'],'exact_report_before_after':True,'exact_frame_before_after':True} for n in ['after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response']]};self.assertEqual(request('POST','/_diag80/http80/currentness.json',json.dumps(receipt).encode(),headers)[0],201)
   finally:httpd.shutdown();httpd.server_close();thread.join(timeout=3)
if __name__=='__main__':unittest.main()
