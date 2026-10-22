"""Independent current-cohort checks; reuse math, never old cohort admission."""
import math
import json
import sys
from pathlib import Path
import current19 as c

sys.path.insert(0,str(c.ROOT/'experiments/84-shoulder-rest-refit/evaluation'))
import evaluate_rest as e

TOPOLOGY_SHA='cd886797a4a221934dc8dfbda73fc9194edbf9370ea4d4e82f746ace90648215'


def source_bone_order(rig):
    """Independent sorted-child preorder of the authenticated source hierarchy."""
    order=[];visiting=set()
    def walk(name):
        c.need(name not in visiting,'source rig cycle')
        visiting.add(name);order.append(name)
        for child in sorted(n for n,row in rig.items() if row['parent']==name):walk(child)
    roots=sorted(n for n,row in rig.items() if not row['parent'])
    c.need(len(roots)==1,'source rig must have one root')
    walk(roots[0]);c.need(len(order)==len(rig),'source rig disconnected/cyclic')
    return order


def source_triangles(faces,deleted=None):
    result=[]
    for face in faces:
        ids=face['source_ids']
        if deleted is not None and (any(i>=13380 for i in ids) or all(i in deleted for i in ids)):
            continue
        result.extend([ids[0],ids[j],ids[j+1]] for j in range(1,len(ids)-1))
    return result


def topology_order(part,reference):
    for field in ('source_ids','indices'):
        expected=reference[part['name']][field]
        raw=json.dumps(part[field],separators=(',',':'),allow_nan=False).encode()
        c.need(len(part[field])==expected['length'] and c.digest(raw)==expected['sha256'],
               'exact source integer topology order differs: '+part['name']+'/'+field)


def source_scale_ratios(axes,cage):
    """Source.axes maps integer XYZ axes to (low helper, high helper, reference)."""
    ratios=[]
    for axis in range(3):
        lo,hi,reference=axes[axis]
        ratios.append((cage[hi][axis]-cage[lo][axis])/reference)
    return ratios


