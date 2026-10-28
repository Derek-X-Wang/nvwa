#!/usr/bin/env python3
"""Bounded analytical application of the ONE frozen target to retained actual poses.
Not actual corrected upload, GPU/pixel ownership, complete collision or visual approval.
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import sys

from derive_target import (ROOT, STAGES, dot, sub, cross, length, scale, add,
                           quaternion, rotate, f32, raw_f32_hash, digest, need)
from map_notch import (camera, projection, project, ray, intersect, point, read_obj,
                      bind_source, deleted_ids, DISTANCE_EPS)
sys.path.insert(0,str(ROOT/'experiments/60-b1-continuous-motion'))
import geometry

TARGET_SHA='f88a431ab6dfb2da3bd9a64852f0c490bafe29b21a86e86b98d063862ad00b51'
LEDGER_SHA='a548dfd0bcec2caaa9d45f8b62277e8aeff53639665b882f3d7632f81da8668f'
ACTIVATION_FIXTURE_SHA='f671f09952653b01126d1599e047e7011afabbf3979aedee95f5b83c4c401f87'
FRESH_SHA='fc4196e7f00fadf0dd2860418fd515ea0befd9de84e4dc0f527057dd5860aa67'
BARY_SAMPLES=((1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6))
POLICY={'target_sha256':TARGET_SHA,'main_cohort':'torso -1/0/+1 x arm0/arm2/knee2','adjacent':'arm1/3/4 each torso','support':'source847 only; normal support from all triangles incident to847; one-ring surface from that fixed topology','default_ROI':[330,185,350,205],'body_surface_probes':'four fixed interior barycentrics per fan of original body quads7941 and7983','ray_tie_m':DISTANCE_EPS,'triangle_degenerate_double_area_m2':1e-12,'proper_segment_barycentric_epsilon':1e-9,'history_vs_fresh_existing_upload_epsilon_m':1e-5,'gates':['exact unchanged positions outside847','exact neutral/knee/end-arm zero','no new degeneracy or winding inversion vs same-frame baseline','no increase in fixed local body-surface opaque exposure probes','no new proper cloth/body or nonadjacent cloth/cloth crossing pairs','strict measurable fresh default ROI body-first count improvement'],'diagnostic_only':['area/edge ratios','fold angle including existing150deg descriptor','normal angles/zero counts','nearest local body-side signs'],'numerical_scope':'Analytical f64 quaternion extraction, relative w rounded f32 and smooth bounded angle; f32 final delta/positions. Actual Rust f32 activation seam already tested on all18 actual bone matrices; this evaluator is not exact runtime upload emulation.'}

def angle(a,b):
    n=length(a)*length(b)
    return math.degrees(math.acos(max(-1.,min(1.,dot(a,b)/n)))) if n>1e-15 else None

def activation(bones):
    arm=next(b for b in bones if b['name']=='upperarm_l');rest=quaternion(arm['local_rest']);posed=quaternion(arm['local_posed'])
    # Scalar part of inverse(rest)*posed. f32 rounding matches neutral relation,
    # never time/clip hardcoding; native tests independently prove runtime endpoints.
    w=f32(sum(a*b for a,b in zip(rest,posed)));radians=2*math.acos(min(1.,abs(w)));u=max(0.,min(1.,radians/(math.pi/4)));weight=f32(u*u*(3-2*u))
    return weight,radians

def predicted_normals(positions,indices,original,source_ids,support,active):
    if not active:return copy.deepcopy(original)
    sums=[[0.,0.,0.] for _ in positions]
    for k in range(0,len(indices),3):
        tri=indices[k:k+3];ps=[positions[i] for i in tri];n=cross(sub(ps[1],ps[0]),sub(ps[2],ps[0]));n=scale(n,1/length(n)) if length(n)>1e-15 else [0.,0.,0.]
        for j,i in enumerate(tri):
            if source_ids[i] not in support:continue
            a,b=sub(ps[(j+1)%3],ps[j]),sub(ps[(j+2)%3],ps[j])
            # Exact existing Bevy smooth-normal branch bound, not quality threshold.
            weight=math.radians(angle(a,b)) if dot(a,a)*dot(b,b)>2**-23 else 0.
            sums[i]=add(sums[i],scale(n,weight))
    result=copy.deepcopy(original)
    for i,sid in enumerate(source_ids):
        if sid in support:
            n=sums[i];result[i]=[f32(x/length(n)) for x in n] if length(n)>1e-15 else [0.,0.,0.]
    return result

def bbox(ps):return ([min(p[i] for p in ps) for i in range(3)],[max(p[i] for p in ps) for i in range(3)])
def overlaps(a,b):return all(a[0][i]<=b[1][i] and b[0][i]<=a[1][i] for i in range(3))
def proper_cross(a,b):
    for first,second in ((a,b),(b,a)):
        for i in range(3):
            direction=sub(first[(i+1)%3],first[i]);hit=intersect(first[i],direction,second)
            if hit and 1e-9<hit['distance_m']<1-1e-9 and min(hit['barycentric'])>1e-9:return True
    return False

def crossing_pairs(cloth,body,changed_triangles,source_ids):
    ct=[cloth['indices'][i:i+3] for i in range(0,len(cloth['indices']),3)];bt=[body['indices'][i:i+3] for i in range(0,len(body['indices']),3)];brows=[([body['positions'][i] for i in t],None) for t in bt];brows=[(p,bbox(p)) for p,_ in brows];crows=[([cloth['positions'][i] for i in t],None) for t in ct];crows=[(p,bbox(p)) for p,_ in crows];body_pairs=[];self_pairs=set()
    for ti in changed_triangles:
        ps,box=crows[ti]
        for bi,(other,b) in enumerate(brows):
            if overlaps(box,b) and proper_cross(ps,other):body_pairs.append((ti,bi))
        local_ids={source_ids[i] for i in ct[ti]}
        for ci,(other,b) in enumerate(crows):
            if ci==ti or local_ids.intersection(source_ids[i] for i in ct[ci]):continue
            if overlaps(box,b) and proper_cross(ps,other):self_pairs.add(tuple(sorted((ti,ci))))
    return {'body_pairs':sorted(set(body_pairs)),'nonadjacent_cloth_pairs':sorted(self_pairs),'scope':'Proper transverse edge/interior triangle crossings only; coplanar/tangent contact and full collision NOT-RUN'}

def source_points(part):
    rows={}
    for sid,p in zip(part['source_ids'],part['positions']):
        if sid in rows:need(rows[sid]==p,'duplicate source positions disagree')
        rows[sid]=p
    return rows

def ray_probes(body,cloth,cam,fr,pixels):
    meshes=[]
    for role,part in [('body',body),('garment',cloth)]:
        world=[point(part['display_transform'],p) for p in part['positions']];screen=[project(p,cam,fr) for p in world]
        for k in range(0,len(part['indices']),3):
            inds=part['indices'][k:k+3];ps=[screen[i] for i in inds];box=[min(p[j] for p in ps) for j in (0,1)]+[max(p[j] for p in ps) for j in (0,1)]
            meshes.append((role,k//3,[world[i] for i in inds],box))
    xs=[p[0] for p in pixels];ys=[p[1] for p in pixels];meshes=[r for r in meshes if r[3][2]>=min(xs) and r[3][0]<=max(xs) and r[3][3]>=min(ys) and r[3][1]<=max(ys)]
    result=[]
    for pixel in pixels:
        direction=ray(pixel,cam,fr);hits=[]
        for role,ti,ps,b in meshes:
            if b[0]-1e-9<=pixel[0]<=b[2]+1e-9 and b[1]-1e-9<=pixel[1]<=b[3]+1e-9:
                hit=intersect(cam[3],direction,ps)
                if hit:hits.append((hit['distance_m'],role,ti))
        hits.sort();first=hits[0] if hits else None;ties=[h for h in hits if first and h[0]<=first[0]+DISTANCE_EPS]
        result.append({'pixel':pixel,'first':first,'cross_role_ambiguity':len({h[1] for h in ties})>1})
    return {'body_first':sum(r['first'] is not None and r['first'][1]=='body' and not r['cross_role_ambiguity'] for r in result),'ambiguous':sum(r['cross_role_ambiguity'] for r in result),'samples':result}

def evaluate(snapshot,target,cam,fr,kind):
    parts={p['name']:p for p in snapshot['parts']};body,cloth=parts['body'],parts['garment'];ids=cloth['source_ids'];indices=cloth['indices'];tris=[indices[i:i+3] for i in range(0,len(indices),3)]
    changed_tri=[i for i,t in enumerate(tris) if any(ids[j]==847 for j in t)];support={ids[j] for i in changed_tri for j in tris[i]};local=[i for i,t in enumerate(tris) if support.intersection(ids[j] for j in t)]
    weight,radians=activation(snapshot['bones']);clav=next(b for b in snapshot['bones'] if b['name']=='clavicle_l');delta=[f32(x*weight) for x in rotate(quaternion(clav['canonical_posed']),target['delta_clavicle_m'])]
    candidate=copy.deepcopy(cloth);candidate['positions']=[[f32(v+d) for v,d in zip(p,delta)] if sid==847 else p[:] for sid,p in zip(ids,cloth['positions'])];candidate['normals']=predicted_normals(candidate['positions'],indices,cloth['normals'],ids,support,weight>0)
    changes=[i for i,(a,b) in enumerate(zip(cloth['positions'],candidate['positions'])) if raw_f32_hash([a])!=raw_f32_hash([b])];normal_changes=[i for i,(a,b) in enumerate(zip(cloth['normals'],candidate['normals'])) if a!=b]
    baseline_source=source_points(cloth);candidate_source=source_points(candidate)
    def strain(part):return geometry.strain(part['positions'],cloth['rest_positions'],[tris[i] for i in local])
    before_cross=crossing_pairs(cloth,body,changed_tri,ids);after_cross=crossing_pairs(candidate,body,changed_tri,ids)
    bvh=geometry.BVH(body['positions'],[body['indices'][i:i+3] for i in range(0,len(body['indices']),3)])
    nearest={'baseline':{str(s):bvh.nearest(baseline_source[s]) for s in sorted(support)},'candidate':{str(s):bvh.nearest(candidate_source[s]) for s in sorted(support)}}
    body_tris=[body['indices'][i:i+3] for i in range(0,len(body['indices']),3)];selected=[]
    for t in body_tris:
        if set(body['source_ids'][i] for i in t) in ({8319,8318,8309},{8319,8309,8310},{8102,8319,8310},{8102,8310,8128}):selected.append(t)
    need(len(selected)==4,'fixed body source probe fans missing');pixels=[]
    for t in selected:
        world=[point(body['display_transform'],body['positions'][i]) for i in t]
        for bary in BARY_SAMPLES:pixels.append(project([sum(w*p[j] for w,p in zip(bary,world)) for j in range(3)],cam,fr))
    before_probe=ray_probes(body,cloth,cam,fr,pixels);after_probe=ray_probes(body,candidate,cam,fr,pixels)
    roi=[[x+.5,y+.5] for y in range(185,205) for x in range(330,350)];before_roi=ray_probes(body,cloth,cam,fr,roi);after_roi=ray_probes(body,candidate,cam,fr,roi)
    faces=[];failures=[]
    for ti in changed_tri:
        tri=tris[ti];a=[cloth['positions'][i] for i in tri];b=[candidate['positions'][i] for i in tri];na=cross(sub(a[1],a[0]),sub(a[2],a[0]));nb=cross(sub(b[1],b[0]),sub(b[2],b[0]));area_a,area_b=length(na)/2,length(nb)/2;normal_dot=dot(na,nb)/(length(na)*length(nb)) if length(na)*length(nb)>1e-30 else None
        if length(na)>1e-12 and length(nb)<=1e-12:failures.append('new_degenerate:'+str(ti))
        if normal_dot is not None and normal_dot<=0:failures.append('winding_inversion:'+str(ti))
        faces.append({'render_triangle0':ti,'source_ids':[ids[i] for i in tri],'baseline_area_m2':area_a,'candidate_area_m2':area_b,'normal_dot':normal_dot,'normal_rotation_degrees':angle(na,nb)})
    if any(ids[i]!=847 for i in changes):failures.append('position_outside847')
    if any(ids[i] not in support for i in normal_changes):failures.append('normal_outside_frozen_support')
    neutral=snapshot['sample']['clip_id']=='b1_knee_flex_v1' or snapshot['sample']['source_seconds'] in (0,4)
    if neutral and (weight!=0 or changes or normal_changes):failures.append('neutral_knee_end_not_exact_zero')
    if after_probe['body_first']>before_probe['body_first']:failures.append('new_body_surface_probe_exposure')
    for key in ('body_pairs','nonadjacent_cloth_pairs'):
        new=sorted(set(map(tuple,after_cross[key]))-set(map(tuple,before_cross[key])))
        if new:failures.append('new_proper_crossing:'+key+':'+str(new))
    if kind=='fresh_default' and not after_roi['body_first']<before_roi['body_first']:failures.append('no_measurable_default_ROI_benefit')
    angles=[angle(cloth['normals'][i],candidate['normals'][i]) for i in normal_changes]
    return {'kind':kind,'parameters':snapshot['parameters'],'sample':snapshot['sample'],'activation':{'weight':weight,'angle_radians':radians,'delta_mesh_local_m':delta},'support':{'position_source_ids':[847],'changed_render_vertex_indices':changes,'normal_source_ids':sorted(support),'changed_render_normal_indices':normal_changes,'incident_triangles':changed_tri,'one_ring_triangles':local,'all_outside_positions_bit_exact':all(raw_f32_hash([a])==raw_f32_hash([b]) for sid,a,b in zip(ids,cloth['positions'],candidate['positions']) if sid!=847),'rest_positions_sha256':raw_f32_hash(cloth['rest_positions']),'source_joint_rows_sha256':hashlib.sha256(json.dumps(cloth['full_joint_influences'],separators=(',',':')).encode()).hexdigest()},'source847':{'baseline':baseline_source[847],'candidate':candidate_source[847]},'faces':faces,'local_shape':{'baseline':strain(cloth),'candidate':strain(candidate)},'normal_diagnostics':{'max_changed_angle_degrees':max((a for a in angles if a is not None),default=0),'zero_normal_indices':[i for i in normal_changes if length(candidate['normals'][i])<=1e-15],'method':'Existing Bevy angle-weighted indexed smooth normals, same f32EPS corner branch; f64 analytical approximation, original normals outside source support retained'},'proper_crossings':{'baseline':before_cross,'candidate':after_cross},'nearest_body_local_side':nearest,'fixed_body_surface_probes':{'baseline':before_probe,'candidate':after_probe},'fixed_default_ROI':{'baseline':before_roi,'candidate':after_roi},'failures':failures}

def run(args):
    need(not args.out.exists(),'unique output exists');args.out.mkdir(parents=True);(args.out/'frozen-evaluation-policy.json').write_text(json.dumps(POLICY,indent=2)+'\n')
    need(digest(args.target)==TARGET_SHA,'single frozen target changed');target=json.loads(args.target.read_text());ledger_path=ROOT/'experiments/70-b1-garment-defect/evidence/final-retained30/report.json';fixture_path=ROOT/'experiments/79-shoulder-pose-corrective/fixtures/historical-actual-activation.json';need(digest(ledger_path)==LEDGER_SHA and digest(fixture_path)==ACTIVATION_FIXTURE_SHA,'retained historical ledgers differ');ledger=json.loads(ledger_path.read_text());fixture=json.loads(fixture_path.read_text());rows={r['input_name']:r for r in ledger['frames']};need(digest(args.fresh)==FRESH_SHA,'new actual default SHA differs');fresh=json.loads(args.fresh.read_text())['frame'];snapshots=[]
    for case in fixture['cases']:
        path=args.history/case['input_name'];need(digest(path)==case['raw_gzip_sha256']==rows[case['input_name']]['input_sha256'],'historical complete input hash differs');record=json.loads(gzip.decompress(path.read_bytes()));s=record['snapshot'];need(s['sample']['clip_id']==case['clip'] and s['sample']['source_seconds']==s['sample']['position_seconds']==case['seconds'] and s['parameters']['torso_length']==case['torso'] and s['parameters']['jaw_drop']==0,'historical actual case mismatch');need(all(all(next(b for b in s['bones'] if b['name']==fb['name'])[k]==v for k,v in fb.items()) for fb in case['bones']),'complete original actual bones differ from selected frozen fixture');snapshots.append((case,s,path))
    old_default=next(s for c,s,p in snapshots if c['torso']==0 and c['clip']=='b1_arm_rehearsal_v1' and c['seconds']==2);comparison={}
    for role in ('body','garment'):
        a=next(p for p in old_default['parts'] if p['name']==role);b=next(p for p in fresh['full_base']['parts'] if p['name']==role);need(a['source_ids']==b['source_ids'] and a['indices']==b['indices'],'historical/fresh topology differs');error=max(abs(x-y) for aa,bb in zip(a['positions'],b['positions']) for x,y in zip(aa,bb));need(error<=1e-5,'historical/fresh default upload difference exceeds existing1e-5bound');comparison[role]=error
    work=json.loads((ROOT/'experiments/79-shoulder-pose-corrective/works/shoulder-rear-baseline-arms.nvwa.json').read_text());actual=fresh['camera'];m=actual['global_transform'];cols=([m[0],m[1],m[2]],[m[4],m[5],m[6]],[m[8],m[9],m[10]]);det=dot(cols[0],cross(cols[1],cols[2]));inverse=[[x/det for x in row] for row in (cross(cols[1],cols[2]),cross(cols[2],cols[0]),cross(cols[0],cols[1]))];cam=(*cols,m[12:15],inverse);fov=float(re.search(r'fov: ([0-9.e-]+)',actual['projection'])[1]);top=.05*math.tan(fov/2);right=top*1280/610;bp=-top+2*top*(610-720)/610;fr=(.05/right,2*.05/(top-bp),0.,(top+bp)/(top-bp));source=ROOT/'assets/characters/mpfb-b1-v1';body_faces=read_obj(source/'base.obj');cloth_faces=read_obj(source/'garment/female_sportsuit01.obj');delete=deleted_ids(source/'garment/female_sportsuit01.mhclo');results=[]
    for case,s,path in snapshots:
        for p in s['parts']:bind_source(p,body_faces if p['name']=='body' else cloth_faces,delete if p['name']=='body' else None)
        result=evaluate(s,target,cam,fr,'historical_actual_pose_analytical_correction');result['input']={'path':str(path),'sha256':digest(path)};results.append(result);print('CASE',case['input_name'],'weight',result['activation']['weight'],'failures',result['failures'],flush=True)
    result=evaluate(fresh['full_base'],target,cam,fr,'fresh_default');result['input']={'path':str(args.fresh),'sha256':digest(args.fresh)};results.append(result);print('FRESH',result['failures'],flush=True)
    failures=[{'sample':r['sample'],'torso':r['parameters']['torso_length'],'kind':r['kind'],'failures':r['failures']} for r in results if r['failures']];report={'status':'REJECT' if failures else 'OFFLINE_CONTROLS_PASS_VISUAL_ACCEPTANCE_NOT_RUN','scope':POLICY['numerical_scope']+' Historical18 full actual inputs and new default actual input are distinct; no new corrected upload/raw/GPU or complete collision.','helper_sha256':digest(Path(__file__)),'target_sha256':TARGET_SHA,'ledger_sha256':LEDGER_SHA,'history_default_vs_fresh_max_position_component_m':comparison,'policy':POLICY,'results':results,'failures':failures};(args.out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return 3 if failures else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);p.add_argument('--history',type=Path,required=True);p.add_argument('--fresh',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    try:sys.exit(run(p.parse_args()))
    except (ValueError,KeyError,TypeError) as e:print('NOT-RUN:',e,file=sys.stderr);sys.exit(2)
