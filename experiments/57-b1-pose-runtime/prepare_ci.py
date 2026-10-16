#!/usr/bin/env python3
"""Explicit portable CI preparation from the exact approved public bundle only."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST_SHA='925688915e0ff918ba9c373c3aba39a5dbc1d4b93cabb65a3b51398fdfab3bcb'
ARCHIVE_SHA='4ee03913687b47f8a7379b2ba00f00a005e2129e3dd2a7f9bdda28a3c99054c5'
COMMON='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition,message):
 if not condition:raise ValueError(message)
def prepare_ci(seed,output):
 bundle=ROOT.parent/'59-b1-ci-inputs';manifest_path=bundle/'manifest.json'
 # Resolve by the repo's unique numbered directory; the pin, not directory spelling, is authority.
 if not manifest_path.exists():bundle=next(ROOT.parent.glob('59-*'));manifest_path=bundle/'manifest.json'
 require(sha(manifest_path)==MANIFEST_SHA,'CI manifest SHA256 mismatch')
 manifest=json.loads(manifest_path.read_text());archive=bundle/'approved-inputs.tar.gz'
 require(sha(archive)==ARCHIVE_SHA==manifest['archive_sha256'],'CI archive SHA256 mismatch')
 require(manifest['common_manifest_sha256']==COMMON,'CI common identity mismatch')
 seed=Path(seed).absolute();require(seed.is_dir() and not seed.is_symlink(),'CI seed missing or symlinked')
 expected={entry['path']:entry for entry in manifest['files']};files={p.relative_to(seed).as_posix():p for p in seed.rglob('*') if p.is_file() or p.is_symlink()}
 require(set(files)==set(expected),'CI seed file set mismatch')
 for name,path in files.items():
  require(not path.is_symlink() and path.resolve().is_relative_to(seed.resolve()),'CI seed symlink/escape')
  require(path.stat().st_size==expected[name]['bytes'] and sha(path)==expected[name]['sha256'],'CI seed hash mismatch: '+name)
 output=Path(output).absolute();derived=output/'derived';deps=output/'.deps'
 require(not derived.exists() and not deps.exists(),'CI derived/dependency output already exists')
 output.mkdir(parents=True,exist_ok=True)
 shutil.copytree(seed/'source/humentity',derived)
 for name in ('bevy_obj-0.19.0','wobj-0.3.0'):shutil.copytree(seed/'crates'/name,deps/name)
 patches=[ROOT.parent/'55-source-character-runtime/evidence/packaging.patch',ROOT.parent/'55-source-character-runtime/evidence/B1-threshold.patch',*sorted((ROOT/'patches').glob('*.patch'))]
 for patch in patches:subprocess.run(['patch','-p1','--batch','-i',str(patch)],cwd=derived,check=True,capture_output=True)
 # Same package feature/physics exclusions as 55; only patch paths become portable.
 cargo=derived/'Cargo.toml';text=cargo.read_text().split('[patch.crates-io]')[0]
 text+='[patch.crates-io]\nbevy_obj = { path = "../.deps/bevy_obj-0.19.0" }\nwobj = { path = "../.deps/wobj-0.3.0" }\n';cargo.write_text(text)
 from prepare import tree
 receipt={'schema_version':1,'status':'portable_candidate_source_prepared','ci_manifest_sha256':sha(manifest_path),'ci_archive_sha256':sha(archive),'common_sha256':COMMON,'source_tree_sha256':tree(derived),'source_code_tree_sha256':tree(derived/'src'),'patches':{p.name:sha(p) for p in patches},'scope':'CI sampled regression only; normal private approval gate and full40 acceptance unchanged','output':str(output)}
 (output/'ci-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
