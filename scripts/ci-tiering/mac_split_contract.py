#!/usr/bin/env python3
"""Authenticate the Mac split and project only its exact delta to v3 contracts."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('mac-workspace-required', 'mac-bridges-required', 'mac-matrix-required', 'mac-workspace-background', 'mac-bridges-background', 'mac-matrix-background')
DIGESTS = {'mac-workspace-required': '94fd692fba003387136a650611a4a7f501d9008c309c1dffc9062153f9dfb75a', 'mac-bridges-required': '15f856a0cf9ea6477e643fd09d47ef6d815711156c287c7f06748bbb149d8f2b', 'mac-matrix-required': 'ce80925a2b90983f4c683608a7a03225d26e90d0389d1686b2b7a379ec30b43b', 'mac-workspace-background': 'f0ce39469c0b7c9c1706c4a9906b6b0961c13b22d36d27fd2cfdc694a8907405', 'mac-bridges-background': '90ed446058f91c44a3b43b966ec8095c1558c00e2558bfd61b377359d06c1609', 'mac-matrix-background': '1e3e044b116f871202f9d06f43ac02e63276833e5b1538cbc77b530833c76e0e'}
GOLD_SHA256 = '1098afb4969e9eda506dc2bf23062f0b272bd28b87bf4621c4bf8109ee52a52a'
V4_SHA256 = 'd4412f6f02f3cc5c48e230c462aab0bd904f647ac1ccdd78014ecc142e4736f6'
V5_JOB_DIGESTS = {
    'mac-workspace-required': '72e922f854777b99b42ebf180844a4bd68c27396592c912938bc4feca1828ed0',
    'mac-workspace-background': 'f4b44537fe9c7e90a224af11c0bdd159cf2c3d319ff117e137c5b633565fe88a',
    'required-gate': 'c274fa2bc6e4bd2471a938986c84395b189592de19050fbd245640ff4f212f4e',
    'full-mac-report': 'abdc8973f63b440529c9730b4322db67f8f6c43b48544a881eec34eed3a90324',
}
V5_SOURCE_DIGESTS = {
    'scripts/ci-tiering/mac_garment_witness.py': 'be8dc3d316f72ac603de0b27c8671f957a88bc36e16bc33212065f6dd8e717ce',
    'experiments/60-b1-continuous-motion/src/bin/matrix.rs': '2922ef91088120e8ecbc102264db4127ae76544dd633a5cc75baf43c0b0a1482',
}

def job(text, name):
    found = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', text)
    if len(found) != 1:
        raise AssertionError('Mac split job must be unique: '+name)
    return found[0]

def project(workflow, checks):
    for name, digest in V5_SOURCE_DIGESTS.items():
        checks.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
    v4 = (ROOT/'scripts/ci-tiering/mac-matrix-v4-ci.yml').read_text()
    checks.assertEqual(hashlib.sha256(v4.encode()).hexdigest(), V4_SHA256)
    # V7: a separate required cargo-check job leaves workspace tests, mutation
    # and matrix on the same warmed target. Reconstruct the exact v4 topology.
    old_linux = job(v4, 'linux-shared')
    workspace_start = old_linux.index('      - name: Shared workspace tests and real CPU export\n')
    timing_start = old_linux.index('      - name: Report existing command timing\n')
    setup = old_linux[:workspace_start]
    timing = old_linux[timing_start:]
    split_check = (setup.replace('  linux-shared:\n', '  linux-check:\n', 1)
                   .replace('    name: Linux shared runtime and full motion evidence\n',
                            '    name: Linux shared workspace check\n', 1)
                   + '      - name: Check shared workspace graph\n'
                     '        run: bash scripts/ci-tiering/linux-shared.sh check\n'
                   + timing)
    checks.assertEqual(job(workflow, 'linux-shared'), old_linux)
    checks.assertEqual(job(workflow, 'linux-check'), split_check)
    workflow = workflow.replace(split_check, '', 1)
    gate = job(workflow, 'required-gate')
    new_needs = 'linux-shared, linux-check, mac-smoke'
    checks.assertEqual(gate.count(new_needs), 1)
    workflow = workflow.replace(gate, gate.replace(new_needs, 'linux-shared, mac-smoke', 1), 1)
    for name, digest in V5_JOB_DIGESTS.items():
        current = job(workflow, name)
        checks.assertEqual(hashlib.sha256(current.encode()).hexdigest(), digest, name)
        workflow = workflow.replace(current, job(v4, name), 1)
    for name, successor in [('mac-matrix-required', 'mac-workspace-background'),
                            ('mac-matrix-background', 'mac-full-background')]:
        checks.assertNotIn('  '+name+':\n', workflow)
        marker = job(workflow, successor)
        workflow = workflow.replace(marker, job(v4, name)+marker, 1)
    # Historical negative controls mutate earlier portable steps. Leave those
    # bytes for their original named assertions after the exact new jobs have
    # been authenticated and projected away.
    golden = (ROOT/'scripts/ci-tiering/portable-split-v3-ci.yml').read_text()
    checks.assertEqual(hashlib.sha256(golden.encode()).hexdigest(), GOLD_SHA256)
    for name in NAMES:
        block = job(workflow, name)
        checks.assertEqual(hashlib.sha256(block.encode()).hexdigest(), DIGESTS[name], name)
        workflow = workflow.replace(block, '', 1)
    for name, condition in [('native-and-wasm', 'true'), ('mac-full-background', 'false')]:
        block = job(workflow, name)
        parked = '    if: ${{ false }} # retired complete lane; split jobs own every check\n'
        restored = "    if: ${{ needs.classify.outputs.full_required == '"+condition+"' }}\n"
        checks.assertEqual(block.count(parked), 1)
        workflow = workflow.replace(block, block.replace(parked, restored, 1), 1)
    for name, new, old in [
        ('required-gate','    needs: [classify, portable, portable-eye, linux-shared, mac-smoke, b1-source-regression, mac-workspace-required, mac-bridges-required, mac-matrix-required]\n','    needs: [classify, portable, portable-eye, linux-shared, mac-smoke, b1-source-regression, native-and-wasm]\n'),
        ('full-mac-report','    needs: [classify, mac-workspace-required, mac-bridges-required, mac-matrix-required, mac-workspace-background, mac-bridges-background, mac-matrix-background]\n','    needs: [native-and-wasm, mac-full-background]\n')]:
        block=job(workflow,name)
        checks.assertEqual(block.count(new),1,name)
        workflow=workflow.replace(block,block.replace(new,old,1),1)
    return workflow

INPUTS = {'scripts/ci-tiering/policy.py': ('mac-split-v3-policy.py', 'a74b3a3d29d02694ba8a9cc25bbef4e9463d39389098d7d882d9c7e8d7840851', 'd9e3d8faaf48a45d2758e9de3159171f6c55f02434db1f27967515549ef4ae85'), 'scripts/ci-tiering/test_policy.py': ('mac-split-v3-test_policy.py', '0fdbce3ce18c91c43ec8b87b37e60afcbe711c042dd76bdcc0fe8af7fe51a11e', '464bb421984cbef27d76263a1a4e4b5d6b01c7c031f7ab99200f329189d124f2'), 'scripts/ci-tiering/test_portable_split.py': ('mac-split-v3-test_portable_split.py', 'bfd9bcffc308898d115241a32aa1b9c4b3908d8998754fd790c34d76648e99d9', '134e510608c6afe932aa085187102656b46911733abf75e2c478e16a6b51ed44'), '.github/workflows/ci-mac-report.yml': ('mac-split-v3-report.yml', '74dcdacfbee4cd4e971378b43e8e84cadad0cbfa003bc47d74fbd1f450d58766', '5d35fadac433d125bbd8942d422dcb84d30ca37aab38429f2b7e5c1ff5257b7a')}
V5_INPUTS = {
    'scripts/ci-tiering/policy.py': ('mac-matrix-v4-policy.py', 'c8e375addd67a2786900ed584a53a9c9001b9a699b857f069a3c4b587342681a'),
    'scripts/ci-tiering/test_policy.py': ('mac-matrix-v4-test_policy.py', 'e85ebea2d0fa8cba5207ae5c50159334d4f9884395893c20fd3da76f8dd6e7ba'),
    'scripts/ci-tiering/test_portable_split.py': ('mac-matrix-v4-test_portable_split.py', 'f71fdfd704973ab248706fa9784d2f2c2a2aa7b1a53d9c0faf1a72a873d6c61f'),
    '.github/workflows/ci-mac-report.yml': ('mac-matrix-v4-report.yml', 'fb2c079e8852d73ea0f4121d4b67c75bc96f05f531d590dc93ad0cdc31675be6'),
}

V6_INPUTS = {
    '.github/workflows/ci-mac-report.yml': ('mac-followup-v5-report.yml',
        'd8e5772acd0203f551af77f18d18b7a21279d65becea0ec4f93b9d625d630c3e',
        'fb2c079e8852d73ea0f4121d4b67c75bc96f05f531d590dc93ad0cdc31675be6'),
    'scripts/ci-tiering/test_policy.py': ('mac-followup-v5-test_policy.py',
        '4ba901b8aec6dda9672e8dcc751a4e12798ee69e516943d7baa3e7f7aa8017d0',
        'e85ebea2d0fa8cba5207ae5c50159334d4f9884395893c20fd3da76f8dd6e7ba'),
}

V7_REPLACEMENTS = {
    "scripts/ci-tiering/policy.py": [
        (b"REQUIRED = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-check', 'mac-smoke', 'b1-source-regression')", b"REQUIRED = ('classify', 'portable', 'portable-eye', 'linux-shared', 'mac-smoke', 'b1-source-regression')"),
    ],
    "scripts/ci-tiering/test_portable_split.py": [
        (b"required = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-check', 'mac-smoke', 'b1-source-regression')", b"required = ('classify', 'portable', 'portable-eye', 'linux-shared', 'mac-smoke', 'b1-source-regression')"),
    ],
    "scripts/ci-tiering/test_policy.py": [
        (b"        check = job((ROOT / '.github/workflows/ci.yml').read_text(), 'linux-check')\n        self.assertIn('    needs: classify\\n', check)\n        self.assertIn('    runs-on: ubuntu-24.04\\n    timeout-minutes: 75\\n', check)\n        self.assertIn(\"      CARGO_BUILD_JOBS: '1'\\n\", check)\n        self.assertIn('run: bash scripts/ci-tiering/linux-shared.sh check\\n', check)\n        self.assertNotIn('continue-on-error', check)\n        self.assertNotIn('actions/cache/', check)\n        self.assertEqual((workflow + check).count('run: bash scripts/ci-tiering/linux-shared.sh check\\n'), 1)\n        self.assertEqual((workflow + check).count('run: bash scripts/ci-tiering/linux-shared.sh workspace\\n'), 1)\n        self.assertIn('linux-shared, linux-check, mac-smoke',\n                      job((ROOT / '.github/workflows/ci.yml').read_text(), 'required-gate'))\n        check_mode = linux[linux.index('  check)\\n'):linux.index('  workspace)\\n')]\n        workspace_mode = linux[linux.index('  workspace)\\n'):linux.index('  bridges)\\n')]\n        self.assertIn('cargo check --workspace --locked --features nvwa-cli/motion-query,bevy/x11', check_mode)\n        self.assertNotIn('cargo check --workspace --locked --features nvwa-cli/motion-query,bevy/x11', workspace_mode)\n        self.assertIn('cargo test --workspace --locked --features nvwa-cli/motion-query,bevy/x11', workspace_mode)\n\n", b""),
    ],
    "scripts/ci-tiering/linux-shared.sh": [
        (b"  check)\n    cargo check --workspace --locked --features nvwa-cli/motion-query,bevy/x11\n    ;;\n  workspace)\n    cargo test --workspace --locked --features nvwa-cli/motion-query,bevy/x11\n", b"  workspace)\n    cargo check --workspace --locked --features nvwa-cli/motion-query,bevy/x11\n    cargo test --workspace --locked --features nvwa-cli/motion-query,bevy/x11\n"),
        (b"Usage: linux-shared.sh fetch|check|workspace|bridges|matrix", b"Usage: linux-shared.sh fetch|workspace|bridges|matrix"),
    ],
}

def project_input(name, checks, data):
    for current, previous in V7_REPLACEMENTS.get(name, []):
        checks.assertEqual(data.count(current), 1, name)
        data = data.replace(current, previous, 1)
    if name in V6_INPUTS:
        snapshot, current_sha, previous_sha = V6_INPUTS[name]
        checks.assertEqual(hashlib.sha256(data).hexdigest(), current_sha, name)
        previous = (ROOT/'scripts/ci-tiering'/snapshot).read_bytes()
        checks.assertEqual(hashlib.sha256(previous).hexdigest(), previous_sha, snapshot)
        data = previous
    if name in V5_INPUTS:
        snapshot, current_sha = V5_INPUTS[name]
        checks.assertEqual(hashlib.sha256(data).hexdigest(), current_sha, name)
        previous = (ROOT/'scripts/ci-tiering'/snapshot).read_bytes()
        checks.assertEqual(hashlib.sha256(previous).hexdigest(), INPUTS[name][1], snapshot)
        data = previous
    if name not in INPUTS:
        return data
    snapshot, current_sha, previous_sha = INPUTS[name]
    checks.assertEqual(hashlib.sha256(data).hexdigest(), current_sha, name)
    previous = (ROOT/'scripts/ci-tiering'/snapshot).read_bytes()
    checks.assertEqual(hashlib.sha256(previous).hexdigest(), previous_sha, snapshot)
    return previous
