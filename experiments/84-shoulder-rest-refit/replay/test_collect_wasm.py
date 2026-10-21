"""Receiver/authentication controls; one ephemeral HTTP timeout control, no corpus server/browser."""
import copy
import gzip
import json
import socket
import threading
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect as native
import collect_wasm as w
from test_collect import record

RUN='unit-wasm-capture-not-production'

def raw_record(key):
    r=record(key);r['run_id']=RUN
    return (json.dumps(r,separators=(', ', ' : '))+'\n').encode()

def headers(raw):
    return {'Host':w.HOST,'Origin':w.ORIGIN,'Content-Type':'application/json','Content-Length':str(len(raw))}

class WasmControls(unittest.TestCase):
    def receiver(self,p):return w.Receiver(p,RUN,lambda *_:{'unit_geometry':'NOT-RUN'})
    def fill(self,r):
        for key in native.RECIPES:
            raw=raw_record(key);r.accept('/capture',headers(raw),raw)
        raw=(json.dumps({'kind':'complete','run_id':RUN,'matrix_samples':18})+'\n').encode()
        r.accept('/complete',headers(raw),raw)

    def test_exact18_raw_retention(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);r=self.receiver(p);self.fill(r)
            self.assertTrue(r.complete);self.assertEqual(len(r.entries),18)
            raw=raw_record(native.RECIPES[0]);entry=r.entries[0]
            self.assertEqual(gzip.decompress((p/entry['path']).read_bytes()),raw)
            self.assertEqual((p/entry['path']).read_bytes(),gzip.compress(raw,mtime=0))

    def reject_transport(self,change):
        with tempfile.TemporaryDirectory() as d:
            r=self.receiver(Path(d));raw=raw_record(native.RECIPES[0]);h=headers(raw);path='/capture'
            path,h,raw=change(path,h,raw)
            with self.assertRaises((ValueError,UnicodeError,KeyError,TypeError)):
                r.accept(path,h,raw)
            self.assertTrue(r.finished);self.assertIsNotNone(r.failure)

    def test_wrong_origin(self):self.reject_transport(lambda p,h,r:(p,{**h,'Origin':'http://localhost:9218'},r))
    def test_wrong_host(self):self.reject_transport(lambda p,h,r:(p,{**h,'Host':'localhost:9218'},r))
    def test_wrong_path(self):self.reject_transport(lambda p,h,r:('/capture?x=1',h,r))
    def test_wrong_length(self):self.reject_transport(lambda p,h,r:(p,{**h,'Content-Length':'1'},r))
    def test_oversize(self):self.reject_transport(lambda p,h,r:(p,{**h,'Content-Length':str(w.MAX_BODY+1)},r))
    def test_chunked(self):self.reject_transport(lambda p,h,r:(p,{**h,'Transfer-Encoding':'chunked'},r))
    def test_missing_lf(self):self.reject_transport(lambda p,h,r:(p,headers(r[:-1]),r[:-1]))
    def test_malformed_case(self):self.reject_transport(lambda p,h,r:(p,headers(b'{}\n'),b'{}\n'))
    def test_mixed_run(self):
        raw=raw_record(native.RECIPES[0]).replace(RUN.encode(),b'other')
        self.reject_transport(lambda p,h,r:(p,headers(raw),raw))

    def test_duplicate_stops_run(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.receiver(Path(d));raw=raw_record(native.RECIPES[0]);r.accept('/capture',headers(raw),raw)
            with self.assertRaisesRegex(ValueError,'duplicate'):r.accept('/capture',headers(raw),raw)
            self.assertTrue(r.finished)

    def test_missing_completion(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.receiver(Path(d));raw=b'{"kind":"complete","run_id":"'+RUN.encode()+b'","matrix_samples":18}\n'
            with self.assertRaisesRegex(ValueError,'complete18'):r.accept('/complete',headers(raw),raw)

    def test_geometry_failure_retains_raw_and_stops(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            def reject(*_):raise ValueError('EXACT original fixture mismatch')
            r=w.Receiver(p,RUN,reject);raw=raw_record(native.RECIPES[0])
            with self.assertRaisesRegex(ValueError,'EXACT'):r.accept('/capture',headers(raw),raw)
            self.assertTrue(r.finished);self.assertEqual(len(r.entries),0)
            self.assertEqual(gzip.decompress(next((p/'keyframes').glob('*.gz')).read_bytes()),raw)

    def test_closed_run_rejects_further_capture(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.receiver(Path(d));self.fill(r);raw=raw_record(native.RECIPES[0])
            with self.assertRaisesRegex(ValueError,'closed'):r.accept('/capture',headers(raw),raw)

    def test_static_traversal_and_external_paths(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for path in ('/assets/../Cargo.toml','/assets/%2e%2e/Cargo.toml','/assets/%252e%252e/Cargo.toml','/pkg/file.js?x=1','/other','/assets/../../etc/passwd'):
                with self.subTest(path=path),self.assertRaises(ValueError):w.static_file(path,p,p/'pkg')

    def fixture(self,p):
        r=self.receiver(p);self.fill(r)
        rows=[{'path':'Cargo.toml','bytes':1,'sha256':native.digest(b'x')},{'path':'experiments/84-shoulder-rest-refit/wasm-replay/src/lib.rs','bytes':1,'sha256':native.digest(b'y')}]
        artifacts=[{'path':'pkg/nvwa_shoulder_wasm_replay.js','bytes':1,'sha256':native.digest(b'j')},{'path':'pkg/nvwa_shoulder_wasm_replay_bg.wasm','bytes':1,'sha256':native.digest(b'w')}]
        source={'files':rows,'inventory_sha256':native.inventory_digest(rows),'artifacts':artifacts,'artifact_inventory_sha256':native.inventory_digest(artifacts)}
        for part in ('before','at-run','after'):native.write_json(p/f'source-{part}.json',source)
        anchor=p/'anchor.json';anchor.write_bytes(b'unit anchor not geometry')
        build={'schema_version':1,'kind':w.BUILD_KIND,'target':w.TARGET,'status':'PASS_COMPLETED_BUILD','exit_code':0,'build_run_id':'unit-wasm-build','source_head':'0'*40,'source_files':rows,'source_files_sha256':native.inventory_digest(rows),'command':['cargo','build','--target',w.TARGET,'and-wasm-bindgen'],'toolchain':{'rustc':'unit','cargo':'unit','wasm_bindgen':'unit'},'host':{'system':'unit','machine':'unit'},'artifacts':artifacts}
        native.write_json(p/'build-receipt.json',build)
        identity={'schema':w.SCHEMA,'run_id':RUN,'build_run_id':build['build_run_id'],'source_head':build['source_head'],'target':w.TARGET,'execution_mode':'CPU_ONLY_WASM_PRODUCTION_PLUGIN','origin':w.ORIGIN,'source_inventory_sha256':source['inventory_sha256'],'source_before_sha256':native.digest((p/'source-before.json').read_bytes()),'build_receipt_sha256':native.digest((p/'build-receipt.json').read_bytes()),'compiled_source_sha256':build['source_files_sha256'],'artifact_inventory_sha256':source['artifact_inventory_sha256'],'build_command':build['command'],'toolchain':build['toolchain'],'host':build['host'],'fresh_nineteenth_sha256':native.digest(anchor.read_bytes())}
        native.write_json(p/'identity.json',identity)
        manifest={'schema_version':1,'cohort_type':w.KIND,'historical_replay':'NOT-RUN_MISSING18','status':w.STATUS,'source_unchanged':True,'historical_input_hashes_reused':False,'failure':None,'source_inventory_sha256':source['inventory_sha256'],'run_id':RUN,'anchor':{'role':'authenticated-original-fresh-default','bytes':anchor.stat().st_size,'sha256':native.digest(anchor.read_bytes())},'cases':r.entries}
        self.bind(p,manifest)
        return manifest,source,anchor

    def bind(self,p,m):
        m['receipts']={k:native.receipt_row(p,n) for k,n in {**w.RECEIPTS,'complete':'complete.json'}.items()}
        native.write_json(p/'manifest.json',m)

    def auth(self,p,m,s,a):
        with patch.object(native,'FRESH_SHA',native.digest(a.read_bytes())):
            return w.authenticate_corpus(p,native.digest((p/'manifest.json').read_bytes()),s['inventory_sha256'],a)

    def test_auth_accepts_exact_new_wasm(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);self.assertEqual(len(self.auth(p,m,s,a)),18)

    def test_auth_rejects_native_kind(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);m['cohort_type']='hybrid-current18-original-anchor';self.bind(p,m)
            with self.assertRaisesRegex(ValueError,'not admitted new-Wasm'):self.auth(p,m,s,a)

    def test_auth_tampered_identity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);(p/'identity.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'tampered Wasm identity'):self.auth(p,m,s,a)

    def test_auth_tampered_build(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);(p/'build-receipt.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'tampered Wasm build'):self.auth(p,m,s,a)

    def test_auth_tampered_case(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);(p/m['cases'][0]['path']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'tampered Wasm compressed'):self.auth(p,m,s,a)

    def test_auth_missing_case(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);(p/m['cases'][0]['path']).unlink()
            with self.assertRaises(OSError):self.auth(p,m,s,a)

    def test_auth_duplicate_case_even_with_new_manifest_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);m['cases'][1]=copy.deepcopy(m['cases'][0]);self.bind(p,m)
            with self.assertRaisesRegex(ValueError,'duplicate/mixed'):self.auth(p,m,s,a)

    def test_auth_failed_case_flag(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p);m['failure']='failed';self.bind(p,m)
            with self.assertRaisesRegex(ValueError,'failure present'):self.auth(p,m,s,a)

    def test_auth_rebound_wrong_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p)
            build=native.strict_load((p/'build-receipt.json').read_bytes());build['artifacts'][0]['sha256']='wrong';native.write_json(p/'build-receipt.json',build)
            i=native.strict_load((p/'identity.json').read_bytes());i['build_receipt_sha256']=native.digest((p/'build-receipt.json').read_bytes());native.write_json(p/'identity.json',i);self.bind(p,m)
            with self.assertRaisesRegex(ValueError,'artifact identity differs'):self.auth(p,m,s,a)

    def test_no_native_binary_receipt_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.fixture(p)
            b=native.strict_load((p/'build-receipt.json').read_bytes());i=native.strict_load((p/'identity.json').read_bytes());b['binary']={'sha256':'wrong'}
            with self.assertRaisesRegex(ValueError,'native executable'):w.validate_build(b,s,i)

    def test_actual_http_stalled_request_line_and_headers_close_promptly(self):
        # An ephemeral local HTTP socket exercises BaseHTTPRequestHandler's reads.
        # No /capture, production assets, Wasm client, browser or corpus run occurs.
        for partial in (b'GET /co', b'GET /config HTTP/1.1\r\nHost: 127.0.0.1:9218\r\nX-Stalled:'):
            with self.subTest(partial=partial),tempfile.TemporaryDirectory() as d:
                p=Path(d);r=self.receiver(p)
                handler=w.handler_for(r,{'run_id':RUN},p,p/'pkg',[],[])
                server=w.HTTPServer(('127.0.0.1',0),handler)
                worker=threading.Thread(target=server.handle_request,daemon=True)
                connection=None
                try:
                    with patch.object(w,'CONNECTION_TIMEOUT_SECONDS',0.05):
                        worker.start()
                        connection=socket.create_connection(server.server_address,timeout=0.5)
                        connection.settimeout(0.5)
                        started=time.monotonic()
                        connection.sendall(partial)
                        self.assertEqual(connection.recv(1),b'')
                        self.assertLess(time.monotonic()-started,0.5)
                    self.assertFalse(r.finished)
                    self.assertEqual(r.entries,[])
                finally:
                    if connection is not None:connection.close()
                    worker.join(timeout=1)
                    server.server_close()
                self.assertFalse(worker.is_alive(),'HTTP control server failed to stop')

if __name__=='__main__':unittest.main()
