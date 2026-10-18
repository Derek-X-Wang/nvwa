#!/usr/bin/env python3
"""Root-owned offline build/export; Web and native receipts are separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / 'experiments/65-b1-appearance-quality/preview'
MANIFEST = EXPERIMENT / 'Cargo.toml'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_closure():
    files = [ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml', ROOT/'docs/evidence/b1-motion/web-edited.nvwa.json', ROOT/'experiments/60-b1-continuous-motion/checker.py', ROOT/'experiments/60-b1-continuous-motion/geometry.py']
    for directory in ['crates', 'vendor', 'assets', 'scripts', 'web']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts) & {'target', '__pycache__'})
    # Result prose/images can be added after the build; compiled/verification inputs freeze here.
    files.extend(p for p in (ROOT/'experiments/62-b1-appearance-preview/assets').rglob('*') if p.is_file())
    files += [EXPERIMENT/name for name in ['Cargo.toml', 'Cargo.lock', 'index.html']]
    files += [EXPERIMENT.parent/'quality.rs', EXPERIMENT/'works/b1-quality-none.nvwa.json']
    for directory in ['src', 'assets', 'tools', 'build', 'asset-tests']:
        files.extend(p for p in (EXPERIMENT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files)) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--wasm-bindgen', type=Path, required=True)
    parser.add_argument('--target-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    target = args.target_dir.resolve()  # root chooses the serialized shared/disposable target
    env = dict(os.environ, CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS='1', CARGO_NET_OFFLINE='true')
    before = source_closure()
    (output/'source-closure.json').write_text(json.dumps(before, indent=2)+'\n')

    def run(command, label):
        print(f'START {label}', flush=True)
        with (output/(label+'.log')).open('w') as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                log.write(line); log.flush(); print(line, end='', flush=True)
            status = process.wait()
        if status:
            raise SystemExit(f'{label} failed exit {status}')
        print(f'PASS {label}', flush=True)

    run(['rustfmt','--edition','2024','--check',str(EXPERIMENT.parent/'quality.rs'),*[str(p) for p in sorted((EXPERIMENT/'src').rglob('*.rs'))]], 'format')
    run(['cargo','build','--manifest-path',str(MANIFEST),'--lib','--target','wasm32-unknown-unknown','--locked','--offline'], 'web-build')
    site = output/'web'
    (site/'pkg').mkdir(parents=True)
    run([str(args.wasm_bindgen),'--target','web','--out-dir',str(site/'pkg'),str(target/'wasm32-unknown-unknown/debug/b1_appearance_quality_preview.wasm')], 'web-bindgen')
    shutil.copy2(EXPERIMENT/'index.html',site/'index.html')
    shutil.copytree(ROOT/'assets',site/'assets')
    (site/'works').mkdir()
    shutil.copy2(EXPERIMENT/'works/b1-quality-none.nvwa.json',site/'works/b1-quality-none.nvwa.json')
    if source_closure() != before:
        raise SystemExit('source closure changed during Web build')
    (output/'web-build-receipt.json').write_text(json.dumps({'scope':'Web compilation and export only; browser/functional/native/performance validation separate','sources':before,'artifacts':{str(p.relative_to(site)):sha(p) for p in site.rglob('*') if p.is_file()}},indent=2)+'\n')
    print('WEB_EXPORT_READY '+str(site),flush=True)
    run(['cargo','build','--manifest-path',str(MANIFEST),'--bins','--locked','--offline'], 'native-build')
    run(['cargo','test','--manifest-path',str(MANIFEST),'--lib','--locked','--offline'], 'native-unit-tests')
    native=output/'native';native.mkdir()
    bins=list((EXPERIMENT/'src/bin').glob('*.rs')) if (EXPERIMENT/'src/bin').is_dir() else []
    names=[p.stem for p in bins]
    if (EXPERIMENT/'src/main.rs').is_file():names.append('b1-appearance-quality-preview')
    if not names:raise SystemExit('no native binary source was declared')
    for name in names:shutil.copy2(target/'debug'/name,native/name)
    if source_closure() != before:raise SystemExit('source closure changed during native build')
    (output/'native-build-receipt.json').write_text(json.dumps({'scope':'Native compilation only; Python controls and Web functional proof recorded separately; native visible launch/GUI remain NOT-RUN','sources':before,'artifacts':{str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file()}},indent=2)+'\n')
    print('ALL_BUILD_EXPORTS_READY',flush=True)

if __name__=='__main__':main()
