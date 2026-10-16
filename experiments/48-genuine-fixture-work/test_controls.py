#!/usr/bin/env python3
"""Controls mutate the actual build/reload/publication path, never model data files."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('export48',HERE/'export.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def run():
    c=e.load_admitted_inputs();outputs=e.build_artifacts();base=c['blobs']['assets/fixtures/nvwa-humanoid.glb'];good=outputs['assets/'+e.ASSET]
    ledger=e.strict_json(outputs['transformation-ledger.json']);passed=[];rejected=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,OSError):rejected.append(name)
        else:raise RuntimeError('mutation accepted: '+name)
    result=e.verify_reloaded(base,good,ledger,c);passed.append('actual serialized90frame derivative reload')
    old,ob=e.decode_glb(base)
    def mutation(name,change):
        d,b=e.decode_glb(good);binary=bytearray(b);change(d,binary)
        reject(name,lambda:e.verify_reloaded(base,e.pack_glb(d,bytes(binary)),ledger,c))
    mutation('root channel changed to ancestor23',lambda d,b:d['animations'][3]['channels'][-1]['target'].update(node=23))
    mutation('root and pelvis channel switched',lambda d,b:d['animations'][3]['channels'][0]['target'].update(node=16))
    mutation('named sides exchanged',lambda d,b:d['animations'][3]['channels'][6]['target'].update(node=7))
    mutation('original animation renamed',lambda d,b:d['animations'][0].update(name='changed'))
    mutation('exact original rest scale changed',lambda d,b:d['nodes'][12]['scale'].__setitem__(0,1.))
    mutation('original BIN byte changed',lambda d,b:b.__setitem__(0,b[0]^1))
    mutation('wrong appended accessor count',lambda d,b:d['accessors'][-1].update(count=89))
    mutation('sampler uses old animation accessor',lambda d,b:d['animations'][3]['samplers'][0].update(input=0))
    mutation('wrong animation index insertion',lambda d,b:d['animations'].reverse())
    def offset(d,index):
        a=d['accessors'][index];return d['bufferViews'][a['bufferView']].get('byteOffset',0)+a.get('byteOffset',0)
    def translate_twice(d,b):
        a=d['animations'][3]['samplers'][-1]['output'];p=offset(d,a)+4
        struct.pack_into('<f',b,p,struct.unpack_from('<f',b,p)[0]+.08)
    mutation('old root height added a second time',translate_twice)
    def wrongq(d,b):
        a=d['animations'][3]['samplers'][6]['output'];p=offset(d,a)
        q=list(struct.unpack_from('<4f',b,p));q[0],q[3]=q[3],q[0];struct.pack_into('<4f',b,p,*q)
    mutation('XYZW component order changed',wrongq)
    def signflip(d,b):
        a=d['animations'][3]['samplers'][6]['output'];p=offset(d,a)+4*4
        q=struct.unpack_from('<4f',b,p);struct.pack_into('<4f',b,p,*[-x for x in q])
    mutation('unrecorded single-frame hemisphere sign flip',signflip)
    def timechange(d,b):struct.pack_into('<f',b,offset(d,len(old['accessors']))+89*4,3.)
    mutation('invented final three-second key',timechange)
    for label,path in [('admission','experiments/48-genuine-fixture-work/admission.json'),('calibration','experiments/47-fixture-rig-calibration/calibration.json'),('raw','experiments/44-approved-cpu-motion-trial/evidence/run/raw/root_positions.f32'),('receipt','experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json')]:
        reject(label+' altered source pin',lambda path=path:e.load_admitted_inputs({path:b'{}'}))
    for name,change in [('false raw ledger binding',lambda x:x['source_generation']['raw_sha256'].update({'bad':'0'*64})),('false calibration ledger binding',lambda x:x.update(calibration_sha256='0'*64)),('false admission ledger binding',lambda x:x.update(admission_sha256='0'*64)),('false derivative hash',lambda x:x['outputs']['assets/'+e.ASSET].update(sha256='0'*64))]:
        bad=copy.deepcopy(ledger);change(bad);reject(name,lambda bad=bad:e.verify_reloaded(base,good,bad,c))
    reject('duplicate JSON keys',lambda:e.strict_json(b'{"a":1,"a":2}'))
    reject('nonfinite JSON',lambda:e.strict_json(b'{"a":NaN}'))
    private=e.ROOT/'.work/m2-genuine-work/primary';private.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(private),prefix='controls-') as td:
        parent=Path(td);dest=parent/'success';e.publish_new(dest);passed.append('exclusive real publication and full reload')
        # Exercise the advertised verifier itself against edited ledger bytes.
        ledger_path=dest/'transformation-ledger.json'; original_ledger=ledger_path.read_bytes()
        recorded=e.strict_json(original_ledger)
        for metric in sorted(p[1] for p in e.DIAGNOSTIC_PATHS):
            close=copy.deepcopy(recorded);close['primary_reload'][metric]+=1e-16
            ledger_path.write_bytes(e.encode(close));e.verify_artifacts(dest)
            passed.append('allowlisted f64 roundoff '+metric)
            for label,value in [('outside roundoff',recorded['primary_reload'][metric]+4e-15),('boolean',True),('integer',0),('nonfinite',float('nan')),('physical bound',2e-6),('negative',-1e-20)]:
                bad=copy.deepcopy(recorded);bad['primary_reload'][metric]=value
                if label=='nonfinite':ledger_path.write_bytes(json.dumps(bad,indent=2).encode()+b'\n')
                else:ledger_path.write_bytes(e.encode(bad))
                reject('verify_artifacts diagnostic '+metric+' '+label,lambda:e.verify_artifacts(dest))
        for label,change in [('provenance value',lambda x:x['source_generation'].update(code_revision='0'*40)),('discrete boolean',lambda x:x['primary_reload'].update(frames=True)),('discrete float type',lambda x:x['primary_reload'].update(frames=90.)),('nonallowlisted numeric field',lambda x:x['transformation'].update(nominal_duration_seconds=3.+1e-15))]:
            bad=copy.deepcopy(recorded);change(bad);ledger_path.write_bytes(e.encode(bad))
            reject('verify_artifacts exact '+label,lambda:e.verify_artifacts(dest))
        positive_zero=copy.deepcopy(recorded);positive_zero['transformation']['basis'][0][1]=0.0
        ledger_path.write_bytes(e.encode(positive_zero));e.verify_artifacts(dest);passed.append('exact positive-zero float representation preserved')
        negative_zero=copy.deepcopy(recorded);negative_zero['transformation']['basis'][0][1]=-0.0
        ledger_path.write_bytes(e.encode(negative_zero));reject('verify_artifacts nonallowlisted signed-zero representation',lambda:e.verify_artifacts(dest))
        ledger_path.write_bytes(original_ledger);e.verify_artifacts(dest);passed.append('restored exact historical ledger')
        before={p.relative_to(dest).as_posix():e.sha(p.read_bytes()) for p in dest.rglob('*') if p.is_file()}
        reject('existing destination',lambda:e.publish_new(dest))
        require_before={p.relative_to(dest).as_posix():e.sha(p.read_bytes()) for p in dest.rglob('*') if p.is_file()}
        e.require(before==require_before,'existing destination unchanged');passed.append('existing destination preserved')
        link=parent/'linked';link.symlink_to(dest,target_is_directory=True)
        reject('symlink output',lambda:e.publish_new(link))
        fake=parent/'source-link';fake.symlink_to(dest/e.WORK)
        reject('symlink input',lambda:e.read_regular(fake))
        # Fault occurs after the first output is written: invoke the real publisher cleanup.
        real_verify=e.verify_artifacts
        def fail(_):raise ValueError('injected postwrite verifier failure')
        e.verify_artifacts=fail
        try:reject('postwrite verification failure',lambda:e.publish_new(parent/'failed'))
        finally:e.verify_artifacts=real_verify
        e.require(not (parent/'failed').exists(),'failed publication removed');passed.append('postwrite failure removes owned outputs')
        original_open=Path.open
        class PartialFailure:
            def __init__(self,file):self.file=file
            def __enter__(self):return self
            def __exit__(self,*args):self.file.close()
            def write(self,b):self.file.write(b[:8]);self.file.flush();raise OSError('injected partial write failure')
        def injected_open(path,mode='r',*args,**kwargs):
            file=original_open(path,mode,*args,**kwargs)
            return PartialFailure(file) if mode=='xb' and path.name=='character.profile.json' else file
        Path.open=injected_open
        try:reject('partial write disk failure',lambda:e.publish_new(parent/'partial'))
        finally:Path.open=original_open
        e.require(not (parent/'partial').exists(),'partial write outputs removed');passed.append('partial write cleanup')
    return dict(status='PASS',positive_checks=passed,rejected_controls=rejected,rejection_count=len(rejected),reload=result,temporary_resources_remaining=0)

if __name__=='__main__':print(e.encode(run()).decode(),end='')
