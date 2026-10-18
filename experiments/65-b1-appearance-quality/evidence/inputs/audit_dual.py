"""Ignored, read-only native65 comparison; writes derived candidates only beside itself.

No renderer, network, GPU or production writes. Hash labels distinguish exact
source bytes from Python canonical JSON semantic hashes. Not visual acceptance.
"""
from pathlib import Path
import copy
import argparse
import hashlib
import json
import math

ROOT = Path.cwd()
parser = argparse.ArgumentParser()
parser.add_argument('--platform', choices=['native', 'web'], required=True)
args = parser.parse_args()
PLATFORM = args.platform
PREFIX = 'n65' if PLATFORM == 'native' else 'w65'
SOURCE = ROOT / ('.work/appearance79/quality-' + PLATFORM)

def envelope_path(stem):
    return SOURCE / 'captures' / (stem + ('-envelope.json' if PLATFORM == 'native' else '.json'))
OUTPUT = ROOT / '.work/appearance79/quality-audit'
CONTROLS = {'reference': 'frozen64', 'hair': 'hair_coverage',
            'eye': 'eye_polygon_normals', 'unlit': 'eyes_unlit_diagnostic'}
GROUPS = {'sf': (-1, 0), 'lf': (1, 1), 'sq': (-1, 0), 'lq': (1, 1), 'low': (0, 0)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def semantic_hash(value):
    return sha(encoded(value))


def without(value, *keys):
    return {k: v for k, v in value.items() if k not in keys}


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0]]


def unit(v):
    length = math.sqrt(dot(v, v))
    require(math.isfinite(length) and length > 0, 'normal domain')
    return [x/length for x in v]


def normal_policy(part, polygon):
    rest = part['rest_model_m']
    sums = [[0., 0., 0.] for _ in rest]
    if polygon:
        text = (ROOT / 'assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.obj').read_text()
        faces = [[int(t.split('/')[0])-1 for t in line.split()[1:]]
                 for line in text.splitlines() if line.startswith('f ')]
        require(len(faces) == 86, 'source eye polygon count')
        for face in faces:
            origin = rest[face[0]]
            edges = [sub(rest[i], origin) for i in face]
            normal = unit([sum(cross(edges[j], edges[(j+1) % len(face)])[a]
                               for j in range(len(face))) for a in range(3)])
            for j, i in enumerate(face):
                prev = unit(sub(rest[face[j-1]], rest[i]))
                following = unit(sub(rest[face[(j+1) % len(face)]], rest[i]))
                angle = math.acos(max(-1., min(1., dot(prev, following))))
                for a in range(3):
                    sums[i][a] += normal[a]*angle
    else:
        pairs = part['source_uv_pairs']
        indices = part['indices']
        for offset in range(0, len(indices), 3):
            a, b, c = [pairs[i][0] for i in indices[offset:offset+3]]
            normal = cross(sub(rest[b], rest[a]), sub(rest[c], rest[a]))
            for i in [a, b, c]:
                for axis in range(3):
                    sums[i][axis] += normal[axis]
    return [unit(v) for v in sums]


def error(a, b):
    require(len(a) == len(b), 'normal coverage')
    return max(abs(x-y) for va, vb in zip(a, b) for x, y in zip(va, vb))


source_notice = json.loads((ROOT / 'assets/appearances/mpfb-b1-cc0-v1/SOURCE.json').read_text())
audit = {'schema_version': 1, 'scope': 'Dual-end65 CPU control isolation audit; no visual quality admission, GPU readback, head-motion or production policy change.',
         'hash_semantics': 'source_envelope_sha256 hashes original bytes. semantic_sha256 hashes Python json.dumps(sort_keys=True,separators=(comma,colon),ensure_ascii=True,allow_nan=False). Producer geometry hashes are retained separately without pretending to reproduce Rust number formatting.',
         'groups': {}, 'unexpected_deltas': []}
