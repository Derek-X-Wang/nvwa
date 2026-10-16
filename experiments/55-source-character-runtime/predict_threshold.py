#!/usr/bin/env python3
"""Predict B0 discrepancy solely from raw target rows discarded by the real loader."""
import gzip,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent;STORE=ROOT.parent.parent/'.work/character-approved-20261016'
SHA='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
import run
def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
def main():
    common=run.read_pinned_json(STORE/'common-sample.json',SHA,'common manifest');m=common['transforms']['raw_obj_to_reference']
    targets={};stats={}
    for parameter,spec in common['parameters'].items():
        for sign,path in spec['targets'].items():
            rows=[];total=0
            with gzip.open(STORE/path,'rt') as stream:
                for line in stream:
                    if not line.strip() or line.lstrip().startswith('#'):continue
                    columns=line.split();vertex=int(columns[0]);raw=[float(v) for v in columns[1:4]];total+=1
                    scaled=[f32(f32(v)*f32(.1)) for v in raw]
                    sq=f32(f32(f32(scaled[0]*scaled[0])+f32(scaled[1]*scaled[1]))+f32(scaled[2]*scaled[2]))
                    if sq<=f32(1e-6):rows.append((vertex,raw))
            targets[(parameter,sign)]=rows;stats[path]={'raw_rows':total,'dropped_rows':len(rows),'retained_rows':total-len(rows)}
    results=[]
    for case in common['cases']:
        candidate=json.loads((ROOT/'results/run3'/(case['case_id']+'.json')).read_text())
        reference=json.loads((STORE/case['reference_path']).read_text())
        predicted=[[0.,0.,0.] for _ in reference['positions']]
        for parameter,value in case['recipe'].items():
            sign='decr' if value<0 else 'incr';weight=abs(value)
            for vertex,raw in targets[(parameter,sign)]:
                for axis in range(3):predicted[vertex][axis]+=weight*sum(m[axis][c]*raw[c] for c in range(3))
        maximum=0.;observed_max=0.;prediction_max=0.;worst=None
        for i,(point,ref) in enumerate(zip(candidate['helper_positions_raw_basis'],reference['positions'])):
            actual=[sum(m[a][c]*point[c] for c in range(3))+m[a][3] for a in range(3)]
            observed=[ref[a]-actual[a] for a in range(3)]
            residual=max(abs(observed[a]-predicted[i][a]) for a in range(3))
            observed_max=max(observed_max,max(abs(x) for x in observed));prediction_max=max(prediction_max,max(abs(x) for x in predicted[i]))
            if worst is None or residual>maximum:maximum=residual;worst={'source_vertex_id':i,'observed_reference_minus_candidate':observed,'predicted_dropped_rows':predicted[i]}
        results.append({'case_id':case['case_id'],'observed_max_component_metres':observed_max,
                        'predicted_max_component_metres':prediction_max,'residual_max_component_metres':maximum,
                        'within_predeclared_tolerance':maximum<=common['tolerances']['body_max_component'],'worst_residual':worst})
    result={'schema_version':1,'common_manifest_sha256':SHA,'status':'body_helper_threshold_cause_supported' if all(c['within_predeclared_tolerance'] for c in results) else 'additional_body_helper_gap',
            'method':'f32 target parse ×f32(0.1), f32 squared length <=f32(1e-6); exact discarded raw rows weighted by the frozen recipe and declared basis',
            'scope':'Posthoc body/helper causal prediction only; no candidate algorithm changed and no garment propagation prediction',
            'target_rows':stats,'cases':results}
    with (ROOT/'evidence/threshold-prediction.json').open('x') as stream:json.dump(result,stream,indent=2)
    print(result['status']);print([(c['case_id'],c['residual_max_component_metres']) for c in results])
if __name__=='__main__':main()
