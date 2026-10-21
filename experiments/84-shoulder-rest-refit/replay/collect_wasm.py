#!/usr/bin/env python3
"""One CPU-only Wasm baseline attempt; native rejection and historical gaps stay intact."""
import argparse
import gzip
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
import platform
import subprocess
import time
from urllib.parse import unquote, urlsplit
import uuid

import collect as original

ROOT = original.ROOT
HERE = Path(__file__).resolve().parent
WRAPPER = ROOT / 'experiments/84-shoulder-rest-refit/wasm-replay'
ORIGIN = 'http://127.0.0.1:9218'
HOST = '127.0.0.1:9218'
MAX_BODY = 64 * 1024 * 1024
CONNECTION_TIMEOUT_SECONDS = 10
KIND = 'hybrid-current18-wasm-original-anchor'
STATUS = 'PASS_NEW_CURRENT18_WASM_CORPUS'
BUILD_KIND = 'nvwa84-completed-cpu-wasm-build-v1'
TARGET = 'wasm32-unknown-unknown'
SCHEMA = 'NEW-current18-production-CPU-WASM-v1'
need, digest, strict_load, write_json = original.need, original.digest, original.strict_load, original.write_json
inventory_digest = original.inventory_digest


def wasm_build_path(path):
    if path.startswith('experiments/84-shoulder-rest-refit/replay/'):
        return False
    return original.is_build_path(path) or path.startswith('experiments/84-shoulder-rest-refit/wasm-replay/')


def wasm_build_source_files(root):
    """Read-only compiled/transport closure helper for the parent's actual build receipt."""
    root = Path(root)
    rows = [r for r in original.build_source_files(root) if wasm_build_path(r['path'])]
    wrapper = root / 'experiments/84-shoulder-rest-refit/wasm-replay'
    for path in wrapper.rglob('*'):
        rel = path.relative_to(root)
        if path.is_file() and not set(path.relative_to(wrapper).parts).intersection({'target', 'pkg', '__pycache__', '.git'}):
            need(path.resolve().is_relative_to(root.resolve()), 'wrapper source escaped')
            raw = path.read_bytes()
            rows.append({'path':str(rel), 'bytes':len(raw), 'sha256':digest(raw)})
    need(any(r['path'].startswith('experiments/84-shoulder-rest-refit/wasm-replay/') and r['path'].endswith('.rs') for r in rows), 'Wasm wrapper source absent')
    return sorted(rows, key=lambda row:row['path'])


def artifact_files(pkg):
    """Bind every file in the dedicated bindgen package, with no native executable claim."""
    pkg = Path(pkg)
    rows = []
    for path in sorted(pkg.rglob('*')):
        if path.is_file():
            need(path.resolve().is_relative_to(pkg.resolve()), 'bindgen artifact escaped')
            raw = path.read_bytes()
            rows.append({'path':'pkg/' + str(path.relative_to(pkg)), 'bytes':len(raw), 'sha256':digest(raw)})
    need(any(r['path'] == 'pkg/nvwa_shoulder_wasm_replay.js' for r in rows), 'required bindgen JS absent')
    need(any(r['path'].endswith('.wasm') for r in rows), 'Wasm artifact absent')
    return rows


def source_closure(root, pkg):
    rows = wasm_build_source_files(root)
    for rel in ('experiments/60-b1-continuous-motion/checker.py', 'experiments/60-b1-continuous-motion/geometry.py', 'experiments/70-b1-garment-defect/diagnose.py', 'experiments/79-shoulder-pose-corrective/fixtures/historical-actual-activation.json'):
        path = root / rel
        raw = path.read_bytes()
        rows.append({'path':rel, 'bytes':len(raw), 'sha256':digest(raw)})
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in ('.py', '.md'):
            raw = path.read_bytes()
            rows.append({'path':str(path.relative_to(root)), 'bytes':len(raw), 'sha256':digest(raw)})
    rows = sorted(rows, key=lambda r:r['path'])
    need(len({r['path'] for r in rows}) == len(rows), 'duplicate source receipt path')
    artifacts = artifact_files(pkg)
    return {'files':rows, 'inventory_sha256':original.inventory_digest(rows), 'artifacts':artifacts, 'artifact_inventory_sha256':original.inventory_digest(artifacts)}


