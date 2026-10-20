#!/usr/bin/env python3
"""One frozen connected patch, authored from authenticated retained actual source proof."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/79-shoulder-pose-corrective'))
from derive_target import (CONTRACT_SHA, OBJ_SHA, STAGES, need, digest, verify_capture,
    verify_cohort, quaternion, rotate, f32, length, sub, dot, cross, scale, raw_f32_hash)
from map_notch import bind_source,read_obj,deleted_ids
sys.path.insert(0,str(ROOT/'experiments/60-b1-continuous-motion'))
import geometry

HERE=Path(__file__).resolve().parent
POLICY_SHA='5164c50f3fc6d66cf1fb62f99c3715c2899281c3254c4cd9ace7f98876c1735c'
TOPOLOGY_SHA='7ab8ba769a76eea787e46c3d4f11e63eacfdc36c39306313f67e627defd2c691'
INPUT_SHA='fdd3918b7124397862adb33d4170eaf8f7b0e2c687687a4866c763e62ae4cda0'
SOURCE_PROOFS={'combined':'fc4196e7f00fadf0dd2860418fd515ea0befd9de84e4dc0f527057dd5860aa67','source_body':'533e1db94b62af8fa9088896af7233241e900e568d2ba60f604aa97db08985fb','source_garment':'82f66ee428f27feea2dea739c044a79e2685c26139257f9e207a42919b9c30a5'}

def frozen():
    for name,sha in [('policy.json',POLICY_SHA),('topology-freeze.json',TOPOLOGY_SHA),('input-hashes.json',INPUT_SHA)]:
        need(digest(HERE/name)==sha,'sealed '+name+' changed')
    return json.loads((HERE/'policy.json').read_text()),json.loads((HERE/'topology-freeze.json').read_text())

def authenticate(retained):
    contract_path=retained/'H80-SOURCE-CONTRACT-v1.json';need(digest(contract_path)==CONTRACT_SHA,'source contract changed')
    contract=json.loads(contract_path.read_text())
    for name,row in contract['runtime_sources'].items():need(digest(ROOT/name)==row['sha256'],'authenticated runtime source changed')
    frames={};works={}
    for stage,sha in SOURCE_PROOFS.items():
        p=retained/'h80proof-v1'/stage/'capture.json';need(digest(p)==sha,'actual source proof changed')
        frames[stage],works[stage]=verify_capture(json.loads(p.read_text()),stage,'h80proof-v1-'+stage,contract)
    verify_cohort(frames)
    expected=json.loads((ROOT/'experiments/79-shoulder-pose-corrective/works/shoulder-rear-baseline-arms.nvwa.json').read_text())
    need(all(w==expected for w in works.values()),'source proof Work differs')
    need([frames[s]['capture_update_epoch'] for s in STAGES]==sorted(set(frames[s]['capture_update_epoch'] for s in STAGES)),'source proof epochs differ')
    descriptor=ROOT/'assets'/expected['profile']['asset_path'];need(digest(descriptor)==expected['profile']['asset_sha256'],'profile manifest changed')
    for row in json.loads(descriptor.read_text())['files']:
        p=descriptor.parent/row['path'];need(p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'profile payload changed')
    return frames['combined']

def derive(frame):
    policy,topo=frozen();full=frame['full_base'];need(all(full[k]==v for k,v in topo['full_base_identity'].items()),'authoring frame identity changed')
    parts={p['name']:p for p in full['parts']};cloth,body=parts['garment'],parts['body']
    need(cloth['display_transform']==body['display_transform'] and cloth['model_to_world']==body['model_to_world'],'body and garment frame differs')
    asset=ROOT/'assets/characters/mpfb-b1-v1';need(digest(asset/'garment/female_sportsuit01.obj')==OBJ_SHA,'garment source changed')
    cb,_,ct=bind_source(cloth,read_obj(asset/'garment/female_sportsuit01.obj'))
    _,_,bt=bind_source(body,read_obj(asset/'base.obj'),deleted_ids(asset/'garment/female_sportsuit01.mhclo'))
    support=set(policy['position_source_ids']);need(support=={s for t in ct if 847 in t for s in t},'position support graph changed')
    affected=[i for i,t in enumerate(ct) if support.intersection(t)];need(affected==topo['position_incident_triangles0'],'affected triangle universe changed')
    need(sorted({s for i in affected for s in ct[i]})==topo['normal_source_ids'],'normal closure changed')
    by_source={s:p for s,p in zip(cloth['source_ids'],cloth['positions'])};rest={s:p for s,p in zip(cloth['source_ids'],cloth['rest_positions'])}
    for s in support:need(length(sub(rest[s],rest[847]))<=policy['max_support_rest_radius_m'],'patch extent exceeded')
    q=quaternion(next(b for b in full['bones'] if b['name']=='clavicle_l')['canonical_posed']);iq=[-q[0],-q[1],-q[2],q[3]]
    rows=[]
    for sid in sorted(support):
        p=by_source[sid];hits=[];nearest=math.inf
        # Exhaustive search retains every distance tie. Degenerate nearest is rejected.
        for ti in range(len(body['indices'])//3):
            inds=body['indices'][3*ti:3*ti+3];a,b,c=[body['positions'][i] for i in inds];point,bary=geometry.closest_triangle(p,a,b,c);d2=dot(sub(p,point),sub(p,point))
            if d2<nearest:nearest=d2
            hits.append((d2,ti,inds,point,bary,a,b,c))
        candidates=[]
        for d2,ti,inds,point,bary,a,b,c in hits:
            if d2>nearest+policy['tie_distance_squared_m2']:continue
            n=cross(sub(b,a),sub(c,a));need(length(n)>1e-12 and bary is not None,'degenerate nearest body triangle')
            n=scale(n,1/length(n));actual=[sum(w*body['normals'][i][axis] for w,i in zip(bary,inds)) for axis in range(3)]
            need(dot(n,actual)>0,'nearest source winding disagrees with actual normals')
            signed=dot(sub(p,point),n);delta=scale(n,max(0.,policy['margin_m']-signed))
            need(length(delta)<=policy['max_vector_m'],'authoring displacement exceeded')
            candidates.append({'distance_squared_m2':d2,'body_triangle0':ti,'body_source_ids':bt[ti],'barycentric':bary,'source_winding_normal':n,'actual_interpolated_normal':actual,'signed_local_side_m':signed,'delta_mesh_local_m':delta})
        candidates.sort(key=lambda x:(x['distance_squared_m2'],x['body_triangle0']));need(bool(candidates),'nearest body candidate missing');chosen=candidates[0]
        need(all(length(sub(c['delta_mesh_local_m'],chosen['delta_mesh_local_m']))<=policy['tie_vector_m'] for c in candidates),'ambiguous nearest body tie')
        local=[f32(x) for x in rotate(iq,chosen['delta_mesh_local_m'])];need(length(local)<=policy['max_vector_m'],'f32 authored vector exceeded bound')
        need(length(sub(rotate(q,local),chosen['delta_mesh_local_m']))<=1e-8,'clavicle roundtrip differs')
        rows.append({'source_id':sid,'delta_clavicle_m':local,'derivation':chosen,'distance_ties':len(candidates)})
    return {'candidate_id':policy['candidate_id'],'policy_sha256':POLICY_SHA,'topology_sha256':TOPOLOGY_SHA,'input_hashes_sha256':INPUT_SHA,'source_obj_sha256':OBJ_SHA,'position_source_ids':sorted(support),'normal_source_ids':topo['normal_source_ids'],'vectors':rows,'garment_rest_positions_sha256':raw_f32_hash(cloth['rest_positions'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();need(not a.out.exists(),'authoring directory exists');a.out.mkdir(parents=True)
    frame=authenticate(a.retained);target=derive(frame);path=a.out/'target.json';path.write_text(json.dumps(target,separators=(',',':'),allow_nan=False)+'\n')
    receipt={'status':'ONE_TARGET_FROZEN_NOT_SCORED','target_sha256':digest(path),'author_sha256':digest(Path(__file__)),'source_proofs':SOURCE_PROOFS,'policy_sha256':POLICY_SHA,'vectors':[{k:r[k] for k in ('source_id','delta_clavicle_m')} for r in target['vectors']]};(a.out/'authoring-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
