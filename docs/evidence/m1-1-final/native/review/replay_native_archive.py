#!/usr/bin/env python3
"""Read-only replay of frozen native evidence, not GUI execution."""
from pathlib import Path, PurePosixPath
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
PINNED = {
    'contracts/compare_native_doc.py': '35d67a4088dd63b3c2f9fa020c98a8b50c5a9b85a665745fc645dfe4a323ba4e',
    'contracts/expected-manifest.json': '5219a5f85f6dd4cbd1774d9bef04b1e9bb24209c1f0034a9af99c2d859e34550',
    'review/native-acceptance-provenance-manifest.json': '9d69e57bb0bc9b10118f0aae9d33f3812a154a1c21739e54f35b8e7bc2c659b7',
    'copy-manifest.initial.json': '1325c982943290098c4156135ff92fc45b31639ae38c61f4252819561b2e37fc',
    'review/provenance-copy-manifest.json': '790176fd9efe8925d5f9a0d0b81f9f1db6c5b06bb3574c6198560d05890944b6',
}


class ReplayError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ReplayError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Archive:
    def __init__(self, root):
        self.root = root.resolve()
        require(self.root.is_dir(), 'Archive root does not exist')
        self.total = 0
        self.cache = {}

    def path(self, relative):
        p = PurePosixPath(relative)
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in relative,
                'Unsafe relative archive path: ' + relative)
        target = (self.root / relative).resolve()
        require(target.is_relative_to(self.root), 'Archive path escapes root: ' + relative)
        return target

    def read(self, relative, expected_sha=None, expected_bytes=None):
        if relative not in self.cache:
            target = self.path(relative)
            require(target.is_file(), 'Missing archive file: ' + relative)
            with target.open('rb') as stream:
                data = stream.read(MAX_FILE + 1)
            require(len(data) <= MAX_FILE, 'Archive file exceeds 8 MiB: ' + relative)
            self.total += len(data)
            require(self.total <= MAX_TOTAL, 'Archive read exceeds 64 MiB total bound')
            self.cache[relative] = data
        data = self.cache[relative]
        if expected_bytes is not None:
            require(len(data) == expected_bytes, 'Byte count differs: ' + relative)
        if expected_sha is not None:
            require(sha(data) == expected_sha, 'SHA-256 differs: ' + relative)
        return data

    def json(self, relative, expected_sha=None):
        return json.loads(self.read(relative, expected_sha))


def rows(data):
    require(data.endswith(b'\n'), 'Raw JSONL archive lacks final newline')
    result = []
    for raw in data.splitlines(keepends=True):
        result.append((sha(raw), json.loads(raw)))
    return result


def images(value):
    if isinstance(value, list):
        for member in value:
            yield from images(member)
    elif isinstance(value, dict):
        if value.get('type') == 'input_image':
            url = value.get('image_url', '')
            require(url.startswith('data:') and ';base64,' in url, 'Invalid raw output image URL')
            data = base64.b64decode(url.split(',', 1)[1], validate=True)
            require(len(data) <= MAX_FILE, 'Decoded output image exceeds bound')
            yield (len(data), sha(data))
        # Raw function output images are top-level input_image blocks. Do not
        # reinterpret truncated item_completed nested image fragments.


