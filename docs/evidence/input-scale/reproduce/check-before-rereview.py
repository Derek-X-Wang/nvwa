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

def check_geometry(capture, args):
    require(capture.get('schema') == 'nvwa-scale-boundary-v1', 'wrong capture schema')
    rows = {row['index']:row for row in capture['rows']}
    require(args.row in rows and args.pointer in rows, 'requested rows absent; capture may have hit its 800-row limit')
    row, pointer = rows[args.row], rows[args.pointer]
    g = row['geometry']
    close(g['dpr'], args.expected_dpr, 0.01, 'observed devicePixelRatio')
    require(g['canvas'] is not None, 'real production #nvwa canvas absent')
    canvas = g['canvas']
    require(canvas['css']['transform'] == 'none', 'canvas has a transform; this bounded checker needs an explicit transform contract')
    close(canvas['rect']['width'], args.expected_css[0], 1, 'canvas CSS width')
    close(canvas['rect']['height'], args.expected_css[1], 1, 'canvas CSS height')
    for dimension in ('width', 'height'):
        close(canvas['backing'][dimension], canvas['rect'][dimension]*g['dpr'], 1.1,
              f'canvas backing {dimension} vs CSS*DPR')
        close(canvas['client'][dimension], canvas['rect'][dimension], 1, f'canvas client {dimension}')
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
            'backing':canvas['backing'],'caret':caret,'trusted_work_click':point}

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
    args = parser.parse_args()
    try:
        if args.command == 'work':
            result = check_work(read(args.baseline),read(args.changed),read(args.undo),args.parameter,args.minimum_delta)
        else:
            result = check_geometry(read(args.capture),args)
        print('PASS '+json.dumps(result,sort_keys=True))
    except (AssertionError,KeyError,TypeError,ValueError) as error:
        print(f'FAIL {error}')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
