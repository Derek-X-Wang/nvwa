#!/usr/bin/env python3
"""Isolated job/artifact import seam. No model execution or network behavior."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct

MAX_JSON = 2 * 1024 * 1024
MAX_ARTIFACT = 16 * 1024 * 1024


class ArtifactError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f'{code}: {message}')


def fail(code, message):
    raise ArtifactError(code, message)


def strict_json(data):
    if len(data.encode()) > MAX_JSON:
        fail('input_too_large', 'JSON exceeds 2 MiB')
    def object_(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                fail('invalid_json', f'duplicate key {key}')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=object_, parse_constant=lambda _: fail('invalid_json', 'nonfinite JSON'))
    except (json.JSONDecodeError, RecursionError) as error:
        fail('invalid_json', str(error))


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        fail('invalid_schema', 'missing or unknown fields')


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        fail('invalid_schema', f'{label} must not be empty')


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail('invalid_schema', f'{label} must be finite numeric data')


def parse_job(data):
    job = strict_json(data)
    fields(job, ['schema_version', 'job_id', 'prompt', 'duration_seconds', 'seed', 'backend'])
    if type(job['schema_version']) is not int or job['schema_version'] != 1:
        fail('unsupported_schema', 'expected job schema 1')
    for name in ['job_id', 'prompt']:
        nonempty(job[name], name)
    number(job['duration_seconds'], 'duration')
    if not 0 < job['duration_seconds'] <= 10:
        fail('out_of_range', 'duration must be in (0,10] seconds')
    if type(job['seed']) is not int or not 0 <= job['seed'] <= 2**32-1:
        fail('out_of_range', 'seed must be a u32')
    if job['backend'] not in ['preset_import', 'kimodo_local']:
        fail('invalid_backend', 'unknown backend')
    return job


def glb_decode(data):
    if len(data) < 12 or data[:4] != b'glTF' or struct.unpack_from('<II', data, 4) != (2, len(data)):
        fail('invalid_artifact', 'invalid GLB header')
    chunks, offset = {}, 12
    while offset < len(data):
        if offset+8 > len(data):
            fail('invalid_artifact', 'truncated chunk header')
        length, kind = struct.unpack_from('<II', data, offset)
        offset += 8
        if length % 4 or offset+length > len(data) or kind in chunks:
            fail('invalid_artifact', 'invalid chunk')
        if not chunks and kind != 0x4E4F534A:
            fail('invalid_artifact', 'JSON must be first')
        chunks[kind] = data[offset:offset+length]
        offset += length
    if set(chunks) != {0x4E4F534A, 0x004E4942}:
        fail('invalid_artifact', 'requires JSON and BIN chunks')
    try:
        doc = strict_json(chunks[0x4E4F534A].decode())
    except UnicodeDecodeError:
        fail('invalid_artifact', 'GLB JSON must be UTF-8')
    return doc, chunks[0x004E4942]


def animation_duration(doc, binary, name):
    if doc.get('asset', {}).get('version') != '2.0':
        fail('invalid_artifact', 'requires glTF2')
    animations = [a for a in doc.get('animations', []) if a.get('name') == name]
    if len(animations) != 1 or not animations[0].get('channels'):
        fail('missing_animation', 'named animation missing or empty')
    duration = 0.
    try:
        for channel in animations[0]['channels']:
            node = channel['target']['node']
            if type(node) is not int or not 0 <= node < len(doc['nodes']):
                fail('invalid_reference', 'animation node out of range')
            sampler = animations[0]['samplers'][channel['sampler']]
            accessor = doc['accessors'][sampler['input']]
            view = doc['bufferViews'][accessor['bufferView']]
            if accessor['type'] != 'SCALAR' or accessor['componentType'] != 5126 or accessor['count'] < 2 or view.get('buffer', 0) != 0:
                fail('invalid_artifact', 'unsupported animation time accessor')
            offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            stride = view.get('byteStride', 4)
            times = [struct.unpack_from('<f', binary, offset + i*stride)[0] for i in range(accessor['count'])]
            if any(not math.isfinite(t) or t < 0 for t in times) or any(a >= b for a, b in zip(times, times[1:])):
                fail('invalid_artifact', 'animation times must be finite/increasing')
            duration = max(duration, times[-1])
            output = doc['accessors'][sampler['output']]
            path = channel['target']['path']
            width = {'translation': 3, 'rotation': 4, 'scale': 3}.get(path)
            if width is None or output['componentType'] != 5126 or output['type'] != f'VEC{width}' or output['count'] != accessor['count']:
                fail('invalid_artifact', 'unsupported/mismatched TRS output accessor')
            output_view = doc['bufferViews'][output['bufferView']]
            if output_view.get('buffer', 0) != 0:
                fail('invalid_artifact', 'external animation buffer')
            output_offset = output_view.get('byteOffset', 0) + output.get('byteOffset', 0)
            output_stride = output_view.get('byteStride', width*4)
            for frame in range(output['count']):
                value = struct.unpack_from('<'+'f'*width, binary, output_offset+frame*output_stride)
                if any(not math.isfinite(x) for x in value):
                    fail('invalid_artifact', 'nonfinite animation value')
                if path == 'rotation' and abs(sum(x*x for x in value)-1) > 1e-4:
                    fail('invalid_artifact', 'nonunit/degenerate animation quaternion')
                if path == 'scale' and any(abs(x) < 1e-12 for x in value):
                    fail('invalid_artifact', 'degenerate animated scale')
    except (KeyError, IndexError, TypeError, struct.error) as error:
        fail('invalid_artifact', str(error))
    return duration


def import_artifact(job, manifest_data, root):
    if job['backend'] == 'kimodo_local':
        fail('inference_unavailable', 'NOT-RUN: no authorized local Kimodo runtime/weights; no fallback')
    manifest = strict_json(manifest_data)
    fields(manifest, ['schema_version', 'job_id', 'source_kind', 'ai_generated', 'model_id',
                      'license', 'source_sha256', 'artifact_path', 'artifact_sha256', 'animation_name'])
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        fail('unsupported_schema', 'expected artifact schema 1')
    if manifest['job_id'] != job['job_id']:
        fail('job_conflict', 'artifact belongs to another job')
    if manifest['source_kind'] != 'authored_preset' or manifest['ai_generated'] is not False or manifest['model_id'] is not None:
        fail('invalid_provenance', 'this experiment imports authored presets only; model generation is unavailable')
    for name in ['license', 'animation_name']:
        nonempty(manifest[name], name)
    for name in ['source_sha256', 'artifact_sha256']:
        digest = manifest[name]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            fail('invalid_provenance', f'{name} must be SHA-256 hex')
    rel = manifest['artifact_path']
    if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or any(x in ['', '.', '..'] for x in rel.split('/')) or PurePosixPath(rel).is_absolute():
        fail('unsafe_path', 'artifact path must be relative and contained')
    root = Path(root).resolve()
    path = (root/rel).resolve()
    if root not in path.parents:
        fail('unsafe_path', 'resolved artifact escapes root')
    try:
        if path.stat().st_size > MAX_ARTIFACT:
            fail('input_too_large', 'artifact exceeds 16 MiB')
        data = path.read_bytes()
    except OSError as error:
        fail('missing_artifact', str(error))
    if hashlib.sha256(data).hexdigest() != manifest['artifact_sha256']:
        fail('hash_mismatch', 'artifact bytes differ from manifest')
    doc, binary = glb_decode(data)
    duration = animation_duration(doc, binary, manifest['animation_name'])
    if abs(duration-job['duration_seconds']) > 1e-5:
        fail('duration_mismatch', 'preset cannot fulfill a different duration')
    return {'job_id': job['job_id'], 'state': 'imported', 'source_kind': 'authored_preset',
            'ai_generated': False, 'prompt_alignment_measured': False,
            'animation_name': manifest['animation_name'], 'duration_seconds': duration,
            'artifact_sha256': manifest['artifact_sha256'], 'skin_count': len(doc.get('skins', []))}
