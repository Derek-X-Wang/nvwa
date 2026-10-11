"""Stage a diagnostic page; root owns serving/copying it into the Web bundle."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', type=Path, default=ROOT / 'dist/web')
parser.add_argument('--output', type=Path, default=ROOT / '.work/input-scale/issue2')
args = parser.parse_args()
bundle = args.bundle.resolve()
output = args.output.resolve()
allowed = ROOT / '.work/input-scale/issue2'
if output != allowed and allowed not in output.parents:
    raise SystemExit('Output must remain inside .work/input-scale/issue2')
source = (bundle / 'index.html').read_text()
if source.count('</body>') != 1:
    raise SystemExit('Expected exactly one body closing tag')
artifacts = ['index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm']
hashes = {name: hashlib.file_digest((bundle / name).open('rb'), 'sha256').hexdigest() for name in artifacts}
output.mkdir(parents=True, exist_ok=True)
(output / 'recovery-capture.js').write_bytes(Path(__file__).with_name('capture.js').read_bytes())
(output / 'recovery.html').write_text(source.replace('</body>', '<script src="./recovery-capture.js"></script>\n</body>'))
(output / 'preparation.json').write_text(json.dumps({'bundle':str(bundle), 'sha256':hashes, 'productionChanged':False}, indent=2) + '\n')
print(f'STAGED {output}/recovery.html and recovery-capture.js')
print('Root must copy these two files beside the unchanged bundle index.html; start/serve remains root-owned.')
