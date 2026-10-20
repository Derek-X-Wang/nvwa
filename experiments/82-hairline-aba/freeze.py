"""Create-only closure of owned source plus authenticated retained input copies."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent;OUT=ROOT/'.work/hairline-aba79';FREEZE=OUT/'SOURCE-FREEZE-v2.json'
def require(ok,msg):
 if not ok:raise ValueError(msg)
def item(p):
 require(p.is_file() and not p.is_symlink(),'unsafe/absent closure file '+str(p));raw=p.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def verify(path=FREEZE):
 doc=json.loads(path.read_text());files=doc.get('files');require(isinstance(files,dict) and len(files)>311,'nonempty full closure required')
 for name,pin in files.items():
  p=Path(name);require(not p.is_absolute() and '..' not in p.parts and str(p)==name,'safe closure path required');require(item(ROOT/p)==pin,'source/input drift '+name)
 print('SOURCE_FREEZE_EXACT',hashlib.sha256(path.read_bytes()).hexdigest(),len(files));return doc
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 if a.verify:verify()
 else:
  paths=[p for p in EXP.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
  for folder in ['retained-r2-site','validator-root']:paths.extend(p for p in (OUT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
  paths.extend([OUT/'INPUT-COPY.json',OUT/'VALIDATOR-ROOT.json']);files={str(p.relative_to(ROOT)):item(p) for p in sorted(paths)}
  with FREEZE.open('x') as f:json.dump({'version':1,'scope':'first bounded actual A/B/A only; no measurement retries/tuning','files':files},f,indent=2)
  verify()
