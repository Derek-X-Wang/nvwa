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

V9_MUTATION_JOB_DIGESTS = {
    'mac-mutation-required': 'a411fb978e42d1ff228e6cb824ca37192ee9f8317144de25882b4383e90042c0',
    'mac-mutation-background': 'ac16fb28cc25cd00234a00eaf03980ecb6119a9f35b4edde9f3a295526489cd7',
}
V9_MUTATION_STEP = '''      - name: Check B1 production-source mutation witnesses
        timeout-minutes: 12
        run: python3 -B scripts/check-b1-motion-mutations.py --disposable-checkout --out "$RUNNER_TEMP/nvwa-b1-motion-mutations"
'''

def job(text, name):
    found = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', text)
    if len(found) != 1:
        raise AssertionError('Mac split job must be unique: '+name)
    return found[0]

def project(workflow, checks):
    # V9: original three witnesses move intact into a separate Mac job.
    # The old combined bridge name depends on mutation success, so the
    # default-branch reporter remains fail-closed during rollout.
    for name, digest in V9_MUTATION_JOB_DIGESTS.items():
        block = job(workflow, name)
        checks.assertEqual(hashlib.sha256(block.encode()).hexdigest(), digest, name)
        workflow = workflow.replace(block, '', 1)
    for kind in ('required', 'background'):
        name = 'mac-bridges-' + kind
        block = job(workflow, name)
        marker = '      - name: Report existing command timing\n'
        checks.assertEqual(block.count(marker), 1, name)
        checks.assertNotIn(V9_MUTATION_STEP, block)
        value = 'true' if kind == 'required' else 'false'
        new_condition = ("    needs: [classify, portable, portable-eye, mac-mutation-" + kind + "]\n"
                         "    if: ${{ success() && needs.classify.outputs.full_required == '" + value + "' }}\n")
        old_condition = ("    needs: [classify, portable, portable-eye]\n"
                         "    if: ${{ needs.classify.outputs.full_required == '" + value + "' }}\n")
        checks.assertEqual(block.count(new_condition), 1, name)
        restored = block.replace(new_condition, old_condition, 1)
        workflow = workflow.replace(block, restored.replace(marker, V9_MUTATION_STEP + marker, 1), 1)
    gate = job(workflow, 'required-gate')
    new_gate = 'mac-workspace-required, mac-bridges-required, mac-mutation-required]'
    checks.assertEqual(gate.count(new_gate), 1)
    workflow = workflow.replace(gate, gate.replace(new_gate, 'mac-workspace-required, mac-bridges-required]', 1), 1)
    report = job(workflow, 'full-mac-report')
    new_report = 'mac-workspace-background, mac-bridges-background, mac-mutation-required, mac-mutation-background]'
    checks.assertEqual(report.count(new_report), 1)
    workflow = workflow.replace(report, report.replace(new_report, 'mac-workspace-background, mac-bridges-background]', 1), 1)
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
    # V8: compile on the warmed shared target, then verify an immutable
    # same-run artifact before running the complete matrix in a required job.
    matrix_start = old_linux.index('      - name: Complete 594-frame matrix and real garment controls\n')
    shared_without_matrix = old_linux[:matrix_start] + timing
    checks.assertEqual(shared_without_matrix.count('    timeout-minutes: 75\n    env:\n'), 1)
    shared_with_artifact = shared_without_matrix.replace(
        '    timeout-minutes: 75\n    env:\n',
        '    timeout-minutes: 75\n    outputs:\n      matrix_sha256: ${{ steps.motion-probe.outputs.matrix_sha256 }}\n    env:\n', 1)
    build_steps = "      - name: Compile exact Linux motion probe for matrix job\n        id: motion-probe\n        run: |\n          set -euo pipefail\n          bash scripts/ci-tiering/linux-shared.sh matrix-build\n          digest=$(sha256sum \"$CARGO_TARGET_DIR/debug/matrix\" | cut -d' ' -f1)\n          [[ \"$digest\" =~ ^[0-9a-f]{64}$ ]] || { echo 'invalid matrix digest' >&2; exit 1; }\n          echo \"matrix_sha256=$digest\" >> \"$GITHUB_OUTPUT\"\n      - name: Transfer exact Linux motion probe\n        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02\n        with:\n          name: nvwa-linux-matrix-${{ github.run_attempt }}\n          path: ${{ github.workspace }}/target/debug/matrix\n          if-no-files-found: error\n          retention-days: 1\n"
    checks.assertEqual(shared_with_artifact.count('      - name: Report existing command timing\n'), 1)
    shared_with_artifact = shared_with_artifact.replace(
        '      - name: Report existing command timing\n',
        build_steps + '      - name: Report existing command timing\n', 1)
    matrix_job = "  linux-matrix:\n    name: Linux full motion matrix and real garment controls\n    needs: [classify, linux-shared]\n    runs-on: ubuntu-24.04\n    timeout-minutes: 75\n    env:\n      CARGO_BUILD_JOBS: '1'\n      CARGO_TARGET_DIR: ${{ github.workspace }}/target\n    steps:\n      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n        with:\n          persist-credentials: false\n      - name: Download exact Linux motion probe\n        uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093\n        with:\n          name: nvwa-linux-matrix-${{ github.run_attempt }}\n          path: ${{ github.workspace }}/target/debug\n      - name: Complete 594-frame matrix and real garment controls\n        timeout-minutes: 20\n        env:\n          EXPECTED_MATRIX_SHA256: ${{ needs.linux-shared.outputs.matrix_sha256 }}\n        run: bash scripts/ci-tiering/linux-matrix-run.sh\n      - name: Report existing command timing\n        if: ${{ always() }}\n        shell: bash\n        run: python3 -B scripts/ci-timing.py report\n"
    checks.assertEqual(job(workflow, 'linux-shared'), shared_with_artifact)
    checks.assertEqual(job(workflow, 'linux-matrix'), matrix_job)
    workflow = workflow.replace(matrix_job, '', 1).replace(shared_with_artifact, old_linux, 1)
    gate = job(workflow, 'required-gate')
    v8_needs = 'linux-shared, linux-matrix, linux-check, mac-smoke'
    checks.assertEqual(gate.count(v8_needs), 1)
    workflow = workflow.replace(gate, gate.replace(v8_needs, 'linux-shared, linux-check, mac-smoke', 1), 1)
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

