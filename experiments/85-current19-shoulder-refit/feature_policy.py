"""Version4 source-feature directions and all-nearest-face inequalities.

Import is inert. Source incidence uses source IDs, never render IDs or positions.
Only relevant vertex fans are required to be manifold; open fans are allowed.
"""
import math
from pathlib import Path
import author as old

HERE=Path(__file__).resolve().parent
POLICY_PATH=HERE/'feature-policy-v4.json'
VERSION=4
CANDIDATE_ID='nvwa-current19-shoulder-feature-refit-v4'
LOGICAL_SAMPLE_COUNT=581
MARGIN=.001
RESIDUAL_FLOOR=.0009999
MAX_DELTA=.020
TIE_DISTANCE_SQUARED=1e-12
NORMAL_AGREEMENT=1e-9
SLOPE_EPSILON=1e-12
AREA_FLOOR=1e-12
need=old.need
sub,dot,cross,norm,scale,add=old.sub,old.dot,old.cross,old.norm,old.scale,old.add
interpolate=old.interpolate
closest_triangle=old.reference.closest_triangle

POLICY={
    'schema_version':1,'authoring_policy_version':VERSION,
    'kind':'nvwa85-current19-feature-policy-v4','candidate_id':CANDIDATE_ID,'candidate_count':1,
    'reference_policy_sha256':'864df1a9956712dda02942fdc3a5a099a8c1d789ab91776a648258d268cafc53',
    'support_sha256':old.SUPPORT_SHA,
    'source_direction':{
        'normal':'normalize oriented source-triangle area sum in frozen source order',
        'interpolation':'normalize source-ID keyed barycentric vertex-normal interpolation before feathering',
        'feature':'exact nonzero barycentric source IDs, exact projected point and exact source-keyed weights',
        'ties':'all nearest faces must identify the same feature; no fallback or averaging',
        'normal_agreement':NORMAL_AGREEMENT,
        'local_topology':'connected manifold oriented incident fan; open boundary allowed',
        'refusals':['invalid indices','nonfinite inputs','repeated source index','relevant degenerate face',
                    'disconnected fan','nonmanifold fan','inconsistent winding','zero normal',
                    'nonpositive applicable orientation','distinct nearest features']},
    'constraints':{'logical_sample_count':LOGICAL_SAMPLE_COUNT,
        'faces':'all nearest faces retain their own projected point and oriented geometric normal',
        'identity':['logical_sample0','body_triangle0'],'preserve_duplicate_logical_samples':True,
        'nearest_tie_distance_squared_m2':TIE_DISTANCE_SQUARED,'margin_m':MARGIN,
        'saved_text_residual_floor_m':RESIDUAL_FLOOR,'slope_epsilon':SLOPE_EPSILON,
        'amplitude':'one original positive lower endpoint of the complete feasible interval; no retry',
        'realized':'every retained face after saved-f32 and MHCLO text round trip'},
    'unchanged':{'position_sources':30,'support_radius_m':.070,'ring_weights':[1.,.75,.25],
        'max_displacement_m':MAX_DELTA,'samples_per_triangle':7,
        'topology_helpers_full_weights_material_body_mask_and_quality_thresholds':'original geometry policy exact'},
}


def validate_policy(policy):
    # JSON equality alone would admit True as1. Match primitive types as well.
    def exact(value,expected):
        if type(value) is not type(expected):return False
        if isinstance(expected,dict):
            return value.keys()==expected.keys() and all(exact(value[k],v) for k,v in expected.items())
        if isinstance(expected,list):
            return len(value)==len(expected) and all(exact(a,b) for a,b in zip(value,expected))
        return value==expected
    need(exact(policy,POLICY),'feature policy v4 semantics differ')
    return policy


def vector(value,label='vector'):
    need(isinstance(value,(tuple,list)) and len(value)==3 and
         all(type(v) in (int,float) and math.isfinite(v) for v in value), 'nonfinite/invalid '+label)
    return value


def normalized(value,label):
    vector(value,label);size=norm(value)
    need(math.isfinite(size) and size>0,'zero/nonfinite '+label)
    result=scale(value,1/size);vector(result,label)
    return result


class SourceNormals(dict):
    """Normal field plus immutable source topology facts for local validation."""
    pass


def source_normals(body,triangles):
    need(bool(triangles),'missing source incidence')
    field=SourceNormals();field.body=body;field.triangles=triangles
    field.incidence={};field.areas=[];field.face_normals=[]
    for ti,tri in enumerate(triangles):
        need(isinstance(tri,(list,tuple)) and len(tri)==3 and
             all(type(i) is int and 0<=i<len(body) for i in tri) and len(set(tri))==3,
             'invalid/repeated source topology index')
        for i in tri:vector(body[i],'source point')
        a,b,c=[body[i] for i in tri];area=cross(sub(b,a),sub(c,a));vector(area,'source area')
        size=norm(area);need(math.isfinite(size),'nonfinite source area')
        field.areas.append(size)
        field.face_normals.append(scale(area,1/size) if size>0 else (0.,0.,0.))
        for i in tri:
            field[i]=add(field.get(i,(0.,0.,0.)),area)
            field.incidence.setdefault(i,[]).append(ti)
    for i,value in field.items():
        size=norm(value);need(math.isfinite(size),'nonfinite accumulated source normal')
        field[i]=scale(value,1/size) if size>0 else (0.,0.,0.)
    field.validated_vertices=set()
    return field


