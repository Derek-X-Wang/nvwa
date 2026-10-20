#!/usr/bin/env python3
"""Independent plane/segment crossing witnesses and fixed-cohort invariant audit.

Consumes frozen evaluator deltas, not its triangle intersection predicate.
Does not author, optimize, or score another candidate.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def check(value):
    if not value:raise ValueError('fixed rejection audit invariant failed')

def witnesses(first,second):
    found=[]
    for direction,(a,b) in enumerate(((first,second),(second,first))):
        u,v=sub(b[1],b[0]),sub(b[2],b[0]);n=cross(u,v);uu,uv,vv=dot(u,u),dot(u,v),dot(v,v);denom=uu*vv-uv*uv
        if abs(denom)<1e-24:continue
        for edge in range(3):
            p,q=a[edge],a[(edge+1)%3];sp,sq=dot(sub(p,b[0]),n),dot(sub(q,b[0]),n)
            if sp*sq>=0:continue
            t=sp/(sp-sq)
            if not 1e-9<t<1-1e-9:continue
            point=[x+t*(y-x) for x,y in zip(p,q)];r=sub(point,b[0]);ru,rv=dot(r,u),dot(r,v);beta=(ru*vv-rv*uv)/denom;gamma=(rv*uu-ru*uv)/denom;bary=[1-beta-gamma,beta,gamma]
            if min(bary)>1e-9:found.append({'direction':direction,'edge':edge,'edge_fraction':t,'barycentric':bary,'point_m':point})
    return found

def audit(report_path):
    report=json.loads(report_path.read_text());check(report['status']=='REJECT');rows=report['results'];check(len(rows)==19)
    failed=[r for r in rows if r['failures']];check(len(failed)==6)
    out=[];zero_count=0
    for r in rows:
        check(r['support']['all_outside_positions_bit_exact'])
        check(all(f['normal_dot'] is None or f['normal_dot']>0 for f in r['faces']))
        check(not any(f.startswith(('new_degenerate','winding_inversion','position_outside','normal_outside','non_position_normal','neutral_knee_end','new_body_surface_probe_exposure')) for f in r['failures']))
        check(r['fixed_body_surface_probes']['candidate']['body_first']<=r['fixed_body_surface_probes']['baseline']['body_first'])
        check(not(set(map(tuple,r['proper_crossings']['candidate']['nonadjacent_cloth_pairs']))-set(map(tuple,r['proper_crossings']['baseline']['nonadjacent_cloth_pairs']))))
        if r['activation']['weight']==0:
            zero_count+=1;check(not r['support']['changed_render_vertex_indices']);check(not r['support']['changed_render_normal_indices'])
        if not r['failures']:continue
        raw=Path(r['input']['path']).read_bytes();check(hashlib.sha256(raw).hexdigest()==r['input']['sha256']);s=json.loads(gzip.decompress(raw))['snapshot'];parts={p['name']:p for p in s['parts']};cloth,body=parts['garment'],parts['body'];deltas=r['activation']['delta_mesh_local_m_by_source']
        def tri(part,ti,corrected=False):
            result=[]
            for i in part['indices'][3*ti:3*ti+3]:
                p=part['positions'][i];delta=deltas.get(str(part['source_ids'][i]),[0,0,0])
                result.append([f32(x+d) for x,d in zip(p,delta)] if corrected and any(delta) else p[:])
            return result
        new=set(map(tuple,r['proper_crossings']['candidate']['body_pairs']))-set(map(tuple,r['proper_crossings']['baseline']['body_pairs']));check(new=={(240,13661),(1577,13661)})
        for ct,bt in sorted(new):
            check(not witnesses(tri(cloth,ct),tri(body,bt)));w=witnesses(tri(cloth,ct,True),tri(body,bt));check(bool(w))
            out.append({'torso':r['parameters']['torso_length'],'seconds':r['sample']['source_seconds'],'pair':[ct,bt],'cloth_source_ids':[cloth['source_ids'][i] for i in cloth['indices'][3*ct:3*ct+3]],'witnesses':w})
    fresh=next(r for r in rows if r['kind']=='fresh_default');check(fresh['fixed_default_ROI']['baseline']['body_first']==44 and fresh['fixed_default_ROI']['candidate']['body_first']==0)
    return {'status':'PASS_INDEPENDENT_REJECTION_AND_INVARIANT_AUDIT','report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),'cases':len(rows),'rejected_cases':len(failed),'exact_zero_cases':zero_count,'independent_new_pair_witnesses':out,'scope':'Analytical finite-pose audit of retained actual baseline positions and frozen analytical delta. Actual candidate upload and complete collision NOT-RUN.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();check(not a.out.exists());r=audit(a.report);a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['cases'],r['rejected_cases'],r['exact_zero_cases'])
