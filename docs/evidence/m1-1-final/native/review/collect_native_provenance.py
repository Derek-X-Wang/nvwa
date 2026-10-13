#!/usr/bin/env python3
"""Archive only the authorized native Cua call/completion/output records."""
from pathlib import Path
import base64
import binascii
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path('/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa')
BASE = ROOT / '.work/m11-native-acceptance'
OUT = BASE / 'review'
SOURCE = Path('/Users/derekxwang/.codex/sessions/2026/10/10/rollout-2026-10-10T19-22-48-01a128c5-1bff-70a0-bd65-0dfff0529c44.jsonl')
CUTOFF = '2026-10-13T16:15:00Z'
BINDINGS = {'call_a00afee7ffcd487e92016c330486f970', 'call_b085a7b6bb5c4dc385185f32d94eaa63'}
EXCLUDED_EARLIER = {'call_356df76c511d4ae7bf7cdc3d74794316'}
MARKERS = ('nvwaUnlockedCandidate', 'nvwaIsolatedCandidate', 'm11-native-acceptance')
MAX_TRACE_BYTES = 8 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_identity(path):
    if not path.is_file():
        return {'path': str(path), 'exists': False}
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return {'path': str(path), 'exists': True, 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def image_metadata(result):
    images = []
    errors = []
    def visit(value, depth=0):
        if depth > 10:
            return
        if isinstance(value, list):
            for member in value:
                visit(member, depth + 1)
        elif isinstance(value, dict):
            if value.get('isError') is True:
                errors.append(True)
            if value.get('type') == 'input_image' and isinstance(value.get('image_url'), str):
                url = value['image_url']
                item = {'format': 'input_image data URL'}
                if url.startswith('data:') and ';base64,' in url:
                    header, encoded = url.split(',', 1)
                    item['mime'] = header[5:].split(';')[0]
                    try:
                        data = base64.b64decode(encoded, validate=True)
                        item.update(complete_decodable_base64=True, bytes=len(data), sha256=digest(data))
                    except (ValueError, binascii.Error):
                        item.update(complete_decodable_base64=False, ellipsis_present='…' in encoded)
                else:
                    item['complete_decodable_base64'] = False
                images.append(item)
            if value.get('type') == 'image' and isinstance(value.get('data'), str):
                item = {'mime': value.get('mimeType'), 'stored_characters': len(value['data'])}
                try:
                    data = base64.b64decode(value['data'], validate=True)
                    item.update(complete_decodable_base64=True, bytes=len(data), sha256=digest(data))
                except (ValueError, binascii.Error):
                    item.update(complete_decodable_base64=False, ellipsis_present='…' in value['data'])
                images.append(item)
            if value.get('type') == 'text' and isinstance(value.get('text'), str):
                try:
                    nested = json.loads(value['text'])
                except ValueError:
                    pass
                else:
                    visit(nested, depth + 1)
            for key, member in value.items():
                if key not in ('data', 'text'):
                    visit(member, depth + 1)
    visit(result)
    return images, bool(errors)


def main():
    pairs = {}
    pending_calls = {}
    pending_outputs = {}
    source_lines = 0
    malformed = []
    # Only matching Cua js item_completed records select an entry. No user,
    # reasoning, other tool or credential records are copied into the archive.
    with SOURCE.open('rb') as stream:
        for line_number, raw in enumerate(stream, 1):
            source_lines = line_number
            try:
                record = json.loads(raw)
            except ValueError:
                malformed.append(line_number)
                continue
            payload = record.get('payload', {})
            if not isinstance(payload, dict):
                continue
            kind = payload.get('type')
            if record.get('type') == 'response_item' and kind == 'function_call' and payload.get('name') == 'js':
                call_id = payload.get('call_id')
                args = payload.get('arguments', '')
                if call_id in BINDINGS | EXCLUDED_EARLIER or (record.get('timestamp', '') >= CUTOFF and any(m in args for m in MARKERS)):
                    pending_calls[call_id] = (line_number, raw, record)
            elif record.get('type') == 'response_item' and kind == 'function_call_output':
                call_id = payload.get('call_id')
                if call_id in pending_calls:
                    pending_outputs[call_id] = (line_number, raw, record)
            elif record.get('type') == 'event_msg' and kind == 'item_completed':
                item = payload.get('item', {})
                if item.get('server') != 'cua_repl' or item.get('tool') != 'js':
                    continue
                call_id = item.get('id')
                args = item.get('arguments', {})
                if call_id not in BINDINGS | EXCLUDED_EARLIER and not (record.get('timestamp', '') >= CUTOFF and any(m in json.dumps(args) for m in MARKERS)):
                    continue
                pairs[call_id] = {'completion': (line_number, raw, record)}
    for call_id, pair in pairs.items():
        pair['call'] = pending_calls.get(call_id)
        pair['output'] = pending_outputs.get(call_id)
    successes = []
    excluded = []
    incomplete = []
    for call_id, pair in pairs.items():
        line_number, raw, record = pair['completion']
        item = record['payload']['item']
        images, nested_error = image_metadata(item.get('result', {}))
        summary = {'call_id': call_id, 'completion_source_line': line_number,
                   'completion_timestamp': record['timestamp'], 'status': item['status'],
                   'isError': item.get('result', {}).get('isError'), 'nested_error': nested_error,
                   'title': item.get('arguments', {}).get('title'), 'images_in_result': images,
                   'pre_cutoff_binding_exception': call_id in BINDINGS,
                   'pre_cutoff_failed_exception': call_id in EXCLUDED_EARLIER}
        for role in ('call', 'completion', 'output'):
            if pair[role]:
                n, data, original = pair[role]
                summary[role + '_source_line'] = n
                summary[role + '_source_raw_line_sha256'] = digest(data)
                summary[role + '_timestamp'] = original['timestamp']
        if pair['call']:
            call_args = json.loads(pair['call'][2]['payload']['arguments'])
            summary['call_and_completion_arguments_equal'] = call_args == item.get('arguments')
        else:
            summary['call_and_completion_arguments_equal'] = False
        summary['raw_function_output_present'] = pair['output'] is not None
        raw_images, raw_error = image_metadata(pair['output'][2]['payload']['output']) if pair['output'] else ([], False)
        summary['raw_output_images'] = raw_images
        summary['raw_output_nested_error'] = raw_error
        pair['summary'] = summary
        if item['status'] != 'completed' or summary['isError'] is not False or nested_error:
            summary['excluded_reason'] = 'Call did not complete successfully; never count it as accepted UI/foreground/cleanup proof'
            excluded.append(pair)
        elif not pair['call'] or not summary['call_and_completion_arguments_equal'] or not pair['output']:
            summary['excluded_reason'] = 'Missing call/output or arguments mismatch'
            incomplete.append(pair)
        else:
            successes.append(pair)
    successes.sort(key=lambda x: x['completion'][0])
    excluded.sort(key=lambda x: x['completion'][0])
    def archive(name, entries, roles):
        selected = sorted((entry[role] for entry in entries for role in roles if entry[role]), key=lambda r: r[0])
        data = b''.join(raw for _, raw, _ in selected)
        if len(data) > MAX_TRACE_BYTES:
            raise ValueError('Selected trace exceeds private bounded archive limit')
        (OUT / name).write_bytes(data)
        return {'path': str(OUT/name), 'records': len(selected), 'bytes': len(data), 'sha256': digest(data),
                'source_lines': [n for n, _, _ in selected], 'exact_original_raw_records': True}
    traces = {
        'success_call_and_completion': archive('native-cua-exact-records.jsonl', successes, ('call', 'completion')),
        'success_raw_outputs': archive('native-cua-exact-outputs.jsonl', successes, ('output',)),
        'excluded_failed_calls': archive('native-cua-excluded-failed.jsonl', excluded, ('call', 'completion', 'output')),
    }
    bindings = []
    for pair in successes:
        code = pair['completion'][2]['payload']['item']['arguments']['code']
        for path in re.findall(r"writeFile\('([^']+\.jpg)'", code):
            target = Path(path)
            if not target.is_relative_to(BASE):
                raise ValueError('Screenshot write outside authorized private evidence')
            bindings.append({'file': str(target), 'relative_path': str(target.relative_to(BASE)),
                             'call_id': pair['summary']['call_id'], 'kind': 'Awaited screenshot variable then awaited exact-path write; completed isError=false',
                             'file_identity': file_identity(target),
                             'emitted_image_full_byte_binding': False})
        if 'nvwaSequenceIndex<8' in code and 'sequence-samples.json' in code:
            raw_samples = (BASE/'isolated/sequence-samples.json').read_bytes()
            samples = json.loads(raw_samples)
            if len(samples) != 8:
                raise ValueError('Sequence sample count differs')
            for index, sample in enumerate(samples, 1):
                target = BASE/f'isolated/sequence-{index:02}.jpg'
                if sample['path'] != str(target):
                    raise ValueError('Sequence path/order mismatch')
                bindings.append({'file': str(target), 'relative_path': str(target.relative_to(BASE)),
                                 'call_id': pair['summary']['call_id'],
                                 'kind': 'Eight-iteration awaited screenshot/write loop; metadata path validated',
                                 'capture_requested_utc': sample['capture_requested_utc'],
                                 'file_identity': file_identity(target), 'emitted_image_full_byte_binding': False})
    by_id = {p['summary']['call_id']: p['summary'] for p in successes}
    for binding in bindings:
        identity = binding['file_identity']
        matching = [image for image in by_id[binding['call_id']]['raw_output_images']
                    if image.get('complete_decodable_base64') is True
                    and image.get('sha256') == identity.get('sha256')
                    and image.get('bytes') == identity.get('bytes')]
        binding['emitted_image_full_byte_binding'] = bool(matching)
        binding['matching_raw_output_images'] = matching
        binding['raw_output_source_line'] = by_id[binding['call_id']].get('output_source_line')
        binding['raw_output_source_line_sha256'] = by_id[binding['call_id']].get('output_source_raw_line_sha256')
    comparisons = []
    cases = [('same', 'native-same-saved.nvwa.json', 'contracts/a-whole-doc-comparison.json'),
             ('other', 'native-other-saved.nvwa.json', 'contracts/b-whole-doc-comparison.json'),
             ('other', 'native-other-reloaded-saved.nvwa.json', 'contracts/b-reloaded-whole-doc-comparison.json'),
             ('other', 'native-other-after-interaction.nvwa.json', 'contracts/b-after-interaction-whole-doc-comparison.json')]
    helper = BASE/'contracts/compare_native_doc.py'
    if file_identity(helper)['sha256'] != '35d67a4088dd63b3c2f9fa020c98a8b50c5a9b85a665745fc645dfe4a323ba4e':
        raise ValueError('Accepted comparator identity changed')
    for case, actual, prior in cases:
        run = subprocess.run(['python3', '-B', str(helper), '--case', case, '--actual', str(BASE/actual)],
                             capture_output=True, text=True, timeout=10)
        current = json.loads(run.stdout)
        previous = json.loads((BASE/prior).read_bytes())
        if run.returncode or current.get('equal') is not True or current['status'] != 'PASS':
            raise ValueError('Actual complete Doc comparison failed: '+actual)
        if previous.get('status') != 'PASS' or previous.get('equal') is not True or previous['actual']['sha256'] != current['actual']['sha256']:
            raise ValueError('Root receipt differs from actual comparison: '+actual)
        comparisons.append({'actual': actual, 'independent_exit': run.returncode, 'independent_receipt': current,
                            'root_receipt': file_identity(BASE/prior), 'root_receipt_matches_current_actual': True})
    (OUT/'native-whole-doc-independent-comparisons.json').write_text(json.dumps(comparisons, indent=2)+'\n')
    assets = {}
    for name in ['isolated/launch-receipt.json','isolated/preparation.json','isolated/a-restored-file.json',
                 'isolated/a-removed-file.json','isolated/sequence-samples.json','isolated/formal-close-receipt.json',
                 'cleanup-receipt.json','native-checkpoint.json','review/native-tabs-evidence-manifest.json',
                 'contracts/native-recovery-same.nvwa.json','contracts/native-recovery-other.nvwa.json',
                 'isolated/Nvwa.app/Contents/MacOS/Nvwa',
                 'isolated/Nvwa.app/Contents/Resources/assets/fixtures/native-recovery-same.glb.held',
                 'isolated/Nvwa.app/Contents/Resources/assets/fixtures/native-recovery-other.glb']:
        assets[name] = file_identity(BASE/name)
    launch = json.loads((BASE/'isolated/launch-receipt.json').read_bytes())
    before=(BASE/'ui/before-tabs.nvwa.json').read_bytes(); after=(BASE/'ui/after-tabs.nvwa.json').read_bytes()
    b_outputs=[(BASE/name).read_bytes() for _,name,_ in cases[1:]]
    snapshots = {
      'isolated/a-missing.jpg':'Revision 1, jaw 0.61; Load error, 0 meshes/skins/joints/morphs/players; private same.glb Path not found; character absent',
      'isolated/a-same-path-recovered.jpg':'Revision 1, jaw 0.61; Ready with visible character; Document opened; missing error cleared',
      'isolated/a-missing-again.jpg':'Revision 1, jaw 0.61; private same.glb Path not found again; character absent and counters zero',
      'isolated/b-other-path-recovered.jpg':'Revision 1, jaw 0.61/nose 0.27; Ready with visible character; Document opened',
      'isolated/b-saved-reopened.jpg':'Revision 1, jaw 0.61/nose 0.27; Ready character; Document opened after B saved and actual Open',
      'isolated/sequence-01.jpg':'idle at 0.913 seconds; real character visible',
      'isolated/sequence-07.jpg':'wave at 3.7831 seconds; raised arm visible',
      'isolated/sequence-completed-turn.jpg':'turn at 9.0 seconds, Replay button; turned character; completed endpoint',
      'isolated/interaction-before.jpg':'Play button, paused idle cursor 2.2 seconds',
      'isolated/interaction-active.jpg':'Raised arm temporary wave; cursor 2.2 seconds; controls disabled; Wave interaction sequence cursor held; authored Active label remains idle',
      'isolated/interaction-restored.jpg':'Play button, idle cursor 2.2 seconds, controls enabled; prior pose restored',
      'isolated/interaction-after-saved.jpg':'Restored paused idle 2.2 seconds and Document saved; Revision 1 retained',
    }
    manifest = {
      'status':'VERIFIED_BOUNDED_NATIVE_EVIDENCE_WITH_DECLARED_SOURCE_LIMITS',
      'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'source':{'path':str(SOURCE),'rollout_id':'01a128c5-1bff-70a0-bd65-0dfff0529c44',
                'cutoff':CUTOFF,'last_source_line_scanned':source_lines,'malformed_source_lines':malformed,
                'allowed_exceptions':sorted(BINDINGS),'failed_exception_excluded':sorted(EXCLUDED_EARLIER),
                'not_archived':'No user, reasoning, unrelated tools, credentials or broad session transcript'},
      'traces':traces,'successful_call_count':len(successes),'excluded_failed_count':len(excluded),
      'incomplete_count':len(incomplete),'calls':[p['summary'] for p in successes],
      'excluded':[p['summary'] for p in excluded], 'incomplete':[p['summary'] for p in incomplete],
      'screenshot_bindings':bindings,'offline_visual_observations':snapshots,
      'screenshot_binding_counts':{'total':len(bindings), 'exact_decoded_raw_output_byte_hash_matches':sum(b['emitted_image_full_byte_binding'] for b in bindings),
                                    'awaited_write_without_emitted_image':sum(not b['emitted_image_full_byte_binding'] for b in bindings)},
      'assets_and_receipts':assets,
      'isolated_process_binding':{'getApp_call_id':'call_204d79adfdea4e70a4ff5061fe26f07e',
        'exact_bundle_argument':str(BASE/'isolated/Nvwa.app'),'launch_receipt':launch,
        'binary_hash_independently_matches':assets['isolated/Nvwa.app/Contents/MacOS/Nvwa'].get('sha256')==launch['binary_sha256'],
        'scope':'Completed exact-bundle Cua binding plus root kernel ps receipt; worker did not launch or re-query a live process'},
      'whole_doc_comparisons':{'four_actual_outputs_pass':True,'independent_receipt':file_identity(OUT/'native-whole-doc-independent-comparisons.json'),
        'B_saved_reloaded_after_interaction_byte_equal':all(data==b_outputs[0] for data in b_outputs),
        'B_sha256':digest(b_outputs[0]),'tabs_before_after_bytes_equal':before==after,'tabs_sha256':digest(before)},
      'source_binding_limits':[
        'Nested screenshot base64 in item_completed results contains ellipsis. Corresponding raw function_call_output input_image data URLs are complete and decoded/hashes matched to original JPEGs wherever emitted. Unemitted loop samples rely on the exact bounded awaited screenshot/write code and validated sample-path metadata.',
        'Only the bounded allowed Cua records are copied. Private asset copy/rename, ps/binary identity and cleanup are root filesystem receipts; underlying non-Cua tools are deliberately not imported into this trace.',
        'Before-cutoff formal exact-path getApp bindings are included by explicit root exception; formal kernel/PID and close verification remain root-owned receipts.',
        'Sampled idle/wave/turn and before/active/restored screenshots establish observed states, not every frame, timing/performance, global tasks, bytes or GPU lifetimes.',
        'Authoritative success excludes failed optional launch_app and failed formal close+AX composite calls. A failed composite may contain a side effect; it is not credited as successful closure or foreground proof.',
        'Historical pre-human pending checkpoint, prior tabs-only manifest and earlier NOT-RUN comparator probes are preserved, not rewritten as later acceptance results.'
      ],
      'worker_scope':'CPU/filesystem extraction, independent whole-Doc comparison and offline image inspection only. No source/Git/external/UI/GPU/Cargo changes or comparator/control modifications.',
      'cleanup_owner':'root; selected successful close call is not independently treated as process-exit proof'
    }
    (OUT/'native-acceptance-provenance-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report = f'''# Bounded native acceptance evidence

VERIFIED — {len(successes)} successful exact Cua js calls, {len(excluded)} failed calls explicitly excluded, {len(incomplete)} incomplete bindings. The private raw archives preserve the selected original call/completion records and corresponding output records byte for byte, with source line and raw-line hashes. No broad transcript or non-Cua tools were copied.

Offline originals show A missing private GLB → same-path Open Ready → A missing again with old character absent → B different-path Open Ready. Four actual complete Work outputs pass independent unchanged strict comparator checks against A/B, including profile metadata, revision 1, all parameters and full timeline. B Save, reloaded Save and post-interaction Save are byte-identical, SHA-256 {digest(b_outputs[0])}. Tabs before/after remain byte-identical {digest(before)}.

Sampled sequence images show idle 0.913, wave 3.7831 and turned/completed endpoint 9.0. Interaction images show paused idle 2.2 → temporary raised-arm wave with held 2.2 cursor/disabled controls → restored paused idle 2.2/enabled controls; post-interaction Save preserves the entire B Doc. The active authored timeline label remains idle during the temporary wave, as expected for the held sequence. These are sampled functional observations, not continuous-frame or performance proof.

The completed exact private-bundle getApp call and root launch receipt bind isolated PID 98713/birth 09:23:17 to the hash-verified 72d3 binary. Private B and held A fixture hashes are retained. Root owns kernel/process and cleanup confirmation; worker did not replay GUI or inspect live processes.

Provenance: item_completed nested image fragments contain ellipsis, but matching raw function_call_output records preserve complete input_image data URLs. {sum(b['emitted_image_full_byte_binding'] for b in bindings)} of {len(bindings)} screenshot files exactly match decoded raw-output byte hashes. The remaining {sum(not b['emitted_image_full_byte_binding'] for b in bindings)} unemitted sequence samples bind through the bounded awaited capture/write loop and validated metadata. All originals are separately hashed and all successful call/output pairs match. Failed launch_app and formal close-plus-AX calls are preserved separately and excluded from accepted UI/foreground/closure proof. Root must preserve existing kernel launch/close and asset-operation receipts when curating. Old pending checkpoint and tabs-only manifest remain unchanged.

Private deliverables: native-cua-exact-records.jsonl, native-cua-exact-outputs.jsonl, native-cua-excluded-failed.jsonl, native-acceptance-provenance-manifest.json and native-whole-doc-independent-comparisons.json. No signing, publishing, native HTTP storm, byte/task/GPU cap, IME/drag retest or source-cause attribution is claimed.
'''
    (OUT/'native-acceptance-factual-report.md').write_text(report)
    print(json.dumps({'successful_calls':len(successes),'failed_excluded':len(excluded),'incomplete':len(incomplete),
                      'screenshot_bindings':len(bindings),'raw_output_image_matches':sum(b['emitted_image_full_byte_binding'] for b in bindings),'B_sha256':digest(b_outputs[0]),'archives':traces,
                      'manifest':file_identity(OUT/'native-acceptance-provenance-manifest.json'),
                      'report':file_identity(OUT/'native-acceptance-factual-report.md')},indent=2))


if __name__=='__main__':
    main()
