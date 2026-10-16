"""Independent bounded raw44 -> serialized glTF oracle. Stdlib only."""
import argparse, copy, hashlib, json, math, platform, struct
from pathlib import Path

class Rejected(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise Rejected(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def exact(a, b):
    """JSON equality including scalar types and object insertion order."""
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return list(a) == list(b) and all((exact(a[k], b[k]) for k in a))
    if type(a) is list:
        return len(a) == len(b) and all((exact(x, y) for x, y in zip(a, b)))
    if type(a) is float:
        return struct.pack('<d', a) == struct.pack('<d', b)
    return a == b

def json_pairs(items):
    out = {}
    for key, value in items:
        need(key not in out, 'duplicate JSON key')
        out[key] = value
    return out

def strict_json(path):

    def pairs(items):
        d = {}
        for k, v in items:
            need(k not in d, 'duplicate JSON key')
            d[k] = v
        return d

    def bad(s):
        raise Rejected('nonfinite JSON: ' + s)
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=bad)

def finite(x):
    return type(x) in (int, float) and math.isfinite(x)

def vec(v, n):
    need(type(v) is list and len(v) == n and all((finite(x) for x in v)), 'finite vector shape/type')
    return v

def index(x, n):
    need(type(x) is int and 0 <= x < n, 'index type/bounds')
    return x

def dot(a, b):
    return sum((x * y for x, y in zip(a, b)))

def add(a, b):
    return [x + y for x, y in zip(a, b)]

def sub(a, b):
    return [x - y for x, y in zip(a, b)]

def mul(a, s):
    return [x * s for x in a]

def unit(a):
    n = math.sqrt(dot(a, a))
    need(n > 1e-12, 'singular normalization')
    return mul(a, 1 / n)

def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

def transpose(a):
    return [list(x) for x in zip(*a)]

def mm(a, b):
    return [[dot(row, col) for col in zip(*b)] for row in a]

def mv(a, b):
    return [dot(row, b) for row in a]

def qm(a, b):
    av, bv = (a[:3], b[:3])
    return add(add(mul(bv, a[3]), mul(av, b[3])), cross(av, bv)) + [a[3] * b[3] - dot(av, bv)]

def qi(q):
    return [-q[0], -q[1], -q[2], q[3]]

def qn(q):
    return unit(vec(list(q), 4))

def qr(q):
    x, y, z, w = qn(q)
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]

def rq(m):
    d = [1 + m[0][0] - m[1][1] - m[2][2], 1 - m[0][0] + m[1][1] - m[2][2], 1 - m[0][0] - m[1][1] + m[2][2], 1 + m[0][0] + m[1][1] + m[2][2]]
    k = max(range(4), key=d.__getitem__)
    v = math.sqrt(max(0, d[k])) / 2
    need(v > 1e-12, 'rotation conversion')
    if k == 3:
        q = [(m[2][1] - m[1][2]) / (4 * v), (m[0][2] - m[2][0]) / (4 * v), (m[1][0] - m[0][1]) / (4 * v), v]
    else:
        i = k
        j = (i + 1) % 3
        l = (i + 2) % 3
        q = [0.0] * 4
        q[i] = v
        q[j] = (m[i][j] + m[j][i]) / (4 * v)
        q[l] = (m[i][l] + m[l][i]) / (4 * v)
        q[3] = (m[l][j] - m[j][l]) / (4 * v)
    return qn(q)

def frame(axis, guide):
    x = unit(axis)
    y = unit(sub(guide, mul(x, dot(x, guide))))
    return transpose([x, y, cross(x, y)])

def inverse(m):
    cols = [cross(m[1], m[2]), cross(m[2], m[0]), cross(m[0], m[1])]
    det = dot(m[0], cols[0])
    need(abs(det) > 1e-12, 'singular affine')
    return [[x / det for x in r] for r in transpose(cols)]
I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
EPS = 2 ** (-24)
# Frozen before output exposure: eight binary32 ulps at unit magnitude.
# Includes independent f64 operation ordering, normalization and f32 rounding.
Q_TOL = 8 * EPS
R_TOL = 32 * EPS

