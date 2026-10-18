#!/usr/bin/env python3
"""Prepare only after root integrates the canonical #85 example and assets."""
import argparse,hashlib,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent
CASES_SHA='7abedf9e9c46245d7c9cf0aaeab77e716fb37dd538aa76cccdae935e6fda9185'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def prepare(root,out):
    cases_path=EXP/'inputs/cases.json';require(sha(cases_path)==CASES_SHA,'frozen cases changed');cases=json.loads(cases_path.read_text())
    source=root/'examples/b1-character.nvwa.json';require(source.is_file(),'NOT-LINKED: integrate #85 canonical example before preparing Works or freezing closure')
    canonical=json.loads(source.read_text());profile=canonical['profile'];appearance=canonical['character']['appearance']
    require(profile['backend']=={'type':'b1_cpu','schema_version':3,'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v2'},'NOT-LINKED: canonical backend3/basev2 required')
    require(profile['id']=='nvwa-mpfb-b1-motion-v2' and [p['id'] for p in profile['parameters']]==cases['parameter_order'],'NOT-LINKED: exact eight-parameter profilev2 required')
    appearance_manifest=root/'assets/appearances/mpfb-b1-cc0-v2/manifest.json'
    # Profile asset_path is relative to assets, never arbitrary caller data.
    base_manifest=root/'assets'/profile['asset_path']
    require(base_manifest.is_file() and sha(base_manifest)==profile['asset_sha256'],'basev2 manifest not linked/authenticated')
    require(appearance['asset_set_id']=='mpfb-b1-cc0-appearance-v2' and sha(appearance_manifest)==appearance['asset_set_sha256'],'appearancev2 manifest not linked/authenticated')
    recipes={r['id']:r['parameters'] for r in cases['recipes']};out.mkdir(parents=True,exist_ok=True);plan=[]
    for case in cases['held_cases']:
        work=copy.deepcopy(canonical);work['revision']=1;work['character']['parameters']=recipes[case['recipe_id']].copy()
        work['character']['appearance'].update(case['appearance'])
        work['timeline']=[{'id':'acceptance-held','clip_id':case['clip_id'],'start_seconds':0.,'duration_seconds':4.,'speed':1.,'looping':False}]
        data=json.dumps(work,indent=2)+'\n';name=case['id']+'.nvwa.json';(out/name).write_text(data)
        plan.append({'case_id':case['id'],'work_file':name,'work_file_sha256':hashlib.sha256(data.encode()).hexdigest(),'requests':[{'request_id':'open-'+case['id'],'action':'open','work_json':data},{'request_id':'held-'+case['id'],'action':'playback','seek_seconds':case['source_seconds'],'playing':False}]})
    receipt={'scope':'linked synthetic held Work preparation only; no runtime/UI/render proof','frozen_cases_sha256':CASES_SHA,'canonical_example_sha256':sha(source),'profile':profile,'appearance':appearance,'base_manifest_sha256':sha(base_manifest),'appearance_manifest_sha256':sha(appearance_manifest),'case_count':len(plan),'plan':plan}
    (out/'plan.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--out',type=Path,default=EXP/'works');a=p.parse_args();print(json.dumps({'cases':prepare(a.root.resolve(),a.out.resolve())['case_count']}))