total_input = 0
total_derived = 0
for group, (torso, jaw) in GROUPS.items():
    reference = json.loads(envelope_path(f'{PREFIX}-{group}-reference').read_text())
    ref_frame = reference['frame']
    ref_runtime = ref_frame['appearance']['accessory_runtime']
    ref_parts = {p['name']: p for p in ref_runtime['accessories']}
    camera = ref_frame['quality']['scene_camera']
    group_result = {'camera': camera, 'parameters': {'torso_length': torso, 'jaw_drop': jaw},
                    'sample': ref_frame['snapshot']['sample'], 'controls': {}}
    controls = {'reference': 'frozen64', 'recovered': 'frozen64'} if group == 'low' else CONTROLS
    for control, selected in controls.items():
        stem = f'{PREFIX}-{group}-{control}'
        source = envelope_path(stem)
        raw = source.read_bytes()
        envelope = json.loads(raw)
        report, frame = envelope['report'], envelope['frame']
        runtime = frame['appearance']['accessory_runtime']
        snapshot = frame['snapshot']
        quality = frame['quality']
        require(envelope['request'] == report['request'] == frame['request'], stem+' request correlation')
        require(report['request']['request_id'] == stem and report['phase'] == 'captured', stem+' phase')
        require(quality == report['quality'], stem+' quality metadata')
        require(quality['selected'] == selected and quality['production_appearance_controller_disabled'] is True
                and quality['work_appearance'] == {'type': 'none'}, stem+' isolated controller boundary')
        require(quality['scene_camera'] == camera == frame['appearance']['observation_camera'], stem+' camera')
        samples = 1 if group == 'low' else 4
        msaa = 'Off' if group == 'low' else 'Sample4'
        require(camera['active'] and camera['msaa_samples'] == samples and camera['msaa'] == msaa, stem+' actual MSAA')
        require(runtime['actual_msaa_samples'] == samples, stem+' accessory MSAA')
        require(runtime['bone_names'] == [bone['name'] for bone in snapshot['bones']]
                and runtime['actual_skin_matrices'] == snapshot['bones'], stem+' actual full bone records')
        require(snapshot == ref_frame['snapshot'], stem+' exact full base snapshot')
        require(snapshot['parameters'] == {'torso_length': torso, 'jaw_drop': jaw}, stem+' shape')
        sample = snapshot['sample']
        require(sample['clip_id'] == 'b1_arm_rehearsal_v1' and sample['source_seconds'] == 2
                and sample['position_seconds'] == 2 and sample['playing'] is False, stem+' held sample')
        require(frame['geometry_equal'] is True and report['geometry_equal'] is True
                and frame['geometry_before_sha256'] == frame['geometry_after_sha256']
                == report['geometry_before_sha256'] == report['geometry_after_sha256'], stem+' producer equality')
        skin_omit = ['accessory_runtime'] + (['material_handle', 'image_handle'] if group == 'low' else [])
        require(without(frame['appearance'], *skin_omit) == without(ref_frame['appearance'], *skin_omit), stem+' unchanged body skin/UV/image data')
        require(without(runtime, 'accessories', 'quality', 'identity') == without(ref_runtime, 'accessories', 'quality', 'identity'), stem+' actual bones/sample matrices')
        require(without(runtime['identity'], 'quality') == without(ref_runtime['identity'], 'quality'), stem+' base runtime identity')
        parts = {p['name']: p for p in runtime['accessories']}
        require(set(parts) == {'eyes', 'hair'}, stem+' roles')
        observed = {}
        for name, part in parts.items():
            baseline = ref_parts[name]
            # Every field is checked; only explicitly expected identity/normal/material differences are excluded.
            omit = ['entity', 'mesh_handle', 'material']
            if control == 'eye' and name == 'eyes':
                omit += ['normals', 'rest_normals']
                require(part['normals'] != baseline['normals'] and part['rest_normals'] != baseline['rest_normals'], stem+' changed eye normals')
            require(without(part, *omit) == without(baseline, *omit), stem+' unexpected '+name+' array/property delta')
            material = without(part['material'], 'handle', 'image_handle', 'quality')
            expected = without(baseline['material'], 'handle', 'image_handle', 'quality')
            if control == 'hair' and name == 'hair':
                expected = dict(expected, alpha='AlphaToCoverage')
            if control == 'unlit' and name == 'eyes':
                expected = dict(expected, unlit=True)
            require(material == expected, stem+' unexpected '+name+' material delta')
            require(part['material']['quality'] == selected, stem+' material label')
            require(part['material']['decoded_rgba_sha256'] == source_notice['png'][part['material']['texture']]['decoded_sha256'], stem+' actual decoded image')
            weights = part['full_normalized_positive_influences']
            require(len(weights) == part['source_vertices'], stem+' full weight coverage')
            for row in weights:
                require(row and all(0 <= i < 53 and math.isfinite(w) and w > 0 for i, w in row)
                        and abs(sum(w for i, w in row)-1) < 1e-12, stem+' normalized positive row')
            normal_error = error(normal_policy(part, control == 'eye' and name == 'eyes'), part['rest_normals'])
            require(normal_error < 1e-12, stem+' source normal reconstruction')
            observed[name] = {'max_positive_influences': max(map(len, weights)),
                              'rest_normal_reconstruction_max_component_error': normal_error,
                              'changed_array_fields': [k for k in ['rest_model_m', 'rest_normals', 'positions', 'normals', 'full_normalized_positive_influences', 'source_uv_pairs', 'uv_0', 'indices'] if part[k] != baseline[k]],
                              'changed_material_fields': [k for k in material if material[k] != without(baseline['material'], 'handle', 'image_handle', 'quality')[k]]}
        screen_path = SOURCE / 'screens' / (stem+'.json')
        screen = json.loads(screen_path.read_text())
        require(screen['request_id'] == stem and screen['camera'] == camera
                and screen['sample'] == sample and screen['parameters'] == snapshot['parameters'], stem+' screenshot pairing')
        if PLATFORM == 'native':
            require(screen['control'] == selected, stem+' screenshot control')
            report_raw = (SOURCE / 'captures' / (stem+'-report.json')).read_bytes()
            require(json.loads(report_raw) == report and sha(report_raw) == screen['report_sha256'], stem+' paired report SHA')
            image_name, image_sha, image_bytes = screen['file'], screen['sha256'], screen['bytes']
        else:
            require(screen['quality'] == selected and screen['capture_sha256'] == sha(raw), stem+' paired envelope SHA')
            image_name, image_sha, image_bytes = screen['screenshot_file'], screen['screenshot_sha256'], screen['screenshot_bytes']
        image_path = SOURCE / 'screens' / image_name
        require(sha(image_path.read_bytes()) == image_sha and image_path.stat().st_size == image_bytes, stem+' screenshot bytes')
        skin = copy.deepcopy(without(frame['appearance'], 'accessory_runtime', 'actual_uv_0'))
        skin['source_uv_proof'].pop('uv_0')
        body_parts = []
        for part in snapshot['parts']:
            body_parts.append({'name': part['name'], 'display_transform': part['display_transform'],
                               'semantic_sha256': semantic_hash(part),
                               'array_hashes': {k: semantic_hash(part[k]) for k in ['positions', 'normals', 'rest_positions', 'rest_normals', 'source_ids', 'full_joint_influences', 'indices', 'tangents']},
                               'vertex_count': len(part['positions']), 'index_count': len(part['indices'])})
        derived = {'schema_version': 1, 'scope': audit['scope'], 'hash_semantics': audit['hash_semantics'],
                   'source_envelope_file_basename': source.name, 'source_envelope_bytes': len(raw), 'source_envelope_sha256': sha(raw),
                   'request': envelope['request'], 'quality': quality, 'camera': camera,
                   'producer_full_snapshot_sha256': frame['geometry_after_sha256'],
                   'semantic_full_snapshot_sha256': semantic_hash(snapshot), 'body_parts': body_parts,
                   'bones_reference': 'accessory_runtime.actual_skin_matrices contains the full actual BoneFrame records',
                   'sample': sample, 'skin': skin,
                   'body_uv_semantic_sha256': semantic_hash(frame['appearance']['actual_uv_0']),
                   'accessory_runtime': runtime, 'paired_screenshot_receipt': screen,
                   'audit': observed, 'omitted': ['full body/clothes mesh arrays', 'two repeated full body UV arrays'],
                   'limits': 'Derived record, not the original envelope. Original source byte SHA retained. No visual-quality pass, GPU readback, gaze/blink/head-motion, geometry-offset, asset-store-disposal or performance claim.'}
        derived_raw = encoded(derived)+b'\n'
        destination = OUTPUT / (PLATFORM + '-derived') / (stem+'.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(derived_raw)
        total_input += len(raw)
        total_derived += len(derived_raw)
        group_result['controls'][control] = {'source_envelope_sha256': sha(raw), 'derived_file': str(destination.relative_to(OUTPUT)),
                                            'derived_bytes': len(derived_raw), 'derived_sha256': sha(derived_raw), 'observed_deltas': observed}
        del envelope, raw, report, frame, runtime, snapshot, parts, derived
    audit['groups'][group] = group_result
audit['sizes'] = {'original_envelope_bytes': total_input, 'derived_candidate_bytes': total_derived}
audit['status'] = 'PASS_CONTROL_ISOLATION_ONLY'
OUTPUT.mkdir(exist_ok=True)
(OUTPUT / (PLATFORM + '-audit.json')).write_text(json.dumps(audit, indent=2)+'\n')
print(json.dumps({'status': audit['status'], 'groups': len(GROUPS), 'envelopes': 18, 'platform': PLATFORM, 'sizes': audit['sizes']}))
