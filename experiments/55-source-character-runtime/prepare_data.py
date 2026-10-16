#!/usr/bin/env python3
"""Unit/encoding adapter for the exact approved common sample, no geometry solver."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
import run
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
STORE=REPO/'.work/character-approved-20261016'
CASES=[('neutral',0.,0.),('body-negative',-1.,0.),('body-half',.5,0.),('body-positive',1.,0.),
       ('face-negative',0.,-1.),('face-half',0.,.5),('face-positive',0.,1.),('combined',.5,.5)]
TARGETS={'body_decr':'torso/torso-scale-vert-decr.target.gz',
         'body_incr':'torso/torso-scale-vert-incr.target.gz',
         'face_decr':'chin/chin-jaw-drop-decr.target.gz',
         'face_incr':'chin/chin-jaw-drop-incr.target.gz'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def scaled_obj(src,dst):
    lines=[];count=0
    for line in src.read_text().splitlines():
        if line.startswith('v '):
            parts=line.split();line='v '+' '.join(format(float(v)*.1,'.12g') for v in parts[1:4]);count+=1
        lines.append(line)
    dst.write_text('\n'.join(lines)+'\n');return count

def main():
    global STORE
    parser=argparse.ArgumentParser();parser.add_argument('--common-manifest',type=Path,required=True)
    parser.add_argument('--common-manifest-sha256',required=True);parser.add_argument('--staging',type=Path,default=STORE)
    args=parser.parse_args();STORE=args.staging.resolve()
    common=run.read_pinned_json(args.common_manifest,args.common_manifest_sha256,'common sample manifest')
    run.require(common.get('sample_class')=='makehuman-approved-sample','wrong common sample class')
    run.require(common.get('parameter_schema')=='paired-local-targets-v1' and common.get('approved') is True,
                'unapproved/unsupported common parameter schema')
    approved={}
    for entry in common['files']:
        relative=Path(entry['path']);absolute=STORE/relative
        run.require(not relative.is_absolute() and '..' not in relative.parts and
                    absolute.resolve().is_relative_to(STORE.resolve()), 'unsafe common input path')
        run.require(absolute.is_file() and absolute.stat().st_size==entry['bytes'] and
                    sha(absolute)==entry['sha256'], 'common frozen file mismatch: '+str(relative))
        approved[relative.as_posix()]=entry['sha256']
    expected_cases={name:{'torso_length':body,'jaw_drop':face} for name,body,face in CASES}
    run.require({case['case_id']:case['recipe'] for case in common['cases']}==expected_cases,
                'common case/recipe mismatch')
    data=ROOT/'data';run.require(not data.exists(),'derived data already exists; audit before repeat')
    addon=STORE/'mpfb-addon/data';garment=STORE/'system-assets/clothes/female_sportsuit01'
    inputs=[addon/'3dobjs/base.obj',addon/'mesh_metadata/basemesh_vertex_groups.json',
            addon/'rigs/standard/rig.game_engine.json',addon/'rigs/standard/weights.game_engine.json']
    inputs += [addon/'targets'/p for p in TARGETS.values()]
    inputs += [garment/'female_sportsuit01.obj',garment/'female_sportsuit01.mhclo']
    run.require(all(p.is_file() for p in inputs),'approved common source missing')
    run.require(all(approved.get(p.relative_to(STORE).as_posix())==sha(p) for p in inputs),
                'selected raw input not in frozen common allowlist')
    run.require(common['source_paths']['basemesh']==str(inputs[0].relative_to(STORE)) and
                common['source_paths']['rig']==str(inputs[2].relative_to(STORE)) and
                common['source_paths']['weights']==str(inputs[3].relative_to(STORE)), 'common base/rig identity mismatch')
    for parameter,prefix in [('torso_length','body'),('jaw_drop','face')]:
        for sign in ['decr','incr']:
            run.require(common['parameters'][parameter]['targets'][sign]=='mpfb-addon/data/targets/'+TARGETS[prefix+'_'+sign],
                        'common target pair mismatch')
    # Root freezes the manifest after independent byte/garment audit. This adapter
    # retains every exact raw input digest, so root can compare its allowlist.
    data.mkdir();(data/'targets').mkdir();(data/'garment').mkdir()
    count=scaled_obj(inputs[0],data/'base.obj');run.require(count==19158,'wrong hm08 helper count')
    shutil.copyfile(inputs[1],data/'vertex_groups.json')
    shutil.copyfile(inputs[2],data/'rig.game_engine.json');shutil.copyfile(inputs[3],data/'weights.game_engine.json')
    (data/'composite.json').write_text('{}\n');(data/'empty.macro').write_text('{"macrotargets":{}}\n')
    names={}
    for key,rel in TARGETS.items():
        name=Path(rel).name.removesuffix('.gz');names[key]=name.removesuffix('.target')
        with gzip.open(addon/'targets'/rel,'rb') as stream:(data/'targets'/name).write_bytes(stream.read())
    (data/'body.mhclo').write_text('obj_file base.obj\nverts 0\n'+'\n'.join(str(i) for i in range(count))+'\n')
    scaled_obj(garment/'female_sportsuit01.obj',data/'garment/female_sportsuit01.obj')
    lines=[];section='header'
    for line in (garment/'female_sportsuit01.mhclo').read_text().splitlines():
        parts=line.split()
        if line.startswith('verts 0'):section='verts'
        elif line.startswith('delete_verts'):section='delete'
        if parts and parts[0] in ['x_scale','y_scale','z_scale']:
            parts[3]=format(float(parts[3])*.1,'.12g');line=' '.join(parts)
        elif section=='verts' and len(parts)==9:
            line=' '.join(parts[:6]+[format(float(v)*.1,'.12g') for v in parts[6:9]])
        lines.append(line)
    (data/'garment/female_sportsuit01.mhclo').write_text('\n'.join(lines)+'\n')
    configs=ROOT/'configs';configs.mkdir(exist_ok=False)
    for case_id,body,face in CASES:
        weights={names['body_decr']:max(0.,-body),names['body_incr']:max(0.,body),
                 names['face_decr']:max(0.,-face),names['face_incr']:max(0.,face)}
        config=dict(case_id=case_id,asset_root=str(data),base='base.obj',vertex_groups='vertex_groups.json',
                    composite='composite.json',macros='empty.macro',targets='targets',rig='rig.game_engine.json',
                    weights='weights.game_engine.json',body='body.mhclo',garment='garment/female_sportsuit01.mhclo',
                    target_weights=weights,common_manifest_sha256=args.common_manifest_sha256,candidate_to_raw_scale=10.)
        (configs/(case_id+'.json')).write_text(json.dumps(config,indent=2)+'\n')
    proof=dict(common_manifest_sha256=args.common_manifest_sha256,
               raw_inputs={str(p.relative_to(STORE)):sha(p) for p in inputs},
               derived_files={str(p.relative_to(data)):sha(p) for p in sorted(data.rglob('*')) if p.is_file()},
               conversions=['OBJ positions ×0.1, axes unchanged','target gzip decoding only; candidate loader retains its ×0.1 and threshold',
                            'garment MHCLO offset/reference-scale lengths ×0.1; indices/weights preserved',
                            'identity body MHCLO maps each source vertex to itself; no downloaded body proxy',
                            'empty macro/composite metadata because requested recipe uses only exact local targets'],
               coordinate_identity={'candidate_to_raw_scale':10.,'candidate_to_blender_reference':[[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]]})
    with (ROOT/'evidence/data-adapter.json').open('x') as stream:json.dump(proof,stream,indent=2)
    print('Prepared exact common sample unit/encoding adapter; candidate execution NOT-RUN')
if __name__=='__main__':main()
