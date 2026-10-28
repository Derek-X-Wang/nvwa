"""Validate controlled CPU A/B captures. This cannot score pixels or admit quality."""
import argparse,json,math
from pathlib import Path
import cpu_probe as cpu
from source_binding import frame_binding,strict_json
EXP=Path(__file__).resolve().parent
CASES=['short-front','long-front','short-quarter','long-quarter']
MODES=['Combined','BodyOnly','EyeOnly'];PALETTES=['Textured','UnlitTextured']
def require(ok,message):cpu.require(ok,message)
def classify_work(raw):
    doc=json.loads(raw)
    found=[c for c in CASES if doc==json.loads((EXP/f'works/{c}.nvwa.json').read_text())]
    require(len(found)==1,'exact fixed Work required');return found[0]
def control_key(e):
    r,f=e['report'],e['frame'];c=f['candidate'];sample=f['full_base']['sample'];d=f['diagnostic']
    return (f['endpoint'],classify_work(r['work_json']),sample['source_seconds'],c['variant'],d['mode'],d['palette'])
def bounds(positions,aabb):
    require(isinstance(aabb,dict),'actual Aabb absent')
    for a in range(3):
        lo=min(p[a] for p in positions);hi=max(p[a] for p in positions)
        # Match compute_aabb's f32 arithmetic; no inflated or disabled culling allowed.
        center=cpu.f32(cpu.f32(lo+hi)*.5);half=cpu.f32(cpu.f32(hi-lo)*.5)
        require(abs(aabb['center'][a]-center)<=1e-6 and abs(aabb['half_extents'][a]-half)<=1e-6,'candidate bounds differ from actual mesh extent')
