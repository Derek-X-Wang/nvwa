#!/usr/bin/env python3
"""One offline command: prepare, build, test importer, stage and verify authored clip."""
import hashlib,json,os,shutil,struct,subprocess,tempfile
from pathlib import Path
from prepare import ROOT,HERE,BASE,encoded,decode,accessor,sha
PRIVATE=ROOT/'.work/m2-import'
def run(args,**kw):return subprocess.run([str(a)for a in args],cwd=ROOT,check=True,**kw)
def main():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    run(['python3','-B',HERE/'prepare.py'],stdout=subprocess.DEVNULL)
    env={**os.environ,'CARGO_TARGET_DIR':str(PRIVATE/'target')}
    with (HERE/'build-output.txt').open('w') as log:run(['cargo','build','--offline','--jobs','2','--manifest-path',HERE/'Cargo.toml'],env=env,stdout=log,stderr=subprocess.STDOUT)
    with (HERE/'test-output.txt').open('w')as log:run(['python3','-B',HERE/'test_boundary.py'],stdout=log,stderr=subprocess.STDOUT)
    runs=PRIVATE/'runs';runs.mkdir(exist_ok=True);session=Path(tempfile.mkdtemp(prefix='authored-',dir=runs));assets=session/'assets';assets.mkdir();clipdir=assets/'fixtures'
    binary=PRIVATE/'target/debug/nvwa-motion-import-experiment';fix=HERE/'fixtures'
    with (session/'import-result.json').open('w')as f:run([binary,fix/'authored.normalized.json',fix/'authored.raw.json',BASE,clipdir],stdout=f)
    raw=json.loads((fix/'authored.raw.json').read_bytes());clip=(clipdir/'clip.glb').read_bytes();doc,bin=decode(clip);base_doc,base_bin=decode(BASE.read_bytes())
    assert doc['nodes']==base_doc['nodes'] and doc['skins']==base_doc['skins'] and doc['meshes']==base_doc['meshes']
    assert bin[:len(base_bin)]==base_bin
    a=doc['animations'][0];assert len(doc['animations'])==1 and a['name']=='imported_authored_control' and len(a['channels'])==19
    joints=doc['skins'][0]['joints'];errors=[]
    expected_times=raw['sample_times_seconds']
    for c in a['channels']:
        sampler=a['samplers'][c['sampler']];actual_times=[v[0]for v in accessor(doc,bin,sampler['input'])]
        assert all(x<y for x,y in zip(actual_times,actual_times[1:]));assert len(actual_times)==73
        assert max(abs(x-y)for x,y in zip(actual_times,expected_times))<1.2e-7
        vals=accessor(doc,bin,sampler['output']);index=joints.index(c['target']['node'])
        expected=[f[index]for f in raw['local_rotations_xyzw']]if c['target']['path']=='rotation'else raw['root_translations_m']
        errors.extend(abs(v-k)for row,target in zip(vals,expected)for v,k in zip(row,target))
    assert max(errors)<1e-7
    profile=json.loads((ROOT/'assets/character.profile.json').read_bytes());profile['asset_path']='fixtures/clip.glb';profile['asset_sha256']=sha(clip);profile['clips']=[{'id':'imported_authored_control','animation_index':0,'duration_seconds':raw['sample_times_seconds'][-1]}]
    work={'schema_version':1,'revision':0,'profile':profile,'character':{'id':'character-1','profile_id':profile['id'],'parameters':{p['id']:0.0 for p in profile['parameters']},'scale':1.0},'timeline':[{'id':'imported-authored-control','clip_id':'imported_authored_control','start_seconds':0.0,'duration_seconds':raw['sample_times_seconds'][-1],'speed':1.0,'looping':True}]}
    (assets/'character.profile.json').write_bytes(encoded(profile));workpath=session/'authored-control.nvwa.json';workpath.write_bytes(encoded(work))
    # Retained artifact bytes are immutable across reproductions; refuse accidental overwrite differences.
    retained=HERE/'artifacts';retained.mkdir(exist_ok=True)
    for name,bytes in [('clip.glb',clip),('character.profile.json',encoded(profile)),('authored-control.nvwa.json',encoded(work)),('manifest-current.json',(clipdir/'manifest.json').read_bytes())]:
        path=retained/name
        if path.exists():assert path.read_bytes()==bytes,f'existing retained artifact differs: {path}'
        else:path.write_bytes(bytes)
    run([binary,'adapt-f32',fix/'synthetic-f32.sidecar.json',fix/'synthetic-root_positions.f32',fix/'synthetic-local_rotations_xyzw.f32',session/'synthetic-adapted'],stdout=subprocess.DEVNULL)
    receipt={'provenance_kind':'authored_control','ai_generated':False,'same_rig_roundtrip_max_component_error':max(errors),'base_nodes_skins_meshes_and_original_binary_preserved':True,'frame_count':73,'joint_count':18,'clip_sha256':sha(clip),'work_sha256':sha(encoded(work)),'profile_sha256':sha(encoded(profile)),'runtime_playback':'NOT-RUN','staged_asset_root':str(assets),'staged_work':str(workpath),'run_directory':str(session)}
    (PRIVATE/'latest-run.json').write_text(json.dumps(receipt,indent=2)+'\n');(HERE/'verification.json').write_text(json.dumps({k:v for k,v in receipt.items()if not k.startswith('staged_')and k!='run_directory'},indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
