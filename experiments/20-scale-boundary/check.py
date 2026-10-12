"""Numeric browser-boundary and complete saved-Work assertions. No GUI driving."""
import argparse
import copy
import json
import math
from pathlib import Path

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def read(path):
    return json.loads(Path(path).read_text())

def close(actual, expected, tolerance, label):
    require(isinstance(actual, (int, float)) and math.isfinite(actual), f'{label} is not finite')
    require(abs(actual - expected) <= tolerance, f'{label}: actual={actual}, expected={expected}, tolerance={tolerance}')

def without_revision(document):
    return {k:v for k,v in document.items() if k != 'revision'}

def check_work(base, changed, undo, parameter, minimum_delta):
    require(changed['revision'] == base['revision'] + 1, 'drag must commit exactly one revision')
    require(undo['revision'] == base['revision'] + 2, 'one Undo must commit exactly one further revision')
    before = base['character']['parameters'][parameter]
    after = changed['character']['parameters'][parameter]
    require(math.isfinite(after) and abs(after-before) >= minimum_delta,
            f'{parameter} did not change by at least {minimum_delta}: {before} -> {after}')
    expected = copy.deepcopy(base)
    expected['revision'] = changed['revision']
    expected['character']['parameters'][parameter] = after
    require(changed == expected, 'drag changed other Work fields; full document comparison failed')
    require(without_revision(undo) == without_revision(base), 'Undo did not restore the complete baseline Work')
    return {'revisions':[base['revision'],changed['revision'],undo['revision']],
            'parameter':parameter,'before':before,'after':after,'whole_work_preserved':True}

def inventory(capture):
    require(capture.get('schema') == 'nvwa-scale-boundary-v1', 'wrong capture schema')
    records = capture['rows']
    require(isinstance(records,list) and records, 'capture rows absent')
    indices = [r['index'] for r in records]
    require(all(type(i) is int and i >= 0 for i in indices), 'row indices must be nonnegative integers')
    gaps = [{'after':left,'before':right,'missing_count':right-left-1}
            for left,right in zip(indices,indices[1:]) if right > left+1]
    return {'count':len(records),'first_index':indices[0],'last_index':indices[-1],
            'gaps':gaps,'duplicate_indices':sorted({i for i in indices if indices.count(i)>1}),
            'strictly_increasing':all(right>left for left,right in zip(indices,indices[1:])),
            'prefix_truncated':indices[0]>0,'session_end_observed':records[-1]['kind']=='stopped',
            'whole_session_proof':False}

def boundary_geometry(g,args,label):
    close(g['dpr'], args.expected_dpr, 0.01, f'{label} devicePixelRatio')
    require(g['canvas'] is not None, f'{label}: real production #nvwa canvas absent')
    canvas = g['canvas']
    require(canvas['css']['transform'] == 'none', f'{label}: canvas has a transform; this bounded checker needs an explicit transform contract')
    close(canvas['rect']['width'], args.expected_css[0], 1, f'{label} canvas CSS width')
    close(canvas['rect']['height'], args.expected_css[1], 1, f'{label} canvas CSS height')
    for dimension in ('width', 'height'):
        close(canvas['backing'][dimension], canvas['rect'][dimension]*g['dpr'], 1.1,
              f'{label} canvas backing {dimension} vs CSS*DPR')
        close(canvas['client'][dimension], canvas['rect'][dimension], 1, f'{label} canvas client {dimension}')