def validate_build(build, before, identity):
    need(build['schema_version'] == 1 and build['kind'] == BUILD_KIND and build['target'] == TARGET, 'wrong CPU-Wasm build identity')
    need(build['status'] == 'PASS_COMPLETED_BUILD' and type(build['exit_code']) is int and build['exit_code'] == 0, 'Wasm build not completed success')
    need(isinstance(build['build_run_id'],str) and bool(build['build_run_id']) and build['build_run_id'] != identity['run_id'] and build['build_run_id'] == identity['build_run_id'], 'Wasm build/capture run identity differs or conflated')
    need(isinstance(build['source_head'],str) and len(build['source_head']) == 40 and all(x in '0123456789abcdef' for x in build['source_head']) and build['source_head'] == identity['source_head'], 'Wasm source HEAD differs')
    compiled = [r for r in before['files'] if wasm_build_path(r['path'])]
    need(compiled == build['source_files'] and original.inventory_digest(compiled) == build['source_files_sha256'] == identity['compiled_source_sha256'], 'Wasm compiled source closure differs')
    need(isinstance(build['command'],list) and bool(build['command']) and all(isinstance(x,str) and bool(x) for x in build['command']) and build['command'] == identity['build_command'], 'Wasm actual build command differs')
    need(set(build['toolchain']) == {'rustc','cargo','wasm_bindgen'} and all(isinstance(v,str) and bool(v) for v in build['toolchain'].values()) and build['toolchain'] == identity['toolchain'], 'Wasm toolchain differs')
    need(all(isinstance(build['host'][k],str) and bool(build['host'][k]) and build['host'][k] == identity['host'][k] for k in ('system','machine')), 'Wasm build host differs')
    need(build['artifacts'] == before['artifacts'] and original.inventory_digest(build['artifacts']) == before['artifact_inventory_sha256'] == identity['artifact_inventory_sha256'], 'Wasm/bindgen artifact identity differs')
    need('binary' not in build and identity['target'] == TARGET and identity['execution_mode'] == 'CPU_ONLY_WASM_PRODUCTION_PLUGIN', 'native executable claim forbidden')


def check_transport(path, headers, raw):
    need(path in ('/capture','/complete'), 'fixed POST path required')
    need(headers.get('Host') == HOST and headers.get('Origin') == ORIGIN, 'fixed loopback host/origin required')
    need(headers.get('Content-Type') == 'application/json', 'exact application/json required')
    need(headers.get('Transfer-Encoding') is None, 'chunked transport forbidden')
    size = headers.get('Content-Length')
    need(isinstance(size,str) and size.isdigit() and 0 < int(size) <= MAX_BODY and int(size) == len(raw), 'body length absent/malformed/oversized')
    need(raw.endswith(b'\n') and not raw.endswith(b'\n\n'), 'one producer LF required')
    raw.decode('utf-8',errors='strict')


class Receiver:
    """The HTTP handler and failure controls use this same acceptance seam."""
    def __init__(self, out, run_id, validator):
        self.out, self.run_id, self.validator = Path(out), run_id, validator
        self.entries, self.seen = [], set()
        self.failure, self.finished, self.complete = None, False, False
        (self.out/'keyframes').mkdir()

    def reject(self, error):
        if self.failure is None:
            self.failure = str(error)
        self.finished = True

    def accept(self, path, headers, raw):
        try:
            need(not self.finished, 'single capture run is closed')
            check_transport(path,headers,raw)
            record = strict_load(raw)
            need(record['run_id'] == self.run_id, 'mixed Wasm capture run')
            if path == '/complete':
                need(record['kind'] == 'complete' and type(record['matrix_samples']) is int and record['matrix_samples'] == 18 and self.seen == set(original.RECIPES), 'missing/extra complete18 cases')
                (self.out/'complete.json').write_bytes(raw)
                self.complete, self.finished = True, True
                return {'accepted':True, 'complete':True}
            key = original.validate_record(record,self.run_id)
            need(key not in self.seen, 'duplicate Wasm case')
            filename = original.case_name(key)
            compressed = gzip.compress(raw,mtime=0)
            path = self.out/'keyframes'/filename
            path.write_bytes(compressed)
            checks = self.validator(record,key)
            self.seen.add(key)
            self.entries.append({'case':filename, 'recipe':{'torso_length':key[0],'jaw_drop':0,'clip_id':key[1],'k':key[2],'seconds':key[2]/8}, 'path':'keyframes/'+filename, 'bytes':len(compressed), 'sha256':digest(compressed), 'raw_bytes':len(raw), 'raw_sha256':digest(raw), 'checks':checks})
            return {'accepted':True,'case':filename,'count':len(self.seen)}
        except (ValueError,KeyError,TypeError,IndexError,UnicodeError,OSError) as error:
            self.reject(error)
            raise


