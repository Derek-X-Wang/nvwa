"""Actual ephemeral loopback lifecycle with synthetic A/B/A records."""
import copy,hashlib,http.client,json,tempfile,threading,unittest
from pathlib import Path
from server import Handler,Receiver,ThreadingHTTPServer,contract_valid,MAX
E=Path(__file__).resolve().parent
class HTTP(unittest.TestCase):
 def test_complete_http_and_negative_controls(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);site=b/'site';(site/'works').mkdir(parents=True);(site/'works/default-arms.nvwa.json').write_text('{}');(site/'aba82.html').write_text('<html>ABA lifecycle</html>');c=json.loads((E/'contract.json').read_text());httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler);port=httpd.server_address[1];httpd.receiver=Receiver(site,b/'actual',c,port);t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
   def request(method,path,body=None,headers=None):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:connection.request(method,path,body,headers or {});r=connection.getresponse();return r.status,r.read()
    finally:connection.close()
   origin=f'http://127.0.0.1:{port}';headers={'Origin':origin,'Content-Type':'application/json'};prefix='/_aba/'+c['run_id']+'/'
   def post(path,v):return request('POST',prefix+path,v if isinstance(v,bytes) else json.dumps(v).encode(),headers)[0]
   try:
    self.assertEqual(request('GET','/aba82.html?case=aba')[0],200);self.assertEqual(request('HEAD','/aba82.html')[0],200);self.assertEqual(json.loads(request('GET','/_aba/config')[1])['stages'],c['stages'])
    for method in ['GET','HEAD']:self.assertEqual(request(method,'/aba82.html',headers={'Host':'evil'})[0],403)
    self.assertEqual(request('OPTIONS','/_aba/config')[0],405);self.assertEqual(request('POST',prefix+'event/1',b'{"seq":1,"name":"boot"}',{'Origin':'evil'})[0],400)
    self.assertEqual(post('event/1',{'seq':1,'name':'boot'}),201);self.assertEqual(post('event/1',{'seq':1,'name':'boot'}),400)
    self.assertEqual(post('../escape',{}),400);self.assertEqual(post('B/manifest.json',{}),400)
    for stage in c['stages']:
     label=stage['label'];rid=stage['request_id'];identity={'generation':3};f={'endpoint':'web','request_id':rid,'work_sha256':'w','identity':identity,'stable_updates':2,'candidate':{'variant':stage['typed_variant'],'pre_visibility_publication_matches':True,'generation':3},'full_base':{'generation':3,'sample':{'source_seconds':0,'playing':False}},'diagnostic':{'mode':'Combined','palette':'Textured'},'witness':[-0.0]};r={'endpoint':'web','request_id':rid,'work_sha256':'w','captured_identity':identity,'phase':'ready','current':True,'acknowledged':True,'request_succeeded':True,'diagnostic':{},'work_json':'{}'};rr=json.dumps(r).encode();ff=json.dumps(f).encode();raw=b'{"report":'+rr+b',"frame":'+ff+b'}';sha=lambda b:hashlib.sha256(b).hexdigest();m={'request_id':rid,'format':'nvwa76-raw-transfer-v1','encoding':'utf-8','bytes':len(raw),'chars':len(raw.decode().encode('utf-16-le'))//2,'sha256':sha(raw),'report_bytes':len(rr),'frame_bytes':len(ff),'report_sha256':sha(rr),'frame_sha256':sha(ff),'token':'transfer-1-'+sha(raw),'chunk_bytes':32768,'chunks':1}
     wrong=dict(m,request_id='unrelated');self.assertEqual(post(label+'/manifest.json',wrong),400);self.assertEqual(post(label+'/manifest.json',m),201);self.assertEqual(post(label+'/capture.json',raw+b' '),400);self.assertEqual(post(label+'/capture.json',raw),201);self.assertEqual((b/'actual'/label/'capture.json').read_bytes(),raw);self.assertEqual(post(label+'/capture.json',raw),400)
     def fence(name):return {'name':name,'ms':2,'ready':True,'token':m['token'],'exact_report_before_after':True,'exact_frame_before_after':True}
     receipt={'run_id':c['run_id'],'request_id':rid,'manifest':m,'fences':[]};self.assertEqual(post(label+'/currentness.json',receipt),400);receipt['fences']=[fence(n) for n in ['after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response']];self.assertEqual(post(label+'/currentness.json',receipt),201)
     window={'request_id':rid,'token':m['token'],'open':{'name':'SCREENSHOT-WINDOW-OPEN','request_id':rid,'token':m['token'],'ms':1},'close':fence('screenshot-close'),'reason':'pace60'};bad=copy.deepcopy(window);bad['close']['ms']=90002;self.assertEqual(post(label+'/window-close.json',bad),400);self.assertEqual(post(label+'/window-close.json',window),201)
    self.assertEqual(httpd.receiver.closed,{'A1','B','A2'})
   finally:httpd.shutdown();httpd.server_close();t.join(timeout=3);self.assertFalse(t.is_alive())
 def test_contract_and_guard_rejections(self):
  c=json.loads((E/'contract.json').read_text());self.assertEqual(contract_valid(c),c)
  for key,value in [('work_path','../other'),('source_seconds',2),('window_ms',100000),('run_id','../../x')]:
   wrong=copy.deepcopy(c);wrong[key]=value
   with self.assertRaises(ValueError):contract_valid(wrong)
  wrong=copy.deepcopy(c);wrong['stages'][1]['request_id']=wrong['stages'][0]['request_id']
  with self.assertRaises(ValueError):contract_valid(wrong)
if __name__=='__main__':unittest.main()
