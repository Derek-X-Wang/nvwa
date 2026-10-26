"""92 held-sample adapter;91 strict default/source0 checker remains immutable."""
import importlib.util
import json
import math
import sys
from pathlib import Path
from supplement_contract import LEGACY, check_context, load_capture
spec=importlib.util.spec_from_file_location('nvwa91_strict_validator',LEGACY/'validate.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
EXP,ROOT,RGBA,numeric,replay,source,hashes,require=(getattr(old,k) for k in ['EXP','ROOT','RGBA','numeric','replay','source','hashes','require'])
close_rows=old.close_rows

def check_record(record,which,case,seconds):
    r,f=record['report'],record['frame'];c=f['candidate']
    variant='AOriginal' if which=='a' else 'BShort01'
    require(r['phase']=='ready' and all(r[k] is True for k in ['current','acknowledged','request_succeeded']), 'current successful ready required')
    require(r['request_id']==f['request_id'] and f['stable_updates']>=2,'request/stability mismatch')
    require(c['variant']==variant and c['A_replay_exact'] is True and c['pre_visibility_publication_matches'] is True,'variant/original replay/visibility failed')
    check_context(record,case,seconds)
    require(f['diagnostic']['mode']=='Combined' and f['diagnostic']['palette']=='Textured','fixed Combined/Textured required')
    # The explicit case/sample contract above replaces only91's default guard.
    base=f['full_base']
    require(c['bones']==base['bones'] and len(base['bones'])==53,'actual full53 bone binding differs')
    require(len({b['name'] for b in base['bones']})==53,'unique53 source bones required')
    expected=replay(base,which);obj,_,_=source(which)
    require((c['source_vertices'],c['render_vertices'],c['triangles'])==(obj['count'],len(obj['pairs']),len(obj['indices'])//3),'declared asset counts differ')
    hair=next(b for b in f['buffers'] if b['role']=='hair')
    pinned_map=json.loads((EXP/('works/a-short04-source-map.json' if which=='a' else 'works/b-short01-source-map.json')).read_text())
    exact_map={'source_uv_pairs':[list(x) for x in obj['pairs']],'uv_0':obj['uv'],'indices':obj['indices']}
    require(pinned_map==exact_map,'pinned source map differs from authenticated OBJ')
    exported_map=hair['source_map']
    require(set(exported_map)==set(exact_map) and exported_map['source_uv_pairs']==exact_map['source_uv_pairs'] and exported_map['indices']==exact_map['indices'],'authenticated source corner/index mapping differs')
    # The existing diagnostic deserializes map UVs to [f32;2] before comparing.
    # Its exported raw Value may move an f64 token by one ULP on parse; require
    # exact equality in that same typed f32 domain, with no numeric tolerance.
    exported_uv=exported_map['uv_0']
    require(isinstance(exported_uv,list) and len(exported_uv)==len(exact_map['uv_0']) and
            all(isinstance(row,list) and len(row)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in row) for row in exported_uv),'finite typed source UV coverage differs')
    require([[numeric.f32(x) for x in row] for row in exported_uv]==exact_map['uv_0'],'exact typed source UV mapping differs')
    require(c['source_uv_pairs']==exact_map['source_uv_pairs'] and hair['uv_0']==exact_map['uv_0'] and hair['indices']==exact_map['indices'],'actual source/render mapping differs')
    for field in ['positions','normals']:
        close_rows(hair[field],expected[field],1e-6,'actual '+field)
    errors=numeric.compare(expected,hair)
    errors['source_rest']=close_rows(c['rest_source_positions'],expected['rest'],1e-12,'fitted rest')
    errors['source_normals']=close_rows(c['rest_source_normals'],expected['rest_normals'],1e-12,'fitted normals')
    errors['source_scales']=close_rows([c['source_scales']],[expected['scales']],1e-12,'source scales')
    require(len(c['full_positive_source_weights'])==len(expected['weights']),'weight source coverage differs')
    for actual,row in zip(c['full_positive_source_weights'],expected['weights']):
        require([x[0] for x in actual]==[x[0] for x in row],'full positive influence IDs differ')
        close_rows([[x[1] for x in actual]],[[x[1] for x in row]],1e-12,'full positive weights')
        require(all(type(x[0]) is int and 0<=x[0]<53 and math.isfinite(x[1]) and x[1]>0 for x in actual),'positive53 weight domain differs')
        require(abs(sum(x[1] for x in actual)-1.)<1e-12,'normalized weight sum differs')
    require(c['decoded_rgba_sha256']==hair['bound_image']['decoded_rgba_sha256']==RGBA[which],'authenticated diffuse decode identity differs')
    require(c['original_decoded_rgba_sha256']==RGBA['a'],'original A diffuse identity differs')
    require(hair['bound_image']['width']==hair['bound_image']['height']==2048 and hair['bound_image']['decoded_bytes']==2048*2048*4,'diffuse image domain differs')
    for key in ['positions','normals']:
        digest=hashes.mesh_array_sha256(hair[key])
        require(digest==c['published_'+key+'_sha256'],'actual uploaded '+key+' digest differs')
        require(digest==c['pre_visibility_publication'][key+'_sha256'],'previsibility '+key+' digest differs')
        if key=='positions':require(digest==hair['positions_sha256'],'buffer POSITION digest differs')
    require(c['actual_image_width']==c['actual_image_height']==2048 and c['actual_image_format']=='Rgba8UnormSrgb' and c['actual_image_mip_count']==1 and c['actual_image_sampler']=='Default','fixed sRGB image policy differs')
    require(hair['bound_image']['format']==c['actual_image_format'] and hair['bound_image']['mip_count']==c['actual_image_mip_count'] and hair['bound_image']['sampler']==c['actual_image_sampler'] and hair['bound_image']['policy']==c['actual_image_policy'],'bound image policy differs')
    witness={'variant':variant,'positions_sha256':c['published_positions_sha256'],'normals_sha256':c['published_normals_sha256'],
             'image_rgba_sha256':RGBA[which],'image_policy':c['actual_image_policy'],'placement':c['display_transform'],
             'camera':f['camera'],'work_sha256':f['work_sha256'],'generation':c['generation']}
    require(c['pre_visibility_publication']==witness,'exact current previsibility witness differs')
    hair_material=next(t for t in f['diagnostic']['targets'] if t['role']=='hair')['render_material']
    require(hair_material['alpha_mode']=='Mask(0.5)' and hair_material['double_sided'] is True and hair_material['cull_mode']=='None' and hair_material['roughness']==numeric.f32(.7) and hair_material['unlit'] is False,'fixed hair material policy differs')
    return errors

def capture_request_ids(records):
    ids=[record['report']['request_id'] for record in records]
    require(all(type(value) is str and value for value in ids) and
            all(record['frame']['request_id']==value for record,value in zip(records,ids)) and
            len(set(ids))==3,'three distinct authenticated nonempty request IDs required')
    return ids

def validate(records,case,seconds):
    require(len(records)==3,'exact A/B/A required')
    capture_request_ids(records)
    a,b,a2=records
    require(old.restore_projection(a)==old.restore_projection(a2),'A restoration differs outside exact request/stability exclusions')
    require(old.comparison_projection(a)==old.comparison_projection(b),'unexpected state change outside declared B asset fields')
    errors=[check_record(record,which,case,seconds) for record,which in zip(records,['a','b','a'])]
    require(a['frame']['candidate']['published_positions_sha256']!=b['frame']['candidate']['published_positions_sha256'],'actual uploaded B positions unchanged')
    return {'result':'PASS','case':case,'source_seconds':seconds,'errors':errors,
            'invariants':'unchanged91 source proof and complete envelope equality except declared B fields; exact A1/A2 restoration',
            'limits':'held CPU source replay only; no rendered/contact/full-motion/identity/save/adoption proof'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',required=True);parser.add_argument('--seconds',type=int,required=True)
    parser.add_argument('capture_and_manifest',nargs=6,metavar='PATH')
    args=parser.parse_args();paths=args.capture_and_manifest
    records=[load_capture(paths[i],paths[i+1]) for i in range(0,6,2)]
    print(json.dumps(validate(records,args.case,args.seconds),indent=2))
