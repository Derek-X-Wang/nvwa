"""Lossless, ordered, bounded evidence frames; base64 never executes workflow commands."""
import base64
import hashlib
import json
from pathlib import PurePosixPath
import re

RAW_MAX = 4194304
WIRE_MAX = 8388608
CHUNK = 3072
PREFIX = 'NVWA73UBUNTUFULLv1 '


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')


def encode(files, identity):
    if len(files) > 64 or sum(map(len, files.values())) > RAW_MAX:
        raise ValueError('raw evidence ceiling exceeded')
    entries = []
    for name, raw in sorted(files.items()):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('invalid evidence path')
        entries.append({'name': name, 'bytes': len(raw), 'sha256': digest(raw),
                        'chunks': (len(raw) + CHUNK - 1) // CHUNK})
    manifest = {'identity': identity, 'files': entries, 'raw_bytes': sum(map(len, files.values()))}
    lines = [PREFIX + 'BEGIN ' + base64.b64encode(canonical(manifest)).decode('ascii')]
    for i, entry in enumerate(entries):
        raw = files[entry['name']]
        for j in range(entry['chunks']):
            lines.append(PREFIX + f'DATA {i} {j} ' + base64.b64encode(raw[j*CHUNK:(j+1)*CHUNK]).decode('ascii'))
    body = ('\n'.join(lines) + '\n').encode('ascii')
    wire = body + (PREFIX + 'END ' + digest(body) + '\n').encode('ascii')
    if len(wire) > WIRE_MAX:
        raise ValueError('encoded evidence ceiling exceeded')
    return wire


def decode(wire, expected_identity):
    if len(wire) > WIRE_MAX or not wire.endswith(b'\n'):
        raise ValueError('wire ceiling or missing terminal newline')
    lines = wire.decode('ascii').splitlines()
    if not lines or not lines[0].startswith(PREFIX + 'BEGIN ') or not lines[-1].startswith(PREFIX + 'END '):
        raise ValueError('missing envelope')
    body = ('\n'.join(lines[:-1]) + '\n').encode('ascii')
    if lines[-1] != PREFIX + 'END ' + digest(body):
        raise ValueError('wire digest mismatch')
    manifest = json.loads(base64.b64decode(lines[0][len(PREFIX+'BEGIN '):], validate=True))
    if manifest['identity'] != expected_identity:
        raise ValueError('run/attempt/tool identity mismatch')
    if len(manifest['files']) > 64:
        raise ValueError('file count ceiling')
    files = {}
    cursor = 1
    total = 0
    prior_name = ''
    for i, entry in enumerate(manifest['files']):
        name = entry['name']
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or str(path) != name
                or name <= prior_name or not isinstance(entry['bytes'], int)
                or not 0 <= entry['bytes'] <= RAW_MAX
                or entry['chunks'] != (entry['bytes'] + CHUNK - 1) // CHUNK):
            raise ValueError('invalid/duplicate/unordered file declaration')
        prior_name = name
        chunks = []
        for j in range(entry['chunks']):
            lead = PREFIX + f'DATA {i} {j} '
            if cursor >= len(lines)-1 or not lines[cursor].startswith(lead):
                raise ValueError('missing/duplicate/conflicting/out-of-order frame')
            piece = base64.b64decode(lines[cursor][len(lead):], validate=True)
            expected_len = min(CHUNK, entry['bytes'] - j*CHUNK)
            if len(piece) != expected_len:
                raise ValueError('chunk size mismatch')
            chunks.append(piece); cursor += 1
        raw = b''.join(chunks)
        total += len(raw)
        if total > RAW_MAX or len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
            raise ValueError('raw ceiling/length/hash mismatch')
        files[name] = raw
    if cursor != len(lines)-1 or total != manifest['raw_bytes']:
        raise ValueError('extra/missing frames or raw total mismatch')
    return files, manifest


def extract_log_frames(log):
    # GitHub raw job log adds one ISO timestamp. No arbitrary substring scanning.
    lines = []
    for line in log.decode('utf-8', errors='strict').splitlines():
        line = re.sub(r'^\d{4}-\d\d-\d\dT[0-9:.]+Z ', '', line)
        if line.startswith(PREFIX):
            lines.append(line)
    return ('\n'.join(lines)+'\n').encode('ascii')
