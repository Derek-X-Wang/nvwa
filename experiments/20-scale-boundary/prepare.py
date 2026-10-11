"""Prepare a loopback-only wrapper around the existing production Web package."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--web-package', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
source = a.web_package.resolve()
output = a.output.resolve()
root = Path(__file__).resolve().parents[2]
allowed = root / '.work/input-scale/issue3'
if not output.is_relative_to(allowed):
    p.error(f'output must be within {allowed}')
if source == output or source.is_relative_to(output) or output.is_relative_to(source):
    p.error('source and output must be disjoint')
for name in ('index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm'):
    if not (source / name).is_file():
        p.error(f'missing production package file: {source / name}')
if output.exists() and any(output.iterdir()):
    p.error('output must be empty; refusing to replace an existing package')
output.mkdir(parents=True, exist_ok=True)
for child in source.iterdir():
    if child.name not in ('index.html', 'index.html.gz'):
        (output / child.name).symlink_to(child, target_is_directory=child.is_dir())
html = (source / 'index.html').read_text()
if html.count('</body>') != 1:
    p.error('production page must contain exactly one closing body tag')
(output / 'scale-collector.js').write_bytes((Path(__file__).parent / 'collector.js').read_bytes())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {'schema':'nvwa-scale-package-v1', 'production_package':str(source),
            'runtime':'unchanged production JS/Wasm; index adds passive collector only',
            'sha256':{name:sha(source/name) for name in ('index.html','nvwa_studio.js','nvwa_studio_bg.wasm')},
            'collector_sha256':sha(output/'scale-collector.js')}
(output / 'index.html').write_text(html.replace('</body>',
    '<script type="application/json" id="nvwa-scale-source">'+json.dumps(manifest)+'</script>'+
    '<script src="scale-collector.js"></script></body>'))
(output / 'probe-package.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
