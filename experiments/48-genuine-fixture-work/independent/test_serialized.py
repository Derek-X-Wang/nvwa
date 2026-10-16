"""Mutation red/restored green at the actual serialized artifact checker boundary."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import tempfile
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_serialized', HERE / 'check_serialized.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def read_glb(path):
    b = path.read_bytes()
    n = struct.unpack_from('<I', b, 12)[0]
    return (json.loads(b[20:20 + n]), bytearray(b[28 + n:]))

def write_glb(path, j, b):
    raw = json.dumps(j, separators=(',', ':'), allow_nan=False).encode()
    raw += b' ' * (-len(raw) % 4)
    b = bytes(b)
    b += b'\x00' * (-len(b) % 4)
    path.write_bytes(struct.pack('<III', 1179937895, 2, 28 + len(raw) + len(b)) + struct.pack('<II', len(raw), 1313821514) + raw + struct.pack('<II', len(b), 5130562) + b)

def load(p):
    return json.loads(p.read_text())

def save(p, j):
    p.write_text(json.dumps(j, indent=2, allow_nan=False) + '\n')

def run(root):
    oracle = m.Oracle(root)
    source = root / 'experiments/48-genuine-fixture-work/artifacts'
    results = []
    with tempfile.TemporaryDirectory(prefix='nvwa48-independent-') as temp:
        directory = Path(temp) / 'artifacts'
        shutil.copytree(source, directory)
        baseline = {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        glb = directory / 'assets/generated/genuine44-calibrated47.glb'

        def restore():
            for p, b in baseline.items():
                (directory / p).write_bytes(b)

        def sync_bindings():
            profile = load(directory / 'character.profile.json')
            profile['asset_sha256'] = m.sha(glb)
            save(directory / 'character.profile.json', profile)
            work = load(directory / 'genuine44-calibrated47.nvwa.json')
            work['profile'] = copy.deepcopy(profile)
            save(directory / 'genuine44-calibrated47.nvwa.json', work)
            ledger = load(directory / 'transformation-ledger.json')
            for rel in ledger['outputs']:
                p = directory / rel
                ledger['outputs'][rel] = {'sha256': m.sha(p), 'bytes': p.stat().st_size}
            save(directory / 'transformation-ledger.json', ledger)

        def rejected(name, change, reason, bind=False):
            restore()
            change()
            if bind:
                sync_bindings()
            try:
                oracle.check_artifacts(directory)
            except m.Rejected as e:
                m.need(reason in str(e), name + ' reached wrong boundary: ' + str(e))
                error = str(e)
            else:
                raise RuntimeError(name + ' survived real checker')
            restore()
            oracle.check_artifacts(directory)
            results.append({'control': name, 'mutant': 'REJECTED', 'boundary': error, 'restored': 'PASS'})

        def glb_change(fn):
            j, b = read_glb(glb)
            fn(j, b)
            write_glb(glb, j, b)

        def json_change(rel, fn):
            p = directory / rel
            j = load(p)
            fn(j)
            save(p, j)

        def output_offset(j, path='rotation', node=17):
            clip = j['animations'][3]
            ch = next((c for c in clip['channels'] if c['target'] == {'node': node, 'path': path}))
            a = j['accessors'][clip['samplers'][ch['sampler']]['output']]
            v = j['bufferViews'][a['bufferView']]
            return v.get('byteOffset', 0) + a.get('byteOffset', 0)

        def root_height(j, b):
            p = output_offset(j, 'translation')
            v = struct.unpack_from('<f', b, p + 4)[0]
            struct.pack_into('<f', b, p + 4, v + 0.988)

        def q_order(j, b):
            p = output_offset(j)
            v = list(struct.unpack_from('<4f', b, p))
            v[2], v[3] = (v[3], v[2])
            struct.pack_into('<4f', b, p, *v)

        def sample_index(j, b):
            p = output_offset(j, node=4)
            b[p:p + 16] = b[p + 16:p + 32]

        def side_swap(j, b):
            for c in j['animations'][3]['channels']:
                if c['target']['path'] == 'rotation' and c['target']['node'] in (4, 7):
                    c['target']['node'] = 11 - c['target']['node']

        def wrong_root(j, b):
            for c in j['animations'][3]['channels']:
                if c['target']['path'] == 'translation':
                    c['target']['node'] = 23

        def accessor(j):
            return j['accessors'][j['animations'][3]['samplers'][0]['output']]

        def time_last(j, b):
            a = j['accessors'][j['animations'][3]['samplers'][0]['input']]
            v = j['bufferViews'][a['bufferView']]
            p = v.get('byteOffset', 0) + a.get('byteOffset', 0) + 89 * 4
            struct.pack_into('<f', b, p, 3.0)

        def nonfinite(j, b):
            struct.pack_into('<f', b, output_offset(j), float('nan'))

        def hemisphere(j, b):
            p = output_offset(j)
            v = struct.unpack_from('<4f', b, p + 16)
            struct.pack_into('<4f', b, p + 16, *[-x for x in v])
        cases = [('wrong-root23', wrong_root, 'exact targets/root17'), ('double-root-exporter-height', root_height, 'root translation'), ('physical-side-exchange', side_swap, 'rotation frame'), ('quaternion-XYWZ', q_order, 'rotation frame'), ('wrong-sample-index', sample_index, 'rotation frame'), ('old-BIN-byte', lambda j, b: b.__setitem__(0, b[0] ^ 1), 'old BIN exact prefix'), ('old-animation-value', lambda j, b: j['animations'][0].__setitem__('name', 'changed'), 'old animations preserved'), ('old-node-bool-type', lambda j, b: j['nodes'][0]['translation'].__setitem__(0, False), 'old JSON nodes'), ('framecount91', lambda j, b: accessor(j).__setitem__('count', 91), '90 samples'), ('framecount-bool', lambda j, b: accessor(j).__setitem__('count', True), '90 samples'), ('out-of-view', lambda j, b: accessor(j).__setitem__('byteOffset', 9999996), 'accessor bounds'), ('misaligned-accessor', lambda j, b: accessor(j).__setitem__('byteOffset', 1), 'accessor alignment'), ('invented-last-frame', time_last, 'exact binary32 time keys'), ('nonfinite-channel', nonfinite, 'accessor finite'), ('discontinuous-q-sign', hemisphere, 'hemisphere continuity'), ('forged-clip-authored', lambda j, b: j['animations'][3]['extras'].__setitem__('provenance_kind', 'authored'), 'clip genuine provenance'), ('root-bool-type', lambda j, b: j['animations'][3]['channels'][0]['target'].__setitem__('node', False), 'index type/bounds')]
        for name, fn, reason in cases:
            rejected(name, lambda fn=fn: glb_change(fn), reason, True)
        ledger_cases = [('wrong-admission', lambda j: j.__setitem__('admission_sha256', '0' * 64), 'ledger admission_sha256'), ('wrong-calibration', lambda j: j.__setitem__('calibration_sha256', '0' * 64), 'ledger calibration_sha256'), ('wrong-source-receipt', lambda j: j['source_generation'].__setitem__('receipt_sha256', '0' * 64), 'source genuine receipt identity'), ('wrong-raw-hash', lambda j: j['source_generation']['raw_sha256'].__setitem__(next(iter(j['source_generation']['raw_sha256'])), '0' * 64), 'genuine raw hash binding'), ('forged-ai-provenance', lambda j: j.__setitem__('provenance_kind', 'authored'), 'genuine experimental provenance'), ('wrong-exporter-identity', lambda j: j.__setitem__('exporter_sha256', '0' * 64), 'actual exporter identity'), ('new-generation-forged', lambda j: j['transformation'].__setitem__('new_generation', True), 'separate generation/transformation')]
        for name, fn, reason in ledger_cases:
            rejected(name, lambda fn=fn: json_change('transformation-ledger.json', fn), reason)
        rejected('authored-wave-fallback', lambda: json_change('genuine44-calibrated47.nvwa.json', lambda j: j['timeline'][0].__setitem__('clip_id', 'wave')), 'explicit clip3 entry')
        rejected('profile-wrong-clip-index', lambda: json_change('character.profile.json', lambda j: j['clips'][3].__setitem__('animation_index', 2)), 'profile old values and clip3')
        rejected('whole-Work-profile-mismatch', lambda: json_change('genuine44-calibrated47.nvwa.json', lambda j: j['profile'].__setitem__('asset_sha256', '0' * 64)), 'whole Work embedded profile')
        rejected('timeline-loop-bool-type', lambda: json_change('genuine44-calibrated47.nvwa.json', lambda j: j['timeline'][0].__setitem__('looping', 0)), 'explicit clip3 entry')
        mini = Path(temp) / 'source-root'
        for rel in list(oracle.pins) + ['experiments/48-genuine-fixture-work/export.py']:
            p = mini / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / rel, p)
        for rel in ('experiments/44-approved-cpu-motion-trial/evidence/run/raw/root_positions.f32', 'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json', 'experiments/48-genuine-fixture-work/admission.json', 'experiments/47-fixture-rig-calibration/calibration.json'):
            p = mini / rel
            original = p.read_bytes()
            p.write_bytes(original + b' ')
            try:
                m.Oracle(mini)
            except m.Rejected as e:
                m.need('pinned input' in str(e), 'source pin boundary')
                error = str(e)
            else:
                raise RuntimeError('source pin mutation survived')
            p.write_bytes(original)
            m.Oracle(mini)
            results.append({'control': 'pinned-source:' + rel, 'mutant': 'REJECTED', 'boundary': error, 'restored': 'PASS'})
        restore()
        positive = oracle.check_artifacts(directory)
    return {'status': 'PASS', 'optimized_python': not __debug__, 'negative_controls': len(results), 'restored_green_checks': len(results), 'controls': results, 'baseline': positive}
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=HERE.parents[2])
    args = parser.parse_args()
    print(json.dumps(run(args.root), indent=2, sort_keys=True))
