#!/usr/bin/env python3
"""Portable independent issue59 oracle. Stdlib; no experiment43/45/46 imports.

This freezes numerical consequences of explicit hypotheses, not anatomy.
All arrays are read from the single public44 sample. No generated output motion.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PINS = {'assets/fixtures/nvwa-humanoid.glb': 'f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6', 'experiments/41-real-short-motion/source-skeleton.json': 'd137f3ea5522deeb70257d2fd5522ca6d5436c0145ea001a1e8b4fc646cddd9a', 'experiments/43-rig-mapping/spike.py': '063aefdd56d988256154b291b7f783d874f513b714303c546a36d8bf695bfe93', 'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json': '554fd2e64e316d218fd699bbbe8d3e45351a7b3a3e08ef077cdc2c6cfaaa52c9', 'experiments/44-approved-cpu-motion-trial/evidence/run/process/receipt.json': 'f67726f84982d6e5bd7c22e944131a7991016508e541d88972da6e20abc6410b', 'experiments/44-approved-cpu-motion-trial/evidence/run/process/stdout.txt': 'd8cafdcca9f05b92f112232345c7435335858a1f019cabc2067d30ba4e71d5d1', 'experiments/44-approved-cpu-motion-trial/evidence/run/raw/local_rotations_xyzw.f32': '67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55', 'experiments/44-approved-cpu-motion-trial/evidence/run/raw/root_positions.f32': 'dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af', 'tools/blender/generate_fixture.py': 'bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e'}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def plus(a, b):
    return [x+y for x, y in zip(a, b)]


def minus(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(dot(v, v))


def normalized(v):
    n = norm(v)
    require(math.isfinite(n) and n > 1e-15, 'independent numerical invariant at source line 47')
    return [x/n for x in v]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def ident(n=3):
    return [[float(i == j) for j in range(n)] for i in range(n)]


def transpose(m):
    return list(map(list, zip(*m)))


def product(a, b):
    return [[dot(row, col) for col in zip(*b)] for row in a]


def transform(m, v):
    return [dot(row, v) for row in m]


def quat_matrix(q):
    # q=(v,w): R=(w*w-v.v)I + 2vv^T + 2w[v]_cross.
    x, y, z, w = normalized(q)
    v = [x, y, z]
    skew = [[0, -z, y], [z, 0, -x], [-y, x, 0]]
    return [[(w*w-dot(v,v))*float(i == j)+2*v[i]*v[j]+2*w*skew[i][j]
             for j in range(3)] for i in range(3)]


def affine(r, t, s):
    return [[r[i][j]*s[j] for j in range(3)]+[t[i]] for i in range(3)]+[[0,0,0,1]]


def rotation_part(m):
    return [row[:3] for row in m[:3]]


def position(m):
    return [m[i][3] for i in range(3)]


def fk(parents, translations, rotations, scales):
    result = []
    for p, t, r, s in zip(parents, translations, rotations, scales):
        local = affine(r, t, s)
        result.append(local if p is None else product(result[p], local))
    return result


def angle(a, b):
    return math.degrees(math.acos(max(-1., min(1., dot(normalized(a), normalized(b))))))


def det(m):
    return dot(m[0], cross(m[1], m[2]))


def target_glb(path):
    raw = path.read_bytes()
    require(struct.unpack_from('<III', raw) == (0x46546c67, 2, len(raw)), 'independent numerical invariant at source line 110')
    offset, chunks = 12, []
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset)
        chunks.append((kind, raw[offset+8:offset+8+size]))
        offset += size+8
    require(offset == len(raw), 'independent numerical invariant at source line 116')
    g = json.loads(next(data for kind, data in chunks if kind == 0x4e4f534a))
    nodes, joints = g['nodes'], g['skins'][0]['joints']
    parent = {}
    for i, node in enumerate(nodes):
        for c in node.get('children', []):
            require(c not in parent, 'independent numerical invariant at source line 122')
            parent[c] = i
    cache = {}
    def local(i):
        n = nodes[i]
        if 'matrix' in n:
            return [[n['matrix'][col*4+row] for col in range(4)] for row in range(4)]
        return affine(quat_matrix(n.get('rotation', [0,0,0,1])), n.get('translation',[0,0,0]), n.get('scale',[1,1,1]))
    def world(i):
        if i not in cache:
            cache[i] = product(world(parent[i]), local(i)) if i in parent else local(i)
        return cache[i]
    for i in range(len(nodes)):
        world(i)
    nj = [nodes[i] for i in joints]
    p = [joints.index(parent[i]) if parent.get(i) in joints else None for i in joints]
    require(all(v is None or v < j for j,v in enumerate(p)), 'independent numerical invariant at source line 138')
    require(all('matrix' not in n for n in nj), 'independent numerical invariant at source line 139')
    external = [parent[i] for i in joints if parent.get(i) not in joints and i in parent]
    require(all(cache[i] == ident(4) for i in external), 'independent numerical invariant at source line 141')
    return {'names':[n['name'] for n in nj], 'parents':p,
            'translations':[n.get('translation',[0,0,0]) for n in nj],
            'rotations':[quat_matrix(n.get('rotation',[0,0,0,1])) for n in nj],
            'scales':[n.get('scale',[1,1,1]) for n in nj],
            'world':[cache[i] for i in joints], 'joint_node_indices':joints,
            'external_ancestor_world_identity':True}


def ray_observability(names, parents, worlds):
    rows=[]
    for j,name in enumerate(names):
        children=[k for k,p in enumerate(parents) if p == j]
        outgoing=[minus(position(worlds[k]),position(worlds[j])) for k in children]
        sine=max((norm(cross(normalized(a),normalized(b)))
                  for a,b in itertools.combinations(outgoing,2)), default=0.)
        rank=0 if not outgoing else 2 if sine>1e-8 else 1
        row={'joint':name,'children':[names[k] for k in children],
             'outgoing_frame_rank':rank,
             'maximum_outgoing_pair_sine':sine,
             'status':'unobservable' if rank==0 else 'twist_free' if rank==1 else 'frame_from_geometry_conditional'}
        if parents[j] is not None and outgoing:
            incoming=minus(position(worlds[j]),position(worlds[parents[j]]))
            row['incident_plane_max_sine']=max(norm(cross(normalized(incoming),normalized(v))) for v in outgoing)
        rows.append(row)
    return rows


def signed_anchors():
    # Source metadata convention, target generator convention after Y-up export.
    s={'up':[0,1,0], 'front':[0,0,1], 'named_left':[1,0,0]}
    t={'up':[0,1,0], 'front':[0,0,1], 'named_left':[-1,0,0]}
    rows=[]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1,1),repeat=3):
            m=[[float(signs[i]) if j==perm[i] else 0. for j in range(3)] for i in range(3)]
            a={k:angle(transform(m,v),t[k]) for k,v in s.items()}
            rows.append({'matrix':m,'determinant':round(det(m)), 'anchor_angle_degrees':a,
                         'exact_anchor_count':sum(v<1e-8 for v in a.values())})
    return {'source_declared_axes':s,'target_authored_axes':t,
            'basis_mapping_assumption':'column vectors; Blender (x,y,z) -> glTF (x,z,-y); front authored -Y',
            'semantic_status':'Conventions and name assignments; no external anatomical validation.',
            'proper_rotation_maximum_matching_anchors':max(r['exact_anchor_count'] for r in rows if r['determinant']==1),
            'best_proper_candidates':[r for r in rows if r['determinant']==1 and r['exact_anchor_count']==2],
            'all_three_anchor_candidates':[r for r in rows if r['exact_anchor_count']==3],
            'all_signed_permutations':rows}


def analyze():
    input_hashes={p:digest(ROOT/p) for p in PINS}
    require(input_hashes==PINS, 'frozen input SHA-256 mismatch')
    source=json.loads((ROOT/'experiments/41-real-short-motion/source-skeleton.json').read_text())
    sn=source['joint_names']; sp=[None if p==-1 else p for p in source['parents']]
    sr=[quat_matrix(q) for q in source['rest_local_rotations_xyzw']]
    sw=fk(sp,source['rest_local_translations'],sr,source['rest_local_scales'])
    target=target_glb(ROOT/'assets/fixtures/nvwa-humanoid.glb')
    tn=target['names']; tp=target['parents']; tt=target['translations']; tr=target['rotations']; ts=target['scales']
    tw=target['world']; ri=tn.index('root'); pi=tn.index('pelvis')
    require(ri==0 and pi==1 and tp[pi]==ri, 'independent numerical invariant at source line 199')
    rawdir=ROOT/'experiments/44-approved-cpu-motion-trial/evidence/run/raw'
    qb=(rawdir/'local_rotations_xyzw.f32').read_bytes(); rb=(rawdir/'root_positions.f32').read_bytes()
    require(len(qb)==90*30*4*4 and len(rb)==90*3*4, 'independent numerical invariant at source line 202')
    qa=struct.unpack('<10800f',qb); ra=struct.unpack('<270f',rb)
    frames=[[list(qa[f*120+j*4:f*120+j*4+4]) for j in range(30)] for f in range(90)]
    roots=[list(ra[f*3:f*3+3]) for f in range(90)]
    require(all(math.isfinite(x) for x in qa+ra), 'independent numerical invariant at source line 206')
    qnorm=[norm(q) for f in frames for q in f]
    anchors=signed_anchors()
    obs={'source':ray_observability(sn,sp,sw),'target':ray_observability(tn,tp,tw)}
    source_index={n:i for i,n in enumerate(sn)}; target_index={n:i for i,n in enumerate(tn)}
    # Exact frozen43 MAP names, transcribed as a relation, not imported or executed.
    relation={'root':'Hips','pelvis':'Hips','spine':'Spine1','chest':'Chest','neck':'Neck1','head':'Head',
              'upper_arm.L':'LeftArm','forearm.L':'LeftForeArm','hand.L':'LeftHand',
              'upper_arm.R':'RightArm','forearm.R':'RightForeArm','hand.R':'RightHand',
              'thigh.L':'LeftLeg','shin.L':'LeftShin','foot.L':'LeftFoot',
              'thigh.R':'RightLeg','shin.R':'RightShin','foot.R':'RightFoot'}
    # Rest orientation matrices are composed without scales for the frozen43 relation.
    def globals_rotation(parents,local):
        out=[]
        for p,r in zip(parents,local):out.append(r if p is None else product(out[p],r))
        return out
    target_rest_r=globals_rotation(tp,tr); source_rest_r=globals_rotation(sp,sr)
    tpelvis=position(tw[pi]); d=[tt[pi][i]*ts[ri][i] for i in range(3)]
    pelvis_rows=[]; negatives={k:[] for k in ('unrotated_pelvis_offset','double_rest_root','double_trajectory','double_absolute_source_root','wrong_root_rotation','historical43_absolute_pelvis_error')}
    qsignmax=0.; target_qsignmax=0.; source_positions=[]
    for f,(qs,root) in enumerate(zip(frames,roots)):
        rs=[quat_matrix(q) for q in qs]
        source_t=list(source['rest_local_translations']);source_t[0]=root
        source_world=fk(sp,source_t,rs,source['rest_local_scales'])
        source_positions.append([position(m) for m in source_world])
        source_global=globals_rotation(sp,rs)
        desired=[product(product(source_global[source_index[relation[n]]],transpose(source_rest_r[source_index[relation[n]]])),target_rest_r[j]) for j,n in enumerate(tn)]
        local=[r if tp[j] is None else product(transpose(desired[tp[j]]),r) for j,r in enumerate(desired)]
        root_r=desired[ri]
        rotated_offset=transform(root_r,d)
        candidate_root=minus(root,rotated_offset)
        cand_t=list(tt);cand_t[ri]=candidate_root
        candidate=fk(tp,cand_t,local,ts)
        cand_pelvis=position(candidate[pi])
        expected=list(root)
        # Hypothesis B: preserve target neutral pelvis, use displacement from first sample.
        delta=minus(root,roots[0]);neutral_relative=plus(tpelvis,delta)
        neutral_root=minus(neutral_relative,rotated_offset)
        relative_t=list(tt);relative_t[ri]=neutral_root
        relative_affine=position(fk(tp,relative_t,local,ts)[pi])
        hist_root=plus(tt[ri],minus(root,source['rest_local_translations'][0]))
        hist_pelvis=plus(hist_root,rotated_offset)
        wrong_r=transpose(root_r)
        controls={
            'unrotated_pelvis_offset':minus(root,d),
            'double_rest_root':plus(candidate_root,tt[ri]),
            'double_trajectory':plus(candidate_root,delta),
            'double_absolute_source_root':plus(candidate_root,root),
            'wrong_root_rotation':minus(root,transform(wrong_r,d)),
        }
        for key, badroot in controls.items():
            negatives[key].append(norm(minus(plus(badroot,rotated_offset),expected)))
        negatives['historical43_absolute_pelvis_error'].append(norm(minus(hist_pelvis,expected)))
        neg_rs=[quat_matrix([-x for x in q]) for q in qs]
        neg_world=fk(sp,source_t,neg_rs,source['rest_local_scales'])
        qsignmax=max(qsignmax,max(norm(minus(position(a),position(b))) for a,b in zip(source_world,neg_world)))
        neg_global=globals_rotation(sp,neg_rs)
        neg_desired=[product(product(neg_global[source_index[relation[n]]],transpose(source_rest_r[source_index[relation[n]]])),target_rest_r[j]) for j,n in enumerate(tn)]
        neg_local=[r if tp[j] is None else product(transpose(neg_desired[tp[j]]),r) for j,r in enumerate(neg_desired)]
        neg_target=fk(tp,cand_t,neg_local,ts)
        target_qsignmax=max(target_qsignmax,max(norm(minus(position(a),position(b))) for a,b in zip(candidate,neg_target)))
        pelvis_rows.append({'frame':f,'raw_root_m':root,'root_rotation_matrix':root_r,
                            'rotated_target_root_to_pelvis_m':rotated_offset,
                            'absolute_pelvis_candidate_root_m':candidate_root,
                            'absolute_pelvis_expected_world_m':expected,
                            'absolute_pelvis_affine_world_m':cand_pelvis,
                            'absolute_pelvis_affine_error_m':norm(minus(cand_pelvis,expected)),
                            'neutral_relative_pelvis_expected_world_m':neutral_relative,
                            'neutral_relative_candidate_root_m':neutral_root,
                            'neutral_relative_pelvis_affine_world_m':relative_affine,
                            'neutral_relative_pelvis_affine_error_m':norm(minus(relative_affine,neutral_relative)),
                            'historical43_root_m':hist_root,'historical43_pelvis_world_m':hist_pelvis})
    segments=[]
    for side in ('L','R'):
        for a,b in [('upper_arm','forearm'),('forearm','hand'),('thigh','shin'),('shin','foot')]:
            ta,tb=a+'.'+side,b+'.'+side
            sa,sb=relation[ta],relation[tb]
            sv=minus(position(sw[source_index[sb]]),position(sw[source_index[sa]]))
            tv=minus(position(tw[target_index[tb]]),position(tw[target_index[ta]]))
            segments.append({'target_segment':[ta,tb],'source_segment':[sa,sb],
                             'source_neutral_vector_m':sv,'target_neutral_vector_m':tv,
                             'source_length_m':norm(sv),'target_length_m':norm(tv),
                             'target_to_source_length_ratio':norm(tv)/norm(sv),
                             'identity_basis_direction_difference_degrees':angle(sv,tv),
                             'proper_candidate_direction_differences_degrees':[
                                 {'matrix':c['matrix'],'angle_degrees':angle(transform(c['matrix'],sv),tv)}
                                 for c in anchors['best_proper_candidates']]})
    # Independent derived controls, not another motion sample.
    conditioning=[]
    for side in ('Left','Right'):
        j=source_index[side+'ForeArm']; p=sp[j]; child=source_index[side+'Hand']
        a=normalized(minus(position(sw[j]),position(sw[p])))
        raw_b=minus(position(sw[child]),position(sw[j]));b=normalized(raw_b)
        sine=norm(cross(a,b)); normal=normalized(cross(a,b))
        trials=[]
        # Perturb only the same neutral source hand position along +/-worldY/Z.
        for eps in (1e-6,1e-5,1e-4):
            for axis_i in (1,2):
                for sign in (-1,1):
                    perturb=[0,0,0];perturb[axis_i]=sign*eps
                    pert=plus(raw_b,perturb);n=normalized(cross(a,normalized(pert)))
                    trials.append({'hand_perturbation_world_axis':'XYZ'[axis_i], 'hand_perturbation_m':sign*eps,
                                   'normal_change_degrees':angle(normal,n),
                                   'primary_ray_change_degrees':angle(raw_b,pert)})
        conditioning.append({'source_elbow':side+'ForeArm','incoming_outgoing_angle_degrees':angle(a,b),
                             'sine':sine,'inverse_sine_amplification':1/sine,'perturbations':trials})
    axis=normalized(minus(position(sw[source_index['LeftHand']]),position(sw[source_index['LeftForeArm']])))
    # Rodrigues 60-degree twist: primary ray fixed; independent off-axis marker moves.
    theta=math.pi/3;axis_cross=[[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]]
    twist=[[math.cos(theta)*float(i==j)+(1-math.cos(theta))*axis[i]*axis[j]+math.sin(theta)*axis_cross[i][j] for j in range(3)] for i in range(3)]
    marker=[0,.1,0]
    twist_control={'kind':'derived numerical control on source neutral LeftForeArm primary ray',
                   'twist_degrees':60,'primary_ray_unit_position_error':norm(minus(transform(twist,axis),axis)),
                   'off_axis_marker_local_m':marker,'off_axis_marker_displacement_m':norm(minus(transform(twist,marker),marker)),
                   'meaning':'Primary-axis alignment cannot identify twist; off-axis reference is required.'}
    summary={'scope':'Independent report-only numerical facts from the one fixed public44 90x30 sample; no product/playback/anatomical admission.',
             'input_sha256':input_hashes,'sample':{'frames':90,'joints':30,'fps':30,'raw_q_float_count':len(qa),'raw_root_float_count':len(ra),'all_finite':True,
                       'min_quaternion_norm':min(qnorm),'max_quaternion_norm':max(qnorm),'max_norm_error':max(abs(n-1) for n in qnorm),
                       'root_component_min':[min(r[i] for r in roots) for i in range(3)],'root_component_max':[max(r[i] for r in roots) for i in range(3)]},
             'target_identity':{k:target[k] for k in ('names','parents','translations','scales','joint_node_indices','external_ancestor_world_identity')},
             'signed_anchors':anchors,'observability':obs,'neutral_segments':segments,'elbow_conditioning':conditioning,
             'pelvis_assumptions':{'absolute_candidate':'P_world_pelvis=raw_source_root; root orientation=R_source_Hips * target_root_rest_R; T_target_root=P_world_pelvis−R_target_root*(S_target_root*t_pelvis_local).',
                                  'neutral_relative_candidate':'P_world_pelvis=target_neutral_pelvis + raw_root(frame)−raw_root(frame0); same rotated offset removal. Not inferred anatomical truth.',
                                  'historical43':'desired_global_R(j)=source_global_R(mapped_j)*transpose(source_rest_global_R(mapped_j))*target_rest_global_R(j); T_target_root=target_rest_local_root+raw_root−source_rest_local_root. Rest source rotations identity. Root/pelvis both map to Hips.',
                                  'root_space_admission':'Neither raw-root anatomical meaning nor choice of placement anchor is established by this numerical closure.'},
             'pelvis_all90_max_affine_error_m':max(r['absolute_pelvis_affine_error_m'] for r in pelvis_rows),
             'neutral_relative_pelvis_all90_max_affine_error_m':max(r['neutral_relative_pelvis_affine_error_m'] for r in pelvis_rows),
             'falsifications':{key:{'max_error_m':max(v),'min_error_m':min(v),'frames_above_1e_6':sum(x>1e-6 for x in v)} for key,v in negatives.items()},
             'q_negative_q_source_affine_max_error_m':qsignmax,
             'q_negative_q_target_affine_max_error_m':target_qsignmax,'twist_control':twist_control,
             'admission':{'numeric_closure':'PASS conditional hypotheses only','anatomical_semantics':'HOLD','target_playable':'HOLD',
                          'missing_references':['Independent source and target up/front/anatomical side reference','Independent per-limb twist or off-axis frames','Chosen source-root to target-pelvis placement policy','External pose/motion ground truth for semantic validation'],
                          'generated_wave_is_external_ground_truth':False}}
    require(summary['pelvis_all90_max_affine_error_m']<1e-12, 'independent numerical invariant at source line 339')
    require(summary['neutral_relative_pelvis_all90_max_affine_error_m']<1e-12, 'independent numerical invariant at source line 340')
    require(qsignmax<1e-12 and target_qsignmax<1e-12 and twist_control['primary_ray_unit_position_error']<1e-12 and twist_control['off_axis_marker_displacement_m']>.09, 'independent numerical invariant at source line 341')
    require(all(v['max_error_m']>1e-3 for v in summary['falsifications'].values()), 'independent numerical invariant at source line 342')
    return {'summary': summary, 'pelvis_all90': pelvis_rows}


def main():
    print(json.dumps(analyze(), sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
