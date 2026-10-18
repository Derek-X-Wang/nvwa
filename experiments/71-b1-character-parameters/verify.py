#!/usr/bin/env python3
"""Complete69-held acceptance per endpoint. Raw oracle is independent Python."""
import argparse,hashlib,json
from pathlib import Path
from oracle import Oracle,require,vector,rows,full_positive_lbs,finite
from prepare_works import CASES_SHA
from hash_encoding import mesh_array_sha256
EXP=Path(__file__).resolve().parent
PART_COUNTS={'body':(22077,68676),'garment':(1986,10308)}

def strict_json(text):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'duplicate JSON key '+key);out[key]=value
        return out
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON '+x)))

def names(items,key,expected,label):
    require(isinstance(items,list),label+' missing list');ids=[p[key] for p in items]
    require(len(ids)==len(set(ids)) and set(ids)==set(expected),label+' missing/duplicate/unexpected identities');return dict(zip(ids,items))

def complete_case_ids(ids,cases):
    require(len(ids)==69 and len(set(ids))==69 and set(ids)=={c['id'] for c in cases['held_cases']},'missing/duplicate/unknown held cases; complete69 required')

def current_pair(envelope):
    r,f=envelope['report'],envelope['frame'];require(r['phase']=='ready' and r['acknowledged'] is True and r['request_succeeded'] is True and r['current'] is True,'not acknowledged/current ready evidence')
    require(r['request_id']==f['request_id'] and bool(f['request_id']),'report/frame request mismatch')
    require(r['endpoint']==f['endpoint'] and f['endpoint'] in ('native','web'),'endpoint mismatch')
    require(r['captured_identity']==f['identity'],'current identity mismatch')
    for key in ('work_sha256','work_json','appearance'):require(r[key]==f[key],'report/frame mismatch '+key)
    require(hashlib.sha256(f['work_json'].encode()).hexdigest()==f['work_sha256'],'serialized Work hash mismatch')
    identity=f['identity']
    require(identity['work_sha256']==f['work_sha256'],'actual identity/saved Work hash mismatch')
    require(identity['runtime_ready'] is True and identity['appearance_ready'] is True,'runtime/appearance not currently ready')
    for key in ('preview_sha256','pending_open_sha256','open_error','runtime_error','runtime_appearance_error','appearance_error','stage_error','playback_error','seek_request'):require(identity[key] is None,'unverified current state '+key)
    return r,f

