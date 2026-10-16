#!/usr/bin/env python3
"""Measure real candidate outputs against frozen MPFB data; no solver or reference-as-input."""
import argparse,json,math
from pathlib import Path
import run
ROOT=Path(__file__).resolve().parent
STORE=ROOT.parent.parent/'.work/character-approved-20261016'
def transform(point,matrix):
    return [sum(matrix[row][col]*point[col] for col in range(3))+matrix[row][3] for row in range(3)]
def metric(pairs,tolerance):
    maximum=0.;sum_sq=0.;count=0;over=0;worst=None
    for key,actual,expected in pairs:
        if not all(math.isfinite(v) for v in actual+expected):raise ValueError('nonfinite measured position')
        errors=[abs(a-b) for a,b in zip(actual,expected)];error=max(errors)
        count+=1;sum_sq+=sum(v*v for v in errors)
        if error>tolerance:over+=1
        if worst is None or error>maximum:
            maximum=error;worst={'id':key,'candidate':actual,'reference':expected,'component_errors':errors}
    return {'compared_points':count,'max_component_error_metres':maximum if count else None,
            'rms_distance_metres':math.sqrt(sum_sq/count) if count else None,
            'points_over_tolerance':over,'tolerance_metres':tolerance,
            'within_tolerance':count>0 and over==0,'worst':worst}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--common-manifest',type=Path,required=True)
    parser.add_argument('--common-manifest-sha256',required=True);parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--variant',choices=['B0','B1'],default='B0')
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    common=run.read_pinned_json(args.common_manifest,args.common_manifest_sha256,'common manifest')
    execution_path=args.results/'summary.json'
    execution=json.loads(execution_path.read_text());require=run.require
    require(execution.get('schema_version')==1 and execution.get('route_id')=='source-runtime' and
            execution.get('sample_class')=='makehuman-approved-sample','execution summary route/class/schema mismatch')
    require(execution.get('common_manifest_sha256')==args.common_manifest_sha256,'execution summary common manifest mismatch')
    require(execution.get('status')=='executed_not_compared','execution summary status is not successful execution')
    expected_ids=[case['case_id'] for case in common['cases']]
    entries=execution.get('cases',[]);ids=[entry.get('case_id') for entry in entries]
    require(len(ids)==len(set(ids))==8 and set(ids)==set(expected_ids),'execution summary incomplete or duplicate cases')
    execution_cases={entry['case_id']:entry for entry in entries}
    for case_id in expected_ids:
        entry=execution_cases[case_id]
        require(entry.get('exit_code')==0 and entry.get('actual_candidate_code_executed') is True and
                entry.get('status')=='executed_not_compared','execution case failed or did not execute: '+case_id)
        output=args.results/(case_id+'.json')
        require(output.is_file() and run.digest(output)==entry.get('output_sha256'),
                'execution output SHA256 mismatch: '+case_id)
    # B0's original receipt predates the variant field. Accept only that exact
    # already-preserved receipt identity, never a generic missing-field default.
    provenance=json.loads((ROOT/'evidence/B1-preparation.json').read_text())
    if 'variant' not in execution:
        original=provenance['B0_preservation']
        require(args.variant=='B0' and run.digest(execution_path)==original['outputs']['summary.json'] and
                execution.get('binary_sha256')==original['binary_sha256'],'unbound legacy B0 variant')
    else:
        require(execution['variant']==args.variant,'run variant mismatch')
    adapter_dir=ROOT/('adapter-b1' if args.variant=='B1' else 'adapter')
    binary=ROOT/'target/debug'/('humentity-probe-b1' if args.variant=='B1' else 'humentity-probe')
    require(execution.get('binary_sha256')==run.digest(binary),'execution binary identity mismatch')
    require(execution.get('adapter_source_sha256')==run.digest(adapter_dir/'src/main.rs'),'execution adapter identity mismatch')
    for entry in entries:
        require(entry.get('command') and Path(entry['command'][0]).resolve()==binary.resolve(),'execution command binary mismatch')
    build_path=ROOT/'evidence'/('B1-adapter-build.json' if args.variant=='B1' else 'actual-adapter-build.json')
    build=json.loads(build_path.read_text())
    require(build.get('exit_code')==0 and build.get('candidate_adapter_linked') is True and
            build.get('manifest_sha256')==run.digest(adapter_dir/'Cargo.toml') and
            build.get('lock_sha256')==run.digest(adapter_dir/'Cargo.lock'),'execution build identity mismatch')
    ablation=provenance if args.variant=='B1' else None
    if ablation:
        patch=ablation['one_line_source_patch']
        require(run.digest(ROOT/'evidence/B1-threshold.patch')==ablation['patch_sha256'] and
                run.digest(ROOT/'derived'/patch['path'])==patch['before_sha256'] and
                run.digest(ROOT/'derived-b1'/patch['path'])==patch['after_sha256'],'B1 patch identity mismatch')
    matrix=common['transforms']['raw_obj_to_reference'];t=common['tolerances']
    receipts={entry['path']:entry for entry in common['files']};results=[]
    for case in common['cases']:
        path=args.results/(case['case_id']+'.json');candidate=json.loads(path.read_text())
        require=run.require
        require(candidate['actual_candidate_code_executed'] is True and
                candidate['common_manifest_sha256']==args.common_manifest_sha256 and candidate['case_id']==case['case_id'],
                'candidate identity/execution mismatch')
        expected_weights={}
        for parameter,value in case['recipe'].items():
            for sign,source in common['parameters'][parameter]['targets'].items():
                key=Path(source).name.removesuffix('.gz').removesuffix('.target')
                expected_weights[key]=max(0.,-value if sign=='decr' else value)
        require(candidate['target_weights']==expected_weights and candidate['candidate_to_raw_scale']==10.,'candidate recipe/scale mismatch')
        reference_path=STORE/case['reference_path']
        require(run.digest(reference_path)==receipts[case['reference_path']]['sha256'],'reference digest mismatch')
        reference=json.loads(reference_path.read_text());helpers=candidate['helper_positions_raw_basis']
        require(len(helpers)==len(reference['positions'])==19158,'helper count mismatch')
        measures={'helpers':metric(((i,transform(p,matrix),reference['positions'][i]) for i,p in enumerate(helpers)),t['body_max_component'])}
        for name,refname,tol in [('body','positions',t['body_max_component']),('garment','garment_positions',t['garment_max_component'])]:
            part=candidate['parts'][name];ids=part['source_vertex_ids'];positions=part['positions_raw_basis'];refs=reference[refname]
            require(len(ids)==len(positions) and all(0<=i<len(refs) for i in ids),'actual mesh source map mismatch')
            measured=metric(((source_id,transform(position,matrix),refs[source_id]) for source_id,position in zip(ids,positions)),tol)
            measured.update(mesh_vertices=len(ids),reference_source_vertices=len(refs),mapped_source_vertices=len(set(ids)),
                            missing_source_ids=sorted(set(range(len(refs)))-set(ids)),
                            joint_indices_present=part['joint_indices_present'],joint_weights_present=part['joint_weights_present'])
            measured['coverage_complete']=len(set(ids))==len(refs)
            measured['within_tolerance']=measured['within_tolerance'] and measured['coverage_complete']
            measures[name]=measured
        refs={b['name']:b for b in reference['bones']};bones=candidate['bones']
        require(set(refs)==set(bones) and len(bones)==53,'actual joint identity mismatch')
        measures['joint_heads']=metric(((name,transform(bones[name]['head_raw_basis'],matrix),refs[name]['head']) for name in sorted(bones)),t['joint_endpoint_max_component'])
        state={name:{'rest_matrix':bone['candidate_rest_matrix'],'inverse_bind_matrix':bone['candidate_inverse_bind_matrix']} for name,bone in bones.items()}
        require(all(len(v)==16 and all(math.isfinite(x) for x in v) for bone in state.values() for v in bone.values()),'invalid actual rest/IBM state')
        results.append({'case_id':case['case_id'],'recipe':case['recipe'],'candidate_output_sha256':run.digest(path),
                        'reference_sha256':run.digest(reference_path),'measures':measures,
                        'all_measured_geometry_within_tolerance':all(m['within_tolerance'] for m in measures.values()),
                        'rest_inverse_bind_state_recorded':True,'rest_inverse_bind_parity':'not_run: exact local-frame convention comparison not established',
                        'joint_tails':'not_run: candidate public API does not expose fitted tail positions',
                        'graphics':'not_run','poses':'not_run'})
    summary={'schema_version':1,'route_id':'source-runtime','sample_class':'makehuman-approved-sample',
             'common_manifest_sha256':args.common_manifest_sha256,'comparison_executed':True,
             'status':'within_numeric_tolerance' if all(c['all_measured_geometry_within_tolerance'] for c in results) else 'numeric_parity_failed',
             'cases':results,'variant':args.variant,'candidate_algorithms_changed':args.variant=='B1',
             'source_patch':ablation['one_line_source_patch'] if ablation else None,
             'source_patch_sha256':ablation['patch_sha256'] if ablation else None,
             'comparator_sha256':run.digest(Path(__file__)),
             'execution_summary_sha256':run.digest(execution_path),
             'execution_binary_sha256':execution['binary_sha256'],
             'execution_adapter_source_sha256':execution['adapter_source_sha256'],
             'execution_build_receipt_sha256':run.digest(build_path),
             'execution_adapter_manifest_sha256':build['manifest_sha256'],
             'execution_adapter_lock_sha256':build['lock_sha256'],
             'tolerances':t,'rest_inverse_bind_parity_executed':False,'joint_tail_parity_executed':False,
             'native_graphical_executed':False,'web_graphical_executed':False,'new_character_admitted':False}
    with args.out.open('x') as stream:json.dump(summary,stream,indent=2,allow_nan=False)
    print(summary['status'])
    for case in results:print(case['case_id'],{k:round(v['max_component_error_metres'],9) for k,v in case['measures'].items()})
    return 0 if summary['status']=='within_numeric_tolerance' else 3
if __name__=='__main__':
    try:raise SystemExit(main())
    except (run.Blocked,OSError,ValueError,KeyError) as error:print('NOT-RUN: '+str(error));raise SystemExit(2)
