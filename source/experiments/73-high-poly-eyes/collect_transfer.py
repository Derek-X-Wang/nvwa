#!/usr/bin/env python3
"""Reassemble bounded Web chunks without rewriting any Rust JSON number token.

Input: exact prepare/status manifest JSON and one chunk object per JSONL line.
Output is created only after full length/hash/framing checks. This is transfer
verification only; run unchanged check_captures.validate on the resulting bytes.
"""
import argparse
import base64
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def manifest_identity(manifest, expected_request_id):
    require(isinstance(manifest, dict), 'malformed transfer manifest')
    valid_id = lambda value: isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None
    require(valid_id(expected_request_id), 'valid independent expected request ID required')
    require(valid_id(manifest.get('request_id')), 'malformed manifest request ID')
    require(manifest['request_id'] == expected_request_id, 'manifest differs from expected request ID')
    # prepare() returns no ready field; visible status() adds ready:true.
    require('ready' not in manifest or manifest['ready'] is True, 'manifest is not ready')
    digest = manifest.get('sha256')
    require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'malformed envelope SHA256')
    token = manifest.get('token')
    match = re.fullmatch(r'transfer-([1-9][0-9]*)-([0-9a-f]{64})', token) if isinstance(token, str) else None
    require(match is not None and match.group(2) == digest, 'manifest token differs from envelope SHA256')


def raw_object(raw, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate raw '+label+' key: '+key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non-JSON raw '+label+' constant: '+value)
    # Parse only to check identity. Original bytes are returned unchanged.
    value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_float=Decimal, parse_constant=constant)
    require(isinstance(value, dict), 'raw '+label+' must be an object')
    return value


def assemble(manifest, chunks, *, expected_request_id):
    manifest_identity(manifest, expected_request_id)
    require(manifest.get('format') == 'nvwa73-raw-transfer-v1', 'unknown transfer format')
    require(manifest.get('encoding') == 'utf-8', 'unknown transfer encoding')
    size = manifest['bytes']
    width = manifest['chunk_bytes']
    count = manifest['chunks']
    require(type(size) is int and size > 0 and width == 32768, 'invalid transfer size')
    require(type(count) is int and count == (size + width - 1) // width, 'invalid chunk count')
    parts = {}
    for chunk in chunks:
        index = chunk['index']
        require(chunk.get('token') == manifest['token'], 'mismatched transfer token')
        require(type(index) is int and 0 <= index < count, 'chunk index out of range')
        require(index not in parts, 'duplicate chunk')
        raw = base64.b64decode(chunk['base64'], validate=True)
        require(len(raw) == min(width, size - index * width), 'truncated or oversized chunk')
        parts[index] = raw
    require(len(parts) == count, 'incomplete transfer')
    raw = b''.join(parts[i] for i in range(count))
    return verify_bytes(manifest, raw, expected_request_id=expected_request_id)


def verify_bytes(manifest, raw, *, expected_request_id):
    manifest_identity(manifest, expected_request_id)
    require(manifest.get('format') == 'nvwa73-raw-transfer-v1', 'unknown transfer format')
    require(manifest.get('encoding') == 'utf-8', 'unknown transfer encoding')
    size = manifest['bytes']
    require(type(size) is int and size > 0, 'invalid transfer size')
    require(len(raw) == size, 'transfer byte length differs')
    require(hashlib.sha256(raw).hexdigest() == manifest['sha256'], 'transfer SHA256 differs')
    text = raw.decode('utf-8', errors='strict')
    require(len(text.encode('utf-16-le')) // 2 == manifest['chars'], 'transfer character length differs')
    prefix = b'{"report":'
    middle = b',"frame":'
    require(type(manifest.get('report_bytes')) is int and manifest['report_bytes'] > 0, 'invalid report byte length')
    require(type(manifest.get('frame_bytes')) is int and manifest['frame_bytes'] > 0, 'invalid frame byte length')
    split = len(prefix) + manifest['report_bytes']
    require(raw.startswith(prefix) and raw[split:split+len(middle)] == middle and raw.endswith(b'}'), 'raw envelope framing differs')
    report = raw[len(prefix):split]
    frame = raw[split+len(middle):-1]
    require(len(frame) == manifest['frame_bytes'], 'frame length differs')
    require(hashlib.sha256(report).hexdigest() == manifest['report_sha256'], 'report SHA256 differs')
    require(hashlib.sha256(frame).hexdigest() == manifest['frame_sha256'], 'frame SHA256 differs')
    report_value = raw_object(report, 'report')
    frame_value = raw_object(frame, 'frame')
    require(report_value.get('request_id') == frame_value.get('request_id') == manifest['request_id'] == expected_request_id, 'raw record differs from manifest/expected request ID')
    require(report_value.get('phase') == 'ready' and report_value.get('current') is True and report_value.get('acknowledged') is True and report_value.get('request_succeeded') is True, 'raw report is stale or unsuccessful')
    require(isinstance(report_value.get('diagnostic'), dict), 'raw diagnostic acknowledgement required')
    require(report_value.get('endpoint') in ['web', 'native'] and report_value.get('endpoint') == frame_value.get('endpoint'), 'raw endpoint correlation differs')
    require(isinstance(report_value.get('work_sha256'), str) and report_value.get('work_sha256') and report_value.get('work_sha256') == frame_value.get('work_sha256'), 'raw Work correlation differs')
    require(type(frame_value.get('stable_updates')) is int and frame_value['stable_updates'] >= 2, 'raw stability differs')
    require(isinstance(report_value.get('captured_identity'), dict) and report_value['captured_identity'] == frame_value.get('identity'), 'raw captured identity correlation differs')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--expected-request-id', required=True, help='request ID retained independently from the issued command; never derive it from the supplied manifest')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--chunks', type=Path)
    source.add_argument('--download', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if args.download:
        if args.out:
            parser.error('--out is only used with --chunks')
        raw = verify_bytes(manifest, args.download.read_bytes(), expected_request_id=args.expected_request_id)
    else:
        if not args.out:
            parser.error('--chunks requires a fresh --out path')
        chunks = (json.loads(line) for line in args.chunks.read_text().splitlines() if line.strip())
        raw = assemble(manifest, chunks, expected_request_id=args.expected_request_id)
        with args.out.open('xb') as output:
            output.write(raw)
    print(f'EXACT TRANSFER {len(raw)} bytes SHA256 {hashlib.sha256(raw).hexdigest()}; CPU/quality validation separate')


if __name__ == '__main__':
    main()
