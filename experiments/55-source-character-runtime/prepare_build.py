#!/usr/bin/env python3
"""Prepare approved immutable Humentity source and two approved crates offline."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import run

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
STORE = REPO / '.work/character-approved-20261016'
CRATES = {'bevy_obj-0.19.0': '894c100f4b3f147d67fab910e176e8c5453593abdfb894a94eb0c93661996dfa',
          'wobj-0.3.0': '28b34b5fbb60f0273c065bfadca18e2decf9e1cac4da09e0ce61b799c05ee631'}

def extract_crate(name, expected):
    archive = STORE / 'crates' / (name + '.crate')
    run.require(archive.is_file() and run.digest(archive) == expected, 'approved crate unavailable: ' + name)
    output = ROOT / '.deps' / name
    run.require(not output.exists(), 'crate output already exists; retain or audit before repeat')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        run.require(sum(m.size for m in members) <= 10000000, 'crate extracted-byte cap exceeded')
        for member in members:
            path = Path(member.name)
            run.require(path.parts and path.parts[0] == name and '..' not in path.parts
                        and not path.is_absolute(), 'unsafe crate member path')
            run.require(member.isfile() or member.isdir(), 'nonregular crate member')
        for member in members:
            path = ROOT / '.deps' / member.name
            if member.isdir(): path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream: shutil.copyfileobj(tar.extractfile(member), stream)
    return output

def main():
    auth = json.loads((STORE / 'authorization.json').read_text())
    run.require(auth['approval_status'] == 'explicit_human_approval_received', 'approval unavailable')
    bill = REPO / 'experiments/53-character-comparison/downloads/manifest.json'
    run.require(run.digest(bill) == auth['approved_manifest_sha256'], 'approved bill identity changed')
    inventory = run.read_pinned_json(ROOT / 'upstream-inventory.json', run.INVENTORY_SHA256, 'upstream inventory')
    upstream = STORE / 'upstream/Humentity'
    run.require(upstream.is_dir(), 'approved source bytes not present')
    hashes = {item['path']: run.digest(upstream / item['path']) for item in inventory['files']}
    run.verify_inventory(upstream, inventory['files'], hashes)
    derived = ROOT / 'derived'
    run.require(not derived.exists(), 'derived output already exists; retain or audit before repeat')
    deps = {name: extract_crate(name, checksum) for name, checksum in CRATES.items()}
    for item in inventory['files']:
        path = derived / item['path']; path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(upstream / item['path'], path)
    original = (derived / 'Cargo.toml').read_text()
    lines = original.splitlines()
    kept = []; skip = False
    for line in lines:
        if line.startswith('['):
            skip = line.startswith(('[dev-dependencies]', '[[example]]', '[features]'))
        if skip or line.startswith(('avian3d =', 'bevy_boxddd =', 'bevy_jolt =')): continue
        kept.append(line)
        if line == '[package]':
            kept += ['autobins = false', 'autoexamples = false', 'autotests = false', 'autobenches = false']
    features = ['std','async_executor','reflect_auto_register','bevy_asset','bevy_scene','bevy_world_serialization','bevy_gltf','bevy_animation','bevy_render','bevy_core_pipeline','bevy_pbr','bevy_light','bevy_camera','bevy_mesh','bevy_image','bevy_shader','bevy_log','bevy_color','bevy_material','morph','morph_animation','gltf_animation','multi_threaded','bevy_gizmos']
    kept = ['bevy = { version = \"=0.19.1\", default-features = false, features = ' + json.dumps(features) + ' }' if line == 'bevy = \"0.19.1\"' else line for line in kept]
    manifest = '\n'.join(kept) + '\n\n[workspace]\n\n[lib]\ntest = false\ndoctest = false\n\n[features]\ndefault = []\ndebug = ["bevy/debug"]\navian = []\njolt = []\nboxddd = []\n\n[patch.crates-io]\n'
    for name, path in deps.items(): manifest += name.rsplit('-', 1)[0] + ' = { path = ' + json.dumps(str(path)) + ' }\n'
    (derived / 'Cargo.toml').write_text(manifest)
    lib = derived / 'src/lib.rs'; before_lib = lib.read_text()
    guard = '\n#[cfg(any(feature = "avian", feature = "jolt", feature = "boxddd"))]\ncompile_error!("Nvwa CPU probe disables physics features");\n'
    lib.write_text(before_lib + guard)
    changes = {'Cargo.toml': (original, manifest), 'src/lib.rs': (before_lib, before_lib + guard)}
    patch_text = ''.join(''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                        fromfile='upstream/' + name, tofile='derived/' + name)) for name, (a,b) in changes.items())
    (ROOT / 'evidence/packaging.patch').write_text(patch_text)
    proof = dict(schema_version=1, upstream_commit=run.PIN, upstream_inventory_sha256=run.INVENTORY_SHA256,
                 upstream_files_sha256=hashes, approved_bill_sha256=auth['approved_manifest_sha256'],
                 patch_sha256=hashlib.sha256(patch_text.encode()).hexdigest(),
                 modified_files={name: {'before_sha256': hashlib.sha256(a.encode()).hexdigest(),
                                        'after_sha256': hashlib.sha256(b.encode()).hexdigest()} for name,(a,b) in changes.items()},
                 bevy_features=features, bevy_default_features=False,
                 authorization_note='Root authorized no-audio/no-physics/no-dev-UI Bevy feature selection',
                 semantics='CPU mesh/morph/rig algorithms unchanged; physics/dev/examples disabled; local approved crates patched')
    (derived / 'patch.json').write_text(json.dumps(proof, indent=2) + '\n')
    (ROOT / 'evidence/packaging.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Prepared real upstream source copy; no candidate code executed')

if __name__ == '__main__':
    try: main()
    except (run.Blocked, OSError, ValueError, KeyError) as error:
        print('NOT-RUN: ' + str(error)); sys.exit(2)