class GLB:

    def __init__(self, path):
        self.path = Path(path)
        data = self.path.read_bytes()
        need(len(data) >= 28, 'GLB short')
        magic, version, total = struct.unpack_from('<III', data)
        need((magic, version, total) == (1179937895, 2, len(data)), 'GLB header')
        chunks = []
        pos = 12
        while pos < len(data):
            need(pos + 8 <= len(data), 'chunk header')
            n, t = struct.unpack_from('<II', data, pos)
            pos += 8
            need(n % 4 == 0 and pos + n <= len(data), 'chunk bounds/alignment')
            chunks.append((t, data[pos:pos + n]))
            pos += n
        need([t for t, b in chunks] == [1313821514, 5130562], 'exact JSON/BIN chunks')
        self.j = json.loads(chunks[0][1], object_pairs_hook=json_pairs, parse_constant=lambda s: (_ for _ in ()).throw(Rejected('nonfinite GLB JSON')))
        self.bin = chunks[1][1]
        need(type(self.j.get('buffers')) is list and len(self.j['buffers']) == 1 and ('uri' not in self.j['buffers'][0]), 'one embedded buffer')
        n = self.j['buffers'][0]['byteLength']
        need(type(n) is int and n <= len(self.bin) and (len(self.bin) - n <= 3), 'buffer length')

    def accessor(self, i, kind):
        j = self.j
        a = j['accessors'][index(i, len(j['accessors']))]
        need(type(a) is dict and a.get('componentType') == 5126 and (a.get('type') == kind) and ('sparse' not in a) and (a.get('normalized', False) is False), 'float accessor representation')
        n = a.get('count')
        need(type(n) is int and n == 90, '90 samples')
        v = j['bufferViews'][index(a.get('bufferView'), len(j['bufferViews']))]
        need(v.get('buffer') == 0 and type(v.get('buffer')) is int, 'view buffer')
        width = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[kind]
        stride = v.get('byteStride', 4 * width)
        off = a.get('byteOffset', 0)
        start = v.get('byteOffset', 0)
        length = v.get('byteLength')
        need(all((type(x) is int for x in [stride, off, start, length])), 'accessor integer types')
        need(off >= 0 and start >= 0 and (length >= 0) and (4 * width <= stride <= 252) and (stride % 4 == 0) and (off % 4 == 0) and (start % 4 == 0), 'accessor alignment')
        need(off + (n - 1) * stride + 4 * width <= length and start + length <= j['buffers'][0]['byteLength'], 'accessor bounds')
        out = [list(struct.unpack_from('<' + 'f' * width, self.bin, start + off + k * stride)) for k in range(n)]
        need(all((all((finite(x) for x in row)) for row in out)), 'accessor finite')
        return out

def hierarchy(nodes):
    parents = [-1] * len(nodes)
    for p, n in enumerate(nodes):
        for c in n.get('children', []):
            c = index(c, len(nodes))
            need(parents[c] == -1, 'multiple parents')
            parents[c] = p
    for i in range(len(nodes)):
        seen = set()
        p = i
        while p != -1:
            need(p not in seen, 'hierarchy cycle')
            seen.add(p)
            p = parents[p]
    return parents

def world(nodes, parents, rotations=None, translation=None):
    rotations = rotations or {}
    out = {}

    def visit(i):
        if i in out:
            return out[i]
        n = nodes[i]
        need('matrix' not in n, 'TRS only exact fixture')
        r = qr(rotations.get(i, n.get('rotation', [0, 0, 0, 1])))
        s = vec(n.get('scale', [1, 1, 1]), 3)
        a = [[r[k][c] * s[c] for c in range(3)] for k in range(3)]
        t = vec(translation if i == 17 and translation is not None else n.get('translation', [0, 0, 0]), 3)
        if parents[i] != -1:
            pa, pt = visit(parents[i])
            a, t = (mm(pa, a), add(mv(pa, t), pt))
        out[i] = (a, t)
        return out[i]
    for i in range(len(nodes)):
        visit(i)
    return out

