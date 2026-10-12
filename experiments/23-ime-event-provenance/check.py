"""Validate exact event/dispatch identity; never infer origin from an absent hook."""
import argparse
import json
import math
from pathlib import Path

COMPOSITION = {'compositionstart', 'compositionupdate', 'compositionend'}

def valid_time(value):
    return (type(value) is int and value >= 0) or (type(value) is float and math.isfinite(value) and value >= 0)

def check(capture, require_selftest=False):
    problems, incomplete, summary = [], [], []
    if capture.get('schema') != 1 or capture.get('kind') != 'ime-event-provenance':
        return {'status':'FAIL','problems':['unexpected capture schema'],'events':[]}, 1
    kind = capture.get('pageKind')
    if kind not in ('nvwa','plain-textarea','synthetic-selftest') or capture.get('synthetic') != (kind == 'synthetic-selftest'):
        problems.append('page kind/synthetic attribution mismatch')
    if require_selftest and kind != 'synthetic-selftest':
        problems.append('physical page cannot count as synthetic selftest')
    if capture.get('running') is not False or capture.get('startedAt') is None or capture.get('stoppedAt') is None:
        incomplete.append('case must have explicit start/stop before export')
    if capture.get('earlyInstallation') is not True or capture.get('hookIntactAtExport') is not True:
        incomplete.append('early hook installation/integrity unverified')
    if capture.get('dropped') != 0 or capture.get('instrumentationErrors') != 0:
        incomplete.append('dropped rows or instrumentation errors')
    if not isinstance(capture.get('runId'), str) or not capture['runId']:
        incomplete.append('missing unique case run ID')
    hook_time, module_time = capture.get('hookInstalledAt'), capture.get('productionModuleStartAt')
    case_start, case_stop = capture.get('startedAt'), capture.get('stoppedAt')
    for field in ('hookInstalledAt','startedAt','stoppedAt','productionModuleStartAt'):
        value = capture.get(field)
        required = field != 'productionModuleStartAt' or kind == 'nvwa'
        if value is None:
            if required: incomplete.append(f'missing timestamp: {field}')
        elif not valid_time(value):
            problems.append(f'invalid finite nonnegative timestamp: {field}')
    chronology = [('hook installation',hook_time),('case start',case_start),('case stop',case_stop)]
    if kind == 'nvwa':
        chronology.insert(1,('production module start',module_time))
        if capture.get('hookIntactBeforeModule') is not True:
            incomplete.append('installed-before-module hook integrity unverified')
    for (earlier_label,earlier),(later_label,later) in zip(chronology,chronology[1:]):
        if valid_time(earlier) and valid_time(later) and earlier > later:
            problems.append(f'{earlier_label} occurs after {later_label}')
    rows = capture.get('rows', [])
    if not isinstance(rows, list): return {'status':'FAIL','problems':['rows must be list'],'events':[]}, 1
    if not rows:
        incomplete.append('missing boundary checkpoints')
    else:
        for position,label in ((0,'start'),(-1,'stop')):
            if rows[position].get('type') != 'checkpoint' or rows[position].get('label') != label:
                problems.append(f'invalid {label} boundary checkpoint type/label')
    dispatches, active, terminals = {}, {}, set()
    last_time = -1
    for index, row in enumerate(rows, 1):
        if row.get('sequence') != index:
            problems.append(f'noncontiguous sequence at row {index}')
        now = row.get('timeMs')
        if not valid_time(now) or now < last_time:
            problems.append(f'nonchronological time at row {index}')
        else: last_time = now
        if valid_time(now):
            if valid_time(case_start) and now < case_start:
                problems.append(f'row {index} precedes case start')
            if valid_time(case_stop) and now > case_stop:
                problems.append(f'row {index} follows case stop')
        if row.get('hookIntact') is not True: incomplete.append(f'hook integrity unavailable at row {index}')
        if any(key in row for key in ('data','value','text','clipboard','keyText')):
            problems.append(f'forbidden raw input field at row {index}')
        row_type, dispatch_id, event_id = row.get('type'), row.get('dispatchId'), row.get('eventId')
        if row_type == 'checkpoint':
            expected = 'start' if index == 1 else 'stop' if index == len(rows) else None
            if expected is None or row.get('label') != expected:
                problems.append(f'unexpected checkpoint type/label at row {index}')
        elif 'label' in row:
            problems.append(f'checkpoint label attached to noncheckpoint row {index}')
        if row_type in ('dispatch-start','observed-event') and row.get('eventType') in COMPOSITION:
            length = row.get('dataLength')
            if not isinstance(event_id,str) or not event_id or not isinstance(row.get('trusted'),bool) or not isinstance(row.get('constructorName'),str) or not (length is None or type(length) is int and length >= 0):
                problems.append(f'invalid composition event metadata at row {index}')
        if row_type == 'dispatch-start':
            if not isinstance(dispatch_id,str) or dispatch_id in dispatches or not isinstance(event_id,str):
                problems.append(f'invalid/duplicate dispatch identity at row {index}'); continue
            if row.get('eventType') not in COMPOSITION or not isinstance(row.get('stack'),str) or not row['stack'].strip():
                problems.append(f'missing composition callstack at row {index}')
            dispatches[dispatch_id] = row
            active.setdefault(event_id, []).append(dispatch_id)
        elif row_type in ('dispatch-return','dispatch-throw'):
            witness = dispatches.get(dispatch_id)
            if not witness or witness.get('eventId') != event_id or dispatch_id in terminals or not active.get(event_id) or active[event_id][-1] != dispatch_id:
                problems.append(f'unmatched dispatch terminal at row {index}'); continue
            if row_type == 'dispatch-return' and not isinstance(row.get('result'), bool):
                problems.append(f'native dispatch result is not boolean at row {index}')
            active[event_id].pop(); terminals.add(dispatch_id)
        elif row_type == 'observed-event' and row.get('eventType') in COMPOSITION:
            witness = dispatches.get(dispatch_id) if dispatch_id else None
            if dispatch_id:
                if not witness or not active.get(event_id) or active[event_id][-1] != dispatch_id:
                    problems.append(f'observer lacks active matching dispatch at row {index}')
                elif any(row.get(field) != witness.get(field) for field in ('eventId','eventType','target','trusted','dataLength','constructorName')):
                    problems.append(f'observer/dispatch metadata differ at row {index}')
                if row.get('provenance') != 'WITNESSED_REALM_DISPATCH': problems.append(f'wrong witnessed label at row {index}')
            elif active.get(event_id):
                problems.append(f'observer omits known active dispatch at row {index}')
            elif row.get('provenance') != 'UNKNOWN':
                problems.append(f'unwitnessed origin must stay UNKNOWN at row {index}')
            item = {key:row.get(key) for key in ('sequence','eventId','eventType','target','trusted','dataLength','dispatchId')}
            item['provenance'] = 'WITNESSED_REALM_DISPATCH' if witness else 'UNKNOWN'
            summary.append(item)
            if not dispatch_id and row.get('trusted') is False:
                incomplete.append(f'untrusted {event_id} origin UNKNOWN')
    if set(dispatches) != terminals: incomplete.append('dispatch started without terminal row')
    if not summary: incomplete.append('no composition events observed')
    if require_selftest:
        if [event['eventType'] for event in summary] != ['compositionstart','compositionupdate','compositionend']:
            problems.append('selftest requires exactly the three known synthetic events')
        if any(event['trusted'] is not False or event['dataLength'] != 2 or event['target'] != 'ime-control' or event['provenance'] != 'WITNESSED_REALM_DISPATCH' for event in summary):
            problems.append('selftest metadata/provenance does not match known local dispatch')
        if any('syntheticSelftest' not in (row.get('stack') or '') for row in dispatches.values()):
            problems.append('selftest lacks the owned synthetic caller in its stack')
    status, code = ('FAIL',1) if problems else ('PARTIAL',2) if incomplete else ('PASS',0)
    return {'status':status,'problems':problems,'incomplete':sorted(set(incomplete)),
        'events':summary,'physicalAcceptance':'NOT-RUN by checker; requires separately attributed physical observation',
        'originLimit':'A witnessed callstack proves this JS realm called dispatchEvent; all unwitnessed origins remain UNKNOWN.'}, code

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    p.add_argument('--selftest',action='store_true')
    a = p.parse_args()
    try: result, code = check(json.loads(a.capture.read_text()), a.selftest)
    except (ValueError, OSError, TypeError, AttributeError) as error:
        result, code = {'status':'FAIL','problems':[str(error)]}, 1
    print(json.dumps(result,indent=2))
    raise SystemExit(code)
