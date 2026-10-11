"""Measure actual gzip transfer sizes; no performance inference from compilation."""
from pathlib import Path
import gzip
import json

root = Path(__file__).resolve().parent.parent
web = root / 'dist/web'
names = ['index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm', 'assets/fixtures/nvwa-humanoid.glb']
files = []
for name in names:
    data = (web / name).read_bytes()
    compressed = gzip.compress(data, mtime=0)
    (web / (name + '.gz')).write_bytes(compressed)
    files.append({'path': name, 'bytes': len(data), 'gzip_bytes': len(compressed)})
report = {'encoding': 'gzip, mtime=0', 'files': files, 'initial_gzip_bytes': sum(f['gzip_bytes'] for f in files)}
(web / 'size-report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
