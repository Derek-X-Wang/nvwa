"""Freeze a successful build and prepare a private bundle. Does not launch it."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil

root = Path(__file__).resolve().parents[2]
experiment = Path(__file__).resolve().parent
packet = root / '.work/m11-perf/native'
target = Path('/Users/derekxwang/Development/incubator/Nvwa/nvwa/target/release/nvwa-native-present-metrics')
baseline = root / 'dist/Nvwa.app/Contents/MacOS/Nvwa'
frozen = packet / 'frozen/nvwa-native-present-metrics'
bundle = packet / 'NvwaPresentMetrics.app'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assert 'Finished `release` profile' in (packet / 'build-attempt-1.log').read_text(), 'successful build log required'
assert sha(baseline) == '72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a'
assert json.loads((packet / 'accepted-inputs-comparison.json').read_text())['all_equal']
assert not frozen.exists() and not bundle.exists(), 'refuse overwrite'
frozen.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(target, frozen)
shutil.copytree(root / 'dist/Nvwa.app', bundle)
shutil.copy2(frozen, bundle / 'Contents/MacOS/Nvwa')
plist = bundle / 'Contents/Info.plist'
info = plistlib.loads(plist.read_bytes())
info.update({'CFBundleIdentifier':'dev.nvwa.perf.native-diagnostic', 'CFBundleName':'NvwaPresentMetrics', 'CFBundleDisplayName':'NvwaPresentMetrics'})
plist.write_bytes(plistlib.dumps(info))
inputs = {str(p.relative_to(root)): sha(p) for p in sorted(experiment.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
for name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','.work/m11-perf/measurement-contract.json','.work/m11-perf/input/character-loop.nvwa.json','.work/m11-perf/native/vendor-manifest.json','.work/m11-perf/native/dependency-comparison.json']:
    p=root/name
    if p.exists(): inputs[name]=sha(p)
result={'status':'BUILD-VERIFIED; RUNTIME-NOT-RUN','baseline':{'path':str(baseline),'sha256':sha(baseline)},'candidate':{'target':str(target),'frozen':str(frozen),'bundle':str(bundle),'bundle_executable':str(bundle/'Contents/MacOS/Nvwa'),'sha256':sha(frozen),'bytes':frozen.stat().st_size},'source_inputs_sha256':inputs,'helper':{'path':str(packet/'proc-memory'),'sha256':sha(packet/'proc-memory')},'bundle_assets_sha256':{str(p.relative_to(bundle)):sha(p) for p in sorted((bundle/'Contents/Resources').rglob('*')) if p.is_file()},'launches':0,'sole_Cargo_writer_lease':'returned after successful build; no GPU launches','clock_domains':['process_Instant','host_CLOCK_MONOTONIC_ns','Metal/CA_host_seconds','kernel_birth_unix_sec_usec','rusage_start_mach_abstime_ticks']}
(packet/'candidate-freeze.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:result[key] for key in ['status','candidate','helper','launches']},indent=2))