class Oracle:

    def __init__(self, root):
        self.root = Path(root)
        r = self.root
        self.cal = strict_json(r / 'experiments/47-fixture-rig-calibration/calibration.json')
        self.contract = strict_json(r / 'experiments/48-genuine-fixture-work/CONTRACT.json')
        self.admission = strict_json(r / 'experiments/48-genuine-fixture-work/admission.json')
        pins = {'experiments/48-genuine-fixture-work/admission.json': '94676288d6e3f22886e4b08512aa9094e6e18cf21d50eac1d52e711d1cb365d6', 'experiments/48-genuine-fixture-work/CONTRACT.json': '58e82af4ab212627844a80a5279e855d5d3b67a535a586e930e3983c5a8d0b26', 'experiments/47-fixture-rig-calibration/calibration.json': 'd730f372adc92d83931c23da84d8709dd8bfa7eb75d57964817577f4b034a6d0', 'experiments/47-fixture-rig-calibration/calibrate.py': '15f620bb1ceabb4d6d32a398b284b28657e2ac7244a04eca0ca945618d4e1eca', 'experiments/47-fixture-rig-calibration/SHA256SUMS.json': 'b4fbb24bffcaf8c061d2b9acd6abf046dd90fd07c013f5f8551c6693575a2957'}
        pins.update(self.cal['input_sha256'])
        pins['assets/character.profile.json'] = 'b7604ebdfb8b090073adead456f78fbf09779c23823b419986e57159bd9e0353'
        for p, h in pins.items():
            need(sha(r / p) == h, 'pinned input ' + p)
        self.pins = pins
        self.source = strict_json(r / 'experiments/41-real-short-motion/source-skeleton.json')
        s = self.source
        self.names = s['joint_names']
        self.sp = s['parents']
        need(len(self.names) == 30 and len(set(self.names)) == 30 and (len(self.sp) == 30), 'SOMA30 shape')
        self.si = {n: i for i, n in enumerate(self.names)}
        self.original = GLB(r / 'assets/fixtures/nvwa-humanoid.glb')
        self.nodes = self.original.j['nodes']
        self.parents = hierarchy(self.nodes)
        self.ni = {n['name']: i for i, n in enumerate(self.nodes)}
        need(self.parents[16] == 17 and self.parents[17] == 23, 'exact pelvis/root ancestry')
        need(self.nodes[23] == {'children': [18, 19, 20, 21, 22, 17], 'name': 'Nvwa humanoid rig'}, 'identity nonjoint ancestor')
        self.bindq = {}
        self.bindpos = {}

        def sb(i):
            if i in self.bindpos:
                return
            p = self.sp[i]
            need(type(p) is int and -1 <= p < i, 'source topological parents')
            q = qn(s['rest_local_rotations_xyzw'][i])
            t = vec(s['rest_local_translations'][i], 3)
            need(s['rest_local_scales'][i] == [1, 1, 1], 'source unit scale')
            if p != -1:
                sb(p)
                t = add(self.bindpos[p], mv(qr(self.bindq[p]), t))
                q = qm(self.bindq[p], q)
            self.bindpos[i] = t
            self.bindq[i] = qn(q)
        for i in range(30):
            sb(i)
        self.tg = {}

        def tq(i):
            if i not in self.tg:
                q = qn(self.nodes[i].get('rotation', [0, 0, 0, 1]))
                self.tg[i] = q if self.parents[i] == -1 else qn(qm(tq(self.parents[i]), q))
            return self.tg[i]
        self.rows = self.cal['rows']
        self.c = {}
        self.markers = {}
        bw = world(self.nodes, self.parents)
        for row in self.rows:
            n = self.ni[row['target']]
            si = self.si[row['source']]
            a = self.bindpos[self.si[row['source_primary_start']]]
            b = self.bindpos[self.si[row['source_distal']]]
            fs = frame(sub(b, a), row['guide'])
            ft = frame(sub(row['target_tail_m'], row['target_head_m']), row['guide'])
            asq = qm(qi(self.bindq[si]), rq(fs))
            atq = qm(qi(tq(n)), rq(ft))
            self.c[n] = qn(qm(atq, qi(asq)))
            self.markers[n] = [mv(inverse(bw[n][0]), mul([ft[k][col] for k in range(3)], 0.1)) for col in (0, 1)]
        need([self.ni[x['target']] for x in self.rows] == self.contract['target_joint_nodes'], 'exact target map')
        raw = r / 'experiments/44-approved-cpu-motion-trial/evidence/run/raw'
        self.rawq = struct.unpack('<10800f', (raw / 'local_rotations_xyzw.f32').read_bytes())
        self.rawt = struct.unpack('<270f', (raw / 'root_positions.f32').read_bytes())
        need(all((finite(x) for x in self.rawq + self.rawt)), 'raw finite')
        receipt = strict_json(r / 'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json')
        need(receipt['returncode'] == 0 and receipt['raw_complete'] is True and (receipt['request']['frames'] == 90) and (receipt['request']['fps'] == 30), 'genuine successful90 receipt')
        need({x['sha256'] for x in receipt['raw_provenance']} == {pins['experiments/44-approved-cpu-motion-trial/evidence/run/raw/' + x] for x in ('root_positions.f32', 'local_rotations_xyzw.f32')}, 'receipt raw hashes')
        self.expected = [self.expect(f) for f in range(90)]

    def expect(self, f):
        sg = []
        for i in range(30):
            q = qn(self.rawq[(f * 30 + i) * 4:(f * 30 + i + 1) * 4])
            sg.append(q if self.sp[i] == -1 else qn(qm(sg[self.sp[i]], q)))
        result = {}
        for row in self.rows:
            n = self.ni[row['target']]
            s = self.si[row['source']]
            p = row['target_parent']
            pname = next((x['source'] for x in self.rows if x['target'] == p), None)
            if n == 16:
                q = self.nodes[n].get('rotation', [0, 0, 0, 1])
            else:
                pi = self.si[pname] if pname else None
                neutral = self.bindq[s] if pi is None else qm(qi(self.bindq[pi]), self.bindq[s])
                pose = sg[s] if pi is None else qm(qi(sg[pi]), sg[s])
                delta = qm(qi(neutral), pose)
                c = self.c[n]
                q = qm(self.nodes[n].get('rotation', [0, 0, 0, 1]), qm(c, qm(delta, qi(c))))
            result[n] = qn(q)
        t = sub(list(self.rawt[3 * f:3 * f + 3]), mv(qr(result[17]), self.nodes[16]['translation']))
        return (result, t)

    def check_glb(self, path):
        g = GLB(path)
        old = self.original.j
        new = g.j
        need(g.bin[:len(self.original.bin)] == self.original.bin, 'old BIN exact prefix')
        for k, v in old.items():
            if k in ('animations', 'accessors', 'bufferViews'):
                need(exact(new[k][:len(v)], v), 'old ' + k + ' preserved')
            elif k == 'buffers':
                expected = copy.deepcopy(v)
                expected[0]['byteLength'] = new[k][0]['byteLength']
                need(exact(new[k], expected), 'old buffer metadata')
            else:
                need(exact(new.get(k), v), 'old JSON ' + k)
        need(list(new) == list(old), 'old top-level ordering/keys')
        need(len(new['animations']) == 4, 'exact fourth animation')
        clip = new['animations'][3]
        need(len(clip['channels']) == 19 and len(clip['samplers']) == 19, '19 channels/samplers')
        actual = {}
        used = set()
        need(clip['name'] == 'genuine44_calibrated47', 'new animation name')
        need(exact(clip['extras'], {'experiment_only': True, 'provenance_kind': 'generated', 'source_experiment': 44, 'calibration_experiment': 47}), 'clip genuine provenance')
        times = [struct.unpack('<f', struct.pack('<f', i / 30))[0] for i in range(90)]
        used_accessors = set()
        for ch in clip['channels']:
            target = ch['target']
            n = index(target['node'], len(self.nodes))
            p = target['path']
            need(p in ('rotation', 'translation'), 'rotation/translation only')
            need((n, p) not in actual, 'duplicate target')
            sidx = index(ch['sampler'], len(clip['samplers']))
            need(sidx not in used, 'unique sampler')
            used.add(sidx)
            sam = clip['samplers'][sidx]
            need(sam.get('interpolation', 'LINEAR') == 'LINEAR', 'linear sampling')
            need([x[0] for x in g.accessor(sam['input'], 'SCALAR')] == times, 'exact binary32 time keys')
            need(type(sam['output']) is int and sam['output'] >= len(old['accessors']), 'new output accessor')
            need(type(sam['input']) is int and sam['input'] >= len(old['accessors']), 'new time accessor')
            used_accessors.update((sam['input'], sam['output']))
            actual[n, p] = g.accessor(sam['output'], 'VEC4' if p == 'rotation' else 'VEC3')
        need(used_accessors == set(range(len(old['accessors']), len(new['accessors']))), 'only used appended accessors')
        new_views = {new['accessors'][i]['bufferView'] for i in used_accessors}
        need(new_views == set(range(len(old['bufferViews']), len(new['bufferViews']))), 'only used appended views')
        for i in new_views:
            need(new['bufferViews'][i].get('byteOffset', 0) >= len(self.original.bin), 'new data after old BIN')
        need(set(actual) == {(n, 'rotation') for n in self.contract['target_joint_nodes']} | {(17, 'translation')}, 'exact targets/root17')
        maxq = maxt = maxaff = maxmarker = 0.0
        maxscale = max((max(n.get('scale', [1, 1, 1])) for n in self.nodes))
        reach = sum((math.sqrt(dot(n.get('translation', [0, 0, 0]), n.get('translation', [0, 0, 0]))) for n in self.nodes)) + 0.2
        # Conservative full-hierarchy bound from binary32 epsilon, bind reach and scale.
        afftol = 18 * R_TOL * reach * maxscale ** 18 + 8 * EPS
        for f, (expected, t) in enumerate(self.expected):
            got = {n: actual[n, 'rotation'][f] for n in expected}
            for n, q in got.items():
                need(abs(dot(q, q) - 1) <= 8 * EPS, 'normalized output quaternion')
                qn0 = qn(q)
                e = expected[n]
                err = min(max((abs(x - y) for x, y in zip(qn0, e))), max((abs(x + y) for x, y in zip(qn0, e))))
                maxq = max(maxq, err)
                need(err <= Q_TOL, 'rotation frame%d node%d' % (f, n))
                if f:
                    need(dot(actual[n, 'rotation'][f - 1], q) >= 0, 'hemisphere continuity')
            gt = actual[17, 'translation'][f]
            err = max((abs(x - y) for x, y in zip(gt, t)))
            maxt = max(maxt, err)
            need(err <= 8 * EPS * max(1, *map(abs, t)), 'root translation')
            ew = world(self.nodes, self.parents, expected, t)
            gw = world(self.nodes, self.parents, got, gt)
            need(max((abs(x - y) for x, y in zip(gw[16][1], self.rawt[3 * f:3 * f + 3]))) <= afftol, 'pelvis world')
            for n in expected:
                maxaff = max(maxaff, max((abs(x - y) for x, y in zip(ew[n][1], gw[n][1]))))
                need(maxaff <= afftol, 'complete affine joint')
                for offset in self.markers[n]:
                    a = mv(ew[n][0], offset)
                    b = mv(gw[n][0], offset)
                    err = max((abs(x - y) for x, y in zip(a, b)))
                    maxmarker = max(maxmarker, err)
                    need(err <= afftol, 'signed affine marker')
        return {'status': 'PASS', 'frames': 90, 'rotation_comparisons': 1620, 'signed_marker_comparisons': 3240, 'root_translation_comparisons': 90, 'pelvis_world_comparisons': 90, 'max_quaternion_error': maxq, 'max_root_translation_error_m': maxt, 'max_joint_world_error_m': maxaff, 'max_signed_marker_error_m': maxmarker, 'quaternion_tolerance': Q_TOL, 'affine_tolerance_m': afftol, 'epsilon_binary32': EPS, 'glb_sha256': sha(path)}

    def check_artifacts(self, directory):
        """Public checker boundary: bytes, bindings, provenance and numeric motion."""
        directory = Path(directory)
        glb = directory / 'assets/generated/genuine44-calibrated47.glb'
        result = self.check_glb(glb)
        profile = strict_json(directory / 'character.profile.json')
        work = strict_json(directory / 'genuine44-calibrated47.nvwa.json')
        ledger = strict_json(directory / 'transformation-ledger.json')
        old = strict_json(self.root / 'assets/character.profile.json')
        duration = struct.unpack('<f', struct.pack('<f', 89 / 30))[0]
        clip = {'id': 'genuine44_calibrated47', 'animation_index': 3, 'duration_seconds': duration}
        need(exact(profile['parameters'], old['parameters']) and exact(profile['clips'], old['clips'] + [clip]), 'profile old values and clip3')
        need(profile['asset_path'] == 'generated/genuine44-calibrated47.glb' and profile['asset_sha256'] == sha(glb), 'profile generated asset identity')
        need(exact(work['profile'], profile), 'whole Work embedded profile')
        need(type(work['schema_version']) is int and work['schema_version'] == 1 and (type(work['revision']) is int) and (work['revision'] == 0), 'Work schema/revision')
        need(work['character']['profile_id'] == profile['id'] and type(work['character']['scale']) is float and (work['character']['scale'] == 1.0), 'Work character binding and scale')
        need(exact(work['character']['parameters'], {x['id']: x['default'] for x in old['parameters']}), 'Work parameters')
        timeline = work['timeline']
        need(type(timeline) is list and len(timeline) == 1, 'explicit one clip3 timeline')
        entry = timeline[0]
        need(entry['clip_id'] == clip['id'] and type(entry['start_seconds']) is float and (entry['start_seconds'] == 0.0) and (type(entry['duration_seconds']) is float) and (entry['duration_seconds'] == duration) and (type(entry['speed']) is float) and (entry['speed'] == 1.0) and (entry['looping'] is False), 'explicit clip3 entry times/speed/nonlooping')
        need(ledger['schema'] == 'nvwa.experiment48.transformation-ledger.v1' and ledger['experiment_only'] is True and (ledger['provenance_kind'] == 'generated'), 'genuine experimental provenance')
        for name, key in [('admission_sha256', 'experiments/48-genuine-fixture-work/admission.json'), ('calibration_sha256', 'experiments/47-fixture-rig-calibration/calibration.json')]:
            need(ledger[name] == self.pins[key], 'ledger ' + name)
        need(ledger['input_sha256'] == self.pins, 'all source/transform/admission pins')
        need(ledger['exporter_sha256'] == sha(self.root / 'experiments/48-genuine-fixture-work/export.py'), 'actual exporter identity')
        receipt_path = 'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'
        source = ledger['source_generation']
        receipt = strict_json(self.root / receipt_path)
        need(source['receipt_path'] == receipt_path and source['receipt_sha256'] == self.pins[receipt_path], 'source genuine receipt identity')
        for key in ('returncode', 'reason', 'raw_complete', 'request'):
            need(exact(source[key], receipt[key]), 'source receipt ' + key)
        rawpins = {k: v for k, v in self.pins.items() if '/run/raw/' in k}
        need(source['raw_sha256'] == rawpins, 'genuine raw hash binding')
        transfer = ledger['transformation']
        need(transfer['new_generation'] is False and transfer['candidate'] == self.cal['candidate'] and exact(transfer['basis'], self.cal['basis']), 'separate generation/transformation')
        for key in ('root_policy', 'neutral', 'delta_policy', 'scale_policy', 'translation_policy'):
            need(transfer[key] == self.cal[key], 'transformation policy ' + key)
        need(exact(transfer['source_shape'], [90, 30, 4]) and exact(transfer['target_shape'], [90, 18, 4]) and (type(transfer['fps']) is int) and (transfer['fps'] == 30), 'bounded shapes/rate')
        need(type(transfer['animation_index']) is int and transfer['animation_index'] == 3 and (transfer['clip_id'] == clip['id']) and exact(transfer['joint_rotation_nodes'], self.contract['target_joint_nodes']) and exact(transfer['translation_nodes'], [17]), 'ledger exact channels')
        for rel in ('assets/generated/genuine44-calibrated47.glb', 'character.profile.json', 'genuine44-calibrated47.nvwa.json'):
            p = directory / rel
            need(ledger['outputs'][rel] == {'sha256': sha(p), 'bytes': p.stat().st_size}, 'serialized output identity ' + rel)
        result['profile_work_ledger_bindings'] = 'PASS'
        result['not_run'] = ['semantic prompt/human motion quality', 'official decoder parity', 'anatomy/contact', 'general rigs', 'native/Web playback and exchange']
        return result
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--glb', type=Path)
    p.add_argument('--artifacts', type=Path)
    p.add_argument('--derive', action='store_true')
    a = p.parse_args()
    o = Oracle(a.root)
    if a.derive:
        result = {'status': 'DERIVATION_REPRODUCTION_AFTER_FREEZE', 'input_sha256': o.pins, 'expected_frames': 90, 'expected_rotations': 1620, 'q_tolerance': Q_TOL, 'r_tolerance': R_TOL, 'expected_digest': hashlib.sha256(json.dumps(o.expected, separators=(',', ':')).encode()).hexdigest(), 'method': 'Hamilton XYZW chain collapse; independently reconstructed static gauges; full affine transport/markers; exposure boundary recorded in first-freeze.json'}
        result['python_runtime'] = {'implementation': platform.python_implementation(), 'version': platform.python_version()}
    else:
        result = o.check_glb(a.glb) if a.glb else o.check_artifacts(a.artifacts or a.root / 'experiments/48-genuine-fixture-work/artifacts')
    print(json.dumps(result, indent=2, sort_keys=True))
