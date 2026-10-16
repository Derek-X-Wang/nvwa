#!/usr/bin/env python3
"""Strict native/Wasm CPU diagnostic frame parity; never GPU vertex readback."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
COMMON='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
POSES='8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2'
spec=importlib.util.spec_from_file_location('b1_runtime_validation',ROOT.parent/'57-b1-pose-runtime/validation.py')
validation=importlib.util.module_from_spec(spec);spec.loader.exec_module(validation)
require=validation.require
COUNTS={'body':19158,'garment':1797}
MATRICES=('rest','posed','inverse_bind','local_rest','local_posed','skin','canonical_rest','canonical_posed','frame_gauge')

def load_frame(path):
    value=json.loads(path.read_text())
    frame=value.get('frame',value)
    require(isinstance(frame,dict),'selected frame missing')
    if 'frame' in value:
        require(value.get('state')==frame.get('state'),'outer/embedded prototype state mismatch')
        require(value.get('phase',4)==4 and not value.get('error'),'report is not a ready error-free selected frame')
    return frame

def expectations(asset_root):
    proof=json.loads((ROOT.parent/'55-source-character-runtime/evidence/data-adapter.json').read_text())
    require(proof['common_manifest_sha256']==COMMON,'approved input identity mismatch')
    for relative,digest in proof['derived_files'].items():
        path=asset_root/relative
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest,'actual staged input hash mismatch: '+relative)
    rig=json.loads((asset_root/'rig.game_engine.json').read_text())
    require(len(rig)==53,'approved rig coverage mismatch')
    return proof['derived_files'],{name:(bone['parent'] or None) for name,bone in rig.items()}

def admit(frame,assets,bones):
    require(frame.get('schema_version')==1,'unsupported selected frame schema')
    require(frame.get('common_manifest_sha256')==COMMON,'common input identity mismatch')
    require(frame.get('actual_candidate_code_executed') is True and frame.get('actual_explicit_loader') is True and frame.get('gpu_vertex_readback') is False,'wrong execution/readback claim')
    state=frame.get('state');require(isinstance(state,dict) and state.get('format')=='nvwa-b1-pose-prototype' and state.get('schema_version')==1,'prototype state missing')
    require(state.get('recipe') in ('neutral','body-negative','body-half','body-positive','face-negative','face-half','face-positive','combined') and state.get('pose') in ('neutral','shoulder','elbow','knee','combined') and state.get('backend') in ('gpu4','full-weight-cpu'),'invalid selected recipe/pose/backend')
    require(isinstance(state.get('camera_yaw'),(int,float)) and math.isfinite(state['camera_yaw']) and abs(state['camera_yaw'])<=180,'invalid selected camera')
    identity=frame.get('build_identity');require(isinstance(identity,dict),'build identity missing')
    inputs=identity.get('input_identity',{})
    require(inputs.get('common_manifest_sha256')==COMMON and inputs.get('pose_manifest_sha256')==POSES and inputs.get('asset_files')==assets and inputs.get('no_baked_frames') is True,'frozen source-input/pose identity mismatch')
    sources=identity.get('source_files');require(isinstance(sources,dict) and {'derived/src/lib.rs','adapter/src/lib.rs'}<=set(sources) and all(isinstance(d,str) and len(d)==64 for d in sources.values()),'actual source file identity missing')
    require(identity.get('pose_manifest_sha256')==POSES,'build pose identity mismatch')
    parts=frame.get('parts');require(isinstance(parts,dict) and set(parts)==set(COUNTS),'exact body and garment parts required')
    admitted={}
    for name,count in COUNTS.items():
        part=parts[name];ids=part.get('source_vertex_ids')
        require(isinstance(ids,list) and ids and all(isinstance(i,int) and not isinstance(i,bool) for i in ids) and set(ids)==set(range(count)),'complete expected source ID coverage required: '+name)
        result=validation.validate_frame(part,len(ids),canonical=True)
        require({b['name']:b['parent'] for b in part['bones']}==bones,'approved 53 bone names/parents required')
        validation.vectors(part.get('joint_indices'),len(ids),4,'joint indices')
        validation.vectors(part.get('joint_weights'),len(ids),4,'joint weights')
        require(all(isinstance(j,int) and not isinstance(j,bool) and 0<=j<53 for row in part['joint_indices'] for j in row),'invalid joint mapping')
        negative=[w for row in part['joint_weights'] for w in row if w<0]
        negative_rows=sum(any(w<0 for w in row) for row in part['joint_weights'])
        full=part.get('full_joint_influences')
        if state['backend']=='full-weight-cpu':
            require(isinstance(full,list) and len(full)==len(ids),'full influence coverage required')
            for row in full:
                require(isinstance(row,list) and row and all(isinstance(pair,list) and len(pair)==2 and isinstance(pair[0],int) and not isinstance(pair[0],bool) and 0<=pair[0]<53 and isinstance(pair[1],(int,float)) and math.isfinite(pair[1]) and pair[1]>0 for pair in row),'invalid full source influences')
                require(math.isfinite(sum(pair[1] for pair in row)) and sum(pair[1] for pair in row)>0,'invalid full influence sum')
        admitted[name]={'vertices':len(ids),'source_ids':count,'bones':53,'frame_validation':result,'legacy_four_slot_negative_weight_components':len(negative),'legacy_four_slot_vertices_with_negative_weights':negative_rows,'legacy_four_slot_min_weight':min(negative) if negative else 0.0,'weight_quality_acceptance':False}
    return admitted

def compare_frames(native,web,asset_root):
    assets,bones=expectations(asset_root)
    coverage=admit(native,assets,bones);admit(web,assets,bones)
    require(native['state']==web['state'],'selected prototype state mismatch')
    require(native['build_identity']==web['build_identity'],'actual source/input identity mismatch')
    maximum={'matrix':0.0,'position':0.0,'normal':0.0,'tangent':0.0,'weight':0.0}
    def compare(left,right,bucket):
        require(isinstance(left,list) and isinstance(right,list) and len(left)==len(right) and left,'nonempty array coverage mismatch')
        for a,b in zip(left,right):
            if isinstance(a,list):compare(a,b,bucket)
            else:
                require(isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isfinite(a) and math.isfinite(b),'invalid comparison component')
                maximum[bucket]=max(maximum[bucket],abs(a-b))
    for name in COUNTS:
        left,right=native['parts'][name],web['parts'][name]
        require(left['source_vertex_ids']==right['source_vertex_ids'] and left['joint_indices']==right['joint_indices'],'source/joint mapping mismatch')
        require(left.get('full_joint_influences')==right.get('full_joint_influences'),'full source influences mismatch')
        compare(left['joint_weights'],right['joint_weights'],'weight')
        require([b['name'] for b in left['bones']]==[b['name'] for b in right['bones']],'bone order mismatch')
        for a,b in zip(left['bones'],right['bones']):
            for key in MATRICES:compare(a[key],b[key],'matrix')
        for key,bucket in [('positions','position'),('rest_positions','position'),('normals','normal'),('rest_normals','normal'),('tangents','tangent')]:compare(left[key],right[key],bucket)
    require(maximum['matrix']<=1e-4 and maximum['position']<=1e-5 and maximum['normal']<=1e-4 and maximum['tangent']<=1e-4 and maximum['weight']<=1e-6,'native/Web numeric frame mismatch: '+str(maximum))
    return {'native_web_original_cpu_diagnostic_frame_parity':True,'gpu_vertex_parity_claimed':False,'state':native['state'],'maximum_component_error':maximum,'coverage':coverage}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('native',type=Path);parser.add_argument('web',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--asset-root',type=Path,default=REPO/'.work/b1-pose-viewer/site/assets');args=parser.parse_args()
    try:
        result=compare_frames(load_frame(args.native),load_frame(args.web),args.asset_root)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result));return 0
    except (ValueError,KeyError,TypeError,IndexError,OSError) as error:
        print('FRAME_PARITY_REJECTED: '+str(error));return 3
if __name__=='__main__':raise SystemExit(main())
