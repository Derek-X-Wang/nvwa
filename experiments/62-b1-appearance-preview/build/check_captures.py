#!/usr/bin/env python3
"""Independently inspect the predeclared real Web captures; no native/pixel credit."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/60-b1-continuous-motion'))
from checker import Checker, require


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--asset-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads((Path(__file__).with_name('cases.json')).read_text())['cases']
    checker=Checker(args.asset_root,surfaces=False)
    results=[]
    for case in cases:
        path=args.captures/(case['request_id']+'.json')
        value=json.loads(path.read_text())
        report=value['report']; frame=value['frame']; snapshot=frame['snapshot']; appearance=frame['appearance']
        require(value['request']==case and report['request']==case and frame['request']==case,'requested/captured identity mismatch')
        require(report['phase']=='captured' and report['desired']==report['applied']=='skin' and appearance['state']=='skin','not current captured skin')
        require(report['geometry_equal'] is True and frame['geometry_equal'] is True,'geometry equality missing')
        hashes=[report['geometry_before_sha256'],report['geometry_after_sha256'],frame['geometry_before_sha256'],frame['geometry_after_sha256']]
        require(len(set(hashes))==1,'inconsistent reported geometry hashes; these are Rust evidence, not independently reserialized')
        body=next(p for p in snapshot['parts'] if p['name']=='body')
        proof=appearance['source_uv_proof']; image=appearance['image']
        require(appearance['body_mesh']==body['mesh_handle'] and appearance['display_entity']==body['display_entity'],'actual current body binding mismatch')
        require(appearance['actual_uv_count']==proof['render_vertices']==len(body['source_ids']),'UV duplicate coverage mismatch')
        require(appearance['actual_uv_sha256']==proof['uv_sha256'] and proof['uv_seam_source_vertices']>0,'exact fitted UV identity/seam proof absent')
        require(0<=proof['rest_max_component_error']<=1e-6,'fitted/current rest mismatch')
        require(image['source_sha256']=='8d1fb3ceedf142fad32a3504eca1feb4539aecca6de66acde1514b9a61fc7ba0' and image['source_bytes']==3724137,'wrong approved diffuse')
        require(image['width']==image['height']==2048 and image['format']=='Rgba8UnormSrgb' and image['decoded_bytes']==2048*2048*4,'actual decoded image mismatch')
        require(appearance['white_tint'] is True and appearance['not_saved'] is True,'texture tint/temporary-state mismatch')
        require(appearance['actual_uv_0']==proof['uv_0'] and len(appearance['actual_uv_0'])==len(body['source_ids']),'actual/fitted duplicate UV arrays differ')
        compact=copy.deepcopy(appearance)
        compact.pop('actual_uv_0')
        compact['source_uv_proof'].pop('uv_0')
        require(report['appearance']==compact and report['sample']==snapshot['sample'] and report['parameters']==snapshot['parameters'],'compact/full report disagreement')
        # This envelope adapter changes no snapshot or request values. Reuse the independently
        # sourced f64 FK/full LBS/foot checker for actual uploaded geometry.
        result,_=checker.check({'kind':'studio','request':case,'snapshot':snapshot,'deep':True})
        results.append({'request_id':case['request_id'],'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'geometry':result,'uv_sha256':appearance['actual_uv_sha256'],'image_rgba_sha256':image['actual_rgba_sha256']})
    args.out.mkdir(parents=True,exist_ok=False)
    with (args.out/'metrics.jsonl').open('x') as stream:
        for result in results:stream.write(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    summary={'passed':len(results)==18,'actual_web_captures':len(results),'scope':'Three diagonal torso/jaw recipes x two authored clips x0/2/4 seconds; actual UV/material/image reports and independent f64 FK/full LBS/foot checks','native_gui':'NOT-RUN','pixel_quality':'Separate actual browser screenshots/observation required','cloth_quality':'HOLD unchanged','performance':'NOT-RUN'}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
