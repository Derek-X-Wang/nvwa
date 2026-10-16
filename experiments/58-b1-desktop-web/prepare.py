"""Stage authenticated original input encodings, never baked meshes/frames."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
COMMON_SHA = '2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
POSE_SHA = '8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2'
CI_MANIFEST_SHA = '925688915e0ff918ba9c373c3aba39a5dbc1d4b93cabb65a3b51398fdfab3bcb'

class InputError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise InputError(str(message))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    text = json.dumps(value, indent=2) + '\n'
    if not path.exists() or path.read_text() != text:
        path.write_text(text)

def source_files(runtime):
    result={}
    for folder in ['derived/src','adapter/src']:
        root=runtime/folder
        require(root.is_dir() and not root.is_symlink(), 'runtime source folder missing: '+folder)
        require((root/'lib.rs').is_file() and (root/'lib.rs').stat().st_size>0, 'runtime source lib.rs missing/empty: '+folder)
        files=[path for path in sorted(root.rglob('*')) if path.is_file()]
        require(bool(files), 'runtime source folder empty: '+folder)
        for path in files:
            require(not path.is_symlink(), 'runtime source symlink rejected')
            result[str(path.relative_to(runtime))]=sha(path)
    return result

def safe_output(out, relative_files):
    out=out.absolute()
    require('..' not in out.parts, 'output traversal rejected')
    require(out.is_relative_to(REPO/'.work/b1-pose-viewer') or out.is_relative_to(ROOT), 'output must be inside owned viewer directories')
    for path in [out,*[out/relative for relative in relative_files]]:
        for ancestor in [path,*path.parents]:
            require(not ancestor.is_symlink(), 'output symlink or symlink ancestor rejected')
    require(not out.exists() or out.is_dir(), 'output must be a directory')
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ci-inputs', type=Path)
    parser.add_argument('--out', type=Path, default=REPO / '.work/b1-pose-viewer/site')
    args = parser.parse_args()
    source = REPO / 'experiments/55-source-character-runtime'
    proof_path = source / 'evidence/data-adapter.json'
    proof = json.loads(proof_path.read_text())
    require(proof['common_manifest_sha256'] == COMMON_SHA, "Input validation failed: proof['common_manifest_sha256'] == COMMON_SHA")
    require(sha(REPO / 'experiments/56-b1-pose-reference/poses.json') == POSE_SHA, "Input validation failed: sha(REPO / 'experiments/56-b1-pose-reference/poses.json') == POSE_SHA")
    if args.ci_inputs:
        bundle = REPO / 'experiments/59-b1-ci-inputs'
        require(sha(bundle / 'manifest.json') == CI_MANIFEST_SHA, 'CI manifest identity mismatch')
        manifest = json.loads((bundle / 'manifest.json').read_text())
        require(manifest['common_manifest_sha256'] == COMMON_SHA, "Input validation failed: manifest['common_manifest_sha256'] == COMMON_SHA")
        archive = bundle / 'approved-inputs.tar.gz'
        require(archive.stat().st_size == manifest['archive_bytes'] and sha(archive) == manifest['archive_sha256'], "Input validation failed: archive.stat().st_size == manifest['archive_bytes'] and sha(archive) == manifest['archive_sha256']")
        seed = args.ci_inputs.absolute()
        require(seed.is_dir() and (not seed.is_symlink()), 'Input validation failed: seed.is_dir() and not seed.is_symlink()')
        for entry in manifest['files']:
            rel = Path(entry['path'])
            require(not rel.is_absolute() and '..' not in rel.parts, "Input validation failed: not rel.is_absolute() and '..' not in rel.parts")
            path = seed / rel
            require(path.is_file() and (not path.is_symlink()) and (path.stat().st_size == entry['bytes']) and (sha(path) == entry['sha256']), path)
        sample = [entry for entry in manifest['files'] if entry['path'].startswith('sample/')]
        require(len(sample) == 13, 'Input validation failed: len(sample) == 13')
        require({entry['path'][7:]: entry['sha256'] for entry in sample} == proof['derived_files'], "Input validation failed: {entry['path'][7:]:entry['sha256'] for entry in sample} == proof['derived_files']")
        for entry in sample:
            require(entry['role'] == 'geometry-only-derived-input', "Input validation failed: entry['role'] == 'geometry-only-derived-input'")
            require(entry['provenance']['adapter_receipt_sha256'] == sha(proof_path), "Input validation failed: entry['provenance']['adapter_receipt_sha256'] == sha(proof_path)")
            require(entry['provenance']['common_manifest_sha256'] == COMMON_SHA, "Input validation failed: entry['provenance']['common_manifest_sha256'] == COMMON_SHA")
        data = seed / 'sample'
    else:
        store = REPO / '.work/character-approved-20261016'
        common = store / 'common-sample.json'
        require(sha(common) == COMMON_SHA, 'Input validation failed: sha(common) == COMMON_SHA')
        for entry in json.loads(common.read_text())['files']:
            path = store / entry['path']
            require(path.is_file() and path.stat().st_size == entry['bytes'] and (sha(path) == entry['sha256']), path)
        data = source / 'data'
    for rel, digest in proof['derived_files'].items():
        require(sha(data / rel) == digest, rel)
    runtime = REPO / 'experiments/57-b1-pose-runtime'
    runtime_identity=source_files(runtime)
    out = safe_output(args.out, ['assets/'+rel for rel in proof['derived_files']]+['assets/input-identity.json','assets/build-identity.json','index.html'])
    out.mkdir(parents=True, exist_ok=True)
    for rel in proof['derived_files']:
        destination = out / 'assets' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(data / rel, destination)
    shutil.copyfile(ROOT / 'index.html', out / 'index.html')
    identity = {'common_manifest_sha256': COMMON_SHA, 'pose_manifest_sha256': POSE_SHA, 'asset_files': {rel: sha(out / 'assets' / rel) for rel in sorted(proof['derived_files'])}, 'conversions': proof['conversions'], 'no_baked_frames': True}
    write_json(out / 'assets/input-identity.json', identity)
    runtime = REPO / 'experiments/57-b1-pose-runtime'
    build = {'source_variant': '57 actual B1: explicit target loader, zero padding repair, source-derived canonical gauge, optional source-derived positive-influence CPU adapter without four-cap', 'source_files': runtime_identity, 'input_identity': identity, 'pose_manifest_sha256': POSE_SHA}
    write_json(out / 'assets/build-identity.json', build)
    print(out)
if __name__ == '__main__':
    main()
