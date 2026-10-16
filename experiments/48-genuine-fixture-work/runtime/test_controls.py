#!/usr/bin/env python3
"""Mutation-red/restored-green controls invoke the real verifier CLI in subprocesses."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]

def require(ok,message):
    if not ok:
        raise RuntimeError(message)

def main():
    with tempfile.TemporaryDirectory(prefix='nvwa-runtime-controls-') as temp:
        root=Path(temp)/'runtime'
        shutil.copytree(HERE,root,ignore=shutil.ignore_patterns('__pycache__'))
        originals={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        def restore():
            for p in root.rglob('*'):
                if p.is_file() and p.relative_to(root) not in originals:
                    p.unlink()
            for name,data in originals.items():
                (root/name).write_bytes(data)
        def refresh(name):
            manifest=json.loads((root/'MANIFEST.json').read_text());data=(root/name).read_bytes()
            manifest['files'][name]['bytes']=len(data);manifest['files'][name]['sha256']=hashlib.sha256(data).hexdigest()
            (root/'MANIFEST.json').write_text(json.dumps(manifest))
        def edit(mutator, name='web/web-edited.nvwa.json'):
            value=json.loads((root/name).read_text());mutator(value)
            (root/name).write_text(json.dumps(value));refresh(name)
        def run():
            argv=[sys.executable]
            if sys.flags.optimize: argv+=['-O']
            argv += [str(HERE/'verify_evidence.py'),'--runtime-root',str(root),'--repo-root',str(REPO)]
            return subprocess.run(argv,capture_output=True,text=True)
        initial=run();require(initial.returncode==0,initial.stderr)
        cases=[]
        def case(name,mutator):
            mutator();result=run();require(result.returncode!=0 and result.stderr.startswith('REJECT:'),'mutation survived: '+name+' '+result.stdout)
            expected = {
                'huge revision beyond u64':'invalid integer field',
                'bool revision equals int':'invalid integer field',
                'float revision equals int':'invalid integer field',
                'additional parameter':'unknown/missing fields',
                'unknown Work field':'unknown/missing fields',
                'numeric looping equals false':'looping bool',
                'bool float equals zero':'f32 requires finite JSON float',
                'integer float equals zero':'f32 requires finite JSON float',
                'duplicate JSON key':'duplicate JSON key',
                'nonfinite float':'nonfinite JSON',
                'infinity float':'nonfinite JSON',
                'image bytes invalid despite refreshed hash':'JPEG signature/boundary',
                'image hash changed':'archive hash',
                'unlisted file':'archive file boundary changed',
                'quality relabeled PASS':'quality must remain HOLD',
                'NOT-RUN erased':'NOT-RUN boundary changed',
                'source cohort altered with refreshed hash':'source cohort identity',
            }.get(name, 'whole typed Work transition')
            require(expected in result.stderr,'wrong rejection boundary: '+name+' '+result.stderr)
            cases.append({'name':name,'red_exit':result.returncode,'reason':result.stderr.strip()})
            restore();result=run();require(result.returncode==0,'restore failed '+name+' '+result.stderr)
            cases[-1]['restored_exit']=result.returncode
        case('wrong clip',lambda:edit(lambda v:v['timeline'][0].update(clip_id='wave')))
        case('wrong asset hash',lambda:edit(lambda v:v['profile'].update(asset_sha256='0'*64)))
        case('wrong revision',lambda:edit(lambda v:v.update(revision=3)))
        case('huge revision beyond u64',lambda:edit(lambda v:v.update(revision=2**100)))
        case('bool revision equals int',lambda:edit(lambda v:v.update(revision=True)))
        case('float revision equals int',lambda:edit(lambda v:v.update(revision=2.0)))
        case('additional parameter',lambda:edit(lambda v:v['character']['parameters'].update(extra=0.0)))
        case('unknown Work field',lambda:edit(lambda v:v.update(extra=0)))
        case('numeric looping equals false',lambda:edit(lambda v:v['timeline'][0].update(looping=0)))
        case('bool float equals zero',lambda:edit(lambda v:v['character']['parameters'].update(smile=False)))
        case('integer float equals zero',lambda:edit(lambda v:v['character']['parameters'].update(smile=0)))
        case('other float changed within same f32',lambda:edit(lambda v:v['character'].update(scale=1.0000000000000002)))
        case('negative zero changes exact field',lambda:edit(lambda v:v['character']['parameters'].update(smile=-0.0)))
        case('jaw wrong value',lambda:edit(lambda v:v['character']['parameters'].update(jaw_width=0.63)))
        case('native1 wrong revision',lambda:edit(lambda v:v.update(revision=2),'native/native-saved-edit.nvwa.json'))
        case('Web1 extra edit',lambda:edit(lambda v:v['character']['parameters'].update(nose_width=0.2),'web/web-saved.nvwa.json'))
        case('native2 return extra edit',lambda:edit(lambda v:v['character'].update(scale=1.1),'native/web-returned-native-saved.nvwa.json'))
        def raw(text):
            name='web/web-edited.nvwa.json';(root/name).write_text(text);refresh(name)
        original=(root/'web/web-edited.nvwa.json').read_text()
        case('duplicate JSON key',lambda:raw(original.replace('"revision": 2','"revision": 2, "revision": 2',1)))
        case('nonfinite float',lambda:raw(original.replace('"jaw_width": 0.62','"jaw_width": NaN',1)))
        case('infinity float',lambda:raw(original.replace('"jaw_width": 0.62','"jaw_width": Infinity',1)))
        def damage_image():
            name='native/seek-mid-clean.jpg';data=(root/name).read_bytes();(root/name).write_bytes(b'not image'+data[9:]);refresh(name)
        case('image bytes invalid despite refreshed hash',damage_image)
        case('image hash changed',lambda:(root/'native/seek-mid-clean.jpg').write_bytes(b'bad'))
        case('unlisted file',lambda:(root/'unexpected.txt').write_text('unlisted'))
        def quality():
            p=root/'MANIFEST.json';v=json.loads(p.read_text());v['quality']='PASS';p.write_text(json.dumps(v))
        case('quality relabeled PASS',quality)
        def boundary():
            p=root/'MANIFEST.json';v=json.loads(p.read_text());v['not_run']=[];p.write_text(json.dumps(v))
        case('NOT-RUN erased',boundary)
        def cohort():
            p=root/'source-cohort.json';v=json.loads(p.read_text());next(iter(v['files'].values()))['sha256']='0'*64;p.write_text(json.dumps(v));refresh('source-cohort.json')
        case('source cohort altered with refreshed hash',cohort)
        print(json.dumps({'status':'PASS','mode':'optimized' if sys.flags.optimize else 'normal','mutation_red':len(cases),'restored_green':len(cases),'baseline_green':1,'cases':cases},sort_keys=True))

if __name__=='__main__':
    main()
