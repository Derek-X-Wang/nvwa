#!/usr/bin/env python3
"""Read the frozen fixture; extract authored wave into v1, no model generation."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'assets/fixtures/nvwa-humanoid.glb'
SHA='f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6'
def encoded(v): return json.dumps(v,separators=(',',':'),allow_nan=False).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    n,k=struct.unpack_from('<II',b,12);assert k==0x4e4f534a
    d=json.loads(b[20:20+n]);z=20+n;length,kind=struct.unpack_from('<II',b,z);assert kind==0x004e4942
    return d,b[z+8:z+8+length]
def accessor(d,bin,i):
    a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
    assert a['componentType']==5126 and 'sparse' not in a and v.get('byteStride',n*4)==n*4
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return list(struct.iter_unpack('<'+'f'*n,bin[offset:offset+a['count']*n*4]))
def main():
    b=BASE.read_bytes();assert sha(b)==SHA;d,bin=decode(b);js=d['skins'][0]['joints'];nodes=d['nodes'];wave=next(a for a in d['animations']if a['name']=='wave')
    parents=[next((i for i,p in enumerate(js)if j in nodes[p].get('children',[])),None)for j in js]
    sk={'identity':'nvwa18','joint_names':[nodes[j]['name']for j in js],'parent_indices':parents,'rest_local_translations_m':[nodes[j].get('translation',[0,0,0])for j in js],'rest_local_rotations_xyzw':[nodes[j].get('rotation',[0,0,0,1])for j in js],'rest_local_scales_xyz':[nodes[j].get('scale',[1,1,1])for j in js]}
    rotations={};translations={};scales={};times=None
    for c in wave['channels']:
        s=wave['samplers'][c['sampler']];assert s.get('interpolation','LINEAR')=='LINEAR'
        t=[v[0]for v in accessor(d,bin,s['input'])]
        if times is None: times=t
        assert times==t
        {'rotation':rotations,'translation':translations,'scale':scales}[c['target']['path']][c['target']['node']]=accessor(d,bin,s['output'])
    n=len(times);root=js[parents.index(None)]
    raw={'schema_version':1,'provenance_kind':'authored_control','skeleton':sk,'convention':{'units':'meters','handedness':'right','up_axis':'Y','rotation_order':'xyzw','transform_space':'local','root_motion_mode':'absolute_translation'},'sample_times_seconds':[t-times[0]for t in times],'local_rotations_xyzw':[[rotations[j][f]for j in js]for f in range(n)],'root_translations_m':translations[root]}
    rawbytes=encoded(raw);envelope={**raw,'provenance':{'source_id':'original-Nvwa-wave-CC0-control','raw_format':'nvwa.motion.portable.v1','raw_sha256':sha(rawbytes),'run_receipt_sha256':None,'provider':None,'code_revision':None,'model_sha256':None}}
    out=HERE/'fixtures';out.mkdir(exist_ok=True)
    (out/'authored.raw.json').write_bytes(rawbytes);(out/'authored.normalized.json').write_bytes(encoded(envelope))
    max_translation=max(abs(v-k)for i,j in enumerate(js)if j!=root for sample in translations[j]for v,k in zip(sample,sk['rest_local_translations_m'][i]))
    max_scale=max(abs(v-k)for i,j in enumerate(js)for sample in scales[j]for v,k in zip(sample,sk['rest_local_scales_xyz'][i]))
    receipt={'provenance_kind':'authored_control','ai_generated':False,'base_sha256':SHA,'raw_sha256':sha(rawbytes),'frame_count':n,'source_first_time':times[0],'source_last_time':times[-1],'normalized_duration_seconds':times[-1]-times[0],'max_omitted_nonroot_translation_m':max_translation,'max_omitted_animated_scale_delta':max_scale,'conversion':'identity units/axes/quaternion order; subtract first source sample time; preserve base rest scales'}
    (out/'extraction-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    # Explicitly synthetic byte controls; no provider execution or motion quality claim.
    soma={**sk,'identity':'soma30','joint_names':[f'synthetic_joint_{i}'for i in range(30)],'parent_indices':[None]+[0]*29,'rest_local_translations_m':[[0,.988,0]]+[[0,0,0]]*29,'rest_local_rotations_xyzw':[[0,0,0,1]]*30,'rest_local_scales_xyz':[[1,1,1]]*30}
    sidecar={'source_format':'kimodo.cpp.f32.v1','code_revision':'5679ff19ba0a522c0b0516e9a9d402fe1af2c027','endianness':'little','frame_count':3,'joint_count':30,'provenance_kind':'authored_control','skeleton':soma,'convention':raw['convention'],'sample_times_seconds':[0,.0333333333,.0666666667]}
    (out/'synthetic-f32.sidecar.json').write_bytes(encoded(sidecar));(out/'synthetic-root_positions.f32').write_bytes(struct.pack('<9f',0,.9,0,.1,.9,0,.2,.9,0));(out/'synthetic-local_rotations_xyzw.f32').write_bytes(struct.pack('<360f',*([0,0,0,1]*90)))
    assert BASE.read_bytes()==b
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
