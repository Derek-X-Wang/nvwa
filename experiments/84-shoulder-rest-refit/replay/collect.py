#!/usr/bin/env python3
"""NEW exact18 production CPU corpus. Historical gzip identities stay unavailable."""
import argparse
import gzip
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/70-b1-garment-defect'))
import diagnose
sys.path.insert(0, str(ROOT / 'experiments/60-b1-continuous-motion'))
from checker import check_time_binding, Checker, check_bones, independent_lbs

PREFIX = 'B1_84_REPLAY '
FRESH_SHA = 'fc4196e7f00fadf0dd2860418fd515ea0befd9de84e4dc0f527057dd5860aa67'
FIXTURE_SHA = 'f671f09952653b01126d1599e047e7011afabbf3979aedee95f5b83c4c401f87'
EPS = 1e-5
ARM = 'b1_arm_rehearsal_v1'
KNEE = 'b1_knee_flex_v1'
RECIPES = tuple((t, c, k) for t in (-1, 0, 1) for c in (ARM, KNEE) for k in ((0, 8, 16, 24, 32) if c == ARM else (16,)))

def need(ok, message):
    if not ok:
        raise ValueError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def strict_load(raw):
    return json.loads(raw, object_pairs_hook=diagnose.pairs,
                      parse_constant=lambda _: need(False, 'nonfinite JSON'))

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def numeric_same(a, b, label, eps=EPS):
    """Reject shape/key changes before bounded finite numeric comparison."""
    if isinstance(a, (int, float)) and not isinstance(a, bool):
        need(isinstance(b, (int, float)) and not isinstance(b, bool) and math.isfinite(a) and math.isfinite(b), label + ': invalid numeric value')
        need(abs(a-b) <= eps, label + ': numeric bound exceeded')
        return
    need(type(a) is type(b), label + ': type changed')
    if isinstance(a, dict):
        need(a.keys() == b.keys(), label + ': keys changed')
        for k in a:
            numeric_same(a[k], b[k], label + '/' + k, eps)
    elif isinstance(a, list):
        need(len(a) == len(b), label + ': array length changed')
        for i, (x, y) in enumerate(zip(a, b)):
            numeric_same(x, y, label + '/' + str(i), eps)
    else:
        need(a == b, label + ': identity changed')

def case_name(key):
    t, c, k = key
    return f't{t:+g}__{c}__k{k:02}.json.gz'

def validate_record(record, run_id):
    need(isinstance(record, dict) and record.get('run_id') == run_id, 'new run identity mismatch')
    need(record.get('kind') == 'matrix', 'unexpected record kind')
    r, s = record['request'], record['snapshot']
    need(isinstance(r, dict) and isinstance(s, dict), 'missing request/snapshot')
    t, c, k = r['torso_length'], r['clip_id'], r['k']
    need(type(t) in (float, int) and type(k) is int and r['jaw_drop'] == 0 and type(r['jaw_drop']) in (float, int), 'malformed recipe')
    key = (t, c, k)
    need(key in RECIPES, 'unrequested case')
    need(s['schema_version'] == 1 and s['profile_id'] == 'nvwa-mpfb-b1-motion-v1' and s['asset_id'] == diagnose.ASSET_ID and s['mode'] == 'motion', 'noncanonical legacy snapshot')
    need(s['backend'] == {'type':'b1_cpu', 'schema_version':2, 'asset_id':diagnose.ASSET_ID}, 'legacy backend identity differs')
    need(s['parameters'] == {'torso_length': t, 'jaw_drop': 0}, 'mislabeled snapshot parameters')
    check_time_binding(record)
    need(s['sample']['clip_id'] == c and s['sample']['playing'] is False, 'mislabeled clip/playing')
    need(isinstance(s['bones'], list) and len(s['bones']) == 53 and len({b['name'] for b in s['bones']}) == 53, 'malformed bones')
    need(isinstance(s['parts'], list) and len(s['parts']) == 2 and {p['name'] for p in s['parts']} == {'body', 'garment'}, 'malformed parts')
    return key

def inventory_digest(rows):
    return digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())

def is_build_path(path):
    """Full local compiled-input closure, excluding noncompiled experiment work."""
    return (path in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml',
                     'experiments/84-shoulder-rest-refit/replay/main.rs',
                     'experiments/84-shoulder-rest-refit/replay/Cargo.toml',
                     'experiments/84-shoulder-rest-refit/replay/Cargo.lock')
            or path.startswith(('crates/', 'vendor/humentity/', 'vendor/bevy_obj/', 'vendor/wobj/', '.cargo/', 'assets/')))

