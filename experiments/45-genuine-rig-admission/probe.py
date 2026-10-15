#!/usr/bin/env python3
"""Numerical HOLD study of one genuine clip; no model, normalizer or exporter.

Defaults to JSON on stdout. --out writes a result file without replacing different
existing bytes. All inputs are checked before frozen experiment 43 definitions load.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
RAW = 'experiments/44-approved-cpu-motion-trial/evidence/run/raw/'
PINNED = {
    'experiments/41-real-short-motion/source-skeleton.json': 'd137f3ea5522deeb70257d2fd5522ca6d5436c0145ea001a1e8b4fc646cddd9a',
    'experiments/43-rig-mapping/spike.py': '063aefdd56d988256154b291b7f783d874f513b714303c546a36d8bf695bfe93',
    'assets/fixtures/nvwa-humanoid.glb': 'f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6',
    'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json': '554fd2e64e316d218fd699bbbe8d3e45351a7b3a3e08ef077cdc2c6cfaaa52c9',
    'experiments/44-approved-cpu-motion-trial/evidence/run/process/receipt.json': 'f67726f84982d6e5bd7c22e944131a7991016508e541d88972da6e20abc6410b',
    'experiments/44-approved-cpu-motion-trial/evidence/run/process/stdout.txt': 'd8cafdcca9f05b92f112232345c7435335858a1f019cabc2067d30ba4e71d5d1',
    RAW+'root_positions.f32': 'dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af',
    RAW+'local_rotations_xyzw.f32': '67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_hash(data, expected, label):
    require(hashlib.sha256(data).hexdigest() == expected, 'SHA256 mismatch: '+label)
    return data


def check_root_oracle(value):
    require(value < 1e-12, 'target pelvis world trajectory mismatch')


def reject_semantic_axis_claim(result):
    # Both proper and improper bases preserve FK, so this study cannot identify
    # semantic front/left. Never turn this invariant into an admission success.
    require(result['proper'] == 24 and result['improper'] == 24, 'basis enumeration')
    require(result['max_equivariant_position_error_m'] < 1e-12, 'basis FK invariant')
    raise ValueError('semantic axes unresolved by signed-basis FK equivalence')


def encode(result):
    return (json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def write_result(path, data):
    path=Path(path)
    require(not path.is_symlink(), 'output symlink rejected')
    if path.exists():
        require(path.is_file() and path.read_bytes() == data, 'different output exists')
        return
    # Parent must already exist. Exclusive create also prevents an overwrite race.
    with path.open('xb') as stream:
        stream.write(data)


def inspect(root=ROOT):
    root=Path(root).resolve()
    require(root == ROOT, 'only the repository containing this study is supported')
    inputs={name:check_hash((root/name).read_bytes(),pin,name) for name,pin in PINNED.items()}
    raw=root/RAW
    generation=json.loads(inputs['experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'])
    require(generation['returncode']==0 and generation['reason']=='exited' and generation['raw_complete'], 'successful public trial receipt required')
    require(generation['request']['frames']==90 and generation['request']['fps']==30, 'exact clip timing')
    for record in generation['raw_provenance']:
        name=Path(record['path']).name
        require(PINNED[RAW+name] == record['sha256'], 'receipt raw identity')
    rb=inputs[RAW+'root_positions.f32']; qb=inputs[RAW+'local_rotations_xyzw.f32']
    require(len(rb)==1080 and len(qb)==43200, 'wrong raw shape')
    rr=struct.unpack('<270f',rb); qq=struct.unpack('<10800f',qb)
    require(all(math.isfinite(x) for x in rr+qq), 'nonfinite raw floats')
    roots=[list(rr[i:i+3]) for i in range(0,len(rr),3)]
    frames=[[list(qq[(t*30+j)*4:(t*30+j+1)*4]) for j in range(30)] for t in range(90)]
    frozen_path=root/'experiments/43-rig-mapping/spike.py'
    m={'__file__':str(frozen_path), '__name__':'readonly_definitions'}
    # Execute the hash-checked bytes, not a second read of the source file.
    exec(compile(inputs['experiments/43-rig-mapping/spike.py'], str(frozen_path), 'exec'),m)
    fk,rot,mm,mv,tr,add,sub,length=[m[k] for k in ('fk','rotation','mm','mv','transpose','add','sub','length')]
    s0=json.loads(inputs['experiments/41-real-short-motion/source-skeleton.json'])
    s={'identity':'soma30','joint_names':s0['joint_names'],'parent_indices':[None if x<0 else x for x in s0['parents']], 'rest_local_translations_m':s0['rest_local_translations'],'rest_local_rotations_xyzw':s0['rest_local_rotations_xyzw'],'rest_local_scales_xyz':s0['rest_local_scales']}
    target=m['fixture']()
    require(target['parent_indices'][:2] == [None, 0], 'target root/pelvis topology')
    require(target['joint_names'][:2] == ['root', 'pelvis'], 'target root/pelvis identities')
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
    receipt={'kind':'report-only genuine-sample numerical admission HOLD study; no normalizer/export/playback','input_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in inputs.items()},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'admission':'HOLD','provenance_kind':'generated','frames':90,'joints':30,'max_raw_quaternion_norm_error':max(abs(length(q)-1) for f in frames for q in f),'root':trajectory(roots),'source_endpoints':endpoint,'target_root_rest':target['rest_local_translations_m'][0],'target_pelvis_local_rest':pelvis_t,'target_pelvis_rest_world':fk(target,target['rest_local_rotations_xyzw'],target['rest_local_translations_m'][0])[1],'old43_policy_hip_position_max_error_m':error([f[1] for f in old],roots),'old43_policy_hip_y_range':[min(f[1][1] for f in old),max(f[1][1] for f in old)],'hip_matched_root':trajectory(exact_roots),'hip_matched_hip_position_max_error_m':error([f[1] for f in exact],roots),'subtract_unrotated_pelvis_offset_max_error_m':error([f[1] for f in unrotated],roots),'add_target_root_rest_again_max_error_m':max(error(f,fk(target,q,add(r,target['rest_local_translations_m'][0]))) for f,q,r in zip(exact,mapped,exact_roots)),'source_negative_controls_max_position_error_m':negative,'all_signed_bases':{'proper':proper,'improper':improper,'max_equivariant_position_error_m':max_equiv,'meaning':'numeric self-consistency cannot establish trained axes'},'signed_90deg_six_algebra_controls':axis_controls}
    source_rest=fk(s,s['rest_local_rotations_xyzw'],[0,0,0])
    target_rest=fk(target,target['rest_local_rotations_xyzw'],target['rest_local_translations_m'][0])
    receipt['rest_correspondence']={sn:{'source_zero_hip_rest_xyz':source_rest[s['joint_names'].index(sn)],
        'target_bind_world_xyz':target_rest[target['joint_names'].index(tn)]}
        for sn,tn in [('LeftArm','upper_arm.L'),('LeftHand','hand.L'),('LeftLeg','thigh.L'),('LeftFoot','foot.L')]}
    receipt['sample_interval_seconds']=1/30
    receipt['sampled_first_to_last_seconds']=89/30
    require(receipt['max_raw_quaternion_norm_error'] < 1e-7, 'raw quaternion norm')
    check_root_oracle(receipt['hip_matched_hip_position_max_error_m'])
    require(.829 < receipt['old43_policy_hip_position_max_error_m'] < .831, 'old43 root negative not exposed')
    require(receipt['subtract_unrotated_pelvis_offset_max_error_m'] > .028, 'unrotated pelvis negative not exposed')
    require(abs(receipt['add_target_root_rest_again_max_error_m']-.07999999821186066)<1e-12, 'root double-add negative')
    require(negative['q_negated']==0, 'q/-q equivalence')
    require(negative['xyz_conjugated']>1 and negative['XYWZ_misread']>1 and negative['parent_localized_twice_m']>.7, 'representation negatives not exposed')
    require(all(c['max_error']<1e-12 for c in axis_controls), 'signed six algebra controls')
    try:
        reject_semantic_axis_claim(receipt['all_signed_bases'])
    except ValueError as error:
        require(str(error).startswith('semantic axes unresolved'), 'unexpected basis failure')
        receipt['semantic_axis_admission']='HOLD: '+str(error)
    else:
        raise ValueError('semantic axes incorrectly admitted')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='new JSON result file; parent must exist')
    args=parser.parse_args()
    data=encode(inspect())
    if args.out is None:
        print(data.decode(),end='')
    else:
        write_result(args.out,data)
        print(json.dumps({'admission':'HOLD','result':str(args.out),'sha256':hashlib.sha256(data).hexdigest()}))


if __name__=='__main__':
    main()