def validate(e):
    r,f=e['report'],e['frame'];c=f['candidate'];key=control_key(e)
    source_proof=frame_binding(e,json.loads((EXP/'BODY-CORRESPONDENCE.json').read_text())['parts'])
    require(key[0] in ['native','web'] and r['endpoint']==key[0],'endpoint mismatch')
    require(r['phase']=='ready' and r['acknowledged'] is True and r['request_succeeded'] is True and r['current'] is True,'current successful acknowledgement required')
    require(r['request_id']==f['request_id'] and r['work_sha256']==f['work_sha256'],'correlation differs')
    require(f['stable_updates']>=2 and c['pre_visibility_publication_matches'] is True and c['A_replay_exact'] is True,'stable publication/culling epoch absent')
    require(key[2] in [0,2] and not f['full_base']['sample']['playing'],'held source0/2 required')
    require(key[3] in ['AOriginal','BHigh'] and key[4] in MODES and key[5] in PALETTES,'unsupported control')
    require(c['bones']==f['full_base']['bones'] and c['sample']==f['full_base']['sample'] and c['generation']==f['full_base']['generation'],'typed sample/bones/generation mismatch')
    pin=json.loads((EXP/f'works/reference-{key[1]}.json').read_text())['camera'];actual=f['camera']
    require(actual['viewport']==pin['viewport_size_pixels'] and actual['msaa']==pin['msaa'] and actual['projection']==pin['projection'],'camera projection/viewport/MSAA changed')
    require(max(abs(a-b) for a,b in zip(actual['global_transform'],pin['global_transform']))<=1e-6,'camera placement changed')
    require(actual['active'] is True and actual['sub_camera_view'] is not None,'actual active sub-camera state required')
    role_buffers={b['role']:b for b in f['buffers']};eyes=role_buffers['eyes'];body=role_buffers['body']
    expected=cpu.replay(f['full_base'],'a' if key[3]=='AOriginal' else 'b');errors=cpu.compare(expected,eyes)
    bounds(eyes['positions'],c['actual_aabb'])
    require(eyes['entity']==c['entity'] and eyes['mesh_handle']==c['mesh_handle'],'actual eye binding mismatch')
    require(eyes['display_transform']==c['display_transform']==body['display_transform'],'single original body/eye placement required')
    require(c['source_vertices']==expected['source_count'] and c['render_vertices']==len(eyes['positions']) and c['triangles']==len(eyes['indices'])//3,'source/upload count mismatch')
    require(len(c['rest_source_positions'])==expected['source_count'] and len(c['full_positive_source_weights'])==expected['source_count'],'full source fit/weight coverage absent')
    require(max(abs(a-b) for x,y in zip(c['rest_source_positions'],expected['rest']) for a,b in zip(x,y))<=1e-10,'actual source rest fit differs')
    for actual_row,expected_row in zip(c['full_positive_source_weights'],expected['weights']):
        require([x[0] for x in actual_row]==[x[0] for x in expected_row] and all(abs(x[1]-y[1])<=1e-12 for x,y in zip(actual_row,expected_row)),'complete final-positive influence row differs')
    require(f['diagnostic']['visibility_prepared_before_postupdate'] is True,'visibility epoch absent')
    targets={t['role']:t for t in f['diagnostic']['targets']};require(set(targets)==set(role_buffers),'binding role set differs')
    for role,t in targets.items():
        hidden=key[4]=='BodyOnly' and role!='body' or key[4]=='EyeOnly' and role!='eyes'
        require(t['entity']==role_buffers[role]['entity'] and t['mesh_handle']==role_buffers[role]['mesh_handle'] and t['isolation_hidden']==hidden,'role/visibility binding differs')
        if hidden:require(t['inherited_visibility'] is False,'hidden role still inherited-visible')
        before,after=t['production_material'],t['render_material']
        for name in ['base_color_texture','alpha_mode','cull_mode','double_sided','roughness','metallic','base_color']:require(before[name]==after[name],'original material policy changed')
        require(after['unlit']==(True if key[5]=='UnlitTextured' and role in ['body','eyes'] else before['unlit']),'unlit control differs')
        if key[5]=='Textured' or role not in ['body','eyes']:require(before==after,'textured/original material changed')
    eye=targets['eyes'];require(c['material_handle']==eye['material_handle'] and c['image_handle']==eye['production_material']['base_color_texture'],'explicit material/image binding differs')
    require(c['original_standard_material_debug']==eye['production_material']['full_standard_material_debug'],'original full material differs')
    texture=next(p for p in f['appearance']['accessories'] if p['name']=='eyes')['texture'];require(texture['image_handle']==c['image_handle'] and texture['decoded_rgba_sha256']==c['decoded_rgba_sha256'],'actual image pixels differ')
    return key,errors

def matrix_keys(endpoint,diagnostic_case=None,seconds=2):
    if diagnostic_case:return {(endpoint,diagnostic_case,seconds,v,m,p) for v in ['AOriginal','BHigh'] for m in MODES for p in PALETTES}
    return {(endpoint,c,s,v,'Combined','Textured') for c in CASES for s in [0,2] for v in ['AOriginal','BHigh']}

def check(envelopes,diagnostic_case=None,seconds=2):
    require(bool(envelopes),'captures required');keys=[];records={};ids=[];errors=[]
    for e in envelopes:
        key,error=validate(e);keys.append(key);records[key]=e;ids.append(e['report']['request_id']);errors.append(error)
    require(len(set(keys))==len(keys) and len(set(ids))==len(ids),'duplicate request/control')
    endpoint=keys[0][0];require(set(keys)==matrix_keys(endpoint,diagnostic_case,seconds),'complete bounded endpoint matrix required')
    groups={(k[1],k[2]) for k in keys}
    for case,s in groups:
        selected=[e for k,e in records.items() if k[1:3]==(case,s)];ref=selected[0]['frame'];ref_buffers={p['role']:p for p in ref['buffers']}
        for e in selected[1:]:
            f=e['frame'];require(f['full_base']==ref['full_base'] and f['appearance']==ref['appearance'] and f['camera']==ref['camera'] and f['identity']==ref['identity'],'Work/sample/body/appearance/camera changed across controls')
            for b in f['buffers']:
                if b['role']!='eyes':require(b==ref_buffers[b['role']],'non-eye geometry changed')
            for k in ['entity','mesh_handle','material_handle','image_handle','decoded_rgba_sha256','display_transform','original_standard_material_debug']:require(f['candidate'][k]==ref['candidate'][k],'A/B identity/material/image/placement changed')
    return {'endpoint':endpoint,'captures':len(keys),'maximum_replay_error':max(v for e in errors for v in e.values()),'scope':'controlled CPU source/upload/binding matrix; GPU pixels and visual quality NOT-SCORED; intended eyelid fit UNKNOWN'}
def main():
    p=argparse.ArgumentParser();p.add_argument('captures',nargs='+',type=Path);p.add_argument('--diagnostic-case',choices=CASES);p.add_argument('--seconds',type=int,choices=[0,2],default=2);a=p.parse_args();print(json.dumps(check([strict_json(p.read_text()) for p in a.captures],a.diagnostic_case,a.seconds),indent=2))
if __name__=='__main__':main()
