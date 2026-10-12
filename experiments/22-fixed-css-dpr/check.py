"""Offline fixed-CSS actual-DPR boundary checks. Does not drive GUI events."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('scale20', ROOT / 'experiments/20-scale-boundary/check.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
require = old.require

def read(path):
    return json.loads(Path(path).read_text())

def inventory(capture):
    require(capture.get('schema') == 'nvwa-fixed-css-dpr-v1', 'wrong capture schema')
    converted = dict(capture, schema='nvwa-scale-boundary-v1')
    result = old.inventory(converted)
    declared = capture['inventory']
    require(declared['limit'] == 1200 and len(capture['rows']) <= 1200, 'unexpected row bound')
    require(type(declared['recorded']) is int and type(declared['dropped']) is int, 'invalid inventory types')
    require(declared['recorded']>=1 and declared['dropped']>=0, 'negative/empty inventory counts')
    require(declared['retained']==min(declared['recorded'],1200), 'retained count violates observer ring bound')
    require(declared['dropped']==max(0,declared['recorded']-1200), 'drop count violates observer ring bound')
    require(declared['retained'] == result['count'], 'retained count disagrees with rows')
    require(declared['firstIndex'] == result['first_index'] and declared['lastIndex'] == result['last_index'],
            'declared row bounds disagree')
    require(declared['recorded'] == declared['dropped'] + result['count'], 'drop accounting disagrees')
    require(declared['dropped'] == result['first_index'] and declared['recorded'] == result['last_index']+1,
            'prefix/drop/serial accounting disagrees')
    require(result['strictly_increasing'] and not result['gaps'] and not result['duplicate_indices'],
            'missing/repeated/out-of-order rows')
    require(capture['collector'] == {'limit':1200, 'pointerCoverage':'all document targets; drag moves only',
            'timerDelayMs':250, 'textRead':False, 'viewportAndCanvasSeparate':True}, 'unexpected observer contract')
    result.update(dropped=declared['dropped'], whole_session_proof=False,
                  export_boundary_observed=capture['rows'][-1]['kind']=='user-export')
    require(type(capture.get('stopped')) is bool, 'missing explicit stop state')
    require(capture['stopped'] == (capture['rows'][-1]['kind']=='stopped'), 'stop state disagrees with end marker')
    return result

def package(manifest_path):
    """Recheck served source symlinks and exact wrapper/observer before comparison."""
    manifest_path = Path(manifest_path)
    manifest = read(manifest_path)
    directory = manifest_path.parent
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    require(sha(directory/'index.html') == manifest['wrapperSha256'], 'wrapper bytes changed')
    source = manifest['source']
    require(source['schema']=='nvwa-fixed-css-package-v1', 'unexpected source schema')
    require(source['dprOverrides'] is False and source['rustChanges'] is False, 'source contract changed')
    require(source['layout'] in ('normal','fixed'), 'unexpected wrapper layout')
    for name, expected in source['productionInputs'].items():
        # index is the disclosed wrapper, not a source symlink.
        path = ROOT/'dist/web'/name if name in ('index.html','index.html.gz') else directory/name
        require(sha(path)==expected, f'production package bytes changed: {name}')
    for name, expected in source['observerFiles'].items():
        require(sha(directory/name)==expected, f'observer bytes changed: {name}')
    return source

def geometry(capture, args, source):
    summary = inventory(capture)
    require(capture['source'] == source, 'capture observer/source identity differs from pinned manifest')
    require(isinstance(capture.get('sessionId'),str) and capture['sessionId'], 'missing capture session ID')
    rows = {row['index']:row for row in capture['rows']}
    require(args.pointer in rows and args.row in rows, 'requested click rows absent')
    pointer, settled = rows[args.pointer], rows[args.row]
    require(settled.get('originIndex') == pointer['index'], 'settled timer belongs to another event')
    require(settled.get('originPointerId') == pointer.get('pointerId'), 'settled pointer identity mismatch')
    require(settled.get('originTimeMs') == pointer['timeMs'], 'settled timer origin time mismatch')
    converted = dict(capture, schema='nvwa-scale-boundary-v1')
    fixed = source.get('layout','fixed')=='fixed'
    expected_css = [1100,640] if fixed else getattr(args,'expected_css',None)
    require(expected_css is not None, 'normal control requires independently observed --expected-css')
    fixed_args = SimpleNamespace(pointer=args.pointer, row=args.row, expected_dpr=args.expected_dpr,
        expected_css=expected_css, work_rect=args.work_rect)
    result = old.check_geometry(converted, fixed_args)
    phase = {key:pointer['geometry'][key] for key in ('fixedParent','parent','parentTransform','scroll')}
    for row in capture['rows']:
        if not args.pointer <= row['index'] <= args.row:
            continue
        g = row['geometry']
        require({key:g[key] for key in phase}==phase, 'parent/scroll phase changed during selected click')
        require(g['parentTransform']=='none' and g['scroll']=={'x':0,'y':0}, 'transformed/scrolled parent unsupported')
        parent = g['fixedParent']
        if fixed:
            require(parent is not None, 'fixed parent absent')
            for dimension, expected in [('width',1100),('height',640),('x',0),('y',0)]:
                old.close(parent[dimension],expected,.02,f'fixed parent {dimension}')
                old.close(g['parent'][dimension],expected,.02,f'actual parent {dimension}')
                old.close(g['canvas']['rect'][dimension],expected,.02,f'fixed canvas {dimension}')
            require(g['viewport']['width'] >= 1100 and g['viewport']['height'] >= 640,
                    'fixed canvas is clipped by whole-window viewport; cannot assess the full visible surface')
        else:
            require(parent is None,'normal control unexpectedly reparented')
    x,y,w,h=args.work_rect
    canvas_rect=settled['geometry']['canvas']['rect']
    require(canvas_rect['x']<=x and canvas_rect['y']<=y and
            x+w<=canvas_rect['x']+canvas_rect['width'] and y+h<=canvas_rect['y']+canvas_rect['height'],
            'screenshot Work bounds must include actual canvas origin and stay inside visible canvas')
    result.update(inventory=summary, fixed_parent=settled['geometry']['fixedParent'],
        viewport=settled['geometry']['viewport'], origin_index=settled['originIndex'],
        observer_limit='all document pointer endpoints observed; pointer moves only while buttons held; DOM metadata is not Rust/egui scale',
        proof_scope='one selected click interval; actual screenshot and saved Work checks required separately')
    return result

def transition(captures, pointers, settled_rows, dprs, rects, source):
    require(len(captures)==3, 'exact100→125→100 triplet required')
    require(source.get('layout','fixed')=='fixed', 'fixed-CSS transition requires fixed wrapper')
    require(len({capture['sessionId'] for capture in captures})==1, 'transition must use one live session')
    require(all(math.isfinite(d) and d>0 for d in dprs), 'DPR values must be positive finite')
    require(abs(dprs[0]-dprs[2]) < .01 and abs(dprs[1]/dprs[0]-1.25)<.01,
            'expected actual Chrome100→125→100 DPR ratio not observed')
    results = []
    for capture, pointer, row, dpr, rect in zip(captures,pointers,settled_rows,dprs,rects):
        results.append(geometry(capture, SimpleNamespace(pointer=pointer,row=row,expected_dpr=dpr,work_rect=rect),source))
    require(all(right['pointer']>left['row'] for left,right in zip(results,results[1:])),
            'phase intervals overlap or reverse order')
    # Require common retained rows to be immutable across cumulative exports.
    known = {}
    for capture in captures:
        for row in capture['rows']:
            if row['index'] in known:
                require(row==known[row['index']], 'same-session exported row changed')
            known[row['index']] = row
    times = [next(r['timeMs'] for r in c['rows'] if r['index']==p) for c,p in zip(captures,pointers)]
    require(times[0]<times[1]<times[2], 'phase timestamps reversed')
    return {'phases':results, 'actual_dprs':dprs, 'fixed_css':[1100,640],
        'claim':'actual browser zoom control only; not original IAB emulator reproduction or display migration'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    setup=commands.add_parser('package'); setup.add_argument('manifest')
    inv=commands.add_parser('inventory'); inv.add_argument('capture')
    geo=commands.add_parser('geometry'); geo.add_argument('capture'); geo.add_argument('--manifest',required=True)
    geo.add_argument('--pointer',type=int,required=True); geo.add_argument('--row',type=int,required=True)
    geo.add_argument('--expected-dpr',type=float,required=True)
    geo.add_argument('--expected-css',nargs=2,type=float)
    geo.add_argument('--work-rect',nargs=4,type=float,required=True)
    tran=commands.add_parser('transition'); tran.add_argument('captures',nargs=3); tran.add_argument('--manifest',required=True)
    tran.add_argument('--pointers',nargs=3,type=int,required=True); tran.add_argument('--rows',nargs=3,type=int,required=True)
    tran.add_argument('--dprs',nargs=3,type=float,required=True)
    tran.add_argument('--work-rects',nargs=12,type=float,required=True)
    work=commands.add_parser('work'); work.add_argument('baseline'); work.add_argument('changed'); work.add_argument('undo')
    args=parser.parse_args()
    try:
        if args.command=='package':
            source=package(args.manifest)
            result={'production_file_count':len(source['productionInputs']), 'wasm_sha256':source['productionInputs']['nvwa_studio_bg.wasm'], 'source':source}
        elif args.command=='inventory': result=inventory(read(args.capture))
        elif args.command=='geometry': result=geometry(read(args.capture),args,package(args.manifest))
        elif args.command=='transition': result=transition([read(p) for p in args.captures],args.pointers,args.rows,
            args.dprs,[args.work_rects[i:i+4] for i in (0,4,8)],package(args.manifest))
        else: result=old.check_work(read(args.baseline),read(args.changed),read(args.undo),'jaw_width',.05)
        print('PASS '+json.dumps(result,sort_keys=True)); return 0
    except (AssertionError,KeyError,TypeError,ValueError,OSError) as error:
        print(f'FAIL {error}'); return 1

if __name__=='__main__':
    raise SystemExit(main())