def build_source_files(root):
    """Read-only helper for the parent to create the completed build receipt."""
    root = Path(root)
    paths = {root / name for name in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml',
             'experiments/84-shoulder-rest-refit/replay/main.rs',
             'experiments/84-shoulder-rest-refit/replay/Cargo.toml',
             'experiments/84-shoulder-rest-refit/replay/Cargo.lock')}
    for name in ('crates', 'vendor/humentity', 'vendor/bevy_obj', 'vendor/wobj', '.cargo', 'assets'):
        for path in (root / name).rglob('*'):
            if path.is_file() and not set(path.relative_to(root).parts).intersection({'target', '__pycache__', '.git'}):
                paths.add(path)
    rows = []
    for path in sorted(paths):
        need(path.is_file() and path.resolve().is_relative_to(root.resolve()), 'compiled source file absent/escaped')
        raw = path.read_bytes()
        rows.append({'path':str(path.relative_to(root)), 'bytes':len(raw), 'sha256':digest(raw)})
    return rows

def receipt_row(directory, name):
    raw = (directory / name).read_bytes()
    return {'path':name, 'bytes':len(raw), 'sha256':digest(raw)}

def validate_build_receipt(build, before, identity):
    need(build['schema_version'] == 1 and build['kind'] == 'nvwa84-completed-native-build-v1', 'wrong build receipt schema')
    need(build['status'] == 'PASS_COMPLETED_BUILD' and type(build['exit_code']) is int and build['exit_code'] == 0, 'build receipt is not completed success')
    need(isinstance(build['build_run_id'], str) and bool(build['build_run_id']) and build['build_run_id'] != identity['run_id'], 'build/capture identity absent or conflated')
    need(identity['build_run_id'] == build['build_run_id'], 'identity/build run crosslink differs')
    need(isinstance(build['command'], list) and bool(build['command']) and all(isinstance(x,str) and bool(x) for x in build['command']), 'actual build command missing')
    need(identity['build_command'] == build['command'], 'identity/build command differs')
    need(isinstance(build['source_head'],str) and len(build['source_head']) == 40 and all(c in '0123456789abcdef' for c in build['source_head']) and build['source_head'] == identity['source_head'], 'identity/build source HEAD differs')
    files = [row for row in before['files'] if is_build_path(row['path'])]
    need(files == build['source_files'] and len({row['path'] for row in files}) == len(files), 'exact compiled source closure differs from completed build')
    need(inventory_digest(files) == build['source_files_sha256'] == identity['compiled_source_sha256'], 'compiled source receipt hash differs')
    need(set(build['toolchain']) == {'rustc','cargo'} and all(isinstance(v,str) and bool(v) for v in build['toolchain'].values()) and identity['toolchain'] == build['toolchain'], 'identity/build toolchain differs')
    need(all(isinstance(build['host'][key],str) and bool(build['host'][key]) and build['host'][key] == identity['host'][key] for key in ('system','machine')), 'identity/build host convention differs')
    need(build['binary']['name'] == 'nvwa-shoulder-rest-replay' and {key:build['binary'][key] for key in ('bytes','sha256')} == before['binary'], 'completed build binary differs from captured producer')
    need(identity['binary_sha256'] == build['binary']['sha256'] and identity['binary_bytes'] == build['binary']['bytes'], 'identity/build binary crosslink differs')

