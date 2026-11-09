#!/usr/bin/env python3
"""Conservative local-Git CI classification and fail-closed aggregate results."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"[0-9a-f]{40}\Z")
MAC = re.compile(r'macos|darwin|apple|appkit|cocoa|objc|metal|coregraphics|NSWindow|NSOpenPanel|NSSavePanel|target_family\s*=\s*"unix"|not\s*\(\s*target_arch\s*=\s*"wasm32"', re.I)
# Platform and unknown conditional compilation require full Mac. The exact
# cfg(test) attribute is platform-neutral and common in ordinary shared files.
TEST_ONLY = re.compile(r'#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]')
CONDITIONAL = re.compile(r'\bcfg(?:_attr)?\b|\bunix\b|target_(?:os|arch|family|vendor|env)', re.I)
REQUIRED = ('classify', 'portable', 'linux-shared', 'mac-smoke', 'b1-source-regression')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)


def parse_changes(raw):
    parts = raw.decode('utf-8', errors='strict').split('\0')
    if parts[-1] != '':
        raise ValueError('unterminated diff inventory')
    parts.pop()
    changes = []
    while parts:
        status = parts.pop(0)
        if not re.fullmatch(r'[AMDTUXB]|[RC][0-9]+', status):
            raise ValueError('unknown change status')
        count = 2 if status[0] in 'RC' else 1
        if len(parts) < count:
            raise ValueError('incomplete change inventory')
        paths = parts[:count]
        del parts[:count]
        if any(not p or p.startswith('/') or '..' in p.split('/') or any(ord(c) < 32 for c in p) for p in paths):
            raise ValueError('unsafe change path')
        changes.append((status, paths))
    return changes


def ordinary_path(path):
    # Unknown paths are intentionally full. Platform/build/policy paths never
    # become ordinary merely because their filenames contain "test" or "docs".
    name = Path(path).name
    if (name in ('Cargo.toml', 'Cargo.lock', 'build.rs', 'rust-toolchain', 'rust-toolchain.toml',
                 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock')
            or '.cargo' in path.split('/') or MAC.search(path)
            or path.startswith(('.github/', 'scripts/', 'vendor/'))):
        return False
    if path.startswith('docs/agents/') or path in ('AGENTS.md', 'rust-toolchain.toml'):
        return False
    if Path(path).suffix not in {'.rs', '.md', '.json', '.txt', '.toml', '.obj', '.mhclo',
                                 '.gz', '.target', '.macro', '.png', '.glb', '.gltf', '.bin',
                                 '.svg', '.webp', '.jpg', '.jpeg', '.license'}:
        return False
    return path.startswith(('assets/', 'examples/', 'docs/', 'crates/nvwa-core/', 'crates/nvwa-cli/', 'crates/nvwa-runtime/', 'crates/nvwa-b1-adapter/')) or path == 'README.md'


def classify(root, event_name, event):
    reasons = []
    if not isinstance(event, dict):
        event = {}
    if event_name != 'pull_request':
        return {'full_required': True, 'reasons': ['main push, release, manual or unknown event requires complete Mac'], 'head': event.get('after', '')}
    try:
        pr = event['pull_request']
        base, head = pr['base']['sha'], pr['head']['sha']
        if not SHA.fullmatch(base) or not SHA.fullmatch(head):
            raise ValueError('missing exact base/head identity')
        for commit in (base, head):
            git(root, 'cat-file', '-e', commit + '^{commit}')
        changes = parse_changes(git(root, 'diff', '--name-status', '-z', '--find-renames', base, head, '--'))
        if not changes:
            reasons.append('empty or ambiguous diff')
        for status, paths in changes:
            if status not in ('A', 'M'):
                reasons.append('rename/delete/nonordinary status: ' + status)
            for path in paths:
                if not ordinary_path(path):
                    reasons.append('platform/build/policy or unknown path: ' + path)
                # Reject symlinks, submodules and unexpected blob types even in
                # ordinary asset/doc paths. Do not follow a worktree link.
                for commit in (base, head):
                    entry = git(root, 'ls-tree', '-z', commit, '--', path)
                    if entry and not entry.startswith((b'100644 blob ', b'100755 blob ')):
                        reasons.append('nonregular source: ' + path)
                if path.startswith('crates/') and not path.endswith(('.rs', '.md', '.json')):
                    reasons.append('unknown shared input type: ' + path)
                if path.endswith('.rs'):
                    # Check both sides, not only added text: deleting a Mac guard
                    # is also a platform-sensitive change. Whole-file scanning is
                    # deliberately conservative for mixed-platform modules.
                    for commit in (base, head):
                        try:
                            data = git(root, 'show', commit + ':' + path).decode('utf-8', errors='strict')
                        except subprocess.CalledProcessError:
                            if (commit == base and status == 'A') or (commit == head and status == 'D'):
                                continue
                            raise
                        if MAC.search(data) or CONDITIONAL.search(TEST_ONLY.sub('', data)):
                            reasons.append('platform-sensitive source: ' + path)
                            break
        return {'full_required': bool(reasons), 'reasons': sorted(set(reasons)), 'base': base, 'head': head, 'changed_entries': len(changes)}
    except (KeyError, TypeError, ValueError, UnicodeError, OSError, subprocess.CalledProcessError) as error:
        return {'full_required': True, 'reasons': ['classification incomplete: ' + type(error).__name__], 'head': ''}


def check_gate(needs):
    failures = [name for name in REQUIRED if needs.get(name, {}).get('result') != 'success']
    full = needs.get('classify', {}).get('outputs', {}).get('full_required')
    if full not in ('true', 'false'):
        failures.append('invalid classification output')
    actual = needs.get('native-and-wasm', {}).get('result')
    if (full == 'true' and actual != 'success') or (full == 'false' and actual != 'skipped'):
        failures.append('complete Mac required result mismatch')
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['classify', 'gate', 'report'])
    args = parser.parse_args()
    if args.command == 'classify':
        try:
            event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        except (KeyError, OSError, ValueError):
            event = {}
        result = classify(ROOT, os.environ.get('GITHUB_EVENT_NAME', ''), event)
        value = str(result['full_required']).lower()
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as out:
            out.write('full_required=' + value + '\n')
        print(json.dumps(result))
    else:
        needs = json.loads(os.environ.get('TIER_NEEDS', '{}'))
        if args.command == 'gate':
            failures = check_gate(needs)
            if failures:
                raise SystemExit('Required CI incomplete: ' + ', '.join(failures))
            print('Required checks passed for this exact workflow identity.')
        else:
            lines = ['## Complete Mac evidence', '', 'This report never converts a failure/timeout into a pass.']
            results = [needs.get(name, {}).get('result', 'missing') for name in ('native-and-wasm', 'mac-full-background')]
            bad = sorted(results) != ['skipped', 'success']
            for name in ('native-and-wasm', 'mac-full-background'):
                status = needs.get(name, {}).get('result', 'missing')
                lines.append(f'- {name}: **{status}**')
                bad |= status not in ('success', 'skipped')
            with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as out:
                out.write('\n'.join(lines) + '\n')
            if bad:
                print('::error::Complete Mac failed, cancelled or missing. Inspect this run; release evidence remains incomplete.')
                raise SystemExit(1)


if __name__ == '__main__':
    main()
