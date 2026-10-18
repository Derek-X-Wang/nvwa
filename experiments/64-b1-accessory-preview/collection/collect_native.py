#!/usr/bin/env python3
"""One explicit native request and immutable collection. Does not launch or advance an app."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid

SAFE_ID = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
ACTIONS = {'baseline', 'skin', 'accessories', 'report', 'sample', 'play', 'pause',
           'view_full', 'view_face', 'view_back'}
CLIPS = {'b1_arm_rehearsal_v1', 'b1_knee_flex_v1'}
LIMIT = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON constant')))


def encode(value):
    return (json.dumps(value, allow_nan=False, indent=2) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_request(request):
    require(isinstance(request, dict) and SAFE_ID.fullmatch(request.get('request_id', '')), 'invalid request_id')
    action = request.get('action')
    require(action in ACTIONS, 'unsupported action')
    expected = {'request_id', 'action'}
    if action == 'sample':
        expected |= {'clip_id', 'seconds', 'torso_length', 'jaw_drop'}
        require(request.get('clip_id') in CLIPS, 'unsupported authored clip')
        for key, low, high in [('seconds', 0, 4), ('torso_length', -1, 1), ('jaw_drop', 0, 1)]:
            require(finite(request.get(key)) and low <= request[key] <= high, 'invalid ' + key)
    require(set(request) == expected, 'inapplicable or missing request fields')


def absolute_path(value):
    path = Path(value)
    require(path.is_absolute(), 'all channel/output/binary paths must be absolute')
    require(not path.is_symlink(), 'symlink target refused')
    require(path.parent.is_dir(), 'parent directory must already exist')
    return path


def read_bounded(path):
    with path.open('rb') as source:
        raw = source.read(LIMIT + 1)
    require(len(raw) <= LIMIT, 'channel exceeds64MiB')
    return raw


def write_new(path, raw):
    with path.open('xb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())


def save_observation(output, stem, raw, source):
    index = 0
    while True:
        path = output / (stem + '-' + str(index).zfill(4) + '.raw')
        try:
            write_new(path, raw)
            return {'file': path.name, 'source_path': str(source), 'bytes': len(raw), 'sha256': digest(raw),
                    'observed_unix_seconds': time.time()}
        except FileExistsError:
            index += 1


def numeric_vector(value, count):
    return isinstance(value, list) and len(value) == count and all(finite(x) for x in value)


def basic_snapshot(snapshot):
    parameters = snapshot.get('parameters')
    require(isinstance(parameters, dict) and set(parameters) == {'torso_length', 'jaw_drop'}
            and finite(parameters['torso_length']) and -1 <= parameters['torso_length'] <= 1
            and finite(parameters['jaw_drop']) and 0 <= parameters['jaw_drop'] <= 1, 'required current parameter dict absent or malformed')
    bones = snapshot.get('bones')
    require(isinstance(bones, list) and len(bones) == 53, 'exact53 actual BoneFrame records required')
    names = []
    for bone in bones:
        require(isinstance(bone, dict) and isinstance(bone.get('name'), str) and bone['name'], 'actual bone name absent')
        require('parent' in bone and (bone['parent'] is None or isinstance(bone['parent'], str)), 'actual bone parent absent')
        for key in ['rest', 'posed', 'inverse_bind', 'local_rest', 'local_posed', 'skin']:
            require(numeric_vector(bone.get(key), 16), 'actual BoneFrame matrix missing or malformed: ' + key)
        names.append(bone['name'])
    require(len(set(names)) == 53, 'bone names must be unique')
    parts = snapshot.get('parts')
    require(isinstance(parts, list) and len(parts) == 2 and all(isinstance(p, dict) for p in parts)
            and {p.get('name') for p in parts} == {'body', 'garment'}, 'exact body/garment parts required')
    for part in parts:
        require(all(isinstance(part.get(key), str) and part[key] for key in ['display_entity', 'mesh_handle']), 'actual part entity/mesh identity absent')
        ids = part.get('source_ids')
        require(isinstance(ids, list) and ids and all(type(x) is int and x >= 0 for x in ids), 'part source ID array missing or malformed')
        count = len(ids)
        for key, width in [('positions', 3), ('normals', 3), ('tangents', 4), ('rest_positions', 3), ('rest_normals', 3)]:
            array = part.get(key)
            require(isinstance(array, list) and len(array) == count and all(numeric_vector(row, width) for row in array), 'part array missing or malformed: ' + key)
        indices = part.get('indices')
        require(isinstance(indices, list) and indices and len(indices) % 3 == 0
                and all(type(x) is int and 0 <= x < count for x in indices), 'part triangle indices missing or malformed')
        rows = part.get('full_joint_influences')
        require(isinstance(rows, list) and len(rows) == count and all(isinstance(row, list) and row for row in rows), 'part full influence rows absent')
        for row in rows:
            require(all(isinstance(pair, list) and len(pair) == 2 and type(pair[0]) is int and 0 <= pair[0] < 53
                        and finite(pair[1]) and pair[1] > 0 for pair in row), 'part influence pair malformed')
        for key in ['model_to_world', 'display_transform']:
            require(numeric_vector(part.get(key), 16), 'part transform missing or malformed')
    return next(p for p in parts if p['name'] == 'body')


def empty_runtime(value):
    return value is None or (isinstance(value, dict) and set(value) == {'accessories'} and value['accessories'] is None)


def verify(request, report, frame):
    require(report.get('phase') == 'captured' and report.get('request') == request, 'report request is not current captured request')
    require(frame.get('request') == request, 'frame request differs')
    require(report.get('geometry_equal') is True and frame.get('geometry_equal') is True, 'geometry equality proof absent')
    hashes = [report.get('geometry_before_sha256'), report.get('geometry_after_sha256'),
              frame.get('geometry_before_sha256'), frame.get('geometry_after_sha256')]
    require(all(isinstance(value, str) and SHA.fullmatch(value) for value in hashes) and len(set(hashes)) == 1,
            'report/frame geometry hashes differ or are invalid')
    snapshot = frame.get('snapshot')
    require(isinstance(snapshot, dict) and snapshot.get('schema_version') == 1 and snapshot.get('profile_id') == 'nvwa-mpfb-b1-motion-v1', 'actual B1 motion snapshot required')
    body = basic_snapshot(snapshot)
    require(type(snapshot.get('generation')) is int and type(snapshot.get('revision')) is int, 'generation/revision absent')
    require(report.get('applied_generation') == snapshot['generation'] == report.get('requested_published_generation'), 'generation mismatch')
    require(report.get('identity', {}).get('revision') == snapshot['revision'], 'revision mismatch')
    require(report.get('sample') == snapshot.get('sample') and isinstance(snapshot.get('sample'), dict), 'sample mismatch')
    require(type(snapshot['sample'].get('serial')) is int, 'actual published sample serial required')
    require(report.get('parameters') == snapshot.get('parameters'), 'parameter mismatch')
    require(report.get('desired') == report.get('applied') and report.get('applied') in {'baseline', 'skin', 'skin+eyes+hair'}, 'mode mismatch')
    expected_mode = {'baseline': 'baseline', 'skin': 'skin', 'accessories': 'skin+eyes+hair'}.get(request['action'])
    require(expected_mode is None or report['applied'] == expected_mode, 'requested action/current applied mode mismatch')
    for appearance in [report.get('appearance'), frame.get('appearance')]:
        require(isinstance(appearance, dict), 'report/frame appearance observations required')
        require(appearance.get('state') == ('plain' if report['applied'] == 'baseline' else 'skin'), 'body appearance/mode mismatch')
        require(appearance.get('body_mesh') == body['mesh_handle'] and appearance.get('display_entity') == body['display_entity'], 'appearance/body binding mismatch')
        require(isinstance(appearance.get('material_handle'), str) and appearance['material_handle'] and appearance.get('not_saved') is True, 'actual unsaved material observation absent')
        if report['applied'] != 'skin+eyes+hair':
            require('accessory_runtime' in appearance and empty_runtime(appearance['accessory_runtime']), 'accessory evidence outside current mode')
    if request['action'] == 'sample':
        for key in ['torso_length', 'jaw_drop']:
            require(snapshot.get('parameters', {}).get(key) == request[key], 'requested shape mismatch')
        sample = snapshot['sample']
        require(sample.get('clip_id') == request['clip_id'] and sample.get('timeline_id') == 'probe-entry', 'requested authored clip mismatch')
        require(finite(sample.get('source_seconds')) and abs(sample['source_seconds'] - request['seconds']) <= 1e-6, 'requested source time mismatch')
        require(sample.get('playing') is False, 'sample must be held for screenshot')
    if report['applied'] == 'skin+eyes+hair':
        runtime = frame['appearance'].get('accessory_runtime')
        compact = report['appearance'].get('accessory_runtime')
        require(isinstance(runtime, dict) and isinstance(compact, dict), 'report/frame accessory proof absent')
        require(compact.get('generation') == snapshot['generation'] and compact.get('revision') == snapshot['revision']
                and compact.get('sample') == snapshot['sample'] and compact.get('identity') == runtime.get('identity'), 'compact accessory proof identity mismatch')
        require(runtime.get('generation') == snapshot['generation'] and runtime.get('revision') == snapshot['revision']
                and runtime.get('sample') == snapshot['sample'], 'accessory proof identity mismatch')
        rows = runtime.get('accessories')
        require(isinstance(rows, list) and len(rows) == 2 and {row.get('name') for row in rows} == {'eyes', 'hair'}, 'exact eyes/hair proof required')
    return snapshot


def collect(args):
    command, report_path, frame_path, output = map(absolute_path, [args.command_file, args.report_file, args.frame_file, args.out])
    require(len({str(p.resolve()) for p in [command, report_path, frame_path]}) == 3, 'channels must be distinct')
    require(not output.exists(), 'output directory must be new; no overwrite')
    require(all(not p.resolve().is_relative_to(output.resolve()) for p in [command, report_path, frame_path]), 'channels must be outside collection output')
    protected = [Path(__file__).resolve()] if '__file__' in globals() else []
    if args.manifest:
        protected.append(absolute_path(args.manifest).resolve())
    if args.binary:
        protected.append(absolute_path(args.binary).resolve())
    for input_path in protected:
        for target in [command, report_path, frame_path, output]:
            resolved = target.resolve()
            require(not (resolved == input_path or resolved.is_relative_to(input_path) or input_path.is_relative_to(resolved)),
                    'channel/output aliases or overlaps protected input')
    require(0 < args.timeout <= 60, 'timeout must be greater than0 and at most60seconds')
    if args.request_json:
        require(not args.case, '--case requires --manifest')
        request = parse(args.request_json.encode())
    else:
        require(args.case is not None, '--manifest requires one explicit --case')
        manifest_path = absolute_path(args.manifest)
        manifest = parse(read_bounded(manifest_path))
        matches = [case for case in manifest['cases'] if case.get('case_id') == args.case]
        require(len(matches) == 1, 'manifest case must match exactly one entry')
        request = matches[0]['native_request']
    validate_request(request)
    binary_sha = args.binary_sha256
    if binary_sha is not None:
        require(SHA.fullmatch(binary_sha), 'invalid binary SHA256')
    if args.binary:
        binary = absolute_path(args.binary)
        with binary.open('rb') as source:
            actual = hashlib.file_digest(source, 'sha256').hexdigest()
        require(binary_sha is None or binary_sha == actual, 'provided binary SHA256 does not match file')
        binary_sha = actual
    output.mkdir(exist_ok=False)
    receipt = {'schema_version': 1, 'kind': 'collector assembly', 'scope': 'tool pipeline; no GPU readback, pixel or quality claim',
               'request': request, 'channels': {'command': str(command), 'report': str(report_path), 'frame': str(frame_path)},
               'binary_sha256': binary_sha, 'started_unix_seconds': time.time(), 'status': 'pending', 'observations': []}
    try:
        try:
            previous = read_bounded(command)
            write_new(output / 'original-command.raw', previous)
            receipt['original_command'] = {'existed': True, 'bytes': len(previous), 'sha256': digest(previous)}
            try:
                previous_request = parse(previous)
            except (UnicodeError, ValueError):
                previous_request = None
            if isinstance(previous_request, dict):
                require(previous_request.get('request_id') != request['request_id'], 'request_id must differ from existing command; no ambiguous replay')
        except FileNotFoundError:
            receipt['original_command'] = {'existed': False}
            write_new(output / 'original-command-absent.json', encode(receipt['original_command']))
        pre_send_report_sha = None
        for name, channel in [('report', report_path), ('frame', frame_path)]:
            try:
                previous_channel = read_bounded(channel)
                write_new(output / ('original-' + name + '.raw'), previous_channel)
                if name == 'report':
                    pre_send_report_sha = digest(previous_channel)
                    receipt['pre_send_report_sha256'] = pre_send_report_sha
                try:
                    previous_value = parse(previous_channel)
                except (UnicodeError, ValueError):
                    previous_value = None
                if isinstance(previous_value, dict):
                    require(previous_value.get('request', {}).get('request_id') != request['request_id'], 'request_id already exists in prior ' + name + '; use a fresh ID')
            except FileNotFoundError:
                pass
        raw_request = encode(request)
        write_new(output / 'sent-command.raw', raw_request)
        temporary = command.parent / ('.' + command.name + '.collector-' + uuid.uuid4().hex)
        write_new(temporary, raw_request)
        os.replace(temporary, command)
        receipt['sent_unix_seconds'] = time.time()
        deadline = time.monotonic() + args.timeout
        last_report_sha = last_frame_sha = None
        while time.monotonic() < deadline:
            try:
                raw_report = read_bounded(report_path)
                if digest(raw_report) != last_report_sha:
                    receipt['observations'].append(save_observation(output, 'report-observed', raw_report, report_path))
                    last_report_sha = digest(raw_report)
                report = parse(raw_report)
                require(isinstance(report, dict), 'report object required')
                if report.get('phase') == 'error':
                    if digest(raw_report) == pre_send_report_sha:
                        # Only this exact already-observed pre-send report is old input state.
                        # It cannot succeed; unchanged persistence still reaches the deadline.
                        time.sleep(0.05)
                        continue
                    raise RuntimeError('runtime report error: ' + str(report.get('error', 'unspecified'))[:300])
                if report.get('phase') != 'captured' or report.get('request') != request:
                    time.sleep(0.05)
                    continue
                raw_frame = read_bounded(frame_path)
                if digest(raw_frame) != last_frame_sha:
                    receipt['observations'].append(save_observation(output, 'frame-observed', raw_frame, frame_path))
                    last_frame_sha = digest(raw_frame)
                frame = parse(raw_frame)
                require(isinstance(frame, dict), 'frame object required')
                if frame.get('request') != request:
                    time.sleep(0.05)
                    continue
                snapshot = verify(request, report, frame)
                # Reread current report: a frame from a moving/stale report is not accepted.
                require(read_bounded(report_path) == raw_report, 'report changed during frame collection')
                if time.monotonic() > deadline:
                    raise TimeoutError('deadline reached during report/frame verification')
                write_new(output / 'report.raw', raw_report)
                write_new(output / 'frame.raw', raw_frame)
                envelope = {'request': request, 'report': report, 'frame': frame}
                envelope_raw = (json.dumps(envelope, allow_nan=False, separators=(',', ':')) + '\n').encode()
                write_new(output / 'envelope.json', envelope_raw)
                receipt.update(status='captured', generation=snapshot['generation'], revision=snapshot['revision'], sample=snapshot['sample'],
                               artifacts={name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in
                                          [('report.raw', raw_report), ('frame.raw', raw_frame), ('envelope.json', envelope_raw)]})
                break
            except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
                time.sleep(0.05)
        else:
            raise TimeoutError('deadline reached without a matching current report/frame')
    except Exception as error:
        receipt.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        receipt['finished_unix_seconds'] = time.time()
        write_new(output / 'receipt.json', encode(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['command-file', 'report-file', 'frame-file', 'out']:
        parser.add_argument('--' + name, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--request-json')
    group.add_argument('--manifest')
    parser.add_argument('--case')
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--binary')
    parser.add_argument('--binary-sha256')
    args = parser.parse_args()
    try:
        receipt = collect(args)
        print('CAPTURED ' + receipt['request']['request_id'] + ' ' + str(Path(args.out) / 'receipt.json'))
        return 0
    except Exception as error:
        print('FAILED ' + type(error).__name__ + ': ' + str(error)[:400], file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
