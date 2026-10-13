"""Copy exact local crate and retain a reproducible minimal patch + hashes."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
experiment = Path(__file__).resolve().parent
original = Path('/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/wgpu-hal-29.0.4')
vendor = root / '.work/m11-perf/native/vendor/wgpu-hal-29.0.4'
if vendor.exists():
    raise SystemExit('Refuse existing vendor destination')
vendor.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(original, vendor)
source = original / 'src/metal/mod.rs'
old = source.read_text()
new = old.replace('mod time;\n', 'mod time;\nmod nvwa_probe;\n', 1)
new = new.replace('                cmd_buffer.raw.commit();', '                nvwa_probe::command(&cmd_buffer.raw, "submitted");\n                cmd_buffer.raw.commit();', 1)
new = new.replace('            if let Some(raw) = extra_command_buffer {\n                raw.commit();', '            if let Some(raw) = extra_command_buffer {\n                nvwa_probe::command(&raw, "internal_signal");\n                raw.commit();', 1)
new = new.replace('            // https://developer.apple.com/documentation/quartzcore/cametallayer/', '            nvwa_probe::present(&texture.drawable, self.shared.raw.device().currentAllocatedSize());\n            nvwa_probe::command(&command_buffer, "internal_present");\n\n            // https://developer.apple.com/documentation/quartzcore/cametallayer/', 1)
assert new != old and new.count('nvwa_probe::command(') == 3 and new.count('nvwa_probe::present(') == 1
(vendor / 'src/metal/mod.rs').write_text(new)
helper = (experiment / 'nvwa_probe.rs').read_text()
(vendor / 'src/metal/nvwa_probe.rs').write_text(helper)
patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/src/metal/mod.rs', tofile='b/src/metal/mod.rs'))
patch += ''.join(difflib.unified_diff([], helper.splitlines(True), fromfile='/dev/null', tofile='b/src/metal/nvwa_probe.rs'))
(experiment / 'wgpu-hal-metal-probe.patch').write_text(patch)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {'original_crate': str(original), 'vendor_crate': str(vendor), 'version': '29.0.4', 'original_files': {str(p.relative_to(original)): sha(p) for p in sorted(original.rglob('*')) if p.is_file()}, 'modified_files': {str(p.relative_to(vendor)): sha(p) for p in [vendor / 'src/metal/mod.rs', vendor / 'src/metal/nvwa_probe.rs']}, 'patch_sha256': sha(experiment / 'wgpu-hal-metal-probe.patch'), 'invariants': ['No Cargo.toml or Cargo feature changes in vendor crate', 'Only observers inserted before original submit/commit/present calls', 'Original command buffer ownership, fence handler, errors and returns retained', 'No GPU query/write/wait or new GPU resources', 'Enabled only with NVWA_METAL_PROBE=1', 'Callback indices bounded: first120 and every60 through1200']}
(root / '.work/m11-perf/native/vendor-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'vendor': str(vendor), 'patch_sha256': manifest['patch_sha256'], 'original_file_count': len(manifest['original_files'])}))
