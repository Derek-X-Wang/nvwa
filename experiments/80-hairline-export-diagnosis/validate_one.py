"""Version2 wrapper around unchanged sealed R2 single-capture checker."""
from pathlib import Path,PurePosixPath
import argparse,json,hashlib,re,sys,traceback
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.work/hairline-export79';VROOT=OUT/'validator-root'
PINNED_ROOT_RECEIPT_SHA256='22b04ae622f3dd465522afebacaaf62bc043792116b4c1919881b0babe6db349'
def require(ok,message):
 if not ok:raise ValueError(message)
def expected_id(value):
 require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value) is not None,'independent request ID invalid');return value
def verify_validator_root(root,receipt_path):
 raw=receipt_path.read_bytes();bound=json.loads(raw);files=bound.get('files');require(isinstance(files,dict) and len(files)==311,'exact nonempty 311 validator entries required')
 for name,item in files.items():
  require(isinstance(name,str) and name and '\\' not in name,'safe relative validator path required');relative=PurePosixPath(name);require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==name,'safe relative validator path required');require(isinstance(item,dict) and type(item.get('bytes')) is int and item['bytes']>=0 and isinstance(item.get('sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',item['sha256']) is not None,'validator entry bytes/SHA invalid')
 require(hashlib.sha256(raw).hexdigest()==PINNED_ROOT_RECEIPT_SHA256,'validator receipt identity drift')
 for name,item in files.items():
  p=root/name;require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()),'validator file absent/unsafe '+name);data=p.read_bytes();require(len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],'validator source drift '+name)
 return bound
def require_original_a(envelope,independent_id):
 expected_id(independent_id);require(envelope['report']['request_id']==envelope['frame']['request_id']==independent_id,'independent request ID mismatch');require(envelope['frame']['candidate']['variant']=='AOriginal','bounded single original A required')
def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--expected-request-id',required=True);a=p.parse_args();expected_id(a.expected_request_id);verify_validator_root(VROOT,OUT/'VALIDATOR-ROOT.json')
 sys.path.insert(0,str(VROOT/'experiments/78-hairline-local-quality'))
 import collect_transfer,check_captures
 from source_binding import strict_json
 raw=a.capture.read_bytes();manifest=json.loads(a.manifest.read_text());record={'wrapper_version':2,'expected_request_id':a.expected_request_id,'capture_path':str(a.capture.resolve()),'capture_sha256':hashlib.sha256(raw).hexdigest(),'manifest_sha256':hashlib.sha256(a.manifest.read_bytes()).hexdigest(),'validator_root_receipt_sha256':hashlib.sha256((OUT/'VALIDATOR-ROOT.json').read_bytes()).hexdigest(),'scope':'single actual source/CPU capture; no full cohort, GPU pixel score or quality admission'}
 dest=OUT/'validation'/f'{a.expected_request_id}-validator-v2.json';dest.parent.mkdir(exist_ok=True)
 try:
  collect_transfer.verify_bytes(manifest,raw,expected_request_id=a.expected_request_id);record['exact_transfer']='PASS';envelope=strict_json(raw.decode('utf-8'));require_original_a(envelope,a.expected_request_id);key,error=check_captures.validate(envelope);record.update(single_source_cpu='PASS',control_key=key,replay_errors=error)
 except Exception as e:
  record.update(single_source_cpu='FAIL',error=str(e),traceback=traceback.format_exc());print(json.dumps(record,indent=2))
  with dest.open('x') as f:json.dump(record,f,indent=2)
  return 1
 with dest.open('x') as f:json.dump(record,f,indent=2)
 print(json.dumps(record,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