def validate(envelope,case,planned,oracle,recipe_parameters):
    r,f=current_pair(envelope)
    identity=f['identity']
    require(r['evidence_kind']==f['evidence_kind']=='held-stable-two-frames' and r['stable_observations']==f['stable_observations']==2,'not held stable two-frame evidence')
    work=strict_json(f['work_json']);expected=strict_json(planned['requests'][0]['work_json']);require(work==expected,'current saved Work differs from exact predeclared held Work');require(work['character']['parameters']==recipe_parameters,'frozen recipe/case label mismatch')
    selection=work['character']['appearance'];require(selection['asset_set_id']=='mpfb-b1-cc0-appearance-v2' and all(selection[k]==v for k,v in case['appearance'].items()),'frozen appearance/case label mismatch')
    base=f['full_base'];appearance=f['appearance'];summary=r['base_summary']
    require(base['backend']==work['profile']['backend'] and base['asset_id']==work['profile']['backend']['asset_id'] and base['profile_id']==work['profile']['id'],'base/profile identity mismatch')
    require(base['parameters']==work['character']['parameters'],'published recipe mismatch')
    for key in ('backend','asset_id','profile_id','generation','revision','parameters','sample'):require(summary[key]==base[key],'compact/full current mismatch '+key)
    require(base['revision']==work['revision'] and appearance['generation']==base['generation'] and appearance['revision']==base['revision'] and identity['generation']==base['generation'] and identity['revision']==base['revision'],'stale generation/revision')
    require(appearance['ready'] is True and appearance['requested']==work['character']['appearance'] and appearance['applied']==work['character']['appearance'] and appearance['error'] is None,'unapplied/current appearance mismatch')
    sample=base['sample'];require(appearance['serial']==sample['serial'] and appearance['base_asset_id']==base['asset_id'],'actual appearance/base sample or asset mismatch');require(finite(sample['source_seconds']) and finite(sample['position_seconds']) and finite(identity['seconds']),'malformed actual sample time');require(sample['clip_id']==case['clip_id'] and sample['source_seconds']==case['source_seconds'] and sample['position_seconds']==case['source_seconds'] and sample['playing'] is False,'held actual clip/source/transport mismatch')
    require(identity['clip_id']==sample['clip_id'] and identity['timeline_id']==sample['timeline_id'] and identity['seconds']==sample['position_seconds'] and identity['playing']==sample['playing'] and identity['completed']==sample['completed'],'actual identity/base transport mismatch')
    require(sample['timeline_id']=='acceptance-held' and identity['playing'] is False and identity['seconds']==case['source_seconds'],'finite held timeline mismatch')
    parts=names(base['parts'],'name',PART_COUNTS,'actual body/garment');observed=names(f['observed'],'role',{'body','garment','eyes','hair'},'actual observed roles');accessories=names(appearance['accessories'],'name',{'eyes','hair'},'actual appearance roles')
    require(identity['body_entity']==appearance['body_entity']==parts['body']['display_entity'],'actual identity/base/appearance body mismatch')
    require(appearance['character_entity']==base['character_entity'],'actual base/appearance character mismatch')
    require(appearance['body_vertices']==len(parts['body']['positions']),'actual appearance/base body coverage mismatch')
    evidence={}
    for role,part in parts.items():
        count,index_count=PART_COUNTS[role];require(len(part['source_ids'])==count and all(type(i) is int and 0<=i<65536 for i in part['source_ids']) and len(part['indices'])==index_count,'truncated/malformed source/index coverage')
        for key,size in (('positions',3),('normals',3),('tangents',4),('rest_positions',3),('rest_normals',3)):rows(part[key],size,count,'full '+role+' '+key)
        require(all(type(i) is int and 0<=i<count for i in part['indices']),'out-of-range uploaded index')
        vector(part['display_transform'],16,'actual global');vector(part['model_to_world'],16,'recorded model frame')
        actual=observed[role];require(actual['entity']==part['display_entity'] and actual['mesh_handle']==part['mesh_handle'],'actual part binding mismatch')
        for key in ('positions','normals','tangents','indices','display_transform'):require(actual[key]==part[key],'observed/full buffer mismatch '+key)
        evidence[role]=full_positive_lbs(part,base['bones'])
    evidence['raw_rest_cage']=oracle.rest_error(parts['body'],work['character']['parameters'])
    require(appearance['body_entity']==parts['body']['display_entity'] and appearance['body_mesh']==parts['body']['mesh_handle'] and appearance['body_material']==observed['body']['material_handle'],'production body binding mismatch')
    for role,actual in observed.items():
        count=len(actual['positions']);rows(actual['positions'],3,count,role+' POSITION');rows(actual['normals'],3,count,role+' NORMAL')
        vector(actual['display_transform'],16,role+' global')
        require(actual['indices'] and len(actual['indices'])%3==0 and all(type(i) is int and 0<=i<count for i in actual['indices']),'actual indices invalid')
        material=actual['material'];require(material['unlit'] is False,'undeclared diagnostic unlit material')
        if role!='garment':
            rows(actual['uv_0'],2,count,role+' UV')
            source=appearance['skin'] if role=='body' else accessories[role]
            require(actual['material_handle']==source['material_handle'],'material binding mismatch')
            image=material['image'];texture=source['texture'];require(image is not None,'selected actual texture missing')
            for key in ('image_handle','width','height','format','decoded_rgba_sha256'):require(image[key]==texture[key],'actual image mismatch '+key)
            require(image['decoded_bytes']==image['width']*image['height']*4,'actual image bytes incomplete')
            for key in ('base_color','roughness','metallic','alpha_mode','cull_mode','double_sided'):require(material[key]==source[key],'actual original material mismatch '+key)
        if role=='body':
            require(mesh_array_sha256(actual['positions'])==actual['positions_sha256']==appearance['body_positions_sha256'],'exported body POSITION/appearance hash mismatch')
            require(mesh_array_sha256(actual['uv_0'])==actual['uv_sha256']==appearance['skin']['uv_sha256'],'exported body UV/skin hash mismatch')
        if role in accessories:
            source=accessories[role];require(actual['entity']==source['entity'] and actual['mesh_handle']==source['mesh_handle'] and count==source['render_vertices'] and actual['display_transform']==source['display_transform'],'actual accessory binding/count/global mismatch')
            for array,key in (('positions','positions_sha256'),('normals','normals_sha256'),('uv_0','uv_sha256'),('indices','indices_sha256')):
                computed=mesh_array_sha256(actual[array],integer=array=='indices')
                require(computed==actual[key]==source[key],'exported array/observed/production hash mismatch '+role+' '+array)
    camera=f['camera'];require(camera==identity['camera'] and camera['active'] is True,'current camera mismatch');vector(camera['global_transform'],16,'actual camera')
    require(camera['viewport'] is not None and camera['projection'] and camera['sub_camera_view'],'actual camera fields missing')
    return {'case_id':case['id'],'endpoint':f['endpoint'],'request_id':f['request_id'],'actual_generation':base['generation'],'actual_revision':base['revision'],'work_sha256':f['work_sha256'],'sample':sample,'evidence':evidence,'scope':'actual CPU identity/full buffers + independent raw rest and observed53bone/fullpositive LBS; GUI/render/quality/performance separate'}

def verify_files(paths,plan_path):
    cases_data=(EXP/'inputs/cases.json').read_bytes();require(hashlib.sha256(cases_data).hexdigest()==CASES_SHA,'frozen69case identity changed');cases=strict_json(cases_data.decode());plan=strict_json(plan_path.read_text())
    require(plan['frozen_cases_sha256']==CASES_SHA and plan['case_count']==69,'linked plan mismatch')
    # Index first without holding69 full multi-MiB snapshots simultaneously.
    index=[]
    for path in paths:
        envelope=strict_json(path.read_text());index.append((envelope['case_id'],path,envelope['frame']['endpoint'],envelope['frame']['request_id']))
    complete_case_ids([x[0] for x in index],cases);require(len({x[2] for x in index})==1,'mixed endpoints');require(len({x[3] for x in index})==69,'duplicate request IDs')
    recipes={r['id']:r['parameters'] for r in cases['recipes']};expected={c['id']:c for c in cases['held_cases']};planned={p['case_id']:p for p in plan['plan']};require(set(planned)==set(expected),'linked plan incomplete');oracle=Oracle();out=[]
    for case_id,path,_,_ in index:out.append(validate(strict_json(path.read_text()),expected[case_id],planned[case_id],oracle,recipes[expected[case_id]['recipe_id']]))
    return {'scope':'complete69held per-endpoint CPU acceptance only; ordinary UI/filetoolbar/live/rendered quality NOT-CERTIFIED','endpoint':index[0][2],'complete_held_cohort':True,'count':len(out),'cases':out}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('captures',type=Path,nargs='+');args=parser.parse_args();result=verify_files(args.captures,args.plan);args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'complete':True,'endpoint':result['endpoint'],'count':result['count']}))
