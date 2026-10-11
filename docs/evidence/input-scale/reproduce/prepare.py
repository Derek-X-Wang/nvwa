"""Stage exact executed diagnostic wrapper around a matching built Web package."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--web-package', type=Path, default=ROOT / 'dist/web')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
source, output = a.web_package.resolve(), a.output.resolve()
if not output.is_relative_to(ROOT / '.work/input-scale'):
    p.error('output must be inside this checkout .work/input-scale')
if output == source or output.is_relative_to(source) or source.is_relative_to(output):
    p.error('source and output must be disjoint')
package = json.loads((HERE.parent / 'observer-package.json').read_text())
for name, sha in package['production_inputs'].items():
    if not (source / name).is_file() or hashlib.sha256((source / name).read_bytes()).hexdigest() != sha:
        p.error('source bytes do not match executed frozen package: ' + name)
if output.exists() and any(output.iterdir()):
    p.error('output must be empty; refusing to overwrite prior work')
output.mkdir(parents=True, exist_ok=True)
for name, sha in package['observer_files'].items():
    data = (HERE / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        p.error('executed observer bytes changed: ' + name)
    (output / name).write_bytes(data)
# Keep original assets/Works and runtime bytes; omit prior diagnostics and compressed HTML.
for name in ('nvwa_studio.js', 'nvwa_studio_bg.wasm', 'assets', 'works'):
    if not (source / name).exists():
        p.error('missing production package path: ' + name)
    (output / name).symlink_to(source / name, target_is_directory=(source / name).is_dir())
print('Prepared exact wrapper. Serve this directory on loopback; open /input-scale.html?work=works/m1-sequence.nvwa.json')