def source_closure(asset_root, binary):
    need(asset_root.resolve() == (ROOT / 'assets').resolve(), 'only current checkout complete assets permitted')
    files = {ROOT / p for p in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml')}
    for rel in ('crates', 'vendor/humentity', 'vendor/bevy_obj', 'vendor/wobj', 'assets', '.cargo'):
        for p in (ROOT / rel).rglob('*'):
            if p.is_file() and not set(p.relative_to(ROOT).parts).intersection({'target', '__pycache__', '.git'}):
                files.add(p)
    for rel in ('experiments/60-b1-continuous-motion/checker.py', 'experiments/60-b1-continuous-motion/geometry.py', 'experiments/70-b1-garment-defect/diagnose.py', 'experiments/79-shoulder-pose-corrective/fixtures/historical-actual-activation.json'):
        files.add(ROOT / rel)
    files.update(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.rs', '.py', '.toml', '.lock', '.proposed'))
    rows = []
    for p in sorted(files):
        need(p.is_file() and p.resolve().is_relative_to(ROOT), 'source closure file absent/escaped: ' + str(p.relative_to(ROOT)))
        raw = p.read_bytes()
        rows.append({'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': digest(raw)})
    raw = binary.read_bytes()
    return {'files': rows, 'binary': {'bytes': len(raw), 'sha256': digest(raw)}, 'inventory_sha256': digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())}

def check_original_fixture(actual_bones, frozen_bones):
    actual = {bone['name']:bone for bone in actual_bones}
    for bone in frozen_bones:
        for field,value in bone.items():
            need(value == actual[bone['name']][field], 'EXACT original fixture field differs: ' + bone['name'] + '/' + field)

def geometry_validator(asset_root, fresh_path):
    """Unchanged source-fit/FK/positive-weight/LBS checks; no fallback on failure."""
    source = diagnose.Source(asset_root / 'characters/mpfb-b1-v1')
    source_checker = Checker(asset_root, surfaces=False)
    fixture_path = ROOT / 'experiments/79-shoulder-pose-corrective/fixtures/historical-actual-activation.json'
    raw = fixture_path.read_bytes()
    need(digest(raw) == FIXTURE_SHA, 'original bone fixture changed')
    fixture = {x['input_name']: x for x in strict_load(raw)['cases']}
    need(set(fixture) == {case_name(k) for k in RECIPES}, 'original fixture does not match exact18 recipes')
    raw = fresh_path.read_bytes()
    need(digest(raw) == FRESH_SHA, 'original nineteenth input changed')
    fresh = strict_load(raw)['frame']['full_base']
    need(fresh['parameters']['torso_length'] == 0 and fresh['parameters']['jaw_drop'] == 0 and fresh['sample']['clip_id'] == ARM and fresh['sample']['source_seconds'] == 2, 'original nineteenth semantics differ')
    expected_bone_order = [b['name'] for b in fresh['bones']]
    need(len(expected_bone_order) == 53 and set(expected_bone_order) == set(source.rig), 'anchor/source full bone coverage differs')
    rest_identities = {}
    def check(record, key):
        t, clip, k = key
        result = diagnose.analyze(record, source, {'torso_length': t, 'jaw_drop': 0, 'clip_id': clip, 'seconds': k/8, 'timeline_id': 'probe-entry'})
        need(result['reconstruction']['rest_max_component_error_m'] <= 1e-7, 'frozen new source/rest reconstruction1e-7 ceiling exceeded')
        old = fixture[case_name(key)]
        need(old['torso'] == t and old['clip'] == clip and old['seconds'] == k/8, 'original fixture recipe differs')
        snapshot = record['snapshot']
        need([b['name'] for b in snapshot['bones']] == expected_bone_order, 'full53 bone ordering differs from authenticated anchor')
        actual = {b['name']: b for b in snapshot['bones']}
        need({b['name']: b['parent'] for b in snapshot['bones']} == {n: v['parent'] or None for n,v in source.rig.items()}, 'full53 source hierarchy differs')
        skins, fk, heads, bind = check_bones(snapshot['bones'], clip, k/8)
        rest_identity = {'bones':[{field:b[field] for field in ('name','parent','rest','inverse_bind','canonical_rest','frame_gauge','local_rest')} for b in snapshot['bones']], 'parts':[]}
        for part in snapshot['parts']:
            rest_identity['parts'].append({field:part[field] for field in ('name','source_ids','indices','rest_positions','rest_normals','full_joint_influences','model_to_world','display_transform')})
            duplicates = {}
            for i, sid in enumerate(part['source_ids']):
                row = {field:part[field][i] for field in ('positions','rest_positions','full_joint_influences')}
                if sid in duplicates:
                    need(duplicates[sid] == row, 'exact render duplicate position/rest/influence identity differs')
                duplicates[sid] = row
        if t not in rest_identities:
            need(clip == ARM and k == 0, 'first per-shape baseline must be actual arm0')
            rest_identities[t] = rest_identity
        need(rest_identities[t] == rest_identity, 'exact fitted rest/influence/placement changed across pose; possible extra floor transform')
        lbs_errors = {}
        for part in snapshot['parts']:
            ids = part['source_ids']
            need(len(part['full_joint_influences']) == len(ids), 'positive influence coverage differs')
            expected_rows = []
            for sid, row in zip(ids, part['full_joint_influences']):
                source_row = {}
                mapping = [(sid, 1.)] if part['name'] == 'body' else source_checker.garment_map[sid]
                for helper, coefficient in mapping:
                    for bone, weight in source_checker.source_weights.get(helper, {}).items():
                        source_row[bone] = source_row.get(bone, 0.) + coefficient*weight
                source_row = {bone: weight for bone,weight in source_row.items() if weight > 0}
                total = sum(source_row.values())
                need(total > 0, 'empty source positive influence')
                expected = {i: source_row[name]/total for i,name in enumerate(expected_bone_order) if name in source_row}
                need(len({j for j,w in row}) == len(row) and all(type(j) is int and 0 <= j < 53 and math.isfinite(w) and w > 0 for j,w in row), 'invalid full positive joint ordering/support')
                row_total = sum(w for j,w in row)
                uploaded = {j:w/row_total for j,w in row}
                need(set(uploaded) == set(expected), 'full positive source joint support differs')
                need(max(abs(uploaded[j]-expected[j]) for j in expected) <= 1e-6, 'original source influence arithmetic bound exceeded')
                expected_rows.append(list(expected.items()))
            independent = independent_lbs(part['rest_positions'], expected_rows, skins)
            need(len(independent) == len(part['positions']), 'body/garment uploaded row coverage differs')
            err = max(abs(x-y) for a,b in zip(independent,part['positions']) for x,y in zip(a,b))
            need(err <= 1e-5, 'original independent full-positive LBS/upload bound exceeded')
            lbs_errors[part['name']] = err
        result['full53_source_order_and_skin'] = {'bone_order': expected_bone_order, 'fk_error_original_bound': fk, 'head_error_original_bound': heads, 'bind_error_original_bound': bind, 'source_positive_lbs_error_original_bound': lbs_errors}

        check_original_fixture(snapshot['bones'], old['bones'])
        if key == (0, ARM, 16):
            s = record['snapshot']
            need(fresh['bones'] == s['bones'], 'EXACT anchor full bone fields differ')
            current = {p['name']: p for p in s['parts']}
            for old_part in fresh['parts']:
                part = current[old_part['name']]
                for field in ('source_ids', 'indices'):
                    need(old_part[field] == part[field], 'overlap exact ' + field + ' differs')
                for field in ('positions', 'normals', 'tangents', 'rest_positions', 'rest_normals', 'full_joint_influences', 'model_to_world', 'display_transform'):
                    if field == 'positions':
                        numeric_same(old_part[field], part[field], 'overlap/' + old_part['name'] + '/positions')
                    else:
                        need(old_part[field] == part[field], 'EXACT anchor ' + old_part['name'] + '/' + field + ' differs')
            result['original_nineteenth_overlap'] = 'PASS sourceIDs/indices, bones, rest/influences/transforms/normals/tangents exact; positions <= original1e-5; profile/entry identities explicitly differ'
        return result
    return check

def collect(lines, out, run_id, validator):
    """The same streaming acceptance path used by production and negative controls."""
    seen = set()
    entries = []
    complete = False
    (out / 'keyframes').mkdir()
    for line in lines:
        if not line.startswith(PREFIX):
            need(not line.startswith('B1_60 '), 'historical producer prefix forbidden')
            continue
        need(not complete, 'records after completion')
        raw = line[len(PREFIX):].encode('utf-8')
        record = strict_load(raw)
        need(isinstance(record, dict) and record.get('run_id') == run_id, 'new run identity mismatch')
        if record.get('kind') == 'complete':
            need(record.get('matrix_samples') == 18 and type(record.get('matrix_samples')) is int, 'wrong completion count')
            complete = True
            continue
        key = validate_record(record, run_id)
        need(key not in seen, 'duplicate case')
        # Preserve the exact producer substring before deeper checks, including its LF.
        compressed = gzip.compress(raw, mtime=0)
        path = out / 'keyframes' / case_name(key)
        path.write_bytes(compressed)
        checks = validator(record, key)
        seen.add(key)
        entries.append({'case': case_name(key), 'recipe': {'torso_length': key[0], 'jaw_drop': 0, 'clip_id': key[1], 'k': key[2], 'seconds': key[2]/8}, 'path': str(path.relative_to(out)), 'bytes': len(compressed), 'sha256': digest(compressed), 'raw_bytes': len(raw), 'raw_sha256': digest(raw), 'checks': checks})
    need(complete and seen == set(RECIPES), 'missing case/completion')
    return entries

def authenticate_corpus(directory, manifest_sha256, source_inventory_sha256, fresh_path):
    """Scoring-input seam: caller must freeze both expected hashes before scoring."""
    manifest_path = directory / 'manifest.json'
    raw = manifest_path.read_bytes()
    need(digest(raw) == manifest_sha256, 'frozen new manifest hash differs')
    m = strict_load(raw)
    need(m['schema_version'] == 1 and m['cohort_type'] == 'hybrid-current18-original-anchor' and m['historical_replay'] == 'NOT-RUN_MISSING18', 'not the declared hybrid cohort')
    need(m['source_inventory_sha256'] == source_inventory_sha256 and m['anchor'] == {'role':'authenticated-original-fresh-default', 'bytes':fresh_path.stat().st_size, 'sha256':FRESH_SHA}, 'hybrid source/anchor differs')
    need(m['status'] == 'PASS_NEW_CURRENT18_CORPUS' and m['source_unchanged'] is True and m['historical_input_hashes_reused'] is False, 'new corpus not admitted')
    receipt_names = {'identity':'identity.json', 'build':'build-receipt.json', 'source_before':'source-before.json', 'source_at_run':'source-at-run.json', 'source_after':'source-after.json'}
    need(set(m['receipts']) == set(receipt_names), 'complete identity/build/source receipt bindings missing')
    for key,name in receipt_names.items():
        need(m['receipts'][key] == receipt_row(directory,name), 'tampered ' + key + ' receipt bytes/hash')
    identity = strict_load((directory / 'identity.json').read_bytes())
    need(identity['run_id'] == m['run_id'] and identity['schema'] == 'NEW-current18-production-CPU-v1', 'mixed corpus identity')
    need(identity['source_inventory_sha256'] == source_inventory_sha256, 'wrong frozen source')
    before = strict_load((directory / 'source-before.json').read_bytes())
    need(before['inventory_sha256'] == source_inventory_sha256 and digest(json.dumps(before['files'], sort_keys=True, separators=(',', ':')).encode()) == source_inventory_sha256, 'source receipt inventory differs')
    need(before == strict_load((directory / 'source-at-run.json').read_bytes()) == strict_load((directory / 'source-after.json').read_bytes()), 'source receipt changed')
    need(identity['source_before_sha256'] == m['receipts']['source_before']['sha256'], 'identity/source receipt crosslink differs')
    need(identity['build_receipt_sha256'] == m['receipts']['build']['sha256'], 'identity/build receipt hash differs')
    validate_build_receipt(strict_load((directory/'build-receipt.json').read_bytes()),before,identity)
    need(digest(fresh_path.read_bytes()) == FRESH_SHA == identity['fresh_nineteenth_sha256'], 'original nineteenth anchor changed')
    seen = set()
    records = []
    need(len(m['cases']) == 18, 'missing/extra manifest cases')
    for entry in m['cases']:
        need(entry['path'] == 'keyframes/' + entry['case'] and entry['case'] in {case_name(k) for k in RECIPES}, 'unsafe/wrong case path')
        compressed = (directory / entry['path']).read_bytes()
        need(len(compressed) == entry['bytes'] and digest(compressed) == entry['sha256'], 'tampered compressed case')
        raw = gzip.decompress(compressed)
        need(len(raw) == entry['raw_bytes'] and digest(raw) == entry['raw_sha256'], 'tampered raw case')
        record = strict_load(raw)
        key = validate_record(record, m['run_id'])
        need(entry['case'] == case_name(key) and key not in seen, 'duplicate/mislabeled corpus case')
        need(entry['recipe'] == {'torso_length':key[0], 'jaw_drop':0, 'clip_id':key[1], 'k':key[2], 'seconds':key[2]/8}, 'manifest recipe differs')
        seen.add(key)
        records.append(record)
    need(seen == set(RECIPES), 'missing corpus recipe')
    return records

def run(args):
    need(args.binary.is_file() and os.access(args.binary, os.X_OK), 'executable producer required')
    args.out.mkdir(parents=True, exist_ok=False)
    run_id = 'nvwa84-current18-' + str(uuid.uuid4())
    before = source_closure(args.asset_root, args.binary)
    write_json(args.out / 'source-before.json', before)
    build_raw = args.build_receipt.read_bytes()
    build = strict_load(build_raw)
    (args.out/'build-receipt.json').write_bytes(build_raw)
    validator = geometry_validator(args.asset_root, args.fresh)
    # Freeze identity immediately before producer start and compare again after all work.
    at_run = source_closure(args.asset_root, args.binary)
    need(before == at_run, 'source changed before run')
    write_json(args.out / 'source-at-run.json', at_run)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True).splitlines()
    versions = {tool: subprocess.check_output([tool, '--version'], cwd=ROOT, text=True).strip() for tool in ('rustc','cargo')}
    identity = {'source_head':head, 'source_dirty_paths':dirty, 'toolchain':versions, 'host':{'system':platform.system(), 'machine':platform.machine(), 'release':platform.release()}, 'source_before_sha256':digest((args.out/'source-before.json').read_bytes()), 'original_garment':{row['path']:row for row in before['files'] if row['path'] in ('assets/characters/mpfb-b1-v1/garment/female_sportsuit01.obj','assets/characters/mpfb-b1-v1/garment/female_sportsuit01.mhclo')}, 'command':'python3 -B experiments/84-shoulder-rest-refit/replay/collect.py --binary <frozen-binary> --build-receipt <completed-build-receipt> --asset-root <source>/assets --fresh <original-anchor> --out <new-output>', 'run_id': run_id, 'schema': 'NEW-current18-production-CPU-v1', 'historical_raw18': 'UNAVAILABLE; never reconstructed byte identities', 'fresh_nineteenth_sha256': FRESH_SHA, 'source_inventory_sha256': before['inventory_sha256'], 'binary_sha256': before['binary']['sha256'], 'producer_prefix': PREFIX.rstrip(), 'recipes': [{'torso': t, 'jaw': 0, 'clip': c, 'k': k, 'seconds': k/8} for t,c,k in RECIPES], 'graphics': 'NOT-RUN'}
    identity.update(build_command=build['command'], build_run_id=build['build_run_id'], build_receipt_sha256=digest(build_raw), compiled_source_sha256=build['source_files_sha256'], binary_bytes=before['binary']['bytes'])
    validate_build_receipt(build,before,identity)
    write_json(args.out / 'identity.json', identity)
    env = os.environ.copy()
    env.update(B1_84_ASSET_ROOT=str(args.asset_root.resolve()), B1_84_RUN_ID=run_id)
    failure = None
    entries = []
    with (args.out / 'producer-stderr.log').open('x') as stderr:
        child = subprocess.Popen([str(args.binary.resolve())], env=env, stdout=subprocess.PIPE, stderr=stderr, text=True, encoding='utf-8')
        try:
            entries = collect(child.stdout, args.out, run_id, validator)
            need(child.wait() == 0, 'producer failed')
        except BaseException as error:
            child.terminate()
            child.wait()
            failure = str(error)
    after = source_closure(args.asset_root, args.binary)
    write_json(args.out / 'source-after.json', after)
    if after != before:
        failure = 'source/binary changed during replay' + (': ' + failure if failure else '')
    result = {'schema_version':1, 'cohort_type':'hybrid-current18-original-anchor', 'historical_replay':'NOT-RUN_MISSING18', 'source_inventory_sha256':before['inventory_sha256'], 'anchor':{'role':'authenticated-original-fresh-default', 'bytes':args.fresh.stat().st_size, 'sha256':FRESH_SHA}, 'status': 'PASS_NEW_CURRENT18_CORPUS' if failure is None else 'REJECT_CORPUS', 'run_id': run_id, 'source_unchanged': before == at_run == after, 'cases': entries, 'failure': failure, 'historical_input_hashes_reused': False, 'quality_acceptance': False, 'graphics': 'NOT-RUN'}
    result['receipts'] = {key:receipt_row(args.out,name) for key,name in {'identity':'identity.json','build':'build-receipt.json','source_before':'source-before.json','source_at_run':'source-at-run.json','source_after':'source-after.json'}.items()}
    write_json(args.out / 'manifest.json', result)
    print(json.dumps({'status': result['status'], 'cases': len(entries), 'failure': failure}))
    return 0 if failure is None else 2

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-receipt', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--asset-root', type=Path, required=True)
    p.add_argument('--fresh', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    try:
        raise SystemExit(run(p.parse_args()))
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        print(json.dumps({'status': 'REJECT_CORPUS', 'failure': str(error)}))
        raise SystemExit(2)