def validate_fan(field,source_id):
    if source_id in field.validated_vertices:return
    need(source_id in field.incidence,'missing source incidence')
    normalized(field[source_id],'accumulated source normal')
    faces=field.incidence[source_id];edges={};adj={ti:set() for ti in faces}
    for ti in faces:
        need(field.areas[ti]>AREA_FLOOR,'relevant degenerate source face')
        tri=field.triangles[ti]
        for a,b in zip(tri,(tri[1],tri[2],tri[0])):
            if source_id in (a,b):edges.setdefault(tuple(sorted((a,b))),[]).append((ti,a,b))
    boundary=0
    for edge,rows in edges.items():
        need(len(rows)<=2,'nonmanifold local source fan')
        if len(rows)==1:boundary+=1
        else:
            first,second=rows
            need(first[1:]==second[1:][::-1],'inconsistent source winding')
            adj[first[0]].add(second[0]);adj[second[0]].add(first[0])
    need(boundary in (0,2),'nonmanifold local source boundary fan')
    seen=set();pending=[faces[0]]
    while pending:
        ti=pending.pop()
        if ti not in seen:seen.add(ti);pending.extend(adj[ti]-seen)
    need(len(seen)==len(faces),'disconnected local source fan')
    for ti in faces:
        need(dot(field[source_id],field.face_normals[ti])>0,
             'nonpositive applicable source face orientation')
    field.validated_vertices.add(source_id)


def nearest_faces(point,body,triangles,smooth,diagnostic=None):
    vector(point,'query point')
    need(isinstance(smooth,SourceNormals) and smooth.body is body and smooth.triangles is triangles,
         'source normal field/topology identity differs')
    nearest=math.inf;hits=[]
    for ti,tri in enumerate(triangles):
        q,bary=closest_triangle(point,*[body[i] for i in tri]);vector(q,'closest point')
        d2=dot(sub(point,q),sub(point,q))
        need(math.isfinite(d2) and d2>=0,'nonfinite closest distance')
        nearest=min(nearest,d2);hits.append((d2,ti,q,bary))
    selected=[]
    for d2,ti,q,bary in hits:
        if d2>nearest+TIE_DISTANCE_SQUARED:continue
        tri=triangles[ti]
        need(smooth.areas[ti]>AREA_FLOOR and bary is not None,'nearest plane degenerate')
        vector(bary,'body barycentric')
        need(all(0<=v<=1 for v in bary),'invalid body barycentric')
        active=sorted((sid,w) for sid,w in zip(tri,bary) if w!=0.)
        for sid,_ in active:validate_fan(smooth,sid)
        normal=smooth.face_normals[ti]
        interpolated=interpolate([smooth[i] for i in tri],bary)
        need(dot(normal,normalized(interpolated,'interpolated source normal'))>0,
             'nearest winding disagrees with independently smoothed body normal')
        selected.append({'body_triangle0':ti,'body_source_ids':list(tri),'point':list(q),
            'normal':list(normal),'body_barycentric':list(bary),'distance_squared_m2':d2,
            'source_feature':[sid for sid,_ in active],
            'source_weights':[[sid,w] for sid,w in active]})
    need(bool(selected),'nearest plane missing')
    selected.sort(key=lambda row:row['body_triangle0'])
    for row in selected:row['distance_ties']=len(selected)
    if diagnostic is not None:
        diagnostic.update(nearest_distance_squared_m2=nearest,eligible_distance_ties=len(selected),nearest_faces=selected)
    return selected


def feature_direction(point,body,triangles,smooth,diagnostic=None):
    faces=nearest_faces(point,body,triangles,smooth,diagnostic)
    first=faces[0];weights=first['source_weights']
    normal=normalized([sum(smooth[sid][k]*w for sid,w in weights) for k in range(3)],
                      'interpolated source normal')
    for face in faces:
        need(face['source_feature']==first['source_feature'] and face['point']==first['point'] and
             face['source_weights']==weights,'distinct nearest source features/point/weights')
        local=normalized(interpolate([smooth[i] for i in face['body_source_ids']],face['body_barycentric']),
                         'face interpolated source normal')
        need(norm(sub(local,normal))<=NORMAL_AGREEMENT,'equivalent face interpolation disagrees')
        need(dot(normal,face['normal'])>0,'nonpositive applicable face orientation')
    return {'normal':list(normal),'point':first['point'],'source_feature':first['source_feature'],
            'source_weights':weights,'nearest_face_ids':[r['body_triangle0'] for r in faces],
            'nearest_faces':faces}


SAMPLE_KEYS=('logical_sample0','triangle0','sample0','barycentric','sources')