V9_REPLACEMENTS = {
    "scripts/ci-tiering/policy.py": [
        (b"MAC_PARTS = ('workspace', 'bridges', 'mutation')\n", b"MAC_PARTS = ('workspace', 'bridges')\n"),
        (b"    expected = (['success'] * len(MAC_PARTS), ['skipped'] * len(MAC_PARTS)) if full == 'true' else (['skipped'] * len(MAC_PARTS), ['success'] * len(MAC_PARTS))\n", b"    expected = (['success'] * 2, ['skipped'] * 2) if full == 'true' else (['skipped'] * 2, ['success'] * 2)\n"),
    ],
    "scripts/ci-tiering/test_portable_split.py": [
        (b"        self.assertIn('    needs: ['+', '.join(required)+', mac-workspace-required, mac-bridges-required, mac-mutation-required]\\n', gate)\n", b"        self.assertIn('    needs: ['+', '.join(required)+', mac-workspace-required, mac-bridges-required]\\n', gate)\n"),
    ],
    "scripts/ci-tiering/test_policy.py": [
        (b"            for part in ('workspace', 'bridges'):\n", b"            for part in policy.MAC_PARTS:\n"),
        (b"            bridge = job((ROOT/'.github/workflows/ci.yml').read_text(), f'mac-bridges-{kind}')\n            self.assertIn(f'mac-mutation-{kind}', bridge)\n            self.assertIn('success() &&', bridge)\n", b""),
        (b"            'bridges': section('Check appearance quality and production acceptance bridges', 'Check B1 production-source mutation witnesses'),\n", b"            'bridges': section('Check appearance quality and production acceptance bridges', 'Execute the actual B1 continuous motion matrix'),\n"),
        (b"        mutation = section('Check B1 production-source mutation witnesses', 'Execute the actual B1 continuous motion matrix')\n", b""),
        (b"                condition = \"needs.classify.outputs.full_required == '\"+('true' if kind=='required' else 'false')+\"'\"\n                self.assertIn('    if: ${{ '+('success() && ' if part == 'bridges' else '')+condition+' }}\\n', lane)\n", b"                self.assertIn(\"    if: ${{ needs.classify.outputs.full_required == '\"+('true' if kind=='required' else 'false')+\"' }}\\n\", lane)\n"),
        (b"        self.assertIn('timeout-minutes: 12', mutation)\n        for kind in ('required', 'background'):\n            lane = job(workflow, f'mac-mutation-{kind}')\n            self.assertIn('    runs-on: macos-15\\n    timeout-minutes: 75\\n', lane)\n            self.assertIn('run: cargo test --workspace --lib --locked --offline --no-run', lane)\n            self.assertIn('timeout-minutes: 12', lane)\n            self.assertEqual(lane.count(mutation), 1)\n            self.assertNotIn('continue-on-error', lane)\n            self.assertNotIn('actions/cache/', lane)\n            self.assertNotIn(mutation, job(workflow, f'mac-bridges-{kind}'))\n", b"        self.assertIn('timeout-minutes: 12', expected['bridges'])\n"),
        (b"        self.assertIn('mac-workspace-required, mac-bridges-required, mac-mutation-required]', gate)\n", b"        self.assertIn('mac-workspace-required, mac-bridges-required]', gate)\n"),
        (b"            for part in (*expected, 'mutation'):\n", b"            for part in expected:\n"),
    ],
}

