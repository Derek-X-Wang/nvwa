"""Stage a frozen, early-hook diagnostic package; never build or modify product files."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def prepare(bundle, output):
    bundle, output = bundle.resolve(), output.resolve()
    if not output.is_relative_to(ROOT / '.work/bounded-scale-ime/issue32'):
        raise ValueError('output must stay inside .work/bounded-scale-ime/issue32')
    if output == bundle or output.is_relative_to(bundle) or bundle.is_relative_to(output):
        raise ValueError('source/output must be disjoint')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output must be empty; refusing to replace prior evidence')
    source_manifest = ROOT / 'docs/evidence/m1-1-ui/build/build-inputs-final-after.json'
    frozen_sources = json.loads(source_manifest.read_text())['files']
    for name, record in frozen_sources.items():
        if sha(ROOT / name) != record['sha256']:
            raise ValueError('source differs from frozen accepted build cohort: ' + name)
    package_manifest = ROOT / 'docs/evidence/input-scale/observer-package.json'
    frozen_package = json.loads(package_manifest.read_text())['production_inputs']
    for name, expected in frozen_package.items():
        if sha(bundle / name) != expected:
            raise ValueError('production package differs from frozen accepted bytes: ' + name)
    build_manifest = ROOT / 'docs/evidence/m1-1-ui/build/web-final-build.json'
    build_files = json.loads(build_manifest.read_text())['files']
    for name in build_files:
        if sha(bundle / name) != build_files[name]['sha256']:
            raise ValueError('build package member differs: ' + name)
    source = (bundle / 'index.html').read_text()
    if source.count('<head>') != 1 or source.count('<script type="module">') != 1:
        raise ValueError('unexpected production HTML script structure')
    hook = '<script src="./ime-provenance.js" data-page-kind="nvwa" data-early="before-production-module"></script>'
    wrapper = source.replace('<head>', '<head>\n' + hook, 1)
    wrapper = wrapper.replace('<script type="module">', '<script>window.nvwaImeProvenance.noteProductionModuleStart();</script>\n  <script type="module">', 1)
    if wrapper.index(hook) > wrapper.index('<script type="module">'):
        raise ValueError('hook must be parsed before production module')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'ime-nvwa.html').write_text(wrapper)
    (output / 'ime-provenance.js').write_bytes((HERE / 'collector.js').read_bytes())
    for kind, name in [('plain-textarea','ime-plain.html'),('synthetic-selftest','ime-selftest.html')]:
        label = 'Plain textarea physical IME control' if kind == 'plain-textarea' else 'SYNTHETIC SELFTEST ONLY'
        html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{label}</title>
<script src="./ime-provenance.js" data-page-kind="{kind}" data-early="before-production-module"></script>
<style>body{{font:18px system-ui;padding:24px;background:#eef3f5}}textarea{{width:70%;height:160px;font:24px system-ui}}p{{max-width:760px}}</style></head>
<body><h1>{label}</h1><p>Start case, click this textarea, compose with the selected OS input method, stop, then export. Trace stores event lengths only. Reset does not clear the textarea.</p>
<textarea id="ime-control" aria-label="Owned plain textarea IME control" autocomplete="off" spellcheck="false"></textarea></body></html>\n'''
        (output / name).write_text(html)
    # Immutable staged copies avoid serving a later-mutated symlinked JS/Wasm cohort.
    import shutil
    for name in ('nvwa_studio.js','nvwa_studio_bg.wasm','assets','works'):
        path = bundle / name
        if path.is_dir(): shutil.copytree(path, output / name)
        else: shutil.copyfile(path, output / name)
    manifest = {'schema':1,'purpose':'issue32 early provenance comparison',
        'sourceManifestSha256':sha(source_manifest),'sourceInputs':frozen_sources,
        'priorPackageManifestSha256':sha(package_manifest),'buildManifestSha256':sha(build_manifest),
        'productionInputs':frozen_package,'diagnostics':{name:sha(output/name) for name in ('ime-nvwa.html','ime-plain.html','ime-selftest.html','ime-provenance.js')},
        'runtimeCopies':{name:sha(output/name) for name in ('nvwa_studio.js','nvwa_studio_bg.wasm')},
        'earlyHook':'synchronous classic head script before production module', 'productionChanged':False}
    (output / 'preparation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('STAGED', output)
    print('manifest sha256', sha(output / 'preparation.json'))
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT/'dist/web')
    parser.add_argument('--output', type=Path, default=ROOT/'.work/bounded-scale-ime/issue32/package')
    args = parser.parse_args()
    try: prepare(args.bundle, args.output)
    except (ValueError, OSError, KeyError) as error: parser.error(str(error))
