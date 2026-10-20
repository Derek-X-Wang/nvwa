"""Version2 wrapper around unchanged sealed R2 single-capture checker."""
from pathlib import Path,PurePosixPath
import argparse,json,hashlib,re,sys,traceback
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.work/hairline-aba79';VROOT=OUT/'validator-root'
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
