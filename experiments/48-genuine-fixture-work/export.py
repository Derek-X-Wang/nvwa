#!/usr/bin/env python3
"""Exact admitted raw44 -> fixture47 transport; Python stdlib only. No inference."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLIP = 'genuine44_calibrated47'
ASSET = 'generated/genuine44-calibrated47.glb'
WORK = 'genuine44-calibrated47.nvwa.json'
JOINTS = [17,16,9,8,1,0,4,3,2,7,6,5,12,11,10,15,14,13]
PINS = {
 'experiments/48-genuine-fixture-work/CONTRACT.json': '58e82af4ab212627844a80a5279e855d5d3b67a535a586e930e3983c5a8d0b26',
 'experiments/48-genuine-fixture-work/admission.json': '94676288d6e3f22886e4b08512aa9094e6e18cf21d50eac1d52e711d1cb365d6',
 'experiments/47-fixture-rig-calibration/SHA256SUMS.json': 'b4fbb24bffcaf8c061d2b9acd6abf046dd90fd07c013f5f8551c6693575a2957',
 'experiments/47-fixture-rig-calibration/calibration.json': 'd730f372adc92d83931c23da84d8709dd8bfa7eb75d57964817577f4b034a6d0',
 'experiments/47-fixture-rig-calibration/calibrate.py': '15f620bb1ceabb4d6d32a398b284b28657e2ac7244a04eca0ca945618d4e1eca',
 'assets/character.profile.json': 'b7604ebdfb8b090073adead456f78fbf09779c23823b419986e57159bd9e0353',
}

def require(ok, why):
    if not ok:
        raise ValueError(why)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def encode(v):
    return (json.dumps(v, indent=2, allow_nan=False)+'\n').encode()

def strict_json(b):
    def pairs(rows):
        out = {}
        for k,v in rows:
            require(k not in out, 'duplicate JSON key')
            out[k] = v
        return out
    def bad(v):
        raise ValueError('nonfinite JSON '+v)
    return json.loads(b, object_pairs_hook=pairs, parse_constant=bad)

def read_regular(p, limit=32*1024*1024):
    p = Path(p)
    require(not any(x.is_symlink() for x in [p]+list(p.parents)), 'symlink input/path')
    require(p.is_file() and p.stat().st_size <= limit, 'bounded regular input')
    return p.read_bytes()

def load_admitted_inputs(overrides=None):
    overrides = {} if overrides is None else overrides
    blobs = {}
    for name,digest in PINS.items():
        b = overrides.get(name)
        if b is None:
            b = read_regular(ROOT/name)
        require(type(b) is bytes and sha(b) == digest, 'pinned input '+name)
        blobs[name] = b
    admit = strict_json(blobs['experiments/48-genuine-fixture-work/admission.json'])
    require(admit['status'] == 'LOCAL_ENGINEERING_CALIBRATION_ADMITTED', 'explicit admission')
    cal = strict_json(blobs['experiments/47-fixture-rig-calibration/calibration.json'])
    require(cal['candidate'] == 'physical_sides_identity' and cal['basis'] == [[1,0,0],[0,1,0],[0,0,1]], 'admitted identity policy')
    # Check the complete admitted47 capsule before executing its pure mapper.
    manifest = strict_json(blobs['experiments/47-fixture-rig-calibration/SHA256SUMS.json'])
    for name,row in manifest.items():
        b = read_regular(ROOT/'experiments/47-fixture-rig-calibration'/name)
        require(sha(b) == row['sha256'] and len(b) == row['bytes'], '47 capsule '+name)
    for name,digest in cal['input_sha256'].items():
        b = overrides.get(name)
        if b is None:
            b = read_regular(ROOT/name)
        require(type(b) is bytes and sha(b) == digest, 'source pin '+name)
        blobs[name] = b
    spec = importlib.util.spec_from_file_location('admitted47', ROOT/'experiments/47-fixture-rig-calibration/calibrate.py')
    mapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mapper)
    source,target,roots,frames,_ = mapper.load_inputs({n:blobs[n] for n in cal['input_sha256']})
    mapper.check_physical_policy(cal)
    receipt = strict_json(blobs['experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'])
    require(receipt['request']['seed'] == 42 and receipt['request']['diffusion_steps'] == 25, 'source request identity')
    return dict(blobs=blobs, admission=admit, calibration=cal, mapper=mapper,
                source=source,target=target,roots=roots,frames=frames,receipt=receipt)

def f32(x):
    require(type(x) in (int,float) and math.isfinite(x), 'finite number')
    return struct.unpack('<f',struct.pack('<f',x))[0]

def quaternion(m):
    # Stable largest-diagonal conversion of a proper matrix; XYZW output.
    t = sum(m[i][i] for i in range(3))
    if t > 0:
        s = math.sqrt(t+1)*2
        q = [(m[2][1]-m[1][2])/s,(m[0][2]-m[2][0])/s,(m[1][0]-m[0][1])/s,s/4]
    else:
        i = max(range(3), key=lambda k:m[k][k]); j=(i+1)%3; k=(i+2)%3
        s = math.sqrt(1+m[i][i]-m[j][j]-m[k][k])*2
        q = [0.,0.,0.,0.]; q[i]=s/4
        q[j]=(m[j][i]+m[i][j])/s; q[k]=(m[k][i]+m[i][k])/s
        q[3]=(m[k][j]-m[j][k])/s
    n = math.sqrt(sum(x*x for x in q))
    require(n > 1e-12, 'nonzero quaternion')
    return [x/n for x in q]

def mapped_frames(c):
    matrices=[]; roots=[]; qs=[]; flips=0
    for raw,hips in zip(c['frames'],c['roots']):
        m,r=c['mapper'].map_frame(c['source'],c['target'],c['calibration'],raw,hips)
        row=[]
        for j,x in enumerate(m):
            q=quaternion(x)
            if qs and sum(a*b for a,b in zip(q,qs[-1][j])) < 0:
                q=[-v for v in q]; flips+=1
            row.append(q)
        matrices.append(m); roots.append(r); qs.append(row)
    return matrices,roots,qs,flips

def decode_glb(b):
    require(len(b)<=32*1024*1024 and len(b)>=28 and b[:4]==b'glTF', 'GLB header')
    require(struct.unpack_from('<II',b,4)==(2,len(b)), 'GLB version/length')
    jl,jk=struct.unpack_from('<II',b,12)
    require(jk==0x4e4f534a and jl%4==0 and jl<=2*1024*1024, 'JSON chunk')
    pos=20+jl; require(pos+8<=len(b),'BIN header')
    bl,bk=struct.unpack_from('<II',b,pos)
    require(bk==0x004e4942 and bl%4==0 and pos+8+bl==len(b),'single BIN chunk')
    return strict_json(b[20:pos]),b[pos+8:]

def pack_glb(d,b):
    j=json.dumps(d,separators=(',',':'),allow_nan=False).encode()
    j+=b' '*((-len(j))%4); b+=b'\0'*((-len(b))%4)
    return b'glTF'+struct.pack('<IIII',2,28+len(j)+len(b),len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b

def append_clip(base,qs,roots):
    d,old=decode_glb(base); binary=bytearray(old)
    def accessor(rows,kind):
        flat=[f32(x) for row in rows for x in row]
        raw=struct.pack('<%df'%len(flat),*flat)
        binary.extend(b'\0'*((-len(binary))%4)); offset=len(binary); binary.extend(raw)
        view=len(d['bufferViews']); d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=len(raw)))
        idx=len(d['accessors']); item=dict(bufferView=view,componentType=5126,count=len(rows),type=kind)
        if kind=='SCALAR': item.update(min=[min(flat)],max=[max(flat)])
        d['accessors'].append(item)
        return idx
    times=accessor([[i/30] for i in range(90)],'SCALAR')
    samplers=[]; channels=[]
    for j,node in enumerate(JOINTS):
        a=accessor([f[j] for f in qs],'VEC4')
        channels.append(dict(sampler=len(samplers),target=dict(node=node,path='rotation')))
        samplers.append(dict(input=times,output=a,interpolation='LINEAR'))
    a=accessor(roots,'VEC3')
    channels.append(dict(sampler=len(samplers),target=dict(node=17,path='translation')))
    samplers.append(dict(input=times,output=a,interpolation='LINEAR'))
    require(len(d['animations'])==3,'three original clips')
    d['animations'].append(dict(name=CLIP,samplers=samplers,channels=channels,extras=dict(experiment_only=True,provenance_kind='generated',source_experiment=44,calibration_experiment=47)))
    d['buffers'][0]['byteLength']=len(binary)
    return pack_glb(d,bytes(binary))

def decode_accessor(d,b,index,kind):
    require(type(index) is int and 0<=index<len(d['accessors']),'accessor index')
    a=d['accessors'][index]; width={'SCALAR':1,'VEC3':3,'VEC4':4}[kind]
    require(a['componentType']==5126 and a['type']==kind and a['count']==90 and 'sparse' not in a,'90 float32 values')
    v=d['bufferViews'][a['bufferView']]
    require(v['buffer']==0 and 'byteStride' not in v and not a.get('normalized',False),'packed buffer0')
    off=v.get('byteOffset',0)+a.get('byteOffset',0); size=90*width*4
    require(off%4==0 and off>=0 and a.get('byteOffset',0)+size<=v['byteLength'] and off+size<=d['buffers'][0]['byteLength']<=len(b),'accessor bounds')
    x=struct.unpack_from('<%df'%(90*width),b,off)
    require(all(math.isfinite(v) for v in x),'finite accessor')
    return [list(x[i:i+width]) for i in range(0,len(x),width)]

def verify_reloaded(base_bytes,derivative_bytes,ledger=None,capsule=None):
    c=load_admitted_inputs() if capsule is None else capsule
    old,ob=decode_glb(base_bytes); d,b=decode_glb(derivative_bytes)
    require(sha(base_bytes)==c['calibration']['input_sha256']['assets/fixtures/nvwa-humanoid.glb'],'base identity')
    require(b[:len(ob)]==ob,'original BIN prefix')
    stripped=copy.deepcopy(d)
    require(len(d['animations'])==4,'append one animation')
    require(len(d['accessors'])==len(old['accessors'])+20 and len(d['bufferViews'])==len(old['bufferViews'])+20,'append20 accessors/views')
    stripped['animations']=stripped['animations'][:3];stripped['accessors']=stripped['accessors'][:len(old['accessors'])];stripped['bufferViews']=stripped['bufferViews'][:len(old['bufferViews'])]
    stripped['buffers'][0]['byteLength']=old['buffers'][0]['byteLength']
    require(stripped==old,'all original JSON values preserved')
    a=d['animations'][3]
    require(a['name']==CLIP and len(a['channels'])==19 and len(a['samplers'])==19,'new clip identity')
    mats,roots,expected_q,flips=mapped_frames(c)
    times=[f32(i/30) for i in range(90)]; decoded_q=[[None]*18 for _ in times]; decoded_roots=None
    expected_targets=[dict(node=n,path='rotation') for n in JOINTS]+[dict(node=17,path='translation')]
    for i,ch in enumerate(a['channels']):
        require(ch['target']==expected_targets[i] and ch['sampler']==i,'exact channel target/order')
        s=a['samplers'][i]
        require(s['interpolation']=='LINEAR' and s['input']==len(old['accessors']) and s['output']==len(old['accessors'])+i+1,'sampler/index insertion')
        require([x[0] for x in decode_accessor(d,b,s['input'],'SCALAR')]==times,'exact90 time keys')
        values=decode_accessor(d,b,s['output'],'VEC4' if i<18 else 'VEC3')
        expected=[q[i] for q in expected_q] if i<18 else roots
        require(values==[[f32(x) for x in row] for row in expected],'serialized frame values')
        if i<18:
            for frame,row in enumerate(values): decoded_q[frame][i]=row
        else: decoded_roots=values
    max_matrix=max_pelvis=max_point=0.
    for frame,(qs,root) in enumerate(zip(decoded_q,decoded_roots)):
        rotations=[c['mapper'].rotation(q) for q in qs]
        max_matrix=max(max_matrix,max(abs(x-y) for a,z in zip(rotations,mats[frame]) for ar,zr in zip(a,z) for x,y in zip(ar,zr)))
        points=c['mapper'].fk(c['target'],rotations,root)
        exact=c['mapper'].fk(c['target'],mats[frame],roots[frame])
        max_pelvis=max(max_pelvis,c['mapper'].norm(c['mapper'].sub(points[1],c['roots'][frame])))
        max_point=max(max_point,max(c['mapper'].norm(c['mapper'].sub(p,q)) for p,q in zip(points,exact)))
    require(max_matrix<2e-6 and max_pelvis<2e-6 and max_point<2e-6,'float32 affine transfer tolerance')
    if ledger is not None:
        require(ledger['source_generation']['raw_sha256']=={n: c['calibration']['input_sha256'][n] for n in c['calibration']['input_sha256'] if n.endswith('.f32')},'ledger original raw bindings')
        require(ledger['admission_sha256']==PINS['experiments/48-genuine-fixture-work/admission.json'] and ledger['calibration_sha256']==PINS['experiments/47-fixture-rig-calibration/calibration.json'],'ledger admission/calibration')
        require(ledger['outputs']['assets/'+ASSET]['sha256']==sha(derivative_bytes),'ledger derivative binding')
    return dict(status='PASS',frames=90,channels=19,original_BIN_prefix_bytes=len(ob),max_rotation_matrix_error=max_matrix,max_pelvis_world_error_m=max_pelvis,max_joint_position_error_m=max_point,hemisphere_flips=flips)

def build_artifacts():
    c=load_admitted_inputs(); _,roots,qs,flips=mapped_frames(c)
    base=c['blobs']['assets/fixtures/nvwa-humanoid.glb']; derivative=append_clip(base,qs,roots)
    profile=strict_json(c['blobs']['assets/character.profile.json']); profile['id']='nvwa-experiment48-genuine44-calibrated47'
    profile.update(asset_path=ASSET,asset_sha256=sha(derivative),license='CC0-1.0 applies to original Nvwa fixture only; generated motion has separate retained source terms. See transformation-ledger.json; no composite rights claim.')
    duration=f32(89/30);profile['clips'].append(dict(id=CLIP,animation_index=3,duration_seconds=duration))
    work=dict(schema_version=1,revision=0,profile=profile,character=dict(id='character-1',profile_id=profile['id'],parameters={p['id']:p['default'] for p in profile['parameters']},scale=1.),timeline=[dict(id='genuine44-entry-1',clip_id=CLIP,start_seconds=0.,duration_seconds=duration,speed=1.,looping=False)])
    outputs={'assets/'+ASSET:derivative,'character.profile.json':encode(profile),WORK:encode(work)}
    receipt=c['receipt']; original_receipt='experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'
    ledger=dict(schema='nvwa.experiment48.transformation-ledger.v1',experiment_only=True,provenance_kind='generated',
        admission_sha256=PINS['experiments/48-genuine-fixture-work/admission.json'],calibration_sha256=PINS['experiments/47-fixture-rig-calibration/calibration.json'],
        input_sha256={n:sha(b) for n,b in c['blobs'].items()},exporter_sha256=sha(read_regular(HERE/'export.py')),
        source_generation=dict(receipt_path=original_receipt,receipt_sha256=sha(c['blobs'][original_receipt]),returncode=receipt['returncode'],reason=receipt['reason'],raw_complete=receipt['raw_complete'],code_revision=receipt['request']['code_revision'],request=receipt['request'],raw_sha256={n:h for n,h in c['calibration']['input_sha256'].items() if n.endswith('.f32')}),
        transformation=dict(new_generation=False,mapper='pinned47 map_frame; exact current fixture only',candidate=c['calibration']['candidate'],basis=c['calibration']['basis'],root_policy=c['calibration']['root_policy'],neutral=c['calibration']['neutral'],delta_policy=c['calibration']['delta_policy'],scale_policy=c['calibration']['scale_policy'],translation_policy=c['calibration']['translation_policy'],roll='authored static projected front/up engineering gauges',source_shape=[90,30,4],target_shape=[90,18,4],fps=30,nominal_duration_seconds=3.,last_key_seconds=duration,time_keys='binary32(i/30), i=0..89',quaternions='proper matrix -> normalized XYZW -> hemisphere continuity -> binary32',hemisphere_flips=flips,interpolation='LINEAR; no extra frame, blend, resample or loop',animation_index=3,clip_id=CLIP,joint_rotation_nodes=JOINTS,translation_nodes=[17]),
        license_scope=dict(fixture='CC0-1.0 original fixture only',generated_motion='Retained upstream terms; no CC0 or new redistribution rights claimed',retained_source_notice='experiments/41-real-short-motion/REPORT.md:33',motion_model_terms='https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/blob/6c9233af1180b8151e3c4703477104af5dce9dd5/LICENSE',encoder_terms='https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/blob/3e8d958803beaddb6011ac534f2be972e2710c7d/LICENSE-META-LLAMA-3.txt'),
        outputs={n:dict(sha256=sha(b),bytes=len(b)) for n,b in outputs.items()},
        not_run=['independent decoded verification','native/Web playback and save exchange','official decoder parity','product provider','general rigs','certified anatomy/contact','prompt meaning/human quality','performance'])
    ledger['primary_reload']=verify_reloaded(base,derivative,ledger,c)
    outputs['transformation-ledger.json']=encode(ledger)
    return outputs

# Residuals measure cancellation in f64 affine arithmetic; they are not asset data.
# Cross-runtime repro differs by 1.89e-16 m. This fixed absolute allowance is
# approximately nine machine epsilons at metre scale, with no relative tolerance.
DIAGNOSTIC_PATHS = {
    ('primary_reload','max_rotation_matrix_error'),
    ('primary_reload','max_pelvis_world_error_m'),
    ('primary_reload','max_joint_position_error_m'),
}
DIAGNOSTIC_ABS_TOLERANCE = 2e-15

def compare_ledger(actual, expected, path=()):
    require(type(actual) is type(expected), 'ledger type '+repr(path))
    if path in DIAGNOSTIC_PATHS:
        require(type(actual) is float and math.isfinite(actual) and math.isfinite(expected), 'finite float diagnostic '+repr(path))
        require(0 <= actual < 2e-6 and 0 <= expected < 2e-6, 'diagnostic bound '+repr(path))
        require(abs(actual-expected) <= DIAGNOSTIC_ABS_TOLERANCE, 'diagnostic f64 roundoff '+repr(path))
    elif type(expected) is dict:
        require(list(actual)==list(expected), 'exact ledger keys/order '+repr(path))
        for key in expected:compare_ledger(actual[key],expected[key],path+(key,))
    elif type(expected) is list:
        require(len(actual)==len(expected),'exact ledger length '+repr(path))
        for i,(a,b) in enumerate(zip(actual,expected)):compare_ledger(a,b,path+(i,))
    elif type(expected) is float:
        require(struct.pack('>d',actual)==struct.pack('>d',expected), 'exact ledger binary64 value '+repr(path))
    else:
        require(actual == expected, 'exact ledger value '+repr(path))

def verify_artifacts(path):
    path=Path(path); c=load_admitted_inputs()
    ledger=strict_json(read_regular(path/'transformation-ledger.json'))
    require(ledger['exporter_sha256']==sha(read_regular(HERE/'export.py')),'exporter identity')
    for n,row in ledger['outputs'].items():
        require(n in ('assets/'+ASSET,'character.profile.json',WORK),'output identity')
        b=read_regular(path/n);require(sha(b)==row['sha256'] and len(b)==row['bytes'],'output hash '+n)
    expected=build_artifacts()
    for n,b in expected.items():
        if n == 'transformation-ledger.json':
            require(read_regular(path/n)==encode(ledger),'canonical ledger encoding')
            compare_ledger(ledger,strict_json(b))
        else:
            require(read_regular(path/n)==b,'deterministic complete output '+n)
    result=verify_reloaded(c['blobs']['assets/fixtures/nvwa-humanoid.glb'],read_regular(path/'assets'/ASSET),ledger,c)
    result['verification_runtime']=dict(implementation=sys.implementation.name,version=sys.version.split()[0])
    result['historical_ledger_diagnostics']='build-time observations; runtime-qualified records in REPORT.md and verification.json'
    result['diagnostic_comparison']=dict(paths=['/'.join(p) for p in sorted(DIAGNOSTIC_PATHS)],absolute_tolerance=DIAGNOSTIC_ABS_TOLERANCE,relative_tolerance=0.,finite_float_only=True,upper_bound_exclusive=2e-6)
    return result

def publish_new(out):
    out=Path(out)
    require(not any(p.is_symlink() for p in [out]+list(out.parents)),'symlink destination/path')
    require(out.parent.is_dir() and not out.exists(),'exclusive new destination')
    outputs=build_artifacts();out.mkdir();created=[];dirs=[]
    try:
        for name,b in outputs.items():
            target=out/name
            for parent in reversed(list(target.relative_to(out).parents)[:-1]):
                p=out/parent
                if not p.exists():p.mkdir();dirs.append(p)
            with target.open('xb') as f:
                created.append(target)
                f.write(b)
        result=verify_artifacts(out)
    except BaseException:
        for p in reversed(created):p.unlink()
        for p in reversed(dirs):p.rmdir()
        out.rmdir()
        raise
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['build','verify']);parser.add_argument('path',type=Path);args=parser.parse_args()
    print(encode(publish_new(args.path) if args.operation=='build' else verify_artifacts(args.path)).decode(),end='')
