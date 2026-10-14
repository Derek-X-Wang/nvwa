#!/usr/bin/env python3
"""Read pinned source as data and count the existing GLB skin. No model run."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', default='.work/m12-motion-readiness/sources')
    parser.add_argument('--fixture', default='assets/fixtures/nvwa-humanoid.glb')
    args = parser.parse_args()
    source = Path(args.sources)
    receipts = json.loads((source / 'receipts.json').read_text())
    for item in receipts:
        assert item['status'] == 200, item
        data = (source / item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'], item['file']

    tree = ast.parse((source / 'official-kimodo__skeleton__definitions.py').read_text())
    skeletons = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in ['SOMASkeleton30', 'SOMASkeleton77']:
            for field in node.body:
                if isinstance(field, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bone_order_names_with_parents' for t in field.targets):
                    skeletons[node.name] = ast.literal_eval(field.value)
    assert len(skeletons['SOMASkeleton30']) == 30
    assert len(skeletons['SOMASkeleton77']) == 77
    names30 = [row[0] for row in skeletons['SOMASkeleton30']]
    names77 = [row[0] for row in skeletons['SOMASkeleton77']]
    assert set(names30) <= set(names77)
    config = (source / 'kimodo-config.yaml').read_text()
    assert '_target_: kimodo.skeleton.SOMASkeleton30' in config
    assert 'fps: 30' in config
    model_source = (source / 'official-kimodo__model__kimodo_model.py').read_text()
    assert model_source.count('output = self.skeleton.output_to_SOMASkeleton77(output)') == 2

    data = Path(args.fixture).read_bytes()
    magic, version, size = struct.unpack_from('<III', data)
    assert magic == 0x46546C67 and version == 2 and size == len(data)
    chunk_size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    gltf = json.loads(data[20:20 + chunk_size])
    assert len(gltf['skins']) == 1
    joints = gltf['skins'][0]['joints']
    target = [gltf['nodes'][index]['name'] for index in joints]
    assert len(target) == 18 and len(set(target)) == 18

    models = {}
    for name in ['kimodo', 'llama', 'mntp', 'supervised', 'cpp-motion', 'cpp-text']:
        obj = json.loads((source / (name + '-metadata.json')).read_text())
        models[name] = {
            'id': obj['id'], 'revision': obj['sha'], 'last_modified': obj['lastModified'],
            'gated': obj.get('gated'), 'metadata_license': obj.get('cardData', {}).get('license'),
            'safetensors': obj.get('safetensors'),
            'artifacts': [dict(path=f['rfilename'], bytes=f.get('size'), lfs=f.get('lfs'))
                          for f in obj['siblings'] if any(f['rfilename'].endswith(ext) for ext in ['.safetensors', '.gguf'])],
        }
    manifest_checks = {}
    for name in ['cpp-motion', 'cpp-text']:
        manifest = json.loads((source / (name + '-MANIFEST.json')).read_text())
        actual = {f['path']: f for f in models[name]['artifacts']}
        hash_matches = 0
        hashes_unavailable = []
        for item in manifest['files']:
            meta = actual[item['path']]
            assert item['bytes'] == meta['bytes']
            if meta['lfs'] is not None:
                assert item['sha256'] == meta['lfs']['sha256']
                hash_matches += 1
            else:
                hashes_unavailable.append(item['path'])
        for repo, revision in manifest['source_revisions'].items():
            matched = [model for model in models.values() if model['id'] == repo]
            assert len(matched) == 1 and matched[0]['revision'] == revision
        manifest_checks[name] = {'artifacts_checked': len(manifest['files']),
                                 'lfs_sha256_matches': hash_matches,
                                 'sha256_unavailable_in_metadata': hashes_unavailable,
                                 'source_revisions': manifest['source_revisions']}
    weights = {f['path']: f['bytes'] for f in models['cpp-text']['artifacts']}
    motion_bytes = models['cpp-motion']['artifacts'][0]['bytes']
    tokenizer_bytes = weights['tokenizer.gguf']
    estimates = {}
    for variant in ['BF16', 'Q8_0', 'Q4_K_M']:
        total = weights['Llama-3-Kimodo-' + variant + '.gguf'] + motion_bytes + tokenizer_bytes
        estimates[variant] = {'payload_bytes': total, 'payload_gib': total / 2**30,
                              'interpretation': 'Artifact bytes only; not peak resident memory or latency.'}
    base = models['llama']['safetensors']['total'] * 2
    official = models['kimodo']['artifacts'][0]['bytes']
    result = {
        'evidence_kind': 'STATIC SOURCE / PUBLIC METADATA / EXISTING AUTHORED FIXTURE ONLY',
        'actual_checkpoint_output_observed': False,
        'source_integrity_checks_passed': len(receipts),
        'checkpoint_internal_skeleton': 'SOMASkeleton30', 'checkpoint_fps': 30,
        'skeleton_joint_counts': {name: len(value) for name, value in skeletons.items()},
        'official_external_conversion_calls': 2,
        'somaskel30_joint_names': names30, 'somaskel77_joint_names': names77,
        'target_fixture': {'sha256': hashlib.sha256(data).hexdigest(), 'skin_count': 1,
                           'joint_count': len(target), 'joint_names': target,
                           'authored_animation_names': [a.get('name') for a in gltf.get('animations', [])]},
        'models': models, 'cpp_payload_estimates': estimates,
        'publisher_manifest_metadata_checks': manifest_checks,
        'official_base_bf16_plus_motion_bytes_lower_bound': base + official,
        'official_base_bf16_plus_motion_gib_lower_bound': (base + official) / 2**30,
        'warning': 'No adapter, tensor, generated motion, retargeting, model memory/latency, or playback was executed.',
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
