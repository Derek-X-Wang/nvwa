#!/usr/bin/env python3
"""Verify and copy immutable B1, then apply only separately recorded adapter patches."""
import hashlib,json,shutil,argparse,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'55-source-character-runtime'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):
    return hashlib.sha256(b''.join(x.relative_to(p).as_posix().encode()+b'\0'+digest(x).encode()+b'\n' for x in sorted(p.rglob('*')) if x.is_file() and not any(k in ('.git','target') for k in x.relative_to(p).parts))).hexdigest()
def require(ok,message):
    if not ok: raise ValueError(message)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');parser.add_argument('--ci-inputs',type=Path);parser.add_argument('--out',type=Path);args=parser.parse_args()
    if args.ci_inputs:
        require(not args.verify, 'CI verification is strict seed verification before preparation; use a new output')
        from prepare_ci import prepare_ci
        print(json.dumps(prepare_ci(args.ci_inputs,args.out or ROOT)));return
    require(not args.out, '--out is only for explicit CI preparation')
    proof=json.loads((OLD/'evidence/B1-preparation.json').read_text())
    require(tree(OLD/'derived-b1')==proof['B1_source_tree_sha256'], 'preparation identity validation failed')
    require(digest(ROOT.parent/'56-b1-pose-reference/poses.json')=='8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2', 'preparation identity validation failed')
    common=ROOT.parent.parent/'.work/character-approved-20261016/common-sample.json'
    require(digest(common)=='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7', 'preparation identity validation failed')
    temporary=tempfile.TemporaryDirectory() if args.verify else None
    dest=Path(temporary.name)/'derived' if temporary else ROOT/'derived'
    require(not dest.exists(), 'refuse to overwrite derived source')
    shutil.copytree(OLD/'derived-b1',dest)
    import subprocess
    for patch in sorted((ROOT/'patches').glob('*.patch')):
        subprocess.run(['patch','-p1','--batch','-i',str(patch)],cwd=dest,check=True)
    if args.verify: require(tree(dest)==tree(ROOT/'derived'), 'prepared source drift')
    receipt={'B1_source_tree_sha256':proof['B1_source_tree_sha256'],'prepared_source_tree_sha256':tree(dest),'patches':{x.name:digest(x) for x in sorted((ROOT/'patches').glob('*.patch'))},'common_sha256':digest(common),'poses_sha256':digest(ROOT.parent/'56-b1-pose-reference/poses.json')}
    if temporary: temporary.cleanup()
    (ROOT/'evidence/preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    deps=ROOT/'.deps'
    if not deps.exists(): shutil.copytree(OLD/'.deps',deps)
    print(json.dumps(receipt))
if __name__=='__main__': main()