def check_geometry(capture, args):
    summary = inventory(capture)
    require(summary['strictly_increasing'] and not summary['duplicate_indices'] and not summary['gaps'],
            f'capture index sequence has missing/repeated/out-of-order records: {summary}')
    timestamps = [r['timeMs'] for r in capture['rows']]
    require(all(isinstance(t,(int,float)) and math.isfinite(t) for t in timestamps), 'nonfinite capture time')
    require(all(right>=left for left,right in zip(timestamps,timestamps[1:])), 'capture time sequence is out of order')
    rows = {row['index']:row for row in capture['rows']}
    require(args.row in rows and args.pointer in rows, 'requested rows absent; capture may have hit its 800-row limit')
    row, pointer = rows[args.row], rows[args.pointer]
    g = row['geometry']
    require(args.row > args.pointer, 'settled row must chronologically follow click')
    require(row['kind']=='settled' and row.get('after')=='pointerdown',
            'select the click-settled(pointerdown) row; later typing snapshots are a separate observation')
    age = row['timeMs']-pointer['timeMs']
    # Frozen collector schedules this output250ms after pointerdown. One ms
    # covers timer precision;1s is the bounded observation deadline, not a
    # claim about application correctness when the browser scheduler is stalled.
    require(249 <= age <= 1000, f'click-settled age {age}ms outside249–1000ms observation window')
    boundary_geometry(pointer['geometry'],args,'click-time')
    boundary_geometry(g,args,'settled')
    canvas = g['canvas']
    phase = {key:pointer['geometry'][key] for key in ('dpr','viewport','canvas')}
    pending_focus = None
    interval = [record for record in capture['rows'] if args.pointer <= record['index'] <= args.row]
    for record in interval:
        current = record['geometry']
        require({key:current[key] for key in phase} == phase,
                f'canvas/DPR/CSS/viewport phase changed at row{record["index"]}')
        require(current['documentFocused'], f'document focus lost at row{record["index"]}')
        if record is pointer:
            continue
        kind = record['kind']
        require(kind not in ('pointerdown','pointercancel'), f'intervening {kind} at row{record["index"]}')
        require(not any(event in kind.lower() for event in ('resize','scale','dpr','blur','focus-loss')),
                f'intervening boundary event {kind} at row{record["index"]}')
        # The genuine Work click transfers focus within the app. Reject loss
        # outside that canvas/textarea handover, while allowing real typing.
        if kind == 'focusout':
            require(pending_focus is None and record.get('target') in ('nvwa','nvwa_text_input'),
                    f'unpaired or external focusout at row{record["index"]}')
            pending_focus = record['target']
        elif kind == 'focusin':
            target = record.get('target')
            require(target in ('nvwa','nvwa_text_input'), f'external focusin at row{record["index"]}')
            if pending_focus is not None:
                require(target != pending_focus, f'focus did not transfer internally at row{record["index"]}')
                pending_focus = None
        elif pending_focus is not None:
            require(kind != 'settled', f'focusout remained unresolved at row{record["index"]}')
        active = current['activeElement']
        require(active in ('nvwa','nvwa_text_input') or (active in ('',None) and pending_focus is not None),
                f'focus left production canvas/textarea at row{record["index"]}')
    require(pending_focus is None, 'click-settled snapshot has unresolved focus loss')
    require(pointer['kind'] == 'pointerdown' and pointer.get('trusted') is True and pointer.get('target') == 'nvwa',
            'Work click must be a real trusted pointerdown on production canvas')
    x,y,w,h = args.work_rect
    require(w > 0 and h > 0, 'screenshot-derived Work rectangle must be positive')
    point = pointer['client']
    require(x <= point['x'] <= x+w and y <= point['y'] <= y+h,
            f'real click {point} outside screenshot-derived Work rectangle {args.work_rect}')
    require(row['timeMs'] >= pointer['timeMs'], 'caret snapshot predates click')
    require(g['activeElement'] == 'nvwa_text_input' and g['caret'] and not g['caret']['hidden'],
            'visible Work click did not focus the actual production caret proxy')
    caret = g['caret']['rect']
    # Production proxy is anchored to cursor_rect.bottom, so a small vertical
    # tolerance includes its 1px height plus screenshot rounding.
    require(x-2 <= caret['x'] <= x+w+2 and y-2 <= caret['y'] <= y+h+4,
            f'caret anchor {caret} outside visible Work rectangle {args.work_rect}')
    require(g['documentFocused'], 'document not focused at measured caret snapshot')
    return {'row':args.row,'pointer':args.pointer,'dpr':g['dpr'],'css':canvas['rect'],
            'backing':canvas['backing'],'caret':caret,'trusted_work_click':point,
            'age_ms':age,'inventory':summary,'proof_scope':'selected_click_interval_only',
            'observer_limit':'frozen collector records canvas pointers only; outside-DOM pointer events may be unobserved'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    work = commands.add_parser('work')
    work.add_argument('baseline'); work.add_argument('changed'); work.add_argument('undo')
    work.add_argument('--parameter', default='jaw_width')
    work.add_argument('--minimum-delta', type=float, default=.05)
    geometry = commands.add_parser('geometry')
    geometry.add_argument('capture')
    geometry.add_argument('--row', type=int, required=True)
    geometry.add_argument('--pointer', type=int, required=True)
    geometry.add_argument('--expected-dpr', type=float, required=True)
    geometry.add_argument('--expected-css', type=float, nargs=2, required=True, metavar=('WIDTH','HEIGHT'))
    geometry.add_argument('--work-rect', type=float, nargs=4, required=True, metavar=('X','Y','WIDTH','HEIGHT'))
    audit = commands.add_parser('inventory')
    audit.add_argument('capture')
    args = parser.parse_args()
    try:
        if args.command == 'work':
            result = check_work(read(args.baseline),read(args.changed),read(args.undo),args.parameter,args.minimum_delta)
        elif args.command == 'geometry':
            result = check_geometry(read(args.capture),args)
        else:
            result = inventory(read(args.capture))
        print('PASS '+json.dumps(result,sort_keys=True))
    except (AssertionError,KeyError,TypeError,ValueError) as error:
        print(f'FAIL {error}')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
