"""Run the actual HTML transfer functions in Node; no browser or GPU claim."""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import unittest

from collect_transfer import assemble, verify_bytes

EXP = Path(__file__).resolve().parent


NODE_TEST = r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const crypto=require('node:crypto').webcrypto;
const html=fs.readFileSync(process.argv[1],'utf8');
const source=html.split('// TRANSFER_CORE_BEGIN:')[1].split('\n').slice(1).join('\n').split('// TRANSFER_CORE_END')[0];
if(!source)throw Error('Live HTML transfer seam missing');
vm.runInThisContext(source);
(async()=>{
 const identity='{"camera":[-0.0,1.0],"generation":3}';
 let report='{"acknowledged":true,"phase":"ready","current":true,"request_succeeded":true,"request_id":"exact-1","work_sha256":"work","endpoint":"web","diagnostic":{},"captured_identity":'+identity+'}';
 let frame='{"request_id":"exact-1","work_sha256":"work","endpoint":"web","stable_updates":2,"identity":'+identity+',"witness":[-0.0,1.0,1e-09],"padding":"'+('🧪'.repeat(20000))+'"}';
 if(process.env.NVWA73_REAL_CAPTURE){
   const raw=fs.readFileSync(process.env.NVWA73_REAL_CAPTURE,'utf8');
   // Retained record uses this exact Rust-string concatenation codec.
   const marker=',"frame":';
   const at=raw.indexOf(marker);
   assert(at>0);report=raw.slice('{"report":'.length,at);frame=raw.slice(at+marker.length,raw.trimEnd().length-1);
 }
 const originalReport=report,originalFrame=frame;
 const transfer=createTransfer(()=>report,()=>frame);
 const manifest=await transfer.prepare();
 assert(transfer.status().ready);
 assert.equal(transfer.exactText(manifest.token),'{"report":'+report+',"frame":'+frame+'}');
 const chunks=Array.from({length:manifest.chunks},(_,i)=>transfer.chunk(manifest.token,i));
 const bytes=Buffer.concat(chunks.map(c=>Buffer.from(c.base64,'base64')));
 assert.equal(bytes.toString('utf8'),transfer.exactText(manifest.token));
 assert.equal(require('node:crypto').createHash('sha256').update(bytes).digest('hex'),manifest.sha256);
 assert(bytes.includes(Buffer.from('-0.0')),'signed-zero token required');
 assert.throws(()=>transfer.chunk('wrong',0),/token/);
 for(const index of [-1,manifest.chunks,0.5])assert.throws(()=>transfer.chunk(manifest.token,index),/index/);
 report=report.replace('"current":true','"current":false');
 assert.throws(()=>transfer.chunk(manifest.token,0),/stale/);
 assert(!transfer.status().ready);assert.match(transfer.status().error,/stale/);
 await assert.rejects(transfer.prepare(),/current/);
 report=originalReport;frame=JSON.stringify({...JSON.parse(originalFrame),request_id:'wrong'});
 await assert.rejects(transfer.prepare(),/correlation/);
 frame=originalFrame;report=JSON.stringify({...JSON.parse(originalReport),work_sha256:'wrong'});
 await assert.rejects(transfer.prepare(),/correlation/);
 report=originalReport;frame=JSON.stringify({...JSON.parse(originalFrame),stable_updates:1});
 await assert.rejects(transfer.prepare(),/stability/);
 frame=originalFrame;
 // Three digest promises must all finish before currentness is tested.
 const resolvers=[];
 const racing=createTransfer(()=>report,()=>frame,()=>new Promise(resolve=>resolvers.push(resolve)));
 const preparation=racing.prepare();report=report.replace('"current":true','"current":false');resolvers.forEach(resolve=>resolve('a'.repeat(64)));
 await assert.rejects(preparation,/changed/);
 report=originalReport;
 const canceled=[];const superseded=createTransfer(()=>report,()=>frame,()=>new Promise(resolve=>canceled.push(resolve)));
 const preparing=superseded.prepare();superseded.invalidate();canceled.forEach(resolve=>resolve('a'.repeat(64)));
 await assert.rejects(preparing,/superseded/);
 const second=await transfer.prepare();frame=frame+' ';
 assert.throws(()=>transfer.exactText(second.token),/stale/);
 // Exercise actual visible button handlers using DOM/Blob adapters, not a browser.
 const nodes=new Map();let downloaded;
 const element=()=>({disabled:true,textContent:'',value:'0',append(){},click(){}});
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},createElement:element};
 const context=vm.createContext({document,crypto,TextEncoder,Uint8Array,Blob,btoa,setTimeout(){},URL:{createObjectURL(blob){downloaded=blob;return 'blob:test'},revokeObjectURL(){}}});
 const moduleBody=html.split('<script type="module">')[1].split('</script>')[0];
 vm.runInContext(moduleBody.split("try{api=await import(")[0],context);
 context.readReport=()=>originalReport;context.readFrame=()=>originalFrame;
 vm.runInContext('api={b1_73_report:readReport,b1_73_frame:readFrame,b1_73_command(){}};transfer=createTransfer(readReport,readFrame)',context);
 await nodes.get('prepare').onclick();
 const visibleManifest=JSON.parse(nodes.get('wire-status').textContent);
 assert(visibleManifest.ready);assert(!nodes.get('export').disabled);assert(!nodes.get('chunk-read').disabled);
 nodes.get('chunk-read').onclick();
 const visibleChunk=JSON.parse(nodes.get('wire-chunk').textContent);
 assert.equal(visibleChunk.token,visibleManifest.token);assert.equal(visibleChunk.index,0);assert(nodes.get('wire-chunk').textContent.length<45000);
 nodes.get('export').onclick();
 assert.equal(await downloaded.text(),'{"report":'+originalReport+',"frame":'+originalFrame+'}');
 vm.runInContext("send({request_id:'next',action:'capture'})",context);
 assert(nodes.get('export').disabled);assert(nodes.get('chunk-read').disabled);assert(!nodes.get('wire-chunk').textContent.includes('base64'));
 console.log(JSON.stringify({manifest,chunks}));
})().catch(error=>{console.error(error);process.exitCode=1});
'''


class TransferContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Existing Node.js required to exercise the live HTML export seam; no download')
        result = subprocess.run([node, '-e', NODE_TEST, str(EXP/'index.html')], text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.result = json.loads(result.stdout)

    def test_exact_live_seam_round_trip_and_negative_controls(self):
        raw = assemble(self.result['manifest'], self.result['chunks'], expected_request_id=self.result['manifest']['request_id'])
        self.assertIn(b'-0.0', raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.result['manifest']['sha256'])

    def test_incomplete_transfer_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            assemble(self.result['manifest'], self.result['chunks'][:-1], expected_request_id=self.result['manifest']['request_id'])

    def test_truncated_chunk_rejected(self):
        chunks = [dict(c) for c in self.result['chunks']]
        chunks[0]['base64'] = base64.b64encode(base64.b64decode(chunks[0]['base64'])[:-1]).decode()
        with self.assertRaisesRegex(ValueError, 'truncated'):
            assemble(self.result['manifest'], chunks, expected_request_id=self.result['manifest']['request_id'])

    def test_stale_or_mismatched_chunk_token_rejected(self):
        chunks = [dict(c) for c in self.result['chunks']]
        chunks[0]['token'] = 'old-transfer'
        with self.assertRaisesRegex(ValueError, 'token'):
            assemble(self.result['manifest'], chunks, expected_request_id=self.result['manifest']['request_id'])

    def test_duplicate_chunk_rejected(self):
        chunks = self.result['chunks'] + [self.result['chunks'][0]]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            assemble(self.result['manifest'], chunks, expected_request_id=self.result['manifest']['request_id'])

    def test_same_size_corrupted_transfer_rejected(self):
        chunks = [dict(c) for c in self.result['chunks']]
        data = bytearray(base64.b64decode(chunks[0]['base64']));data[0] ^= 1
        chunks[0]['base64'] = base64.b64encode(data).decode()
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            assemble(self.result['manifest'], chunks, expected_request_id=self.result['manifest']['request_id'])

    def record_parts(self):
        manifest = dict(self.result['manifest'])
        raw = b''.join(base64.b64decode(c['base64']) for c in self.result['chunks'])
        split = len(b'{"report":') + manifest['report_bytes']
        return manifest, raw[len(b'{"report":'):split], raw[split+len(b',"frame":'):-1]

    def reheader(self, report, frame, request_id=None):
        manifest = dict(self.result['manifest'])
        raw = b'{"report":' + report + b',"frame":' + frame + b'}'
        manifest.update(bytes=len(raw), chars=len(raw.decode().encode('utf-16-le'))//2,
                        sha256=hashlib.sha256(raw).hexdigest(), report_bytes=len(report),
                        report_sha256=hashlib.sha256(report).hexdigest(), frame_bytes=len(frame),
                        frame_sha256=hashlib.sha256(frame).hexdigest(), chunks=(len(raw)+32767)//32768)
        if request_id is not None:
            manifest['request_id'] = request_id
        manifest['token'] = 'transfer-1-' + manifest['sha256']
        chunks = [{'token':manifest['token'], 'index':i, 'base64':base64.b64encode(raw[i*32768:(i+1)*32768]).decode()}
                  for i in range(manifest['chunks'])]
        return manifest, raw, chunks

    def assert_both_reject(self, manifest, raw, chunks, reason, expected=None):
        expected = expected or self.result['manifest']['request_id']
        with self.subTest(path='download'), self.assertRaisesRegex(ValueError, reason):
            verify_bytes(manifest, raw, expected_request_id=expected)
        with self.subTest(path='chunks'), self.assertRaisesRegex(ValueError, reason):
            assemble(manifest, chunks, expected_request_id=expected)

    def test_manifest_request_id_must_match_original_raw_on_both_paths(self):
        manifest, report, frame = self.record_parts()
        manifest, raw, chunks = self.reheader(report, frame)
        manifest['request_id'] = 'other-expected-request'
        self.assert_both_reject(manifest, raw, chunks, 'raw record.*request ID', expected='other-expected-request')

    def test_ready_false_or_nonboolean_rejected_on_both_paths(self):
        _, report, frame = self.record_parts()
        for ready in [False, 0, 1, 'true', None]:
            manifest, raw, chunks = self.reheader(report, frame)
            manifest['ready'] = ready
            self.assert_both_reject(manifest, raw, chunks, 'not ready')

    def test_wrong_manifest_token_rejected_even_with_matching_chunks(self):
        _, report, frame = self.record_parts()
        for token in ['arbitrary', 'transfer-1-'+'0'*64, 'transfer-0-'+self.result['manifest']['sha256']]:
            manifest, raw, chunks = self.reheader(report, frame)
            manifest['token'] = token
            for chunk in chunks:
                chunk['token'] = token
            self.assert_both_reject(manifest, raw, chunks, 'token')

    def test_coherent_fake_header_cannot_pass_independent_expected_id(self):
        _, report, frame = self.record_parts()
        old = self.result['manifest']['request_id'].encode()
        report = report.replace(b'"request_id":"'+old+b'"', b'"request_id":"coherent-other"')
        frame = frame.replace(b'"request_id":"'+old+b'"', b'"request_id":"coherent-other"')
        manifest, raw, chunks = self.reheader(report, frame, request_id='coherent-other')
        self.assert_both_reject(manifest, raw, chunks, 'expected request ID')

    def test_coherently_hashed_stale_raw_report_rejected(self):
        _, report, frame = self.record_parts()
        report = report.replace(b'"current":true', b'"current":false')
        manifest, raw, chunks = self.reheader(report, frame)
        self.assert_both_reject(manifest, raw, chunks, 'stale or unsuccessful')

    def test_coherently_hashed_raw_work_mismatch_rejected(self):
        _, report, frame = self.record_parts()
        frame = re.sub(rb'"work_sha256":"[^"]*"', b'"work_sha256":"wrong-work"', frame)
        manifest, raw, chunks = self.reheader(report, frame)
        self.assert_both_reject(manifest, raw, chunks, 'Work correlation')

    def test_duplicate_raw_identity_key_rejected_without_reencoding(self):
        _, report, frame = self.record_parts()
        report = b'{"request_id":"duplicate",' + report[1:]
        manifest, raw, chunks = self.reheader(report, frame)
        self.assert_both_reject(manifest, raw, chunks, 'duplicate raw report key')

    def test_prepare_manifest_and_ready_status_verify_identically(self):
        manifest, report, frame = self.record_parts()
        raw = b'{"report":' + report + b',"frame":' + frame + b'}'
        expected = manifest['request_id']
        self.assertEqual(verify_bytes(manifest, raw, expected_request_id=expected), raw)
        manifest['ready'] = True
        self.assertEqual(verify_bytes(manifest, raw, expected_request_id=expected), raw)
        self.assertEqual(assemble(manifest, self.result['chunks'], expected_request_id=expected), raw)

    def test_raw_arrays_never_mirrored_into_dom(self):
        html = (EXP/'index.html').read_text()
        for identifier in ['wire-report', 'wire-frame', 'wire-motion']:
            self.assertNotIn(identifier, html)
        self.assertNotIn("$('report').textContent=raw", html)
        self.assertIn("$('report').textContent=compactReport(raw)", html)


if __name__ == '__main__':
    unittest.main()
