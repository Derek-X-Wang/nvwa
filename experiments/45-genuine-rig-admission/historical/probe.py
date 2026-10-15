"""Private stdlib numeric inspection only. No inference or artifact export."""
import hashlib, itertools, json, math, runpy, struct
from pathlib import Path
P=Path('/Users/derekxwang/.codex/worktrees/m2-motion-provider/nvwa')
E=Path('/Users/derekxwang/.codex/worktrees/m2-experiment-integration/nvwa')
O=P/'.work/m2-genuine-mapping-feasibility'
raw=P/'.work/m2-provider/genuine-run-d375b71b87b1/raw'
expected={'root_positions.f32':'dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af','local_rotations_xyzw.f32':'67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55'}
hashes={}
for name, h in expected.items():
    b=(raw/name).read_bytes(); hashes[name]=hashlib.sha256(b).hexdigest(); assert hashes[name]==h
rb=(raw/'root_positions.f32').read_bytes(); qb=(raw/'local_rotations_xyzw.f32').read_bytes()
assert len(rb)==1080 and len(qb)==43200
rr=struct.unpack('<270f',rb); qq=struct.unpack('<10800f',qb)
assert all(math.isfinite(x) for x in rr+qq)
roots=[list(rr[i:i+3]) for i in range(0,len(rr),3)]
frames=[[list(qq[(t*30+j)*4:(t*30+j+1)*4]) for j in range(30)] for t in range(90)]
m=runpy.run_path(str(E/'experiments/43-rig-mapping/spike.py'),run_name='private_readonly_definitions')
fk,rot,mm,mv,tr,add,sub,length=[m[k] for k in ('fk','rotation','mm','mv','transpose','add','sub','length')]
s0=json.loads((P/'experiments/41-real-short-motion/source-skeleton.json').read_text())
s={'identity':'soma30','joint_names':s0['joint_names'],'parent_indices':[None if x<0 else x for x in s0['parents']], 'rest_local_translations_m':s0['rest_local_translations'],'rest_local_rotations_xyzw':s0['rest_local_rotations_xyzw'],'rest_local_scales_xyz':s0['rest_local_scales']}
target=m['fixture']()
source=[fk(s,q,r) for q,r in zip(frames,roots)]
mapped=[m['map_pose'](s,target,q,r)[0] for q,r in zip(frames,roots)]
# Exact target affine parent contribution to pelvis position, including target root scale.
root_scale=target['rest_local_scales_xyz'][0]
pelvis_t=target['rest_local_translations_m'][1]
offsets=[mv(rot(q[0]),[a*b for a,b in zip(root_scale,pelvis_t)]) for q in mapped]
exact_roots=[sub(r,d) for r,d in zip(roots,offsets)]
exact=[fk(target,q,r) for q,r in zip(mapped,exact_roots)]
old_roots=[add(target['rest_local_translations_m'][0],r) for r in roots]
old=[fk(target,q,r) for q,r in zip(mapped,old_roots)]
unrotated_roots=[sub(r,pelvis_t) for r in roots]
unrotated=[fk(target,q,r) for q,r in zip(mapped,unrotated_roots)]
def error(a,b): return max(length(sub(x,y)) for x,y in zip(a,b))
def trajectory(points):
    return {'first':points[0],'last':points[-1], 'min_xyz':[min(p[d] for p in points) for d in range(3)],'max_xyz':[max(p[d] for p in points) for d in range(3)],'path_3d_m':sum(length(sub(b,a)) for a,b in zip(points,points[1:])), 'path_xz_m':sum(math.hypot(b[0]-a[0],b[2]-a[2]) for a,b in zip(points,points[1:]))}
endpoint={}
for tn,sn in [('hand.L','LeftHand'),('hand.R','RightHand'),('foot.L','LeftFoot'),('foot.R','RightFoot')]:
    ti=target['joint_names'].index(tn); si=s['joint_names'].index(sn)
    endpoint[sn]={'source':trajectory([f[si] for f in source]),'target_hip_matched':trajectory([f[ti] for f in exact]),'max_target_source_position_difference_m':error([f[ti] for f in exact],[f[si] for f in source])}
# Quaternion representation negative controls on genuine bytes; q and -q equivalent.
negative={}
for label,fn in [('q_negated',lambda q:[-v for v in q]),('xyz_conjugated',lambda q:[-q[0],-q[1],-q[2],q[3]]),('XYWZ_misread',lambda q:[q[0],q[1],q[3],q[2]])]:
    pp=[fk(s,[fn(q) for q in qs],r) for qs,r in zip(frames,roots)]
    negative[label]=max(error(a,b) for a,b in zip(source,pp))
