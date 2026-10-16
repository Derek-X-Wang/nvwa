#!/usr/bin/env python3
"""Independent f64 arithmetic and full MPFB comparison; never used as candidate input."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from validation import require,validate_frame
COMMON='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
POSES='8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2'
C=np.array([[1.,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metric(a,b,tol):
    a=np.array(a,dtype=float);b=np.array(b,dtype=float)
    require(a.shape==b.shape and a.size and np.isfinite(a).all() and np.isfinite(b).all(), 'full comparator validation failed')
    d=a-b
    return dict(count=len(a),max_component=float(np.max(np.abs(d))),rms_distance=float(np.sqrt(np.mean(np.sum(d*d,axis=-1)))),tolerance=tol,passed=bool(np.max(np.abs(d))<=tol))
def matrix(v):return np.array(v,dtype=float).reshape((4,4),order='F')
def points(p):return np.array(p)@C[:3,:3].T

def compare(candidate,reference,mutation=None):
    require(candidate['schema_version']==reference['schema_version']==1, 'full comparator validation failed')
    require(candidate['common_manifest_sha256']==reference['common_sha256']==COMMON, 'full comparator validation failed')
    require(reference['pose_sha256']==POSES and candidate['case_id']==reference['recipe_id'] and candidate['pose_id']==reference['pose_id'], 'full comparator validation failed')
    common_path=Path(__file__).resolve().parent.parent.parent/'.work/character-approved-20261016/common-sample.json'
    require(sha(common_path)==COMMON, 'common manifest hash mismatch')
    common=json.loads(common_path.read_text())
    expected_weights={}
    for parameter,value in reference['recipe'].items():
        for sign,source in common['parameters'][parameter]['targets'].items():
            name=Path(source).name.removesuffix('.gz').removesuffix('.target')
            expected_weights[name]=max(0.,-value if sign=='decr' else value)
    require(candidate['target_weights']==expected_weights, 'candidate recipe mismatch')
    result={};refs={b['name']:b for b in reference['bones']}
    for part in ('body','garment'):
        prefix='' if part=='body' else 'garment_'; entry=candidate['parts'][part];f=entry['frame'];ids=np.array(entry['source_vertex_ids'],dtype=int)
        vector_validation=validate_frame(f,len(ids),canonical=bool(candidate.get('frame_gauge_enabled')))
        bones=f['bones'];require(len(bones)==len(refs)==53 and {b['name'] for b in bones}==set(refs), 'full comparator validation failed')
        require(all(b['parent']==refs[b['name']]['parent'] for b in bones), 'full comparator validation failed')
        rest=np.array([matrix(b['rest']) for b in bones]);posed=np.array([matrix(b['posed']) for b in bones]);ibm=np.array([matrix(b['inverse_bind']) for b in bones])
        ref_rest=np.array([refs[b['name']]['matrix_local'] for b in bones]);ref_posed=np.array([refs[b['name']]['matrix_pose'] for b in bones])
        raw_rest=rest.copy();raw_posed=posed.copy();gauge_metrics={}
        if candidate.get('frame_gauge_enabled'):
            q=np.array([matrix(b['frame_gauge']) for b in bones]);canonical_rest=np.array([matrix(b['canonical_rest']) for b in bones]);canonical_posed=np.array([matrix(b['canonical_posed']) for b in bones]);qinverse=np.linalg.inv(q)
            gauge_metrics={'rest_gauge_identity':metric(raw_rest@qinverse,canonical_rest,1e-5),'posed_gauge_identity':metric(raw_posed@qinverse,canonical_posed,1e-5),'physical_skin_identity':metric(raw_posed@ibm,canonical_posed@np.linalg.inv(canonical_rest),1e-5)}
            require(all(m['passed'] for m in gauge_metrics.values()), 'frame gauge identity failed')
            rest=canonical_rest;posed=canonical_posed

        kernel=raw_posed@ibm
        if mutation=='wrong-bone-map':kernel=np.roll(kernel,1,axis=0)
        positions=np.array(f['positions']);unposed=np.array(f['rest_positions']);ji=np.array(f['joint_indices'],dtype=int);jw=np.array(f['joint_weights'])
        require(len(ids)==len(positions)==len(unposed)==len(ji)==len(jw) and ji.min()>=0 and ji.max()<53, 'full comparator validation failed')
        full_influences=f.get('full_joint_influences')
        raw_sums=None
        if candidate.get('route_id')=='b1-full-weight-cpu':
            require(full_influences is not None and len(full_influences)==len(ids), 'full comparator validation failed')
            max_influences=max(map(len,full_influences));ji=np.zeros((len(ids),max_influences),dtype=int);jw=np.zeros((len(ids),max_influences));raw_sums=[]
            for i,row in enumerate(full_influences):
                total=sum(w for _,w in row);require(total>0 and all(0<=j<53 and w>0 and math.isfinite(w) for j,w in row), 'full comparator validation failed')
                raw_sums.append(total)
                for k,(j,w) in enumerate(row):ji[i,k]=j;jw[i,k]=w/total

        homogeneous=np.c_[unposed,np.ones(len(unposed))]
        oracle=np.sum(np.einsum('nkij,nj->nki',kernel[ji],homogeneous)*jw[:,:,None],axis=1)[:,:3]
        actual=unposed if mutation=='omitted-skin' else positions
        oracle_metric=metric(actual,oracle,1e-5)
        expected=np.array(reference[prefix+'positions']);require(ids.min()>=0 and ids.max()<len(expected), 'full comparator validation failed')
        coverage=len(set(ids.tolist()))==len(expected)
        full=metric(points(actual),expected[ids],1e-3 if part=='body' else 3e-3);full.update(source_count=len(expected),mapped_source_count=len(set(ids.tolist())),mesh_count=len(ids),coverage_complete=coverage);full['passed'] &= coverage
        errors=np.abs(points(actual)-expected[ids]).max(axis=1)
        worst=int(errors.argmax());full['worst_source_id']=int(ids[worst])
        if part=='body':
            groups=json.loads((Path(__file__).resolve().parent.parent/'55-source-character-runtime/data/vertex_groups.json').read_text())
            classifications={}
            for group in ('body','HelperGeometry','helper-tights','helper-skirt','JointCubes'):
                group_ids={i for start,end in groups[group] for i in range(start,end+1)}
                mask=np.array([int(i) in group_ids for i in ids])
                if mask.any():
                    selected=np.flatnonzero(mask);w=selected[int(errors[mask].argmax())]
                    classifications[group]={'source_vertices':len(set(ids[mask].tolist())),'max_component':float(errors[mask].max()),'worst_source_id':int(ids[w]),'points_over_full_gate':int((errors[mask]>1e-3).sum())}
            full['secondary_source_groups']=classifications
            full['worst_source_groups']=[name for name,ranges in groups.items() if any(start<=int(ids[worst])<=end for start,end in ranges)]
        # Compare actual source attributes to original MPFB deform distributions; no substitutions.
        ref_weights=reference['body_weights' if part=='body' else 'garment_weights'];ref_bone_names=[b['name'] for b in reference['bones']];cand_names=[b['name'] for b in bones]
        unique={}
        for i,sid in enumerate(ids):unique.setdefault(int(sid),i)
        l1=[];padded=0;truncated=0;lost=[]
        for sid,i in unique.items():
            full_weights={ref_bone_names[j]:w for j,w in ref_weights[sid] if w>0};total=sum(full_weights.values())
            normalized={k:v/total for k,v in full_weights.items()} if total else {}
            actual_weights={}
            for j,w in zip(ji[i],jw[i]):actual_weights[cand_names[j]]=actual_weights.get(cand_names[j],0)+float(w)
            l1.append(sum(abs(actual_weights.get(n,0)-normalized.get(n,0)) for n in set(normalized)|set(actual_weights)))
            padded+=0<len(full_weights)<4;truncated+=len(full_weights)>4;lost.append(sum(sorted(normalized.values(),reverse=True)[4:]))
        finite=all(np.isfinite(np.array(f[k])).all() and len(f[k])==len(ids) for k in ('normals','rest_normals','tangents'))
        norm_lengths=np.linalg.norm(f['normals'],axis=1);tan_lengths=np.linalg.norm(np.array(f['tangents'])[:,:3],axis=1)
        result[part]={'candidate_weight_oracle':oracle_metric,'full_mpfb_geometry':full,
            'rest_matrix':metric(C@rest,ref_rest,1e-4),'posed_matrix':metric(C@posed,ref_posed,1e-4),
            'raw_rest_matrix':metric(C@raw_rest,ref_rest,1e-4),'raw_posed_matrix':metric(C@raw_posed,ref_posed,1e-4),'frame_gauge_identities':gauge_metrics,
            'joint_heads':metric((C@posed)[:,:3,3],ref_posed[:,:3,3],1e-5),
            'normals_tangents':vector_validation,
            'weight_difference':{'source_vertices':len(unique),'reference_influences_under_four':padded,'reference_influences_over_four':truncated,'max_l1_normalized_distribution_delta':max(l1),'mean_l1_normalized_distribution_delta':sum(l1)/len(l1),'reference_mass_beyond_four_diagnostic':max(lost),'actual_truncation_performed':raw_sums is None,'actual_route':candidate.get('route_id','b1-four-slot'),'actual_max_influences':int(ji.shape[1]),'raw_transferred_sum_min':min(raw_sums) if raw_sums else None,'raw_transferred_sum_max':max(raw_sums) if raw_sums else None,'source_padding_policy':('full candidate transfer, no truncation; recorded raw then normalized for LBS' if raw_sums else 'actual four slots, zero-pad repair; no reference substitution')}}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--reference-sha256',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutation',choices=['wrong-bone-map','omitted-skin']);a=p.parse_args()
    require(sha(a.reference)==a.reference_sha256, 'frozen reference hash mismatch')
    c=json.loads(a.candidate.read_text());r=json.loads(a.reference.read_text());m=compare(c,r,a.mutation)
    passed=all(v['candidate_weight_oracle']['passed'] and v['full_mpfb_geometry']['passed'] and v['rest_matrix']['passed'] and v['posed_matrix']['passed'] and v['joint_heads']['passed'] and v['normals_tangents']['present_finite'] for v in m.values())
    result=dict(status='PASS' if passed else 'FAIL',candidate_sha256=sha(a.candidate),reference_sha256=sha(a.reference),comparator_sha256=sha(Path(__file__)),validator_sha256=sha(Path(__file__).with_name('validation.py')),mutation=a.mutation,measures=m)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result));return 0 if passed else 3
if __name__=='__main__':raise SystemExit(main())
