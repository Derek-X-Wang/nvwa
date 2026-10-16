#!/usr/bin/env python3
"""Authorized one-line threshold ablation; preserve B0 source, binary and outputs."""
import difflib,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import run

def main():
    prediction=json.loads((ROOT/'evidence/threshold-prediction.json').read_text())
    run.require(prediction['status']=='body_helper_threshold_cause_supported','causal prediction did not meet conditional authorization')
    source=ROOT/'derived-b1';adapter=ROOT/'adapter-b1'
    run.require(not source.exists() and not adapter.exists(),'B1 output already exists')
    original_binary=ROOT/'target/debug/humentity-probe'
    before={'binary_sha256':run.digest(original_binary),'derived_tree_sha256':run.tree_digest(ROOT/'derived'),
            'adapter_tree_sha256':run.tree_digest(ROOT/'adapter'),
            'outputs':{p.name:run.digest(p) for p in sorted((ROOT/'results/run3').iterdir()) if p.is_file()}}
    shutil.copytree(ROOT/'derived',source,ignore=shutil.ignore_patterns('resolved-metadata.json'))
    target=source/'src/loaders/target.rs';old=target.read_text()
    needle='const DELTA_SQ_THRESHOLD: f32 = 1e-6;';run.require(old.count(needle)==1,'threshold source identity changed')
    new=old.replace(needle,'const DELTA_SQ_THRESHOLD: f32 = 0.0;');target.write_text(new)
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='B0/src/loaders/target.rs',tofile='B1/src/loaders/target.rs'))
    shutil.copytree(ROOT/'adapter',adapter)
    manifest=adapter/'Cargo.toml';text=manifest.read_text().replace('name = "humentity-probe"','name = "humentity-probe-b1"').replace('path = "../derived"','path = "../derived-b1"');manifest.write_text(text)
    # Preserve every resolved external version; only the local probe package name changes.
    lock=adapter/'Cargo.lock';text=lock.read_text();run.require(text.count('name = "humentity-probe"')==1,'B0 lock identity changed')
    lock.write_text(text.replace('name = "humentity-probe"','name = "humentity-probe-b1"'))
    proof={'variant':'B1-threshold-zero','authorization':'Root explicitly authorized conditional single-threshold ablation after residual <=1e-5; condition passed',
           'common_manifest_sha256':prediction['common_manifest_sha256'],'upstream_commit':run.PIN,
           'one_line_source_patch':{'path':'src/loaders/target.rs','before':needle,'after':'const DELTA_SQ_THRESHOLD: f32 = 0.0;',
                                    'before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest()},
           'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'B0_preservation':before,
           'B1_source_tree_sha256':run.tree_digest(source),'B1_adapter_tree_sha256':run.tree_digest(adapter),
           'B1_manifest_sha256':run.digest(manifest),'B1_lock_sha256':run.digest(lock)}
    with (ROOT/'evidence/B1-threshold.patch').open('x') as stream:stream.write(patch)
    with (ROOT/'evidence/B1-preparation.json').open('x') as stream:json.dump(proof,stream,indent=2)
    print('B1 one-line ablation prepared; B0 preserved; no candidate execution yet')
if __name__=='__main__':main()
