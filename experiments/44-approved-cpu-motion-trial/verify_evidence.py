#!/usr/bin/env python3
"""Verify retained evidence offline; never acquire models or execute a provider."""
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.flags.optimize:
        raise SystemExit('Evidence verification requires Python optimization disabled; use normal Python without -O/-OO or PYTHONOPTIMIZE.')
    inventory = read('SHA256SUMS.json')
    listed = set()
    for row in inventory:
        name = row['path']
        assert name not in listed and not Path(name).is_absolute()
        assert '..' not in Path(name).parts
        listed.add(name)
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
        if path.suffix == '.json':
            json.loads(path.read_text())
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()}
    assert actual == listed | {'SHA256SUMS.json'}
    for row in read('evidence/copy-provenance.json')['files']:
        path = HERE / row['published_path']
        assert path.stat().st_size == row['original_bytes']
        assert sha(path) == row['original_sha256']
        assert row['transformation'] == 'none; exact original bytes'

    approval = read('evidence/authorization-public.json')
    ledger = read('evidence/one-attempt-ledger.json')
    controller = read('evidence/inference-controller.json')
    process = read('evidence/run/process/receipt.json')
    generation = read('evidence/run/generation-receipt.json')
    assert approval['inference_attempt_limit'] == ledger['guard_invocation_count'] == 1
    assert not ledger['retry_allowed'] and ledger['state'] == 'consumed_before_launch'
    assert ledger['recorded_utc'] < controller['started_utc']
    assert controller['guard_invocation_count'] == 1 and controller['returncode'] == 0
    assert all(generation[key] == value for key, value in process.items())
    assert process['reason'] == 'exited' and process['returncode'] == 0
    assert process['owned_group_exit_verified'] and not process['cleanup_errors']
    assert process['wall_stop_seconds'] == 600 and process['rss_stop_bytes'] == 7 * 2**30
    assert len(process['samples']) == 544
    assert max(s['rss_bytes'] for s in process['samples']) == process['max_sampled_group_rss_bytes'] == 1234583552
    assert generation['raw_complete']
    assert (HERE / 'evidence/run/process/stdout.txt').read_bytes() == b'generated 90 frames with 30 joints\n'
    assert sha(HERE / 'evidence/run/prompt.txt') == generation['prompt_file_sha256']
    assert (HERE / 'evidence/run/prompt.txt').read_text() == 'A person stands in place and waves their right hand.\n'
    profile = (HERE / 'evidence/run/process/stderr.txt').read_text()
    assert all(line.startswith('profile ') for line in profile.splitlines())
    steps = [int(v) for v in re.findall(r'^profile motion.diffusion_step index=(\d+) ', profile, re.M)]
    assert steps == list(range(24, -1, -1))

    proposal = json.loads((HERE.parent / '41-real-short-motion/proposal.json').read_text())
    assert generation['request'] == {key: proposal[key] for key in (
        'code_revision', 'ggml_revision', 'artifacts', 'prompt', 'seed', 'frames',
        'fps', 'diffusion_steps', 'text_cfg', 'constraint_cfg')}
    acquisition = read('evidence/acquisition/receipt.json')
    assert len(acquisition['artifacts']) == 3
    for expected, actual_artifact in zip(proposal['artifacts'], acquisition['artifacts']):
        assert all(actual_artifact[key] == value for key, value in expected.items())
        assert actual_artifact['verified_bytes'] == expected['bytes']
        assert actual_artifact['verified_sha256'] == expected['sha256']
    assert sum(a['verified_bytes'] for a in acquisition['artifacts']) == 6198789742
    assert read('evidence/acquisition/process.json')['returncode'] == 0
    assert (HERE / 'evidence/acquisition/stdout.txt').read_bytes() == b'Verified 6198789742 exact model bytes; inference not started\n'
    assert not (HERE / 'evidence/acquisition/stderr.txt').read_bytes()

    post = read('evidence/reviews/post-run-review.json')
    roots = struct.unpack('<270f', (HERE / 'evidence/run/raw/root_positions.f32').read_bytes())
    rotations = struct.unpack('<10800f', (HERE / 'evidence/run/raw/local_rotations_xyzw.f32').read_bytes())
    assert all(math.isfinite(v) for v in roots + rotations)
    norms = [math.sqrt(sum(v*v for v in rotations[i:i+4])) for i in range(0, len(rotations), 4)]
    assert len(norms) == 2700 and all(v > 0 for v in norms)
    stats = read('evidence/numeric-structure.json')
    assert stats['finite_scalar_count'] == len(roots) + len(rotations) == 11070
    assert stats['quaternion_norm_min'] == post['numeric_admission']['quaternion_norm_min'] == min(norms)
    assert stats['quaternion_norm_max'] == post['numeric_admission']['quaternion_norm_max'] == max(norms)
    assert stats['max_absolute_norm_error'] == max(abs(v-1) for v in norms)
    assert stats['max_absolute_norm_error'] == post['numeric_admission']['max_absolute_norm_error']
    assert stats['sample_times']['last_seconds'] == 89/30
    for spec in post['raw_files']:
        path = HERE / 'evidence/run/raw' / spec['name']
        assert path.stat().st_size == spec['bytes'] and sha(path) == spec['sha256']
    for observation in post['cleanup']['fresh_ps']:
        assert observation['returncode'] == 1 and observation['stdout'] == observation['stderr'] == ''

    # Inspect published text only. Raw F32 bytes are intentionally not text.
    forbidden = [r'https?://[^\s"<>]+\?', r'gh[pousr]_[A-Za-z0-9]{15,}',
                 r'hf_[A-Za-z0-9]{15,}', r'sk-[A-Za-z0-9]{15,}',
                 r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'(?i)authorization:\s*bearer\s+',
                 r'(?i)(x-amz-signature|x-amz-credential|x-goog-signature)=']
    for name in listed:
        path = HERE / name
        if path.suffix != '.f32' and name != 'verify_evidence.py':
            text = path.read_text()
            assert not any(re.search(pattern, text) for pattern in forbidden), name
    print(json.dumps({'published_files_verified': len(inventory), 'raw_files': 2,
                      'finite_scalars': 11070, 'quaternions': len(norms),
                      'max_quaternion_norm_error': max(abs(v-1) for v in norms),
                      'diffusion_steps': len(steps), 'one_attempt_receipts_consistent': True,
                      'numeric_structure': 'PASS',
                      'axes_normalization_mapping_semantics_playback': 'NOT-RUN'}, indent=2))


if __name__ == '__main__':
    main()
