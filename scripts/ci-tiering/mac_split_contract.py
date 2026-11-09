#!/usr/bin/env python3
"""Authenticate the Mac split and project only its exact delta to v3 contracts."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('mac-workspace-required', 'mac-bridges-required', 'mac-matrix-required', 'mac-workspace-background', 'mac-bridges-background', 'mac-matrix-background')
DIGESTS = {'mac-workspace-required': '94fd692fba003387136a650611a4a7f501d9008c309c1dffc9062153f9dfb75a', 'mac-bridges-required': '15f856a0cf9ea6477e643fd09d47ef6d815711156c287c7f06748bbb149d8f2b', 'mac-matrix-required': 'ce80925a2b90983f4c683608a7a03225d26e90d0389d1686b2b7a379ec30b43b', 'mac-workspace-background': 'f0ce39469c0b7c9c1706c4a9906b6b0961c13b22d36d27fd2cfdc694a8907405', 'mac-bridges-background': '90ed446058f91c44a3b43b966ec8095c1558c00e2558bfd61b377359d06c1609', 'mac-matrix-background': '1e3e044b116f871202f9d06f43ac02e63276833e5b1538cbc77b530833c76e0e'}
GOLD_SHA256 = '1098afb4969e9eda506dc2bf23062f0b272bd28b87bf4621c4bf8109ee52a52a'

def job(text, name):
    found = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', text)
    if len(found) != 1:
        raise AssertionError('Mac split job must be unique: '+name)
    return found[0]

def project(workflow, checks):
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

def project_input(name, checks, data):
    if name not in INPUTS:
        return data
    snapshot, current_sha, previous_sha = INPUTS[name]
    checks.assertEqual(hashlib.sha256(data).hexdigest(), current_sha, name)
    previous = (ROOT/'scripts/ci-tiering'/snapshot).read_bytes()
    checks.assertEqual(hashlib.sha256(previous).hexdigest(), previous_sha, snapshot)
    return previous
