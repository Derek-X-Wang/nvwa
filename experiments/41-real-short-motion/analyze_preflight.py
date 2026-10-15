#!/usr/bin/env python3
"""Check text-source hashes and model metadata without executing provider code."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / '.work/m2-provider'
SOURCES = PRIVATE / 'sources'


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    receipts = json.loads((HERE / 'evidence/source-receipts.json').read_text())
    for row in receipts:
        data = (SOURCES / row['file']).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    artifacts = []
    for key, revision, paths in [
        ('motion', '65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d', ['models/kimodo-soma-rp-v1.1-f32.gguf']),
        ('text', '3e8d958803beaddb6011ac534f2be972e2710c7d', ['Llama-3-Kimodo-Q4_K_M.gguf', 'tokenizer.gguf']),
    ]:
        metadata = json.loads((SOURCES / f'{key}-current.json').read_text())
        manifest = json.loads((SOURCES / f'{key}-MANIFEST.json').read_text())
        assert metadata['sha'] == revision
        for path in paths:
            actual = next(s for s in metadata['siblings'] if s['rfilename'] == path)
            declared = next(s for s in manifest['files'] if s['path'] == path or s['path'].endswith('/' + path))
            assert declared['bytes'] == actual['size'] == actual['lfs']['size']
            assert declared['sha256'] == actual['lfs']['sha256']
            artifacts.append({'repository': manifest['repository'], 'revision': revision, 'path': path,
                              'bytes': declared['bytes'], 'sha256': declared['sha256'],
                              'download_url_after_approval_only': f'https://huggingface.co/{manifest["repository"]}/resolve/{revision}/{path}'})
    cpp = (SOURCES / 'cpp-src__skeleton.hpp').read_text()
    names = re.findall(r'"([^"]+)"', re.search(r'soma30_names\{(.*?)\};', cpp, re.S)[1])
    parents = [int(v) for v in re.search(r'soma30_parents\{(.*?)\};', cpp, re.S)[1].split(',')]
    block = re.search(r'soma30_offsets\{\{(.*?)\}\};', cpp, re.S)[1]
    offsets = [[float(v.rstrip('F')) for v in row.split(',')] for row in re.findall(r'\{([^{}]+)\}', block)]
    assert len(names) == len(set(names)) == len(parents) == len(offsets) == 30
    assert parents[0] == -1 and all(0 <= parent < i for i, parent in enumerate(parents) if i)
    skeleton = {'identity': 'kimodo.cpp/soma30', 'code_revision': '5679ff19ba0a522c0b0516e9a9d402fe1af2c027',
                'source_sha256': hashlib.sha256(cpp.encode()).hexdigest(), 'joint_names': names, 'parents': parents,
                'rest_local_translations': offsets, 'rest_local_rotations_xyzw': [[0, 0, 0, 1] for _ in names],
                'rest_local_scales': [[1, 1, 1] for _ in names],
                'rest_convention': 'C++ source parent-local offsets; identity rotations as in exporter; root rest offset zero, not exporter height 0.988',
                'units': 'meters', 'up_axis': '+Y', 'forward_axis': '+Z',
                'handedness': 'UNKNOWN: right-handed glTF identity export is static intent, actual axis control NOT-RUN',
                'motion_data': 'NONE; source skeleton metadata only'}
    write('source-skeleton.json', skeleton)
    total = sum(a['bytes'] for a in artifacts)
    proposal = {'state': 'AWAITING_EXPLICIT_MODEL_DOWNLOAD_AND_RUN_APPROVAL', 'artifacts': artifacts,
                'model_payload_bytes': total, 'model_payload_gib': total / 2**30,
                'code_revision': skeleton['code_revision'], 'ggml_revision': '8c63e70982c95ceb862e3a1073a2c1beef75d60a',
                'prompt': 'A person stands in place and waves their right hand.', 'seed': 42,
                'frames': 90, 'fps': 30, 'diffusion_steps': 25, 'text_cfg': 2.0, 'constraint_cfg': 2.0,
                'nominal_frame_budget_seconds': 3.0, 'sampled_first_to_last_seconds': 89 / 30,
                'backend': 'cpu', 'threads': 4, 'wall_stop_seconds': 600,
                'rss_soft_stop_bytes': 7 * 2**30, 'rss_target_ceiling_bytes': 8 * 2**30,
                'rss_limit_note': 'sampled own-process-group watchdog; not an OS hard memory cap; peak and completion time unmeasured',
                'raw_outputs': [{'name': 'root_positions.f32', 'shape': [90, 3], 'bytes': 1080},
                                {'name': 'local_rotations_xyzw.f32', 'shape': [90, 30, 4], 'bytes': 43200}],
                'raw_format': 'host-native IEC559 binary32, 8-bit bytes, little endian; model-free same-compiler probe is enforced before inference and bound to exact runtime/compiler hashes',
                'float_prerequisite_receipt': 'evidence/float-prerequisite.json',
                'wall_limit_note': '600-second monitoring abort threshold; bounded inspection and teardown can add latency; not a hard process-runtime deadline',
                'success_stdout': 'generated 90 frames with 30 joints\n',
                'normalization': 'pending root contract: source identity soma30, samples i/30, root trajectory replaces root translation once; do not add exporter 0.988m offset',
                'license_instruments': ['Apache-2.0: kimodo.cpp code', 'MIT: GGML code', 'NVIDIA Open Model License: SOMA-RP weights',
                                        'Meta Llama 3 Community License and acceptable use: converted text encoder', 'MIT: McGill adapters'],
                'terms_approval': 'UNKNOWN; no terms accepted or gated account inspected',
                'genuine_generation': 'NOT-RUN; no model payload downloaded'}
    write('proposal.json', proposal)
    print(json.dumps({'verified_text_responses': len(receipts), 'verified_metadata_artifacts': len(artifacts),
                      'model_payload_bytes': total, 'skeleton_joints': len(names), 'inference': 'NOT-RUN'}, indent=2))


if __name__ == '__main__':
    main()