class Baseline:
    def __init__(self):
        self.source=e.corpus.diagnose.Source(c.ROOT/'assets/characters/mpfb-b1-v1')
        self.checker=e.corpus.Checker(c.ROOT/'assets',surfaces=False)
        self.mapping=e.parse_mapping((e.SOURCE/'garment/female_sportsuit01.mhclo').read_bytes())
        self.body_faces=e.kernels.read_obj(e.SOURCE/'base.obj')
        self.cloth_faces=e.kernels.read_obj(e.SOURCE/'garment/female_sportsuit01.obj')
        self.deleted=e.kernels.deleted_ids(e.SOURCE/'garment/female_sportsuit01.mhclo')
        self.bone_order=source_bone_order(self.checker.rig)
        raw=(c.HERE/'topology-reference.json').read_bytes()
        c.need(c.digest(raw)==TOPOLOGY_SHA,'original integer topology reference changed')
        self.topology_reference=c.strict_load(raw)['parts']
        self.rests={}
        self.topology={}
        # Independent source reconstruction is valid for v2's zero extra parameters
        # only after proving the actual shared source bytes, not by profile rewriting.
        v2=c.ROOT/'assets/characters/mpfb-b1-v2'
        manifest=c.strict_load((v2/'manifest.json').read_bytes())
        for row in manifest['files']:
            path=c.safe_path(v2,row['path'])
            c.need(path.stat().st_size==row['bytes'] and c.digest(path.read_bytes())==row['sha256'],
                   'v2 admitted source bytes differ: '+row['path'])
        for name in ('base.obj','body.mhclo','garment/female_sportsuit01.mhclo',
                     'garment/female_sportsuit01.obj','rig.game_engine.json','weights.game_engine.json',
                     'targets/torso-scale-vert-incr.target','targets/torso-scale-vert-decr.target'):
            c.need((v2/name).read_bytes()==(e.SOURCE/name).read_bytes(),
                   'v1/v2 independent common source differs: '+name)

    def __call__(self,record):
        case=c.validate_record(record,record['run_id'])
        snapshot=record['snapshot'];bones=snapshot['bones'];parts={p['name']:p for p in snapshot['parts']}
        names=[b['name'] for b in bones]
        c.need(set(names)==set(self.checker.rig), 'source full53 bone coverage differs')
        c.need(names==self.bone_order, 'source full53 order changed')
        c.need({b['name']:b['parent'] for b in bones}==
               {name:row['parent'] or None for name,row in self.checker.rig.items()},
               'source full53 hierarchy differs')
        skins,fk,heads,bind=e.corpus.check_bones(bones,snapshot['sample']['clip_id'],
                                              snapshot['sample']['source_seconds'])
        reconstructed,scales=e.reconstruct_source(self.mapping,snapshot['parameters'])
        checks={};rest_identity={'bones':[{key:b[key] for key in (
            'name','parent','rest','inverse_bind','canonical_rest','frame_gauge','local_rest')}
            for b in bones],'parts':[]}
        for name,count in (('body',19158),('garment',1797)):
            part=parts[name];ids=part['source_ids']
            c.need(isinstance(ids,list) and all(type(i) is int and 0<=i<count for i in ids) and
                   set(ids)==set(range(count)), 'full source ID coverage differs: '+name)
            for field,width in (('positions',3),('rest_positions',3),('normals',3),
                                ('rest_normals',3),('tangents',4)):
                rows=part[field]
                c.need(len(rows)==len(ids) and all(isinstance(v,list) and len(v)==width and
                       all(c.finite(x) for x in v) for v in rows), 'invalid finite '+name+'/'+field)
            for field in ('model_to_world','display_transform'):
                c.need(len(part[field])==16 and all(c.finite(v) for v in part[field]),
                       'invalid placement matrix: '+name+'/'+field)
            indices=part['indices']
            c.need(indices and len(indices)%3==0 and all(type(i) is int and 0<=i<len(ids) for i in indices),
                   'invalid topology indices: '+name)
            e.kernels.bind_source(part,self.body_faces if name=='body' else self.cloth_faces,
                                  self.deleted if name=='body' else None)
            actual_triangles=[[ids[i] for i in indices[k:k+3]] for k in range(0,len(indices),3)]
            c.need(actual_triangles==source_triangles(
                   self.body_faces if name=='body' else self.cloth_faces,
                   self.deleted if name=='body' else None), 'exact source face/fan triangle order differs')
            topology_order(part,self.topology_reference)
            topology={'source_ids':ids,'indices':indices}
            if name not in self.topology:self.topology[name]=topology
            c.need(topology==self.topology[name], 'exact uploaded topology changed across cases: '+name)
            duplicates={}
            for i,sid in enumerate(ids):
                row={key:part[key][i] for key in ('positions','rest_positions','full_joint_influences')}
                c.need(sid not in duplicates or duplicates[sid]==row, 'exact render duplicates differ')
                duplicates[sid]=row
            c.need(all([j for j,w in row]==sorted(j for j,w in row)
                       for row in part['full_joint_influences']),
                   'original full-positive joint row order differs')
            expected=[reconstructed[name][sid] for sid in ids]
            checks[name]=e.check_baseline_part(part,expected,bones,self.checker,names,skins,case+'/'+name)
            rest_identity['parts'].append({key:part[key] for key in (
                'name','source_ids','indices','rest_positions','rest_normals','full_joint_influences',
                'model_to_world','display_transform')})
        # Keep the older independent binary64 signed-helper source fit ceiling too.
        cage=e.source_rows(parts['body'],'rest_positions')
        d=e.corpus.diagnose
        ratios=source_scale_ratios(self.source.axes,cage)
        fitted=[d.fit_row(row,cage,ratios) for row in self.source.mapping]
        garment=parts['garment']
        f64rest=max(abs(a-b) for sid,row in zip(garment['source_ids'],garment['rest_positions'])
                    for a,b in zip(fitted[sid],row))
        c.need(f64rest<=d.REST_EPS==1e-6,'independent binary64 source/rest exceeds original1e-6')
        shape=(snapshot['profile_id'],snapshot['parameters']['torso_length'])
        if shape not in self.rests:self.rests[shape]=rest_identity
        c.need(self.rests[shape]==rest_identity, 'exact fitted rest/weight/placement changed across poses')
        c.need(max(abs(a-b) for a,b in zip(parts['body']['display_transform'],
                                         parts['garment']['display_transform']))<=1e-6,
               'body/garment placement differs')
        return {'case':case,'parts':checks,'independent_binary64_source_rest_error_m':f64rest,
                'independent_FK':{'max_matrix_error':fk,'max_head_error_m':heads,'max_bind_error':bind},
                'scale_f32':scales,'geometry':'PASS_CURRENT_BASELINE_ONLY',
                'GPU_pixels_shading':'NOT-RUN'}