def append_constraints(logical_samples,planes,triangle0,sample0,barycentric,sources,point,direction,
                       body,triangles,smooth,diagnostic=None):
    faces=nearest_faces(point,body,triangles,smooth,diagnostic)
    identity={'logical_sample0':len(logical_samples),'triangle0':triangle0,'sample0':sample0,
              'barycentric':list(barycentric),'sources':list(sources)}
    logical_samples.append({**identity,'nearest_face_ids':[face['body_triangle0'] for face in faces]})
    for plane in faces:
        d=dot(sub(point,plane['point']),plane['normal']);slope=dot(direction,plane['normal'])
        need(math.isfinite(d) and math.isfinite(slope),'nonfinite plane constraint')
        planes.append({**identity,'body_triangle0':plane['body_triangle0'],'d_m':d,'slope':slope,'plane':plane})


def validate_constraint_coverage(logical_samples,planes,*,expected_count=LOGICAL_SAMPLE_COUNT,expected_samples=None):
    need(type(expected_count) is int and expected_count>0 and len(logical_samples)==expected_count,
         'logical sample coverage differs')
    if expected_samples is not None:
        need(logical_samples==expected_samples,'independent nearest-face/sample coverage differs')
    wanted={};seen=set()
    for index,sample in enumerate(logical_samples):
        need(type(sample['logical_sample0']) is int and sample['logical_sample0']==index,
             'logical sample identity differs')
        need(type(sample['triangle0']) is int and sample['triangle0']>=0 and
             type(sample['sample0']) is int and 0<=sample['sample0']<7,'sample identity invalid')
        vector(sample['barycentric'],'sample barycentric')
        need(list(sample['barycentric'])==list(old.SAMPLES[sample['sample0']]),'logical sample barycentric differs')
        sources=sample['sources'];need(isinstance(sources,list) and len(sources)==3 and
            len(set(sources))==3 and all(type(i) is int and i>=0 for i in sources),'sample sources invalid')
        ids=sample['nearest_face_ids']
        need(isinstance(ids,list) and bool(ids) and all(type(i) is int and i>=0 for i in ids) and
             ids==sorted(set(ids)),'nearest face IDs invalid')
        for ti in ids:wanted[(index,ti)]=sample
    for plane in planes:
        need(all(type(plane[k]) is int for k in ('logical_sample0','body_triangle0','triangle0','sample0')),
             'plane integer identity invalid')
        need(type(plane['plane']['body_triangle0']) is int,'nested plane integer identity invalid')
        key=(plane['logical_sample0'],plane['body_triangle0'])
        need(key in wanted and key not in seen,'extra/duplicate face constraint')
        sample=wanted[key]
        need(all(plane[k]==sample[k] for k in SAMPLE_KEYS),'plane logical sample metadata differs')
        need(type(plane['body_triangle0']) is int and plane['plane']['body_triangle0']==key[1],
             'plane body face identity differs')
        vector(plane['plane']['point'],'plane point');vector(plane['plane']['normal'],'plane normal')
        need(abs(norm(plane['plane']['normal'])-1.)<=NORMAL_AGREEMENT,'invalid plane unit normal')
        need(type(plane['d_m']) in (int,float) and math.isfinite(plane['d_m']) and
             type(plane['slope']) in (int,float) and math.isfinite(plane['slope']),'nonfinite plane constraint')
        seen.add(key)
    need(seen==set(wanted),'omitted nearest face constraint')
    return len(planes)


def amplitude_interval(logical_samples,planes,directions,*,expected_count=LOGICAL_SAMPLE_COUNT,expected_samples=None):
    validate_constraint_coverage(logical_samples,planes,expected_count=expected_count,expected_samples=expected_samples)
    lower=0.;upper=math.inf
    for row in planes:
        d,a=row['d_m'],row['slope']
        if a>SLOPE_EPSILON:lower=max(lower,(MARGIN-d)/a)
        elif a< -SLOPE_EPSILON:upper=min(upper,(MARGIN-d)/a)
        else:need(d>=MARGIN,'infeasible fixed/zero-slope sample')
    for direction in directions.values():
        vector(direction,'displacement direction');size=norm(direction)
        need(math.isfinite(size),'nonfinite displacement direction')
        if size:upper=min(upper,MAX_DELTA/size)
    need(math.isfinite(lower) and not math.isnan(upper) and 0<lower<=upper,
         'empty/nonpositive amplitude interval')
    need(all(math.isfinite(row['d_m']+lower*row['slope']) and
             row['d_m']+lower*row['slope']>=MARGIN for row in planes),'ideal plane residual failed')
    return lower,upper


def validate_realized_constraints(logical_samples,planes,realized,*,expected_count=LOGICAL_SAMPLE_COUNT,
                                  expected_samples=None):
    validate_constraint_coverage(logical_samples,planes,expected_count=expected_count,expected_samples=expected_samples)
    for row in planes:
        values=[vector(realized[i],'realized source point') for i in row['sources']]
        point=interpolate(values,row['barycentric'])
        side=dot(sub(point,row['plane']['point']),row['plane']['normal'])
        row['realized_side_m']=side
        need(math.isfinite(side) and side>=RESIDUAL_FLOOR,
             'saved-text realized face below frozen0.9999mm floor')
    return len(planes)
