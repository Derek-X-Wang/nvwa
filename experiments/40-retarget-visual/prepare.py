#!/usr/bin/env python3
"""Prepare private copies for issue 13. Never edits the fixture or runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRIVATE = ROOT / '.work/m12-retarget'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def glb_json(path):
    data = path.read_bytes()
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4e4f534a
    return json.loads(data[20:20+length])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-app', type=Path, required=True)
    args = parser.parse_args()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    copied = PRIVATE / 'Nvwa-retarget.app'
    if not copied.exists():
        shutil.copytree(args.baseline_app, copied)
    baseline_binary = args.baseline_app / 'Contents/MacOS/Nvwa'
    binary = copied / 'Contents/MacOS/Nvwa'
    assert sha(binary) == sha(baseline_binary)
    asset_root = PRIVATE / 'assets'
    (asset_root / 'fixtures').mkdir(parents=True, exist_ok=True)
    work_root = PRIVATE / 'works'
    work_root.mkdir(exist_ok=True)
    profile_template = json.loads((ROOT / 'assets/character.profile.json').read_text())
    sources = {
        'reference': ROOT / 'assets/fixtures/nvwa-humanoid.glb',
        'naive': ROOT / 'experiments/04-retarget-basis/target-naive.glb',
        'corrected': ROOT / 'experiments/04-retarget-basis/target-corrected.glb',
    }
    manifest = {'baseline_app': str(args.baseline_app), 'binary_sha256': sha(binary),
                'copied_binary': str(binary), 'asset_root': str(asset_root),
                'renderer_cohort': 'frozen release artifact, not current-main acceptance',
                'variants': {}, 'sample_times_seconds': [0.0, 0.123, 0.5, 1.25, 2.345, 3.0]}
    for variant, source in sources.items():
        target = asset_root / f'fixtures/{variant}.glb'
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
        glb = glb_json(target)
        names = [animation['name'] for animation in glb['animations']]
        assert names == ['idle', 'turn', 'wave'], names
        profile = json.loads(json.dumps(profile_template))
        profile['asset_path'] = f'fixtures/{variant}.glb'
        profile['asset_sha256'] = sha(target)
        for clip in profile['clips']:
            clip['animation_index'] = names.index(clip['id'])
        works = {}
        for mode in ['rest', 'wave']:
            work = {'schema_version': 1, 'revision': 0, 'profile': profile,
                    'character': {'id': 'character-1', 'profile_id': profile['id'],
                                  'parameters': {p['id']: 0.0 for p in profile['parameters']}, 'scale': 1.0},
                    'timeline': [] if mode == 'rest' else [
                        {'id': 'controlled-wave', 'clip_id': 'wave', 'start_seconds': 0.0,
                         'duration_seconds': 3.0416667, 'speed': 1.0, 'looping': True}]}
            path = work_root / f'{variant}-{mode}.nvwa.json'
            path.write_text(json.dumps(work, indent=2) + '\n')
            retained = OUT / 'works' / path.name
            retained.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, retained)
            works[mode] = {'path': str(path), 'sha256': sha(path)}
        manifest['variants'][variant] = {'source': str(source), 'sha256': sha(source),
                                         'animation_names': names, 'wave_animation_index': names.index('wave'),
                                         'works': works}
    (OUT / 'preparation.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