V8_REPLACEMENTS = {
    "scripts/ci-tiering/policy.py": [
        (b"REQUIRED = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-matrix', 'linux-check', 'mac-smoke', 'b1-source-regression')", b"REQUIRED = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-check', 'mac-smoke', 'b1-source-regression')"),
    ],
    "scripts/ci-tiering/test_portable_split.py": [
        (b"required = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-matrix', 'linux-check', 'mac-smoke', 'b1-source-regression')", b"required = ('classify', 'portable', 'portable-eye', 'linux-shared', 'linux-check', 'mac-smoke', 'b1-source-regression')"),
    ],
    "scripts/ci-tiering/test_policy.py": [
        (b"        self.assertNotIn('timeout-minutes: 20', workflow)\n", b"        self.assertIn('timeout-minutes: 20', workflow)\n"),
        (b"        self.assertIn('linux-shared, linux-matrix, linux-check, mac-smoke',\n                      job((ROOT / '.github/workflows/ci.yml').read_text(), 'required-gate'))", b"        self.assertIn('linux-shared, linux-check, mac-smoke',\n                      job((ROOT / '.github/workflows/ci.yml').read_text(), 'required-gate'))"),
        (b"        matrix = job((ROOT / '.github/workflows/ci.yml').read_text(), 'linux-matrix')\n        self.assertIn('    needs: [classify, linux-shared]\\n', matrix)\n        self.assertIn('    runs-on: ubuntu-24.04\\n    timeout-minutes: 75\\n', matrix)\n        self.assertIn(\"      CARGO_BUILD_JOBS: '1'\\n\", matrix)\n        self.assertIn('      - name: Complete 594-frame matrix and real garment controls\\n        timeout-minutes: 20\\n', matrix)\n        self.assertIn('run: bash scripts/ci-tiering/linux-matrix-run.sh\\n', matrix)\n        self.assertIn('actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093', matrix)\n        self.assertIn('EXPECTED_MATRIX_SHA256: ${{ needs.linux-shared.outputs.matrix_sha256 }}', matrix)\n        self.assertNotIn('continue-on-error', matrix)\n        self.assertNotIn('actions/cache/', matrix)\n        self.assertNotIn('run: bash scripts/ci-tiering/linux-shared.sh matrix\\n', workflow + check + matrix)\n        self.assertIn('bash scripts/ci-tiering/linux-shared.sh matrix-build\\n', workflow)\n        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', workflow)\n        self.assertIn('if-no-files-found: error', workflow)\n        self.assertIn('matrix_sha256: ${{ steps.motion-probe.outputs.matrix_sha256 }}', workflow)\n        source_linux = (HERE / 'linux-shared.sh').read_text()\n        self.assertEqual(source_linux.count('  matrix-build)\\n'), 1)\n        build_mode = source_linux.split('  matrix-build)\\n', 1)[1].split('  matrix)\\n', 1)[0]\n        self.assertIn('cargo fmt --manifest-path experiments/60-b1-continuous-motion/Cargo.toml', build_mode)\n        self.assertIn('cargo build --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --bins --locked --offline --features bevy/x11', build_mode)\n        old_matrix = source_linux.split('  matrix)\\n', 1)[1].split('    ;;\\n', 1)[0]\n        runtime = old_matrix[old_matrix.index('    python3 -B experiments/60-'):]\n        expected_runtime = ''.join(line[4:] if line.startswith('    ') else line for line in runtime.splitlines(keepends=True))\n        runner = (HERE / 'linux-matrix-run.sh').read_text()\n        self.assertIn('\"$(uname -s)\" == Linux', runner)\n        self.assertIn('Matrix artifact digest mismatch', runner)\n        self.assertEqual(runner.split('trap verify_lock EXIT\\n', 1)[1], expected_runtime + '\\n')\n        if sys.platform.startswith('linux'):\n            with tempfile.TemporaryDirectory() as temp:\n                binary = Path(temp) / 'debug/matrix'\n                binary.parent.mkdir()\n                binary.write_bytes(b'wrong-matrix-artifact')\n                env = dict(os.environ, CARGO_TARGET_DIR=temp, EXPECTED_MATRIX_SHA256='0' * 64)\n                result = subprocess.run(['bash', str(HERE / 'linux-matrix-run.sh')],\n                                        env=env, capture_output=True, text=True)\n                self.assertNotEqual(result.returncode, 0)\n                self.assertIn('Matrix artifact digest mismatch', result.stderr)\n\n", b""),
    ],
    "scripts/ci-tiering/linux-shared.sh": [
        (b"  matrix-build)\n    cargo fmt --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --package b1-continuous-probe --check\n    cargo build --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --bins --locked --offline --features bevy/x11\n    ;;\n", b""),
        (b"Usage: linux-shared.sh fetch|check|workspace|bridges|matrix-build|matrix", b"Usage: linux-shared.sh fetch|check|workspace|bridges|matrix"),
    ],
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
    for current, previous in V9_REPLACEMENTS.get(name, []):
        checks.assertEqual(data.count(current), 1, name)
        data = data.replace(current, previous, 1)
    for current, previous in V8_REPLACEMENTS.get(name, []):
        checks.assertEqual(data.count(current), 1, name)
        data = data.replace(current, previous, 1)
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