def static_file(path, root, pkg):
    need(path == urlsplit(path).path and '\\' not in path, 'query/fragment/backslash forbidden')
    decoded = unquote(path)
    need('%' not in decoded and '..' not in decoded.split('/'), 'encoded/traversal path forbidden')
    if decoded in ('/','/index.html'):
        target, base = root/'experiments/84-shoulder-rest-refit/wasm-replay/index.html', root/'experiments/84-shoulder-rest-refit/wasm-replay'
    elif decoded == '/client.js':
        target, base = root/'experiments/84-shoulder-rest-refit/wasm-replay/client.js', root/'experiments/84-shoulder-rest-refit/wasm-replay'
    elif decoded.startswith('/pkg/'):
        base = pkg
        target = pkg/decoded[len('/pkg/'):]
    elif decoded.startswith('/assets/'):
        base = root/'assets'
        target = base/decoded[len('/assets/'):]
    else:
        raise ValueError('unserved path')
    need(target.is_file() and target.resolve().is_relative_to(base.resolve()), 'static file absent/escaped')
    return target


def handler_for(receiver, config, root, pkg, source_rows, artifact_rows):
    allowed_assets = {r["path"] for r in source_rows if r["path"].startswith("assets/")}
    allowed_artifacts = {r["path"] for r in artifact_rows}
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            # Bound request-line/header reads and blocked response writes from accept.
            self.request.settimeout(CONNECTION_TIMEOUT_SECONDS)
            super().setup()
        def log_message(self,*_):pass
        def reply(self,status,raw,content_type='application/json'):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(raw)
        def do_GET(self):
            try:
                need(self.headers.get('Host') == HOST and self.headers.get('Origin') in (None,ORIGIN), 'fixed loopback host/origin required')
                need(not receiver.finished, 'single capture run is closed')
                if self.path == '/config':
                    self.reply(200,json.dumps(config,separators=(',',':')).encode())
                else:
                    path = static_file(self.path,root,pkg)
                    decoded = unquote(self.path)
                    if decoded.startswith('/assets/'):
                        need(decoded[1:] in allowed_assets, 'unbound asset path')
                    if decoded.startswith('/pkg/'):
                        need(decoded[1:] in allowed_artifacts, 'unbound bindgen artifact path')
                    self.reply(200,path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            except (ValueError,OSError) as error:
                self.reply(404,json.dumps({'error':str(error)}).encode())
        def do_POST(self):
            try:
                self.connection.settimeout(CONNECTION_TIMEOUT_SECONDS)
                size = self.headers.get('Content-Length','')
                need(size.isdigit() and 0 < int(size) <= MAX_BODY and self.headers.get('Transfer-Encoding') is None, 'invalid body length/encoding')
                raw = self.rfile.read(int(size))
                result = receiver.accept(self.path,self.headers,raw)
                self.reply(200,json.dumps(result,separators=(',',':')).encode())
            except (ValueError,KeyError,TypeError,IndexError,UnicodeError,OSError) as error:
                receiver.reject(error)
                self.reply(400,json.dumps({'accepted':False,'error':str(error)}).encode())
    return Handler


RECEIPTS = {'identity':'identity.json','build':'build-receipt.json','source_before':'source-before.json','source_at_run':'source-at-run.json','source_after':'source-after.json'}


def authenticate_corpus(directory, manifest_sha256, source_inventory_sha256, fresh_path):
    """Strict new-Wasm scoring seam; never invokes or relaxes native admission."""
    directory = Path(directory)
    raw = (directory/'manifest.json').read_bytes()
    need(digest(raw) == manifest_sha256, 'frozen Wasm manifest hash differs')
    m = strict_load(raw)
    need(m['schema_version'] == 1 and m['cohort_type'] == KIND and m['historical_replay'] == 'NOT-RUN_MISSING18' and m['status'] == STATUS, 'not admitted new-Wasm cohort')
    need(m['source_unchanged'] is True and m['historical_input_hashes_reused'] is False and m['failure'] is None, 'Wasm case/source failure present')
    need(m['source_inventory_sha256'] == source_inventory_sha256, 'wrong frozen Wasm source')
    names = {**RECEIPTS,'complete':'complete.json'}
    need(set(m['receipts']) == set(names), 'complete Wasm provenance bindings missing')
    for key,name in names.items():
        need(m['receipts'][key] == original.receipt_row(directory,name), 'tampered Wasm '+key+' receipt')
    identity = strict_load((directory/'identity.json').read_bytes())
    before = strict_load((directory/'source-before.json').read_bytes())
    need(identity['schema'] == SCHEMA and identity['run_id'] == m['run_id'] and identity['source_inventory_sha256'] == source_inventory_sha256 == before['inventory_sha256'] and original.inventory_digest(before['files']) == source_inventory_sha256, 'mixed Wasm run/source identity')
    need(identity['origin'] == ORIGIN and identity['source_before_sha256'] == m['receipts']['source_before']['sha256'] and identity['build_receipt_sha256'] == m['receipts']['build']['sha256'], 'Wasm transport/receipt crosslink differs')
    need(before == strict_load((directory/'source-at-run.json').read_bytes()) == strict_load((directory/'source-after.json').read_bytes()), 'Wasm source/artifacts changed')
    validate_build(strict_load((directory/'build-receipt.json').read_bytes()),before,identity)
    need(m['anchor'] == {'role':'authenticated-original-fresh-default','bytes':fresh_path.stat().st_size,'sha256':original.FRESH_SHA} and digest(fresh_path.read_bytes()) == original.FRESH_SHA == identity['fresh_nineteenth_sha256'], 'original anchor changed')
    complete = strict_load((directory/'complete.json').read_bytes())
    need(complete['kind'] == 'complete' and complete['run_id'] == m['run_id'] and type(complete['matrix_samples']) is int and complete['matrix_samples'] == 18, 'Wasm completion differs')
    need(len(m['cases']) == 18, 'missing/extra Wasm manifest cases')
    seen, records = set(), []
    for entry in m['cases']:
        need(entry['path'] == 'keyframes/'+entry['case'] and entry['case'] in {original.case_name(k) for k in original.RECIPES}, 'wrong Wasm case path')
        compressed = (directory/entry['path']).read_bytes()
        need(len(compressed) == entry['bytes'] and digest(compressed) == entry['sha256'], 'tampered Wasm compressed case')
        raw = gzip.decompress(compressed)
        need(len(raw) == entry['raw_bytes'] and digest(raw) == entry['raw_sha256'], 'tampered Wasm raw case')
        r = strict_load(raw)
        key = original.validate_record(r,m['run_id'])
        need(key not in seen and entry['case'] == original.case_name(key), 'duplicate/mixed Wasm case')
        need(entry['recipe'] == {'torso_length':key[0],'jaw_drop':0,'clip_id':key[1],'k':key[2],'seconds':key[2]/8}, 'mislabeled Wasm recipe')
        seen.add(key);records.append(r)
    need(seen == set(original.RECIPES), 'missing Wasm recipe')
    return records


def run(args):
    need(args.port == 9218, 'fixed assigned port9218 required')
    need(args.asset_root.resolve() == (ROOT/'assets').resolve(), 'current original assets only')
    args.out.mkdir(parents=True,exist_ok=False)
    before = source_closure(ROOT,args.pkg)
    write_json(args.out/'source-before.json',before)
    raw = args.build_receipt.read_bytes()
    build = strict_load(raw)
    (args.out/'build-receipt.json').write_bytes(raw)
    run_id = 'nvwa84-current18-wasm-'+str(uuid.uuid4())
    versions = {tool:subprocess.check_output([tool,'--version'],cwd=ROOT,text=True).strip() for tool in ('rustc','cargo')}
    versions['wasm_bindgen'] = subprocess.check_output([str(args.wasm_bindgen),'--version'],cwd=ROOT,text=True).strip()
    identity = {'schema':SCHEMA,'run_id':run_id,'build_run_id':build['build_run_id'],'target':TARGET,'execution_mode':'CPU_ONLY_WASM_PRODUCTION_PLUGIN','origin':ORIGIN,'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_dirty_paths':subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).splitlines(),'source_inventory_sha256':before['inventory_sha256'],'source_before_sha256':digest((args.out/'source-before.json').read_bytes()),'build_receipt_sha256':digest(raw),'compiled_source_sha256':build['source_files_sha256'],'artifact_inventory_sha256':before['artifact_inventory_sha256'],'build_command':build['command'],'toolchain':versions,'host':{'system':platform.system(),'machine':platform.machine()},'fresh_nineteenth_sha256':original.FRESH_SHA,'historical_raw18':'MISSING; not recovered','graphics':'NOT-RUN'}
    validate_build(build,before,identity)
    write_json(args.out/'identity.json',identity)
    # Reuse every original exact geometry, source, fixture and anchor gate unchanged.
    validator = original.geometry_validator(args.asset_root,args.fresh)
    at_run = source_closure(ROOT,args.pkg)
    need(before == at_run,'source/artifacts changed before Wasm run')
    write_json(args.out/'source-at-run.json',at_run)
    receiver = Receiver(args.out,run_id,validator)
    config = {'run_id':run_id,'recipes':[{'torso_length':t,'jaw_drop':0,'clip_id':c,'k':k,'seconds':k/8} for t,c,k in original.RECIPES],'asset_root':'assets','pkg_module':'/pkg/nvwa_shoulder_wasm_replay.js','capture_path':'/capture','complete_path':'/complete'}
    server = HTTPServer(('127.0.0.1',args.port),handler_for(receiver,config,ROOT,args.pkg,before['files'],before['artifacts']))
    server.timeout = 1
    print(json.dumps({'phase':'READY_FOR_OWNED_CLIENT','origin':ORIGIN,'run_id':run_id}),flush=True)
    deadline = time.monotonic()+args.timeout_seconds
    try:
        while not receiver.finished and time.monotonic() < deadline:
            server.handle_request()
        if not receiver.finished:receiver.reject('bounded Wasm receiver timeout')
    finally:
        server.server_close()
    after = source_closure(ROOT,args.pkg)
    write_json(args.out/'source-after.json',after)
    if after != before:receiver.reject('source/artifacts changed during Wasm capture')
    receipts = {key:original.receipt_row(args.out,name) for key,name in RECEIPTS.items()}
    if receiver.complete:receipts['complete']=original.receipt_row(args.out,'complete.json')
    result = {'schema_version':1,'cohort_type':KIND,'historical_replay':'NOT-RUN_MISSING18','status':STATUS if receiver.complete and receiver.failure is None else 'REJECT_WASM_CORPUS','run_id':run_id,'source_inventory_sha256':before['inventory_sha256'],'anchor':{'role':'authenticated-original-fresh-default','bytes':args.fresh.stat().st_size,'sha256':original.FRESH_SHA},'source_unchanged':before == at_run == after,'historical_input_hashes_reused':False,'cases':receiver.entries,'failure':receiver.failure,'receipts':receipts,'quality_acceptance':False,'graphics':'NOT-RUN'}
    write_json(args.out/'manifest.json',result)
    print(json.dumps({'status':result['status'],'cases':len(receiver.entries),'failure':receiver.failure}),flush=True)
    return 0 if result['status'] == STATUS else 2


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pkg','build-receipt','wasm-bindgen','asset-root','fresh','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--port',type=int,default=9218)
    p.add_argument('--timeout-seconds',type=int,default=300)
    try:raise SystemExit(run(p.parse_args()))
    except (ValueError,KeyError,TypeError,IndexError,OSError) as error:
        print(json.dumps({'status':'REJECT_WASM_CORPUS','failure':str(error)}));raise SystemExit(2)