def replay(root):
    archive = Archive(root)
    for path, pin in PINNED.items():
        archive.read(path, pin)
    # Import only the hash-pinned, unchanged helper. Do not invoke its absolute
    # path CLI/load_inputs/self_test or modify its original expected manifest.
    spec = importlib.util.spec_from_file_location('frozen_native_doc_comparator', archive.path('contracts/compare_native_doc.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = archive.json('contracts/expected-manifest.json')
    provenance = archive.json('review/native-acceptance-provenance-manifest.json')
    initial = archive.json('copy-manifest.initial.json')
    require(len(initial['files']) == 78, 'Initial-copy inventory is not exactly 78 records')
    inventory_paths = set()
    for entry in initial['files']:
        path = entry['path']
        require(path not in inventory_paths, 'Duplicate initial-copy path')
        inventory_paths.add(path)
        archive.read(path, entry['sha256'], entry['bytes'])
    compressed = archive.json('review/provenance-copy-manifest.json')
    require(len(compressed['files']) == 5, 'Frozen provenance-copy inventory must have five records')
    decoded = {}
    compressed_paths = set()
    for entry in compressed['files']:
        relative = 'review/' + entry['path']
        require(relative not in compressed_paths, 'Duplicate provenance-copy path')
        compressed_paths.add(relative)
        data = archive.read(relative, entry['sha256'], entry['bytes'])
        if 'decoded_name' in entry:
            require(relative.endswith('.gz') and 'gzip' in entry['encoding'], 'Invalid compression entry')
            require(data[:2] == b'\x1f\x8b' and data[4:8] == b'\0\0\0\0', 'Gzip must retain deterministic mtime=0')
            # Cap expanded bytes before hashing/parsing to reject decompression bombs.
            with gzip.open(archive.path(relative), 'rb') as stream:
                raw = stream.read(MAX_FILE + 1)
            require(len(raw) <= MAX_FILE, 'Decoded trace exceeds 8 MiB')
            archive.total += len(raw)
            require(archive.total <= MAX_TOTAL, 'Expanded archive exceeds total bound')
            require(len(raw) == entry['decoded_bytes'] and sha(raw) == entry['decoded_sha256'],
                    'Decoded trace identity differs: ' + relative)
            name = entry['decoded_name']
            archive.path('review/' + name)
            require(name not in decoded, 'Duplicate decoded trace')
            decoded[name] = raw
    traces = provenance['traces']
    decoded_names = {'success_call_and_completion': 'native-cua-exact-records.jsonl',
                     'success_raw_outputs': 'native-cua-exact-outputs.jsonl',
                     'excluded_failed_calls': 'native-cua-excluded-failed.jsonl'}
    trace_rows = {}
    for role, name in decoded_names.items():
        require(name in decoded, 'Missing decoded trace: ' + name)
        data = decoded[name]
        require(len(data) == traces[role]['bytes'] and sha(data) == traces[role]['sha256'],
                'Trace differs from pinned provenance: ' + name)
        parsed = rows(data)
        require(len(parsed) == traces[role]['records'], 'Trace record count differs')
        trace_rows[role] = parsed
    require(len(trace_rows['success_call_and_completion']) == 44 and len(trace_rows['success_raw_outputs']) == 22,
            'Successful trace counts differ')
    calls, completed, outputs = {}, {}, {}
    for line_sha, record in trace_rows['success_call_and_completion']:
        payload = record['payload']
        if record['type'] == 'response_item' and payload['type'] == 'function_call':
            require(payload['name'] == 'js', 'Unrelated function in success archive')
            call_id = payload['call_id']
            require(call_id not in calls, 'Duplicate successful call')
            calls[call_id] = (line_sha, payload)
        else:
            require(record['type'] == 'event_msg' and payload['type'] == 'item_completed', 'Unrelated completion record')
            item = payload['item']
            require(item['server'] == 'cua_repl' and item['tool'] == 'js', 'Unrelated completed tool')
            require(item['status'] == 'completed' and item['result']['isError'] is False, 'Failed call in successful archive')
            call_id = item['id']
            require(call_id not in completed, 'Duplicate successful completion')
            completed[call_id] = (line_sha, item)
    for line_sha, record in trace_rows['success_raw_outputs']:
        payload = record['payload']
        require(record['type'] == 'response_item' and payload['type'] == 'function_call_output', 'Unrelated output record')
        call_id = payload['call_id']
        require(call_id not in outputs, 'Duplicate successful output')
        outputs[call_id] = (line_sha, payload)
    declared = provenance['calls']
    ids = {entry['call_id'] for entry in declared}
    require(len(declared) == len(ids) == 22 and set(calls) == set(completed) == set(outputs) == ids,
            'Successful call/completion/output IDs differ')
    output_images = {}
    for entry in declared:
        call_id = entry['call_id']
        call_sha, call = calls[call_id]
        completion_sha, completion = completed[call_id]
        output_sha, output = outputs[call_id]
        require(call_sha == entry['call_source_raw_line_sha256'] and completion_sha == entry['completion_source_raw_line_sha256']
                and output_sha == entry['output_source_raw_line_sha256'], 'Exact source-line identity differs: ' + call_id)
        require(json.loads(call['arguments']) == completion['arguments'], 'Call/completion arguments differ')
        output_images[call_id] = set(images(output['output']))
    failed = [record['payload']['item'] for _, record in trace_rows['excluded_failed_calls']
              if record['type'] == 'event_msg' and record['payload'].get('type') == 'item_completed']
    require(len(trace_rows['excluded_failed_calls']) == 6 and len(failed) == 2
            and all(item['status'] == 'failed' and item['result']['isError'] is True for item in failed),
            'Excluded failure archive differs')
    bindings = provenance['screenshot_bindings']
    require(len(bindings) == 27 and len({b['relative_path'] for b in bindings}) == 27, 'Screenshot binding inventory differs')
    matched_images = 0
    for binding in bindings:
        identity = binding['file_identity']
        data = archive.read(binding['relative_path'], identity['sha256'], identity['bytes'])
        require(data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9', 'Archived screenshot is not a complete JPEG')
        require(binding['call_id'] in ids, 'Screenshot references unknown call')
        matching = (len(data), sha(data)) in output_images[binding['call_id']]
        require(matching == binding['emitted_image_full_byte_binding'], 'Raw emitted image byte binding differs')
        matched_images += int(matching)
    require(matched_images == 22, 'Expected 22 complete emitted-image byte matches')
    expected = {}
    for case in ('same', 'other'):
        record = manifest['inputs'][case]
        basename = Path(record['path']).name
        data = archive.read('contracts/' + basename, record['sha256'], record['bytes'])
        doc = module.parse(data)
        module.validate_expected(doc, manifest['comparison'])
        expected[case] = doc
    actual_cases = [('same', 'native-same-saved.nvwa.json'), ('other', 'native-other-saved.nvwa.json'),
                    ('other', 'native-other-reloaded-saved.nvwa.json'), ('other', 'native-other-after-interaction.nvwa.json')]
    actual_results = []
    for case, name in actual_cases:
        data = archive.read(name)
        result = module.compare(expected[case], module.parse(data), manifest['comparison'])
        require(result['equal'], 'Complete Doc differs: ' + name + ' ' + json.dumps(result['differences']))
        actual_results.append({'path': name, 'sha256': sha(data), 'bytes': len(data), 'whole_document_equal': True})
    before = archive.read('ui/before-tabs.nvwa.json')
    after = archive.read('ui/after-tabs.nvwa.json')
    module.parse(before)
    require(before == after and sha(before) == provenance['whole_doc_comparisons']['tabs_sha256'], 'Tabs whole-Doc byte equality differs')
    b_values = [archive.read(name) for _, name in actual_cases[1:]]
    require(all(data == b_values[0] for data in b_values) and sha(b_values[0]) == provenance['whole_doc_comparisons']['B_sha256'],
            'B saved/reloaded/post-interaction byte identity differs')
    return {'status': 'PASS', 'scope': 'Portable offline archive replay only; no native GUI or product execution',
            'initial_copy_records_checked': 78, 'initial_copy_is_not_final_directory_inventory': True,
            'provenance_copy_records_checked': 5, 'successful_calls': 22, 'excluded_failed_calls': 2,
            'screenshots_checked': 27, 'exact_raw_output_pixel_byte_matches': 22,
            'unemitted_sequence_samples_with_completed_loop_binding': 5,
            'whole_documents': actual_results, 'tabs_byte_equal': True, 'B_saved_reloaded_interaction_byte_equal': True,
            'bounded_bytes_read_and_expanded': archive.total,
            'limits': ['No GUI replay, frame/performance proof or process/cleanup re-query.',
                       'Private app bundle/binaries are intentionally absent from the portable archive; original identity receipts are retained.',
                       'Root owns the final archive inventory and any later additions.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = replay(args.root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError) as error:
        result = {'status': 'FAIL', 'reason': str(error), 'scope': 'Offline archive replay failure; no GUI claim'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
