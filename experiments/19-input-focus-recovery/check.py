"""Check passive tab-return evidence, plus separately attributed canonical text."""
import argparse
import json
from pathlib import Path

EXPECTED = 'nvwa-issue2-before-after.nvwa.json'


def check(trace, observation=None):
    reasons = []
    failures = []
    rows = trace.get('rows', [])
    if trace.get('schema') != 1 or trace.get('kind') != 'passive-browser-capture':
        reasons.append('wrong/missing capture schema')
    if trace.get('syntheticDispatch') is not False or any(row.get('trusted') is False for row in rows if row.get('type') in {'input', 'compositionstart', 'compositionend'}):
        reasons.append('capture lacks trusted input provenance; untrusted event origin is unknown, so this trace cannot prove real browser input')
    if trace.get('dropped', 0):
        reasons.append('capture overflow; event sequence incomplete')
    initial = next((i for i, row in enumerate(rows) if row.get('type') == 'input' and row.get('trusted') is True and row.get('target') == 'nvwa_text_input' and row.get('pageFocused') is True), None)
    away = next((i for i, row in enumerate(rows) if initial is not None and i > initial and (row.get('pageFocused') is False or row.get('visibility') == 'hidden')), None)
    returned = next((i for i, row in enumerate(rows) if away is not None and i > away and row.get('pageFocused') is True and row.get('visibility') == 'visible'), None)
    resumed = next((i for i, row in enumerate(rows) if returned is not None and i >= returned and row.get('type') == 'input' and row.get('trusted') is True and row.get('target') == 'nvwa_text_input' and row.get('pageFocused') is True and not row.get('composing', False)), None)
    if initial is None:
        reasons.append('no trusted baseline input into proxy')
    if away is None:
        reasons.append('no actual page blur/hidden observation after baseline input')
    if returned is None:
        reasons.append('no visible focused return observation')
    if resumed is None:
        reasons.append('no trusted committed input into proxy after return')
    if returned is not None and resumed is not None:
        if any(row.get('type') == 'pointerdown' and row.get('target') == 'nvwa' for row in rows[returned:resumed + 1]):
            reasons.append('canvas click after return; natural recovery was not exercised')
        row = rows[resumed]
        if row.get('proxyCount') != 1 or row.get('proxyHidden') is not False or row.get('active') != 'nvwa_text_input':
            failures.append('resumed input proxy ownership/visibility is incorrect')
    canonical = 'NOT-RUN'
    if observation:
        if observation.get('returnTrigger') != 'browser-tab':
            reasons.append('departure needs observer attribution to actual browser-tab activation')
        if observation.get('baselineWork') != 'nvwa-issue2-before' or not observation.get('baselineEvidence'):
            reasons.append('exact rendered baseline Work and evidence are missing')
        if observation.get('renderedWork') != EXPECTED:
            failures.append(f'canonical Work mismatch: expected {EXPECTED!r}; see private observation')
            canonical = 'FAIL'
        elif not observation.get('renderedEvidence') or not observation.get('observer'):
            reasons.append('canonical text needs observer attribution and evidence path')
        else:
            canonical = 'PASS (observer-attributed rendered Work)'
        if 'downloadFilename' in observation and observation['downloadFilename'] != EXPECTED:
            failures.append('Save download filename does not match canonical sentinel')
    else:
        reasons.append('canonical rendered Work observation missing; DOM proxy is not canonical text')
    status = 'FAIL' if failures else 'PARTIAL' if reasons else 'PASS'
    return {'status':status,'browserEventIndices':{'baseline':initial,'away':away,'return':returned,'resumed':resumed},
        'canonical':canonical,'failures':failures,'limits':reasons,
        'physicalIME':'NOT-RUN — candidate UI requires separate physical observation',
        'zoomDPR':'NOT-RUN — geometry metadata alone does not prove candidate placement'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--observation', type=Path)
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text())
    observation = json.loads(args.observation.read_text()) if args.observation else None
    result = check(trace, observation)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {'PASS':0, 'FAIL':1, 'PARTIAL':2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
