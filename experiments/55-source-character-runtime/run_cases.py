#!/usr/bin/env python3
"""Execute the linked real adapter against eight frozen common cases, fail closed."""
import argparse,hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
import run
ROOT=Path(__file__).resolve().parent
IDS=['neutral','body-negative','body-half','body-positive','face-negative','face-half','face-positive','combined']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--common-manifest',type=Path,required=True)
    parser.add_argument('--common-manifest-sha256',required=True);parser.add_argument('--binary-sha256',required=True)
    parser.add_argument('--variant',choices=['B0','B1'],default='B0')
    parser.add_argument('--staging',type=Path,default=ROOT.parent.parent/'.work/character-approved-20261016')
    parser.add_argument('--candidate',type=Path,default=ROOT.parent.parent/'.work/character-approved-20261016/upstream/Humentity')
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--case',choices=IDS)
    args=parser.parse_args();args.out=args.out.resolve()
    common=run.read_pinned_json(args.common_manifest,args.common_manifest_sha256,'common manifest')
    run.require(common.get('sample_class')=='makehuman-approved-sample','wrong sample class')
    proof=json.loads((ROOT/'evidence/data-adapter.json').read_text())
    run.require(proof['common_manifest_sha256']==args.common_manifest_sha256,'derived data manifest identity mismatch')
    store=args.staging.resolve()
    derived_dir=ROOT/('derived-b1' if args.variant=='B1' else 'derived')
    adapter_dir=ROOT/('adapter-b1' if args.variant=='B1' else 'adapter')
    ablation=json.loads((ROOT/'evidence/B1-preparation.json').read_text()) if args.variant=='B1' else None
    packaging=json.loads((ROOT/'evidence/packaging.json').read_text())
    inventory=run.read_pinned_json(ROOT/'upstream-inventory.json',run.INVENTORY_SHA256,'fixed upstream inventory')
    run.verify_inventory(args.candidate,inventory['files'],packaging['upstream_files_sha256'])
    for entry in inventory['files']:
        name=entry['path'];expected=packaging['modified_files'].get(name,{}).get('after_sha256',packaging['upstream_files_sha256'][name])
        if ablation and name==ablation['one_line_source_patch']['path']:expected=ablation['one_line_source_patch']['after_sha256']
        run.require(run.digest(derived_dir/name)==expected,'derived candidate source changed: '+name)
    for path,expected in proof['raw_inputs'].items():
        run.require(run.digest(store/path)==expected,'raw source changed after derivation: '+path)
    for path,expected in proof['derived_files'].items():
        run.require(run.digest(ROOT/'data'/path)==expected,'derived sample changed: '+path)
    build=json.loads((ROOT/'evidence'/('B1-adapter-build.json' if ablation else 'actual-adapter-build.json')).read_text())
    run.require(build.get('exit_code')==0 and build.get('candidate_adapter_linked') is True,'actual adapter build unavailable')
    binary=ROOT/'target/debug'/('humentity-probe-b1' if ablation else 'humentity-probe')
    run.require(binary.is_file() and run.digest(binary)==args.binary_sha256,'actual adapter binary identity mismatch')
    run.require(run.digest(adapter_dir/'Cargo.toml')==build['manifest_sha256'] and
                run.digest(adapter_dir/'Cargo.lock')==build['lock_sha256'],'build input identity changed')
    run.require(not args.out.exists(),'result directory already exists')
    run.require(not any(args.out.is_relative_to(path.resolve()) for path in
                [store,args.candidate,ROOT/'data',ROOT/'configs',ROOT/'derived',ROOT/'adapter']),
                'output directory collides with protected inputs/source')
    expected_recipes={case['case_id']:case['recipe'] for case in common['cases']}
    # Validate all configs before creating or executing a partial run.
    for case_id in ([args.case] if args.case else IDS):
        cfg=json.loads((ROOT/'configs'/(case_id+'.json')).read_text());recipe=expected_recipes[case_id]
        expected={}
        for parameter,value in recipe.items():
            for sign,source in common['parameters'][parameter]['targets'].items():
                key=Path(source).name.removesuffix('.gz').removesuffix('.target')
                expected[key]=max(0.,-value if sign=='decr' else value)
        run.require(cfg['target_weights']==expected and cfg['candidate_to_raw_scale']==10.,'config recipe/scale tamper')
        expected_paths={'base':'base.obj','vertex_groups':'vertex_groups.json','composite':'composite.json',
                        'macros':'empty.macro','targets':'targets','rig':'rig.game_engine.json',
                        'weights':'weights.game_engine.json','body':'body.mhclo','garment':'garment/female_sportsuit01.mhclo'}
        run.require(Path(cfg['asset_root'])==ROOT/'data' and all(cfg[k]==v for k,v in expected_paths.items()),'config source path tamper')
    args.out.mkdir(parents=True)
    cases=[];started=time.monotonic();ok=True
    for case_id in ([args.case] if args.case else IDS):
        config=ROOT/'configs'/(case_id+'.json');cfg=json.loads(config.read_text())
        run.require(cfg['common_manifest_sha256']==args.common_manifest_sha256 and cfg['case_id']==case_id,
                    'config identity mismatch')
        output=args.out/(case_id+'.json');log=args.out/(case_id+'.log')
        command=[str(binary),str(config),str(output)];t=time.monotonic()
        try:
            with log.open('x') as stream:
                completed=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=200)
            code=completed.returncode
        except subprocess.TimeoutExpired: code=124
        actual=None
        if code==0 and output.is_file():
            data=json.loads(output.read_text())
            run.require(data.get('case_id')==case_id and data.get('common_manifest_sha256')==args.common_manifest_sha256,
                        'candidate result identity mismatch')
            actual=data.get('actual_candidate_code_executed')
        passed=code==0 and actual is True
        cases.append(dict(case_id=case_id,command=command,exit_code=code,duration_seconds=time.monotonic()-t,
                          candidate_execution_attempted=True,actual_candidate_code_executed=actual,
                          status='executed_not_compared' if passed else 'failed',
                          log_path=str(log),log_sha256=run.digest(log),
                          output_sha256=run.digest(output) if output.exists() else None))
        print(case_id,code,'executed_not_compared' if passed else 'failed',flush=True)
        if not passed:ok=False;break
    result=dict(schema_version=1,route_id='source-runtime',sample_class='makehuman-approved-sample',
                common_manifest_sha256=args.common_manifest_sha256,binary_sha256=args.binary_sha256,
                adapter_source_sha256=run.digest(adapter_dir/'src/main.rs'),variant=args.variant,
                status='executed_not_compared' if ok else 'failed',cases=cases,duration_seconds=time.monotonic()-started,
                child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                child_peak_rss_platform='macOS bytes',native_graphical_executed=False,web_graphical_executed=False,
                reference_pipeline_executed=False,comparison_executed=False)
    with (args.out/'summary.json').open('x') as stream:json.dump(result,stream,indent=2)
    return 0 if ok else 2
if __name__=='__main__':
    try:sys.exit(main())
    except (run.Blocked,OSError,ValueError,KeyError) as error:print('NOT-RUN: '+str(error));sys.exit(2)
