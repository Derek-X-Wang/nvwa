"""Explicit seven-Work/two-sample contract; no body reconstruction or renderer."""
import hashlib
import json
import sys
from pathlib import Path

EXP=Path(__file__).resolve().parent
ROOT=EXP.parents[1]
LEGACY=ROOT/'experiments/91-hair-short01-ab'
sys.path.append(str(LEGACY))
from source_check import numeric
require=numeric.require
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
CASES_SHA='2d1509ec221ac977426642653cb263d73f2d94d704a88e75804eb787e1bfa937'
CAMERA_SHA='05c7b5ff02ced362c4140ef7fb0710bfdd56422b3554af3604c9b33a78b9dd6c'

def cases():
    raw=(EXP/'CASES.json').read_bytes();require(SHA(raw)==CASES_SHA,'case contract authentication failed')
    return json.loads(raw)

def work(case,seconds):
    table=cases();require(case in table,'explicit approved case required')
    require(type(seconds) in (int,float) and seconds in table[case]['samples_seconds'],'explicit held sample0 or2 required')
    spec=table[case];raw=(ROOT/spec['work_path']).read_bytes()
    require(SHA(raw)==spec['work_file_sha256'],'pinned Work changed')
    return json.loads(raw)

def camera():
    raw=(EXP/'reference-camera.json').read_bytes();require(SHA(raw)==CAMERA_SHA,'pilot camera authentication failed')
    return json.loads(raw)

def check_context(record,case,seconds):
    expected=work(case,seconds);r,f=record['report'],record['frame'];c=f['candidate'];base=f['full_base'];identity=f['identity']
    require(json.loads(r['work_json'])==expected,'exact selected Work required')
    digest=SHA(r['work_json'].encode('utf-8'))
    require(r['work_sha256']==f['work_sha256']==identity['work_sha256']==digest,'actual Work raw hash binding differs')
    require(r['captured_identity']==identity,'current captured identity differs')
    require(r['base']==f['base'] and r['appearance']==f['appearance'] and r['diagnostic']==f['diagnostic'],'report/frame snapshots differ')
    require(base['parameters']==f['base']['parameters']==expected['character']['parameters'],'actual selected body parameters differ')
    require(base['backend']==f['base']['backend']==expected['profile']['backend'],'actual selected backend differs')
    require(base['generation']==f['base']['generation']==c['generation']==identity['generation'],'actual generation binding differs')
    require(base['revision']==f['base']['revision']==identity['revision']==expected['revision'],'actual revision binding differs')
    sample=base['sample'];timeline=expected['timeline'][0]
    require(sample==c['sample']==f['base']['sample'],'actual sample replicas differ')
    require(sample['clip_id']==identity['clip_id']==timeline['clip_id'] and sample['timeline_id']==identity['timeline_id']==timeline['id'],'selected clip/timeline differs')
    require(sample['source_seconds']==sample['position_seconds']==identity['seconds']==seconds and sample['playing'] is False and identity['playing'] is False,'exact held source/position sample differs')
    require(sample['completed'] is False and identity['completed'] is False and identity['seek_request'] is None,'held sample is completed or seeking')
    require(type(sample['serial']) is int and sample['serial']>=0,'actual sample serial missing')
    require(identity['runtime_ready'] is True and identity['appearance_ready'] is True and identity['appearance_pending'] is False,'actual current readiness differs')
    require(all(identity[k] is None for k in ['preview_sha256','pending_open_sha256','open_error','runtime_error','runtime_appearance_error','stage_error','appearance_error','playback_error']),'actual identity retains pending/error state')
    require(f['camera']==r['camera']==identity['camera']==camera(),'exact authenticated pilot front camera differs')
    # Bind non-hair body/garment uploads to this record's actual production frame.
    for part in base['parts']:
        uploaded=next(b for b in f['buffers'] if b['role']==part['name'])
        require(all(uploaded[k]==part[k] for k in ['positions','normals','indices','display_transform']),'non-hair upload differs from actual production part')

def parse_capture(raw,manifest):
    """Authenticate the existing91 exact-string transfer; never reserialize it."""
    transfer=json.loads(manifest['transfer']) if isinstance(manifest['transfer'],str) else manifest['transfer']
    require(transfer['format']=='nvwa76-raw-transfer-v1' and transfer['encoding']=='utf-8' and transfer['ready'] is True,'existing exact transfer required')
    text=raw.decode('utf-8');require(len(raw)==transfer['bytes'] and len(text)==transfer['chars'] and SHA(raw)==transfer['sha256'],'raw transfer size/hash differs')
    prefix='{"report":';middle=',"frame":';require(text.startswith(prefix),'exact report/frame envelope required')
    decoder=json.JSONDecoder();report,end=decoder.raw_decode(text,len(prefix));require(text[end:end+len(middle)]==middle,'exact frame delimiter differs')
    frame_start=end+len(middle);frame,frame_end=decoder.raw_decode(text,frame_start);require(text[frame_end:]=='}','exact raw envelope ending differs')
    for label,payload in [('report',text[len(prefix):end]),('frame',text[frame_start:frame_end])]:
        encoded=payload.encode('utf-8');require(len(encoded)==transfer[label+'_bytes'] and SHA(encoded)==transfer[label+'_sha256'],'raw '+label+' size/hash differs')
    require(report['request_id']==frame['request_id']==transfer['request_id'],'raw transfer request correlation differs')
    return {'report':report,'frame':frame}

def load_capture(path,manifest_path):
    return parse_capture(Path(path).read_bytes(),json.loads(Path(manifest_path).read_text()))
