"""Bound a future root-authorized reference run; never fetch/install/change host state."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    resources = a.out.resolve() / 'blender-user'
    extension = resources / 'extensions/user_default/mpfb'
    extension.parent.mkdir(parents=True)
    extension.symlink_to((a.stage / 'mpfb-addon').resolve(), target_is_directory=True)
    command = [str(a.executable.resolve()), '--background', '--factory-startup', '--offline-mode',
               '--threads', '1', '--python-exit-code', '7', '--python',
               str(Path(__file__).with_name('blender_reference.py').resolve()), '--',
               '--addon', str((a.stage / 'mpfb-addon').resolve()), '--garment',
               str((a.stage / 'system-assets/clothes/female_sportsuit01/female_sportsuit01.mhclo').resolve()),
               '--inputs', str(a.inputs.resolve()), '--out', str(a.out.resolve() / 'reference')]
    env = dict(os.environ, BLENDER_USER_RESOURCES=str(resources), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    start = time.monotonic()
    with (a.out / 'stdout.log').open('wb') as stdout, (a.out / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr)
        timed_out = False
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            code = 124
    receipt = dict(command=command, elapsed_seconds=time.monotonic() - start,
                   exit_code=code, timed_out=timed_out, owned_pid=process.pid,
                   no_render_requested=True, declared_threads=1,
                   original_reference_status='CHECK reference/summary.json; process exit alone is not proof')
    (a.out / 'execution.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    return code


if __name__ == '__main__':
    sys.exit(main())
