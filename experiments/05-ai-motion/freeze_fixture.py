#!/usr/bin/env python3
"""Freeze the existing authored wave preset. Does not generate motion."""
import hashlib
import json
from pathlib import Path
import struct
from artifact import glb_decode, animation_duration

source = Path('assets/fixtures/nvwa-humanoid.glb')
root = Path(__file__).resolve().parent
original = source.read_bytes()
doc, binary = glb_decode(original)
doc['animations'] = [a for a in doc['animations'] if a.get('name') == 'wave']
assert len(doc['animations']) == 1
doc['asset']['extras'] = {'source_kind': 'authored_preset', 'ai_generated': False,
                          'source_sha256': hashlib.sha256(original).hexdigest()}
raw = json.dumps(doc, separators=(',', ':')).encode()
raw += b' '*(-len(raw)%4)
length = 12+8+len(raw)+8+len(binary)
data = b'glTF'+struct.pack('<II',2,length)+struct.pack('<II',len(raw),0x4E4F534A)+raw+struct.pack('<II',len(binary),0x004E4942)+binary
(root/'authored-wave.glb').write_bytes(data)
job = {'schema_version':1,'job_id':'preset-wave-1','prompt':'A person waves with the right hand',
       'duration_seconds':animation_duration(doc, binary, 'wave'),'seed':42,'backend':'preset_import'}
manifest = {'schema_version':1,'job_id':job['job_id'],'source_kind':'authored_preset',
            'ai_generated':False,'model_id':None,'license':'CC0-1.0',
            'source_sha256':hashlib.sha256(original).hexdigest(),'artifact_path':'authored-wave.glb',
            'artifact_sha256':hashlib.sha256(data).hexdigest(),'animation_name':'wave'}
for name,value in [('job.json',job),('artifact-manifest.json',manifest)]:
 (root/name).write_text(json.dumps(value,indent=2)+'\n')
(root/'SOURCE-LICENSE.txt').write_bytes(source.with_name('LICENSE.txt').read_bytes())
assert source.read_bytes() == original
print(json.dumps({'source_sha256':manifest['source_sha256'],'artifact_sha256':manifest['artifact_sha256'],'bytes':len(data),'ai_generated':False},indent=2))
