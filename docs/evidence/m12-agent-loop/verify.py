#!/usr/bin/env python3
"""Verify complete saved Works and retained acceptance evidence, CPU only."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original_path = HERE / 'agent-input.nvwa.json'
    assert sha(original_path) == 'e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc'
    original = json.loads(original_path.read_text())
    expected_edit = copy.deepcopy(original)
    expected_edit['revision'] = 3
    expected_edit['character']['parameters']['jaw_width'] = .71
    expected_undo = copy.deepcopy(original)
    expected_undo['revision'] = 4
    expectations = {
        'web-initial-saved.nvwa.json': original,
        'web-initial-extra.nvwa.json': original,
        'native-edited.nvwa.json': expected_edit,
        'web-edited.nvwa.json': expected_edit,
        'native-undone.nvwa.json': expected_undo,
        'web-undone.nvwa.json': expected_undo,
        'web-reloaded-saved.nvwa.json': expected_undo,
    }
    comparisons = {}
    for filename, expected in expectations.items():
        actual = json.loads((HERE / filename).read_text())
        assert actual == expected, filename
        comparisons[filename] = {'whole_document_equal': True, 'revision': actual['revision'],
                                 'jaw_width': actual['character']['parameters']['jaw_width'],
                                 'sha256': sha(HERE / filename)}
    assert sha(HERE/'native-edited.nvwa.json') == sha(HERE/'web-edited.nvwa.json')
    assert sha(HERE/'native-undone.nvwa.json') == sha(HERE/'web-undone.nvwa.json')
    assert sha(HERE/'web-undone.nvwa.json') == sha(HERE/'web-reloaded-saved.nvwa.json')
    initial_attempt = json.loads((HERE / 'native-typing-attempt-rev5.nvwa.json').read_text())
    expected_attempt = copy.deepcopy(original)
    expected_attempt['revision'] = 5
    expected_attempt['character']['parameters']['jaw_width'] = .7
    assert initial_attempt == expected_attempt
    native_receipts = {}
    for log in ['native-studio.log','native-player.log']:
        lines = [line.split('NVWA_EVIDENCE ',1)[1] for line in (HERE/log).read_text().splitlines() if 'NVWA_EVIDENCE ' in line]
        assert len(lines) == 1
        receipt = json.loads(lines[0])
        assert receipt['ready'] and receipt['error'] is None
        assert receipt['document_revision'] == 2 and receipt['timeline_count'] == 3
        assert receipt['joints'] == 18 and receipt['skins'] == 9 and receipt['morph_weights'] == 4
        assert receipt['active_animations'] == 1 and receipt['capture_callback']
        native_receipts[log] = receipt
    report = {'whole_document_comparisons': comparisons,
              'cross_platform_edited_bytes_equal': True,
              'cross_platform_undo_bytes_equal': True,
              'web_reload_saved_bytes_equal': True,
              'native_typing_attempt_preserved_but_not_acceptance_cycle': True,
              'native_renderer_receipts': native_receipts,
              'web_evidence_boundary': 'Actual visible WebGPU scene and UI plus downloaded full Works; browser console and GPU timing were not inspected.'}
    (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 7 complete Work comparisons, cross-platform saved bytes, Web reload-save bytes, and 2 native renderer receipts.')

if __name__ == '__main__':
    main()