# Treating already-local raw rotations as globals then localizing a second time.
wrong=[]
for qs,r in zip(frames,roots):
    loc=[q if p is None else m['mul'](m['inv'](qs[p]),q) for p,q in zip(s['parent_indices'],qs)]
    wrong.append(fk(s,loc,r))
negative['parent_localized_twice_m']=max(error(a,b) for a,b in zip(source,wrong))
# Exhaust all 48 signed permutation bases; conjugating every rotation and every
# offset/root together yields indistinguishable equivariant FK, including det=-1.
max_equiv=0.; proper=improper=0
q=frames[47]; r=roots[47]; globals_=m['matrix_globals'](s,q)
for perm in itertools.permutations(range(3)):
    for signs in itertools.product((-1,1),repeat=3):
        B=[[float(signs[i]) if j==perm[i] else 0. for j in range(3)] for i in range(3)]
        det=(B[0][0]*(B[1][1]*B[2][2]-B[1][2]*B[2][1])-B[0][1]*(B[1][0]*B[2][2]-B[1][2]*B[2][0])+B[0][2]*(B[1][0]*B[2][1]-B[1][1]*B[2][0]))
        proper+=det>0; improper+=det<0
        g=[mm(mm(B,G),tr(B)) for G in globals_]; pos=[]
        for j,p in enumerate(s['parent_indices']):
            pos.append(mv(B,r) if p is None else add(pos[p],mv(g[p],mv(B,s['rest_local_translations_m'][j]))))
        max_equiv=max(max_equiv,error(pos,[mv(B,p) for p in source[47]]))
# Nondegenerate C++ six() algebra mirrored directly, independent of quaternion.
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): return [v/length(a) for v in a]
def six(x):
    a=norm(x[:3]); z=norm(cross(a,x[3:])); b=cross(z,a)
    return [list(v) for v in zip(a,b,z)]
axis_controls=[]
for i in range(3):
    for sign in (-1,1):
        R=rot(m['axis'](i,sign*math.pi/2)); x=[R[j][0] for j in range(3)]+[R[j][1] for j in range(3)]
        decoded=six(x); axis_controls.append({'axis':'XYZ'[i],'degrees':90*sign,'six':x,'matrix':decoded,'max_error':max(abs(a-b) for A,B in zip(R,decoded) for a,b in zip(A,B))})
paths=[P/'.work/m2-provider/runtime/kimodo/src'/n for n in ('motion_decode.cpp','skeleton.hpp','sequence.cpp','model.cpp','generate.cpp','motion_rep.cpp')]+[P/'.work/m2-provider/sources/cpp-scripts__export_glb.py',P/'experiments/41-real-short-motion/source-skeleton.json',E/'experiments/43-rig-mapping/spike.py',E/'experiments/43-rig-mapping/mapping-manifest.json',E/'experiments/42-motion-import/src/lib.rs',E/'experiments/42-motion-import/CONTRACT.md',E/'assets/fixtures/nvwa-humanoid.glb']
receipt={'kind':'private numeric feasibility only; no inference, admission, export, or playback','raw_sha256':hashes,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'frames':90,'joints':30,'max_raw_quaternion_norm_error':max(abs(length(q)-1) for f in frames for q in f),'root':trajectory(roots),'source_endpoints':endpoint,'target_root_rest':target['rest_local_translations_m'][0],'target_pelvis_local_rest':pelvis_t,'target_pelvis_rest_world':fk(target,target['rest_local_rotations_xyzw'],target['rest_local_translations_m'][0])[1],'old43_policy_hip_position_max_error_m':error([f[1] for f in old],roots),'old43_policy_hip_y_range':[min(f[1][1] for f in old),max(f[1][1] for f in old)],'hip_matched_root':trajectory(exact_roots),'hip_matched_hip_position_max_error_m':error([f[1] for f in exact],roots),'subtract_unrotated_pelvis_offset_max_error_m':error([f[1] for f in unrotated],roots),'add_target_root_rest_again_max_error_m':max(error(f,fk(target,q,add(r,target['rest_local_translations_m'][0]))) for f,q,r in zip(exact,mapped,exact_roots)),'source_negative_controls_max_position_error_m':negative,'all_signed_bases':{'proper':proper,'improper':improper,'max_equivariant_position_error_m':max_equiv,'meaning':'numeric self-consistency cannot establish trained axes'},'signed_90deg_six_algebra_controls':axis_controls}
(O/'numeric-proof.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_sha256','signed_90deg_six_algebra_controls')},indent=2))
