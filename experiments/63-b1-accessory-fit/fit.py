#!/usr/bin/env python3
"""Bounded source-grounded accessory fitting/LBS on six actual retained r4 frames."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREP = REPO/'experiments/62-b1-appearance-preview/assets'
BASE = REPO/'assets/characters/mpfb-b1-v1'
PREP_HASH = '620099486462ed31f5ca0a7e06b351d8fb8a6a59120f85b604d5ea94c3808a59'
CAGE_SIZE = 19158
CLIPS = ('b1_arm_rehearsal_v1','b1_knee_flex_v1')
ACCESSORIES = {'eyes': ('eyes/low-poly/low-poly', 96, 'eyes/materials/brown_eye.png'), 'hair': ('hair/short04/short04', 865, 'hair/short04/short04_diffuse.png')}


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def encode(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def value_sha(v):return hashlib.sha256(encode(v)).hexdigest()
def finite(values):return all(math.isfinite(v) for v in values)


def source_cage(part, count=CAGE_SIZE):
    require(len(part['source_ids'])==len(part['rest_positions']), 'cage render/source coverage')
    result={};duplicates=0
    for sid,p in zip(part['source_ids'],part['rest_positions']):
        require(type(sid) is int and 0<=sid<count and len(p)==3 and finite(p),'cage ID/domain/nonfinite')
        if sid in result:
            duplicates+=1
            require(result[sid]==p,'conflicting UV-split source rest positions')
        result[sid]=p
    require(set(result)==set(range(count)),'missing fitted source cage IDs')
    return result,duplicates


def parse_mapping(path, unit, expected=None, observe_existing_mask=False):
    require(unit in (0.1,1.0),'undeclared units')
    rows=[];rules={};section='header';deleted=[];obj=None
    for raw in path.read_text().splitlines():
        f=raw.split()
        if not f or f[0].startswith('#'):continue
        if f[:2]==['verts','0']:section='verts';continue
        if f[0]=='delete_verts':section='delete';continue
        if section=='header':
            if f[0]=='obj_file':obj=f[1]
            if f[0] in ('x_scale','y_scale','z_scale'):
                axis=('x_scale','y_scale','z_scale').index(f[0])
                require(len(f)==4 and axis not in rules,'invalid/duplicate scale axis')
                a,b=int(f[1]),int(f[2]);ref=float(f[3])
                require(0<=a<CAGE_SIZE and 0<=b<CAGE_SIZE and math.isfinite(ref) and abs(ref)>1e-12,'invalid scale/helper reference')
                rules[axis]={'helpers':[a,b],'original_reference':ref,'reference_m':ref*unit}
        elif section=='verts':
            if f[0]=='material':continue
            require(len(f) in (1,9),'unsupported mapping row')
            ids=list(map(int,f[:1] if len(f)==1 else f[:3]))
            require(all(0<=i<CAGE_SIZE for i in ids),'MHCLO helper ID out of cage domain')
            coefficients=[1.] if len(f)==1 else list(map(float,f[3:6]))
            offset=[0.,0.,0.] if len(f)==1 else list(map(float,f[6:9]))
            require(finite(coefficients+offset) and abs(sum(coefficients))>2**-23,'illegal/nonfinite/zero-sum helper coefficients')
            total=sum(coefficients)
            rows.append({'helpers':ids,'raw_coefficients':coefficients,'coefficients':[w/total for w in coefficients],'offset_original':offset,'offset_m':[v*unit for v in offset]})
        else:deleted.append(raw)
    require(set(rules)=={0,1,2} and obj and rows,'incomplete mapping')
    if expected is not None:require(len(rows)==expected,'mapping/source vertex count')
    require(not deleted or observe_existing_mask,'new accessory delete_verts policy unsupported in this bounded experiment')
    for line in deleted:
        require(all(t == '-' or (t.isdigit() and 0 <= int(t) < CAGE_SIZE) for t in line.split()),'invalid existing mask source ID')
    return {'rows':rows,'rules':rules,'unit_to_m':unit,'obj_file':obj,'existing_delete_mask_lines_record_only':deleted}


def fit_rest(mapping,cage):
    scales={axis:(cage[r['helpers'][1]][axis]-cage[r['helpers'][0]][axis])/r['reference_m'] for axis,r in mapping['rules'].items()}
    require(finite(scales.values()),'unreproducible nonfinite scales')
    positions=[]
    for row in mapping['rows']:
        require(all(i in cage for i in row['helpers']),'missing fitting helper')
        p=[sum(cage[h][axis]*w for h,w in zip(row['helpers'],row['coefficients']))+scales[axis]*row['offset_m'][axis] for axis in range(3)]
        require(finite(p),'nonfinite fitted position');positions.append(p)
    return positions,scales


def original_weights(path,names):
    data=json.loads(path.read_bytes())['weights']
    require(set(data)==set(names) and len(names)==len(set(names))==53,'original stable53 bone names')
    weights={name:{} for name in names}
    for name,entries in data.items():
        for sid,w in entries:
            require(type(sid) is int and 0<=sid<CAGE_SIZE and math.isfinite(w) and w>=0 and sid not in weights[name],'illegal original source weights/IDs')
            weights[name][sid]=w
    return weights


def transfer(mapping,weights,names):
    rows=[];nonpositive=0;negative=0
    for row in mapping['rows']:
        raw=[]
        for joint,name in enumerate(names):
            aggregate=sum(weights[name].get(h,0.)*c for h,c in zip(row['helpers'],row['coefficients']) if weights[name].get(h,0.)>0)
            require(math.isfinite(aggregate),'nonfinite final weight aggregate')
            negative+=aggregate<0;nonpositive+=aggregate<=0
            if aggregate>0:raw.append([joint,aggregate])
        total=sum(w for _,w in raw)
        require(total>0 and math.isfinite(total),'no finite final-positive influences')
        normalized=[[j,w/total] for j,w in raw]
        require(all(w>0 and math.isfinite(w) for _,w in normalized) and abs(sum(w for _,w in normalized)-1)<1e-12,'invalid normalized positive row')
        rows.append(normalized)
    return rows,{'negative_final_aggregates_omitted':negative,'nonpositive_final_aggregates_omitted':nonpositive}


def point(matrix,p):
    require(len(matrix)==16 and finite(matrix),'invalid matrix')
    return [sum(matrix[col*4+axis]*p[col] for col in range(3))+matrix[12+axis] for axis in range(3)]


def lbs(rest,influences,bones):
    require(len(rest)==len(influences) and len(bones)==53,'LBS coverage')
    result=[]
    for p,row in zip(rest,influences):
        require(row and len({j for j,_ in row})==len(row) and all(type(j) is int and 0<=j<53 and math.isfinite(w) and w>0 for j,w in row) and abs(sum(w for _,w in row)-1)<1e-6,'invalid LBS influences')
        q=[0.,0.,0.]
        for j,w in row:
            v=point(bones[j]['skin'],p)
            for axis in range(3):q[axis]+=w*v[axis]
        require(finite(q),'nonfinite LBS result');result.append(q)
    return result


def obj_mesh(path,expected):
    vertices=[];uv=[];faces=[]
    for raw in path.read_text().splitlines():
        f=raw.split()
        if not f:continue
        if f[0]=='v':
            p=list(map(float,f[1:]));require(len(p)==3 and finite(p),'OBJ position');vertices.append([v*.1 for v in p])
        elif f[0]=='vt':
            p=list(map(float,f[1:]));require(len(p)==2 and finite(p),'OBJ UV');uv.append(p)
        elif f[0]=='f':
            row=[]
            for token in f[1:]:
                ids=token.split('/');require(len(ids)>=2 and ids[0] and ids[1],'OBJ UV binding absent')
                v,t=int(ids[0])-1,int(ids[1])-1
                require(0<=v<len(vertices) and 0<=t<len(uv),'OBJ vertex/UV ID out of domain')
                row.append([v,t])
            require(len(row)>=3,'OBJ face coverage');faces.append(row)
    require(len(vertices)==expected and set(v for f in faces for v,t in f)==set(range(expected)),'OBJ missing source vertex/face coverage')
    render=list(dict.fromkeys((v,t) for f in faces for v,t in f))
    return {'original_positions_m':vertices,'uv_original':uv,'uv_bevy_v_flipped':[[u,1-v] for u,v in uv],'source_faces':faces,'render_source_uv_pairs':render,'triangles_fan':sum(len(f)-2 for f in faces)}


def bounds(points):return {'min':[min(p[a] for p in points) for a in range(3)],'max':[max(p[a] for p in points) for a in range(3)]}
def max_delta(a,b):return max(abs(x-y) for p,q in zip(a,b) for x,y in zip(p,q))
def normalized(row):
    total=sum(w for _,w in row);require(total>0,'invalid baseline influence sum')
    return [[j,w/total] for j,w in row]


def garment_control(snapshot,cage,names,weights):
    part=next(p for p in snapshot['parts'] if p['name']=='garment')
    mapping=parse_mapping(BASE/'garment/female_sportsuit01.mhclo',1.,1797,observe_existing_mask=True)
    rest,scales=fit_rest(mapping,cage)
    rows,_=transfer(mapping,weights,names)
    actual={};actual_rows={}
    for sid,p,row in zip(part['source_ids'],part['rest_positions'],part['full_joint_influences']):
        require(0<=sid<1797,'garment source domain')
        if sid in actual:require(actual[sid]==p and actual_rows[sid]==normalized(row),'garment duplicate mismatch')
        actual[sid]=p;actual_rows[sid]=normalized(row)
    require(set(actual)==set(range(1797)),'garment source coverage')
    rest_error=max_delta(rest,[actual[i] for i in range(1797)])
    weight_error=max(sum(abs(dict(rows[i]).get(j,0)-dict(actual_rows[i]).get(j,0)) for j in set(dict(rows[i]))|set(dict(actual_rows[i]))) for i in range(1797))
    posed=lbs(rest,rows,snapshot['bones'])
    upload_error=max_delta([posed[i] for i in part['source_ids']],part['positions'])
    require(rest_error<=1e-5 and weight_error<=1e-5 and upload_error<=1e-5,'admitted garment scaled-offset/weight/LBS control failed')
    return {'rest_max_component_error_m':rest_error,'normalized_weight_max_L1':weight_error,'actual_upload_max_component_error_m':upload_error,'existing_guard':1e-5,'passed':True,'scales':scales}


def run(captures,output):
    require(not output.exists(),'output must be new');output.mkdir(parents=True)
    manifest=PREP/'asset-manifest.json';require(sha(manifest)==PREP_HASH,'experiment62 decoded manifest identity changed')
    prep=json.loads(manifest.read_bytes())
    for name,identity in prep['outputs'].items():
        path=PREP/name
        require(path.stat().st_size==identity['size'] and sha(path)==identity['sha256'],'prepared source bytes mismatch: '+name)
    assets={name:{'mapping':parse_mapping(PREP/(stem+'.mhclo'),.1,count),'obj':obj_mesh(PREP/(stem+'.obj'),count),'texture':texture} for name,(stem,count,texture) in ACCESSORIES.items()}
    require(sha(BASE/'manifest.json')=='abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18' and sha(BASE/'garment/female_sportsuit01.mhclo')=='700e8cb224a2c27a30220efa2ed7077e6a6901f5fcd74a1ee610f3e0370776e7','admitted source manifest/garment identity')
    require(sha(BASE/'weights.game_engine.json')=='9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473','admitted weight identity')
    records=[];fit_by_torso={};weight_rows=None;source_inputs={};meshes=output/'meshes';meshes.mkdir()
    for tag,torso in [('tm1',-1.),('tp0',0.),('tp1',1.)]:
        for clip in CLIPS:
            filename=f'resume17_r4_{tag}_{clip}_2.json';path=captures/filename
            record=json.loads(path.read_bytes());snapshot=record['snapshot'];req=record['request']
            require(record['kind']=='studio' and req['action']=='sample' and req['clip_id']==clip and req['torso_length']==torso and req['jaw_drop']==0 and req['seconds']==2,'actual capture request')
            require(snapshot['asset_id']=='mpfb-hm08-game-engine-female-sportsuit01-v1' and snapshot['profile_id']=='nvwa-mpfb-b1-motion-v1' and snapshot['backend']['schema_version']==2 and snapshot['parameters']=={'torso_length':torso,'jaw_drop':0.} and snapshot['sample']['clip_id']==clip and snapshot['sample']['source_seconds']==snapshot['sample']['position_seconds']==2.,'actual capture sample identity')
            require(len(snapshot['bones'])==53 and [p['name'] for p in snapshot['parts']]==['body','garment'],'actual rig/part coverage')
            body=snapshot['parts'][0];garment=snapshot['parts'][1]
            require(body['display_transform']==garment['display_transform'] and body['model_to_world']==garment['model_to_world'],'ambiguous body/garment placement')
            cage,duplicates=source_cage(body)
            for bone in snapshot['bones']:
                require(len(bone['skin'])==16 and finite(bone['skin']),'all53 actual skin matrices must be finite')
            names=[b['name'] for b in snapshot['bones']];weights=original_weights(BASE/'weights.game_engine.json',names)
            control=garment_control(snapshot,cage,names,weights)
            if torso in fit_by_torso:require(cage==fit_by_torso[torso],'fitted rest changed across poses')
            else:fit_by_torso[torso]=cage
            source_inputs[filename]={'sha256':sha(path),'bytes':path.stat().st_size,'request':req,'revision':snapshot['revision'],'generation':snapshot['generation'],'sample':snapshot['sample']}
            frame={'capture':filename,'torso':torso,'clip':clip,'source_seconds':2.,'cage_source_count':len(cage),'cage_domain':[0,CAGE_SIZE-1],'render_vertices':len(body['source_ids']),'UV_split_duplicate_rest_positions_exact':True,'duplicate_render_vertices':duplicates,'garment_reproduction_control':control,'model_to_world_record_only':body['model_to_world'],'display_transform_applied_once':body['display_transform'],'accessories':{}}
            for name,asset in assets.items():
                mapping=asset['mapping'];rest,scales=fit_rest(mapping,cage);rows,aggregate_stats=transfer(mapping,weights,names)
                posed=lbs(rest,rows,snapshot['bones'])
                rest_world=[point(body['display_transform'],p) for p in rest];posed_world=[point(body['display_transform'],p) for p in posed]
                nonhead=[i for i,row in enumerate(rows) if sum(w for j,w in row if names[j]!='head')>.01]
                position_data={'rest_model_m':rest,'posed_model_m':posed,'rest_stage_m':rest_world,'posed_stage_m':posed_world,'full_normalized_positive_influences':rows,'bone_names':names,'obj':asset['obj'],'source_mapping':mapping,'placement':body['display_transform'],'model_to_world_record_only':body['model_to_world'],'scope':'offline f64 fit/LBS; source/render UV mapping preserved; no runtime mesh/normal/tangent parity or quality claim'}
                mesh_path=meshes/f'{tag}_{clip}_{name}.json.gz'
                with mesh_path.open('xb') as f:f.write(gzip.compress(encode(position_data),mtime=0))
                rawnegative=sum(c<0 for row in mapping['rows'] for c in row['raw_coefficients'])
                info={'source_vertices':len(rest),'original_obj_uv_count':len(asset['obj']['uv_original']),'source_faces':len(asset['obj']['source_faces']),'fan_triangles_for_offline_only':asset['obj']['triangles_fan'],'unique_source_UV_pairs':len(asset['obj']['render_source_uv_pairs']),'signed_source_coefficients_retained':rawnegative,'axis_scales':scales,'offset_unit_to_m':.1,'rest_model_bounds_m':bounds(rest),'posed_model_bounds_m':bounds(posed),'rest_stage_bounds_m':bounds(rest_world),'posed_stage_bounds_m':bounds(posed_world),'max_posed_from_rest_component_m':max_delta(posed,rest),'rest_positions_sha256':value_sha(rest),'posed_positions_sha256':value_sha(posed),'normalized_influences_sha256':value_sha(rows),'influence_count_min':min(map(len,rows)),'influence_count_max':max(map(len,rows)),'vertices_over4_influences':sum(len(row)>4 for row in rows),'vertices_nonhead_over1percent':len(nonhead),'nonhead_source_ids':nonhead,'normalized_sum_max_error':max(abs(sum(w for _,w in row)-1) for row in rows),'aggregate_policy':aggregate_stats,'alpha_metadata':prep['png'][asset['texture']],'mesh_sidecar':str(mesh_path.relative_to(output)),'mesh_sha256':sha(mesh_path),'mesh_bytes':mesh_path.stat().st_size}
                if name=='eyes':require(info['vertices_nonhead_over1percent']==0 and all(len(row)==1 and names[row[0][0]]=='head' and row[0][1]==1 for row in rows),'eye head-only hypothesis did not reproduce original source weights')
                frame['accessories'][name]=info
            records.append(frame)
            print(json.dumps({'completed':len(records),'torso':torso,'clip':clip,'garment_control':control}),flush=True)
    source_paths=[BASE/'manifest.json',BASE/'weights.game_engine.json',BASE/'garment/female_sportsuit01.mhclo',REPO/'vendor/humentity/src/assets.rs',REPO/'vendor/humentity/src/loaders/mhclo.rs',REPO/'vendor/bevy_obj/src/util.rs',REPO/'crates/nvwa-b1-adapter/src/lib.rs',manifest,HERE/'fit.py',HERE/'test_controls.py',HERE/'CONTRACT.md']+[PREP/(stem+suffix) for stem,_,_ in ACCESSORIES.values() for suffix in ['.obj','.mhclo']]
    summary={'passed':len(records)==6,'scope':'Actual offline fitted accessories + full-positive LBS from six actual current-r4 cages/bone frames; not independent MPFB oracle, runtime upload or rendered/quality acceptance.','source_hashes':{str(p.relative_to(REPO)):sha(p) for p in source_paths},'actual_capture_inputs':source_inputs,'frames':records,'unit_policy':'Original accessory OBJ, offset and reference lengths ×0.1 to model metres; no axis swap. Ordered signed helper-axis differences. Admitted garment conversion1 control.','transform_policy':'Actual body display_transform exactly once after actual-bone model-local skin. model_to_world recorded only, never multiplied again.','UV_limit':'Snapshots omit UV coordinates. Exact duplicated-source REST position coverage checked; accessory original OBJ face-corner UV mapping retained, V-flip recorded separately once per bevy_obj. No runtime UV/tangent/triangulation parity claimed.','alpha_limit':'Reused actual decoded experiment62 manifest after exact current source image/manifest identity; no decoder rerun or mask/blend/render policy.','not_run':['independent MPFB reference','runtime accessory fitting/upload','native/Web render','eye/eyelid contact/gaze','hair physics','collision/quality acceptance','jaw variants']}
    with (output/'summary.json').open('x') as f:f.write(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--captures',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:run(args.captures,args.output)
    except (ValueError,KeyError,IndexError,OSError) as error:
        if args.output.exists():
            with (args.output/'FAILED.json').open('x') as f:f.write(json.dumps({'passed':False,'gap':str(error),'scope':'Stopped; no formula/threshold guessed'})+'\n')
        raise


if __name__=='__main__':main()
