#!/usr/bin/env python3
"""Strict retained-evidence audit. No GUI, network, build, or inference is run."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

COHORT_SHA = 'ac79a480817ebde7660f9c4e64bcb4519ffa9ba393620a5826f62ed28fa4def9'
ARTIFACTS = {
 'artifacts/transformation-ledger.json': 'd71e323362b750491f46f1f106a0079eefb015a0271a8460e8a9f11542febe6e',
 'artifacts/assets/generated/genuine44-calibrated47.glb': 'c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc',
 'artifacts/character.profile.json': 'af8638e626c0ade115d94663f191621ab5753c1f970e8a337ecc03aad16429b0',
 'artifacts/genuine44-calibrated47.nvwa.json': '7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779',
}
ADAPTATION_SHA = 'e5df9e734fd68cdf121b4c536dda94fead945d43ddd630be5a6d1b991b8a9ce4'
OBSERVATIONS_SHA = 'd92dc4a07f135a2a837b4e9e27bb1cf141236cb4368e801ed36f410136c499e7'
WORKS = ['native/native-saved.nvwa.json', 'native/native-saved-edit.nvwa.json', 'web/web-saved.nvwa.json', 'web/web-edited.nvwa.json', 'native/web-returned-native-saved.nvwa.json']

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result

def load(path):
    def bad(value):
        raise ValueError('nonfinite JSON: ' + value)
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=bad)

def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'unknown/missing fields: ' + label)

def f32(value):
    require(type(value) is float and math.isfinite(value), 'f32 requires finite JSON float')
    result = struct.unpack('<f', struct.pack('<f', value))[0]
    require(math.isfinite(result), 'f32 overflow')
    return result

def uint(value, bits):
    require(type(value) is int and 0 <= value < 2**bits, 'invalid integer field')
    return value

def text(value):
    require(type(value) is str, 'invalid string field')
    return value

def profile(value):
    value = copy.deepcopy(value)
    keys(value, ['id','asset_path','asset_sha256','license','parameters','clips'], 'profile')
    for name in ['id','asset_path','asset_sha256','license']:
        text(value[name])
    require(type(value['parameters']) is list and type(value['clips']) is list, 'profile collections')
    for item in value['parameters']:
        keys(item, ['id','morph_index','min','max','default'], 'parameter')
        text(item['id']); uint(item['morph_index'], 64)
        for name in ['min','max','default']:
            item[name] = f32(item[name])
    for item in value['clips']:
        keys(item, ['id','animation_index','duration_seconds'], 'clip')
        text(item['id']); uint(item['animation_index'], 64)
        item['duration_seconds'] = f32(item['duration_seconds'])
    return value

def work(value):
    value = copy.deepcopy(value)
    keys(value, ['schema_version','revision','profile','character','timeline'], 'Work')
    uint(value['schema_version'], 32); uint(value['revision'], 64)
    value['profile'] = profile(value['profile'])
    character = value['character']
    keys(character, ['id','profile_id','parameters','scale'], 'character')
    text(character['id']); text(character['profile_id'])
    keys(character['parameters'], ['jaw_width','nose_width','smile','shoulder_width'], 'character parameters')
    character['parameters'] = {name:f32(v) for name,v in character['parameters'].items()}
    character['scale'] = f32(character['scale'])
    require(type(value['timeline']) is list, 'timeline list')
    for item in value['timeline']:
        keys(item, ['id','clip_id','start_seconds','duration_seconds','speed','looping'], 'timeline')
        text(item['id']); text(item['clip_id'])
        require(type(item['looping']) is bool, 'looping bool')
        for name in ['start_seconds','duration_seconds','speed']:
            item[name] = f32(item[name])
    return value

def typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(typed_equal(a,b) for a,b in zip(left,right))
    if type(left) is float:
        return struct.pack('<d',left) == struct.pack('<d',right)
    return left == right


def image_format(data, suffix):
    """Validate PNG chunks/CRC/zlib data or JPEG marker structure and dimensions."""
    if suffix == '.png':
        require(data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
        pos=8; chunks=[]; packed=b''; dimensions=None
        while pos < len(data):
            require(pos+12 <= len(data), 'truncated PNG')
            length=struct.unpack('>I', data[pos:pos+4])[0]
            kind=data[pos+4:pos+8]; end=pos+12+length
            require(end <= len(data), 'PNG chunk bounds')
            body=data[pos+8:pos+8+length]
            require(zlib.crc32(kind+body)&0xffffffff == struct.unpack('>I',data[end-4:end])[0], 'PNG CRC')
            chunks.append(kind)
            if kind == b'IHDR':
                require(len(body)==13 and dimensions is None, 'PNG IHDR')
                w,h,depth,color,comp,filt,interlace=struct.unpack('>IIBBBBB',body)
                require(w>0 and h>0 and depth==8 and color in (2,6) and comp==filt==interlace==0, 'PNG encoding')
                dimensions=(w,h); channels={2:3,6:4}[color]
            if kind == b'IDAT': packed+=body
            pos=end
            if kind == b'IEND': break
        require(chunks[0]==b'IHDR' and chunks[-1]==b'IEND' and pos==len(data), 'PNG boundary')
        raw=zlib.decompress(packed); w,h=dimensions
        require(len(raw)==h*(1+w*channels), 'PNG decompressed dimensions')
        require(all(raw[row*(1+w*channels)]<=4 for row in range(h)), 'PNG row filter')
        return {'format':'PNG','width':w,'height':h}
    require(suffix=='.jpg' and data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9', 'JPEG signature/boundary')
    pos=2; dimensions=None; scans=0
    while pos<len(data)-2:
        require(data[pos]==255, 'JPEG marker')
        while data[pos]==255: pos+=1
        marker=data[pos];pos+=1
        if marker in range(0xd0,0xd8): continue
        require(pos+2<=len(data), 'JPEG length')
        size=struct.unpack('>H',data[pos:pos+2])[0]
        require(size>=2 and pos+size<=len(data), 'JPEG segment bounds')
        body=data[pos+2:pos+size];pos+=size
        if marker in (0xc0,0xc1,0xc2):
            require(len(body)>=6 and body[0]==8, 'JPEG frame')
            h,w=struct.unpack('>HH',body[1:5]);require(w>0 and h>0,'JPEG dimensions');dimensions=(w,h)
        if marker==0xda:
            scans+=1
            while pos<len(data)-2:
                if data[pos]!=255: pos+=1;continue
                if data[pos+1]==0 or 0xd0<=data[pos+1]<=0xd7: pos+=2;continue
                break
    require(pos==len(data)-2 and dimensions and scans, 'JPEG scan/end')
    return {'format':'JPEG','width':dimensions[0],'height':dimensions[1]}

def verify(runtime_root, repo_root):
    runtime_root=Path(runtime_root); repo_root=Path(repo_root)
    manifest=load(runtime_root/'MANIFEST.json')
    keys(manifest,['schema_version','files','artifact_bindings','quality','not_run'], 'manifest')
    require(type(manifest['schema_version']) is int and manifest['schema_version']==1,'manifest version')
    require(manifest['quality']=='HOLD','quality must remain HOLD')
    require(manifest['not_run']==['fresh GUI replay','exact runtime pose numbers','semantic/anatomical/contact quality','performance','fresh local compile','unassisted Alpha49'],'NOT-RUN boundary changed')
    require(manifest['artifact_bindings']==ARTIFACTS,'artifact binding changed')
    require(digest((runtime_root/'archive-adaptation.json').read_bytes())==ADAPTATION_SHA,'archive adaptation changed')
    require(digest((runtime_root/'observations.json').read_bytes())==OBSERVATIONS_SHA,'observer claims changed')
    adaptation=load(runtime_root/'archive-adaptation.json')
    image_names=set(adaptation['raw_image_sha256'])
    expected_files=image_names | set(WORKS) | {'native/reload-command.json','source-cohort.json','observations.json','archive-adaptation.json','verify_evidence.py','test_controls.py','REPORT.md'}
    require(set(manifest['files'])==expected_files,'manifest boundary changed')
    actual={p.relative_to(runtime_root).as_posix() for p in runtime_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='MANIFEST.json'}
    require(actual==set(manifest['files']), 'archive file boundary changed')
    for name,entry in manifest['files'].items():
        require(name and not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe archive path')
        p=runtime_root/name;require(not p.is_symlink(),'symlink archive')
        data=p.read_bytes()
        require(type(entry['bytes']) is int and len(data)==entry['bytes'] and digest(data)==entry['sha256'],'archive hash: '+name)
        if p.suffix in ('.png','.jpg'):
            require(image_format(data,p.suffix)==entry['image'],'image format: '+name)
        elif p.suffix in ('.json','.md','.py'):
            require((b'/' + b'Users/') not in data and (b'/' + b'home/') not in data,'private home path: '+name)
    for name,sha in adaptation['raw_image_sha256'].items():
        require(digest((runtime_root/name).read_bytes())==sha,'raw image changed: '+name)
    require(digest((runtime_root/'source-cohort.json').read_bytes())==COHORT_SHA,'source cohort identity')
    cohort=load(runtime_root/'source-cohort.json');require(len(cohort['files'])==54,'cohort count')
    for name,entry in cohort['files'].items():
        data=(repo_root/name).read_bytes()
        require(digest(data)==entry['sha256'] and len(data)==entry['bytes'],'source input changed: '+name)
        require(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entry['retained_git_blob'],'source blob mismatch')
    experiment=repo_root/'experiments/48-genuine-fixture-work'
    for name,sha in ARTIFACTS.items():
        require(digest((experiment/name).read_bytes())==sha,'source artifact changed: '+name)
    source=work(load(experiment/'artifacts/genuine44-calibrated47.nvwa.json'))
    require(profile(load(experiment/'artifacts/character.profile.json'))==source['profile'],'profile binding')
    glb=(experiment/'artifacts/assets/generated/genuine44-calibrated47.glb').read_bytes()
    magic,version,length=struct.unpack('<4sII',glb[:12]);require(magic==b'glTF' and version==2 and length==len(glb),'GLB header')
    size,kind=struct.unpack('<II',glb[12:20]);require(kind==0x4e4f534a,'GLB JSON chunk')
    gltf=json.loads(glb[20:20+size],object_pairs_hook=pairs)
    clip=gltf['animations'][3]
    require(clip['name']=='genuine44_calibrated47' and len(clip['channels'])==19,'serialized clip binding')
    native0=load(runtime_root/WORKS[0])
    require(digest((runtime_root/WORKS[0]).read_bytes())=='b3c7ead0e48bb584e2e52e17687e9d14280b1885703fed85d26e54cc76417b91','canonical native0 bytes')
    require(typed_equal(work(native0),source),'source-to-canonical declared f32 fields')
    expected1=copy.deepcopy(native0);expected1['revision']=1;expected1['character']['parameters']['jaw_width']=0.23
    expected2=copy.deepcopy(expected1);expected2['revision']=2;expected2['character']['parameters']['jaw_width']=0.62
    for name,expected in zip(WORKS[1:],[expected1,expected1,expected2,expected2]):
        observed=load(runtime_root/name)
        work(observed)  # Validate fields/types before exact canonical-to-canonical comparison.
        require(typed_equal(observed,expected),'whole typed Work transition: '+name)
    require((runtime_root/WORKS[1]).read_bytes()==(runtime_root/WORKS[2]).read_bytes(),'native1/Web1 byte mismatch')
    require((runtime_root/WORKS[3]).read_bytes()==(runtime_root/WORKS[4]).read_bytes(),'Web2/native2 byte mismatch')
    command=load(runtime_root/'native/reload-command.json')
    require(command=={'command_id':'runtime-native-open-jaw-023','expected_revision':0,'command':{'type':'set_parameters','character_id':'character-1','values':{'jaw_width':0.23}}} and type(command['expected_revision']) is int,'CLI command binding')
    observation=load(runtime_root/'observations.json')
    require(observation['quality']=='HOLD' and len(observation['not_run'])==8,'observation limits')
    return {'status':'PASS_RETAINED_AUDIT','work_files':5,'images':13,'source_inputs':54,'quality':'HOLD','fresh_GUI_replay':'NOT-RUN','runtime_pose_numbers':'NOT-RUN'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[3])
    args=parser.parse_args()
    try:
        print(json.dumps(verify(args.runtime_root,args.repo_root),sort_keys=True))
    except (ValueError,KeyError,TypeError,OverflowError,OSError,struct.error,zlib.error) as error:
        parser.exit(1,'REJECT: '+str(error)+'\n')

if __name__=='__main__':
    main()
