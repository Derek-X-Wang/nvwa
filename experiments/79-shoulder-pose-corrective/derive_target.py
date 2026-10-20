#!/usr/bin/env python3
"""One-shot source847 authoring, only after three fresh source confirmations.
No prior76 input can author a target. No screenshot optimization or alternate rule.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from map_notch import (ROOT, FRAME_SHA, WORK_SHA, bind_source, deleted_ids,
                       digest, dot, cross, read_obj, sub)

CONTRACT_SHA = '43a2c8ce5e024bc2813e9bf92c7619b522fbdc50f7b7b3ef241b9ab147422372'
OBJ_SHA = 'f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9'
STAGES = ('combined', 'source_body', 'source_garment')
MARGIN_M = .001
MAX_VECTOR_M = .020
TIE_DISTANCE_SQUARED_M2 = 1e-12
TIE_VECTOR_M = 1e-9

class InvalidEvidence(ValueError): pass
class RejectedTarget(ValueError): pass

def need(value, message):
    if not value: raise InvalidEvidence(message)

def reject(value, message):
    if not value: raise RejectedTarget(message)

def length(v): return math.sqrt(dot(v, v))
def scale(v, s): return [x*s for x in v]
def add(a, b): return [x+y for x,y in zip(a,b)]
def finite(v): return all(math.isfinite(x) for x in v)
def f32(x): return struct.unpack('<f', struct.pack('<f', x))[0]
def jhash(v): return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def closest_triangle(p, a, b, c):
    """Closest point and barycentrics on a nondegenerate triangle, all Voronoi regions."""
    ab, ac = sub(b,a), sub(c,a)
    reject(dot(cross(ab,ac),cross(ab,ac)) > 1e-24, 'degenerate selected body fan')
    ap=sub(p,a); d1,d2=dot(ab,ap),dot(ac,ap)
    if d1<=0 and d2<=0: return a, [1.,0.,0.]
    bp=sub(p,b); d3,d4=dot(ab,bp),dot(ac,bp)
    if d3>=0 and d4<=d3: return b,[0.,1.,0.]
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        v=d1/(d1-d3); return add(a,scale(ab,v)),[1-v,v,0.]
    cp=sub(p,c); d5,d6=dot(ab,cp),dot(ac,cp)
    if d6>=0 and d5<=d6: return c,[0.,0.,1.]
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        w=d2/(d2-d6); return add(a,scale(ac,w)),[1-w,0.,w]
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:
        w=(d4-d3)/((d4-d3)+(d5-d6)); return add(b,scale(sub(c,b),w)),[0.,1-w,w]
    denom=1/(va+vb+vc);v=vb*denom;w=vc*denom
    return add(a,add(scale(ab,v),scale(ac,w))),[1-v-w,v,w]

def quaternion(matrix):
    """Normalized rotation from the actual near-rigid column-major bone matrix."""
    need(len(matrix)==16 and finite(matrix), 'actual bone matrix invalid')
    need([matrix[i] for i in (3,7,11,15)]==[0.,0.,0.,1.], 'actual clavicle frame not affine')
    cols=[matrix[i:i+3] for i in (0,4,8)]; sizes=[length(v) for v in cols]
    need(all(abs(dot(cols[i],cols[j])-(1. if i==j else 0.))<1e-5 for i in range(3) for j in range(3)), 'actual clavicle frame not orthonormal; shear/scale rejected')
    need(abs(dot(cols[0],cross(cols[1],cols[2]))-1)<1e-5,'actual clavicle determinant not one')
    need(all(abs(s-1)<1e-4 for s in sizes), 'actual clavicle frame not rigid')
    cols=[scale(v,1/s) for v,s in zip(cols,sizes)]
    need(dot(cols[0],cross(cols[1],cols[2]))>0, 'actual clavicle rotation reflected')
    m=[[cols[j][i] for j in range(3)] for i in range(3)];tr=sum(m[i][i] for i in range(3))
    if tr>0:
        s=math.sqrt(tr+1)*2;q=[(m[2][1]-m[1][2])/s,(m[0][2]-m[2][0])/s,(m[1][0]-m[0][1])/s,.25*s]
    else:
        i=max(range(3),key=lambda i:m[i][i]);j=(i+1)%3;k=(i+2)%3
        s=math.sqrt(1+m[i][i]-m[j][j]-m[k][k])*2;q=[0.,0.,0.,0.]
        q[i]=.25*s;q[j]=(m[j][i]+m[i][j])/s;q[k]=(m[k][i]+m[i][k])/s;q[3]=(m[k][j]-m[j][k])/s
    n=math.sqrt(sum(x*x for x in q));q=[x/n for x in q]
    need(all(length(sub(rotate(q,[float(k==i) for k in range(3)]),cols[i]))<1e-5 for i in range(3)), 'quaternion disagrees with independent matrix rotation')
    return q

def rotate(q, v):
    xyz=q[:3];t=scale(cross(xyz,v),2)
    return add(v,add(scale(t,q[3]),cross(xyz,t)))

def raw_f32_hash(rows):
    return hashlib.sha256(b''.join(struct.pack('<f',v) for row in rows for v in row)).hexdigest()

def expected_bounds(positions):
    lo=[min(p[i] for p in positions) for i in range(3)];hi=[max(p[i] for p in positions) for i in range(3)]
    return {'center':[f32(f32(a+b)*.5) for a,b in zip(lo,hi)],'half_extents':[f32(f32(b-a)*.5) for a,b in zip(lo,hi)]}

def verify_part_geometry(actual, part, buffer, changed, source):
    need(actual['entity']==part['display_entity']==buffer['entity'] and actual['production_mesh_handle']==part['mesh_handle']==buffer['mesh_handle'],'actual part entity/production mesh differs from full-base buffer')
    need(actual['display_transform']==part['display_transform']==buffer['display_transform'],'actual part transform differs from full-base')
    need(all(buffer[k]==part[k] for k in ('positions','normals','indices')),'reference geometry differs between buffer and full-base')
    need(actual['inherited_production_no_frustum_culling'] is True,'production NoFrustumCulling policy differs')
    need(actual['changed_mesh_exact_bounds'] is (True if changed else None),'changed mesh scope/bounds flag differs')
    if changed:
        need(actual['actual_render_mesh_handle']!=part['mesh_handle'] and source['display_entity']==part['display_entity'] and source['original_mesh']==part['mesh_handle'],'source highlight actual/original mesh association differs')
    else:need(actual['actual_render_mesh_handle']==part['mesh_handle'],'unchanged part mesh replaced')
    inds=part['indices'];order=inds if changed else list(range(len(part['positions'])))
    positions=[part['positions'][i] for i in order];normals=[part['normals'][i] for i in order]
    uv=buffer['uv_0'];tangent=part['tangents'];attributes={'Vertex_Position':('Float32x3',positions),'Vertex_Normal':('Float32x3',normals)}
    if uv is not None:attributes['Vertex_Uv']=('Float32x2',[uv[i] for i in order])
    if tangent is not None:attributes['Vertex_Tangent']=('Float32x4',[tangent[i] for i in order])
    b=actual['buffers'];rows=b['complete_rendered_attributes'];names=[r['name'] for r in rows]
    need(len(set(names))==len(names) and len({r['id'] for r in rows})==len(rows),'duplicate rendered attribute identity')
    if changed or 'Vertex_Color' in names:
        colors=[[1.,1.,1.,1.] for _ in order]
        if changed:
            fans=([[8319,8318,8309],[8319,8309,8310]] if part['name']=='body' else [[830,168,212],[830,212,847]])
            selected=[i for i in range(len(inds)//3) if sorted(part['source_ids'][j] for j in inds[3*i:3*i+3]) in [sorted(fan) for fan in fans]]
            need(len(selected)==2 and selected==source['source_render_triangles0'],'highlight source fan indices differ')
            color=[0.,1.,0.,1.] if part['name']=='body' else [1.,0.,1.,1.]
            for tri in selected:colors[3*tri:3*tri+3]=[color]*3
        attributes['Vertex_Color']=('Float32x4',colors)
    need(set(names)==set(attributes),'rendered attribute presence unbound to reference (unknown attribute requires new authenticated data)')
    for row in rows:
        fmt,values=attributes[row['name']]
        need(row['format']==fmt and row['values']==len(values) and row['raw_bytes_sha256']==raw_f32_hash(values),'actual rendered attribute differs from reference/allowed source colors')
    expected_indices=None if changed else inds
    need(b['positions_sha256_le_f32']==raw_f32_hash(positions) and b['normals_sha256_le_f32']==raw_f32_hash(normals),'actual position/normal hash differs from reference')
    need(b['vertex_count']==len(positions) and b['index_count']==(None if changed else len(inds)) and b['index_format']==(None if changed else 'U32') and b['primitive_topology']=='TriangleList','actual topology/count differs from expected source publication')
    need(b['indices_sha256']==jhash(expected_indices),'actual index hash differs')
    need(b['vertex_colors_sha256_le_f32']==(raw_f32_hash(attributes['Vertex_Color'][1]) if 'Vertex_Color' in attributes else None),'actual color hash differs')
    need(actual['computed_mesh_aabb']==expected_bounds(positions),'computed mesh Aabb differs from reference geometry')
    if changed:need(actual['actual_aabb']==actual['computed_mesh_aabb'],'changed mesh actual Aabb incoherent')

def verify_outer_publication(frame, stage):
    source=frame['source_diagnostic'];pub=source['actual_render_publication'];full=frame['full_base']
    need(pub['camera']==frame['camera'] and pub['work_sha256']==frame['work_sha256'] and pub['generation']==full['generation'] and pub['mode']==source['mode'],'actual publication camera/Work/generation/mode differs from outer frame')
    refs=full['parts'];actual=pub['parts'];buffers=frame['buffers']
    need(len(actual)==len(refs)>0 and len({p['role'] for p in actual})==len(actual),'actual publication parts absent/duplicate/incomplete')
    need({p['role'] for p in actual}=={p['name'] for p in refs},'actual publication roles differ from full-base')
    for p in refs:
        a=next(v for v in actual if v['role']==p['name']);matches=[b for b in buffers if b['role']==p['name']]
        need(len(matches)==1,'reference buffer role missing/duplicate')
        changed=stage!='combined' and source['role']==p['name']
        verify_part_geometry(a,p,matches[0],changed,source)
        diag=frame['diagnostic'];targets=[t for t in diag['targets'] if t['role']==p['name']]
        need(len(targets)==1,'diagnostic material/visibility reference missing')
        t=targets[0]
        need(t['entity']==p['display_entity'] and t['mesh_handle']==p['mesh_handle'] and t['material_handle']==a['material_handle'],'actual material/entity binding differs')
        need(diag['palette']=='Textured' and t['isolation_hidden'] is False and t['coverage_culling_policy_preserved'] is True and t['production_material']==t['render_material'],'material/visibility coverage policy changed')
        need(a['visibility']==t['visibility_actual'] and t['visibility_actual']==('Some('+t['visibility_original']+')' if t['visibility_original'] in ('Inherited','Visible','Hidden') else t['visibility_original']),'actual visibility differs from production diagnostic reference')

def verify_capture(envelope, stage, expected_request, contract):
    r,f=envelope['report'],envelope['frame'];s=f['source_diagnostic']
    need(r['phase']=='ready' and all(r[k] is True for k in ('current','acknowledged','request_succeeded')), 'capture not actual current/ready/succeeded')
    need(r['endpoint']==f['endpoint']=='web', 'fresh Web endpoint required')
    need(r['request_id']==f['request_id']==expected_request, 'request association differs')
    need(r['work_sha256']==f['work_sha256']==hashlib.sha256(r['work_json'].encode()).hexdigest(), 'Work bytes/hash differ')
    need(r['captured_identity']==f['identity'] and r['camera']==f['camera']==f['identity']['camera'], 'identity/camera association differs')
    need(r['base']==f['base'] and r['source_diagnostic']==s, 'report/frame base or source differs')
    epoch=f['capture_update_epoch'];stable=f['stable_updates']
    need(type(epoch) is int and epoch>0 and r['capture_update_epoch']==epoch, 'capture epoch missing/different')
    need(type(stable) is int and stable>=2 and r['stable_updates']==stable, 'measured stability missing/different')
    rules=contract['stage_rules'][stage]
    need(all(k in s and type(s[k]) is type(v) and s[k]==v for k,v in rules['source_equals'].items()), 'root-frozen source rule differs')
    need(all(k in s for k in rules['required_source_keys']), 'source witness absent')
    need(s['actual_render_publication']['target_sha256'] is None, 'target already authored')
    key=s['publication_key_sha256'];need(isinstance(key,str) and len(key)==64, 'publication hash absent')
    for name in ('pre_visibility_witness','Last_independent_witness'):
        w=s[name];need(w['update_epoch']==epoch, 'source witness not same epoch')
        need(w['publication']=={'key_sha256':key,'actual':s['actual_render_publication']}, 'source witness publication differs')
    need(s['Last_independent_witness']['pre_visibility_publication_matches'] is True, 'Last witness not coherent')
    verify_outer_publication(f,stage)
    return f,json.loads(r['work_json'])

def verify_cohort(frames):
    baseline=frames['combined']
    baseline_parts={p['role']:p for p in baseline['source_diagnostic']['actual_render_publication']['parts']}
    for stage,f in frames.items():
        need(all(f[k]==baseline[k] for k in ('identity','full_base','buffers')),'production identity/full geometry changed across source proofs')
        if stage=='combined':continue
        source=f['source_diagnostic']
        for part in source['actual_render_publication']['parts']:
            original=baseline_parts[part['role']]
            if part['role']!=source['role']:need(part==original,'unchanged publication part differs across source proofs')
            else:
                # Deindexing excludes unused vertices. Exact changed Aabb is already
                # independently bound to expanded triangle positions in verify_capture.
                for k in ('entity','production_mesh_handle','material_handle','material_debug_sha256','display_transform','visibility','inherited_production_no_frustum_culling'):need(part[k]==original[k],'highlight changed non-color production association/policy')

def derive(frame, evidence=None):
    if evidence is None: evidence={}
    full=frame['full_base'];parts={p['name']:p for p in full['parts']};body,cloth=parts['body'],parts['garment']
    need(body['display_transform']==cloth['display_transform'] and body['model_to_world']==cloth['model_to_world'], 'shared body/cloth mesh frame differs')
    source=ROOT/'assets/characters/mpfb-b1-v1'
    need(digest(source/'garment/female_sportsuit01.obj')==OBJ_SHA, 'source garment identity differs')
    delete=deleted_ids(source/'garment/female_sportsuit01.mhclo')
    selected=[];topology={}
    for role,part,path in (('body',body,source/'base.obj'),('garment',cloth,source/'garment/female_sportsuit01.obj')):
        bound,removed,tris=bind_source(part,read_obj(path),delete if role=='body' else None)
        topology[role]={'source_obj_sha256':digest(path),'render_triangles':len(tris),'removed_source_faces':len(removed)}
        if role=='body':
            for ti,row in enumerate(bound):
                if row['source_face0']==7941:
                    inds=part['indices'][3*ti:3*ti+3]
                    selected.append((ti,tris[ti],[part['positions'][i] for i in inds],[part['normals'][i] for i in inds]))
    need(len(selected)==2, 'selected body source quad lacks exactly two fans')
    points=[p for i,p in zip(cloth['source_ids'],cloth['positions']) if i==847]
    need(points and all(p==points[0] for p in points), 'source847 missing or duplicate positions differ')
    p=points[0];candidates=[]
    evidence.update(source847_mesh_local_position_m=p,shared_display_transform=cloth['display_transform'],shared_model_to_world=cloth['model_to_world'],topology=topology,body_candidates=candidates)
    for ti,ids,ps,normals in selected:
        closest,bary=closest_triangle(p,*ps);n=cross(sub(ps[1],ps[0]),sub(ps[2],ps[0]));n=scale(n,1/length(n))
        interpolated=[sum(w*v[j] for w,v in zip(bary,normals)) for j in range(3)]
        reject(length(interpolated)>1e-15 and dot(n,interpolated)>0, 'source winding normal disagrees with actual body normal')
        signed=dot(sub(p,closest),n);delta=scale(n,MARGIN_M-signed)
        candidates.append({'render_triangle0':ti,'source_triangle_ids':ids,'closest_point_m':closest,'barycentric':bary,'source_winding_unit_normal':n,'actual_interpolated_normal':interpolated,'signed_side_separation_m':signed,'distance_squared_m2':dot(sub(p,closest),sub(p,closest)),'proposed_delta_mesh_local_m':delta})
    candidates.sort(key=lambda r:(r['distance_squared_m2'],r['render_triangle0']));chosen=candidates[0]
    evidence['chosen_render_triangle0']=chosen['render_triangle0']
    if abs(candidates[1]['distance_squared_m2']-chosen['distance_squared_m2'])<=TIE_DISTANCE_SQUARED_M2:
        reject(length(sub(candidates[1]['proposed_delta_mesh_local_m'],chosen['proposed_delta_mesh_local_m']))<=TIE_VECTOR_M, 'nearest body fans ambiguous with different source-normal targets')
    reject(chosen['signed_side_separation_m']<MARGIN_M, 'source847 already meets frozen 1mm side-margin; no target justified')
    delta=chosen['proposed_delta_mesh_local_m'];reject(0<length(delta)<=MAX_VECTOR_M,'derived vector outside frozen nonzero/20mm bound')
    clav=next(b for b in full['bones'] if b['name']=='clavicle_l');q=quaternion(clav['canonical_posed']);local=[f32(x) for x in rotate([-q[0],-q[1],-q[2],q[3]],delta)]
    reject(finite(local) and 0<length(local)<=MAX_VECTOR_M,'f32 authored vector outside bound')
    roundtrip=rotate(q,local);reject(length(sub(delta,roundtrip))<=1e-8,'clavicle inverse/forward roundtrip inconsistent')
    return local,{'source847_mesh_local_position_m':p,'shared_display_transform':cloth['display_transform'],'shared_model_to_world':cloth['model_to_world'],'body_candidates':candidates,'chosen_render_triangle0':chosen['render_triangle0'],'geometric_delta_mesh_local_m':delta,'delta_clavicle_m_f32':local,'clavicle_rotation_xyzw':q,'roundtrip_delta_mesh_local_m':roundtrip,'topology':topology}

def run(args):
    need(not args.out.exists(),'refusing to overwrite unique authoring output');args.out.mkdir(parents=True)
    receipt={'status':'NOT-RUN','scope':'Offline one-shot authoring; operator-confirmed source colors, CPU geometry, no GPU ownership or quality acceptance','helper_sha256':digest(Path(__file__)),'fixed_rule':{'margin_m':MARGIN_M,'max_vector_m':MAX_VECTOR_M,'tie_distance_squared_m2':TIE_DISTANCE_SQUARED_M2,'tie_vector_m':TIE_VECTOR_M},'inputs':{}}
    try:
        need(args.confirmed_source_correspondence,'explicit root source-correspondence confirmation required')
        need(digest(args.contract)==CONTRACT_SHA,'root-frozen source contract hash differs');contract=json.loads(args.contract.read_text())
        for name,row in contract['runtime_sources'].items():need(digest(ROOT/name)==row['sha256'], 'current runtime source differs from root freeze')
        manifest=json.loads(args.manifest.read_text());receipt['inputs']['manifest']={'path':str(args.manifest),'sha256':digest(args.manifest)};receipt['inputs']['root_contract']={'path':str(args.contract),'sha256':CONTRACT_SHA}
        frames={};works={};ids=[]
        for stage in STAGES:
            row=manifest[stage];path=Path(row['path']);actual=digest(path)
            need(actual==row['sha256'] and actual!=FRAME_SHA,'fresh raw SHA differs or historical frame supplied')
            envelope=json.loads(path.read_text());frames[stage],works[stage]=verify_capture(envelope,stage,row['request_id'],contract)
            receipt['inputs'][stage]={**row,'bytes':path.stat().st_size};ids.append(row['request_id'])
        need(len(set(ids))==3,'three distinct source capture request IDs required')
        base=frames['combined'];work=works['combined'];frozen=json.loads((ROOT/'experiments/79-shoulder-pose-corrective/works/shoulder-rear-baseline-arms.nvwa.json').read_text())
        need(work==frozen and all(w==work for w in works.values()),'fresh source Work differs from frozen rear/default cohort')
        need(base['full_base']['parameters']=={k:0. for k in work['character']['parameters']},'nondefault actual parameters')
        need(base['full_base']['asset_id']=='mpfb-hm08-game-engine-female-sportsuit01-v2' and base['full_base']['profile_id']=='nvwa-mpfb-b1-motion-v2' and base['full_base']['backend']=={'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v2','schema_version':3,'type':'b1_cpu'} and base['full_base']['mode']=='motion' and base['full_base']['diagnostic_pose']=='neutral','actual production backend/profile differs')
        sample=base['full_base']['sample'];need(sample['clip_id']=='b1_arm_rehearsal_v1' and sample['source_seconds']==sample['position_seconds']==2 and sample['playing'] is False,'actual held arm2 differs')
        verify_cohort(frames)
        epochs=[frames[s]['capture_update_epoch'] for s in STAGES];need(epochs==sorted(set(epochs)),'three captures lack distinct increasing epochs')
        descriptor=ROOT/'assets'/work['profile']['asset_path'];need(digest(descriptor)==work['profile']['asset_sha256'],'profile descriptor differs')
        for row in json.loads(descriptor.read_text())['files']:
            p=descriptor.parent/row['path'];need(p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'approved payload differs')
        receipt['derivation']={}
        vector,derivation=derive(base,receipt['derivation']);receipt['derivation']=derivation
        target={'candidate_id':'nvwa-source847-pose-target-v1','source_obj_sha256':OBJ_SHA,'source_id':847,'delta_clavicle_m':vector,'baseline_request_id':ids[0],'body_highlight_request_id':ids[1],'garment_highlight_request_id':ids[2]}
        raw=json.dumps(target,separators=(',', ':'),allow_nan=False).encode();(args.out/'target.json').write_bytes(raw)
        receipt.update(status='FROZEN_SINGLE_TARGET_NOT_QUALITY_ACCEPTANCE',target_sha256=hashlib.sha256(raw).hexdigest(),target_bytes=len(raw))
        code=0
    except RejectedTarget as e:receipt.update(status='REJECT',reason=str(e));code=3
    except (InvalidEvidence,ValueError,KeyError,TypeError,StopIteration,OSError) as e:receipt.update(status='NOT-RUN',reason=str(e));code=2
    (args.out/'authoring-receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt,indent=2,allow_nan=False));return code

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--confirmed-source-correspondence',action='store_true')
    try:sys.exit(run(p.parse_args()))
    except InvalidEvidence as e:print('NOT-RUN:',e,file=sys.stderr);sys.exit(2)
