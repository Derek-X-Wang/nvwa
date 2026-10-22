#!/usr/bin/env python3
"""One separately identified current19 offset attempt, after parent stage freeze.

The neutral geometry body remains literal experiment84 v3 math. Reuse its pure
helpers; current admission and publication are explicit, with no old auth override.
Importing this file never computes planes or generates a candidate.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import execution as x
from geometry_checks import e as engine

sys.path.insert(0,str(x.c.ROOT/'experiments/84-shoulder-rest-refit/authoring'))
import generate as reference

# Immutable pure functions and constants. Never call reference.admission/attempt.
positive_scales=reference.positive_scales
triangle_sources=reference.triangle_sources
interpolate=reference.interpolate
nearest_plane=reference.nearest_plane
diagnostic_value=reference.diagnostic_value
SAMPLES=reference.SAMPLES
MARGIN=reference.MARGIN
RESIDUAL_FLOOR=reference.RESIDUAL_FLOOR
MAX_DELTA=reference.MAX_DELTA
SUPPORT_SHA=reference.SUPPORT_SHA
need=reference.need
digest=reference.digest
norm=reference.norm
sub=reference.sub
dot=reference.dot
cross=reference.cross
scale=reference.scale
add=reference.add


def reserve_attempt(out,freeze):
    need(out.is_absolute() and out==out.resolve() and
         str(out)==freeze['attempt_directory'],'parent frozen attempt path differs')
    need(not out.exists(),'attempt directory exists; no second candidate')
    out.mkdir(parents=True,exist_ok=False)


def attempt(freeze_path,corpus,out):
    context=x.load_context(freeze_path,corpus,(x.AUTHORING,))
    freeze,policy,support=context.freeze,context.policy,context.support
    loaded,mapping,baseline=context.loaded,context.mapping,context.baseline
    reserve_attempt(out,freeze)  # Consume the one attempt BEFORE source-plane sampling.
    args=SimpleNamespace(policy=x.REFERENCE_POLICY_PATH,out=out)
    receipt={'schema_version':1,'kind':'nvwa85-current19-authoring-receipt-v1',
             'status':'AUTHORING_STARTED_ONE_ATTEMPT','candidate_id':freeze['candidate_id'],
             'candidate_count':1,'candidate_created':False,'cohort_kind':freeze['cohort_kind'],
             **{key:freeze[key] for key in ('cohort_manifest_sha256','source_inventory_sha256',
                'execution_files_sha256','reference_policy_sha256','support_sha256','baseline_geometry_sha256')},
             'independent_audit_sha256':freeze['independent_audit']['sha256'],
             'authoring_generator_sha256':digest(Path(__file__)),
             'attempt_directory':str(out),'scoring':'NOT-RUN'}
    def save():
        (out/'authoring-receipt.json').write_text(json.dumps(diagnostic_value(receipt),indent=2,allow_nan=False)+'\n')
    save()
    try:
        receipt['diagnostic']={'phase':'neutral_input_reconstruction','completed_source_planes':0,
                               'completed_sample_records':0,'expected_sample_records':581}
        receipt['neutral_inputs']={'recipe':{'torso_length':0,'jaw_drop':0,'all_other_parameters':0},
            'sources':{name:{'path':str(engine.SOURCE/name),'bytes':(engine.SOURCE/name).stat().st_size,
                             'sha256':digest(engine.SOURCE/name)}
                       for name in ('base.obj','garment/female_sportsuit01.obj','garment/female_sportsuit01.mhclo')},
            'fixed_policy_sha256':digest(args.policy),'support_sha256':SUPPORT_SHA}
        neutral=engine.raw_cage({'torso_length':0,'jaw_drop':0})
        receipt['neutral_inputs']['raw_neutral_helper_cage']=neutral
        scales=positive_scales(mapping,neutral)
        fitted,_=engine.fit_rows(mapping,neutral)
        anchor=loaded[-1][1];parts={p['name']:p for p in anchor['parts']}
        cloth_tris=triangle_sources(parts['garment']);body_tris=triangle_sources(parts['body'])
        engine.support_closure(parts['garment'],policy)
        ids=support['position_source_ids']
        receipt['neutral_inputs']['fitted_support_positions']={sid:fitted[sid] for sid in ids}
        receipt['diagnostic'].update(phase='support_radius',
            support_distances_m={sid:norm(sub(fitted[sid],fitted[847])) for sid in ids})
        need(all(norm(sub(fitted[s],fitted[847]))<=.070 for s in ids), 'neutral70mm support radius exceeded')
        smooth={i:[0.,0.,0.] for tri in body_tris for i in tri}
        for tri in body_tris:
            a,b,c=[neutral[i] for i in tri];normal=cross(sub(b,a),sub(c,a))
            for i in tri:smooth[i]=add(smooth[i],normal)
        smooth={i:scale(v,1/norm(v)) if norm(v)>0 else [0.,0.,0.] for i,v in smooth.items()}
        directions={i:[0.,0.,0.] for i in range(len(fitted))};source_planes={}
        receipt['source_planes']=source_planes
        for ring,weight in zip(support['position_graph_rings'],(1.,.75,.25)):
            for sid in ring:
                receipt['diagnostic']={'phase':'source_direction_nearest_plane','source_id':sid,
                    'point':fitted[sid],'feather_weight':weight,'completed_source_planes':len(source_planes),
                    'completed_sample_records':0,'expected_sample_records':581}
                plane=nearest_plane(fitted[sid],neutral,body_tris,smooth,receipt['diagnostic'])
                source_planes[sid]=plane;directions[sid]=scale(plane['normal'],weight)
        receipt['source_planes']=source_planes
        records=[];lower=0.;upper=math.inf
        receipt['planes']=records
        for ti in support['incident_triangles0']:
            tri=cloth_tris[ti]
            for bi,bary in enumerate(SAMPLES):
                p=interpolate([fitted[i] for i in tri],bary)
                direction=interpolate([directions[i] for i in tri],bary)
                receipt['diagnostic']={'phase':'sample_nearest_plane','triangle0':ti,'sample0':bi,
                    'sources':tri,'barycentric':bary,'point':p,'direction':direction,
                    'completed_source_planes':len(source_planes),'completed_sample_records':len(records),
                    'expected_sample_records':581,'lower_m':lower,'upper_m':upper}
                plane=nearest_plane(p,neutral,body_tris,smooth,receipt['diagnostic'])
                d=dot(sub(p,plane['point']),plane['normal']);a=dot(direction,plane['normal'])
                receipt['diagnostic'].update(phase='sample_interval_constraint',plane=plane,d_m=d,slope=a)
                need(math.isfinite(d) and math.isfinite(a), 'nonfinite plane constraint')
                if a>1e-12:lower=max(lower,(MARGIN-d)/a)
                elif a< -1e-12:upper=min(upper,(MARGIN-d)/a)
                else:need(d>=MARGIN, 'infeasible fixed/zero-slope sample')
                records.append({'triangle0':ti,'sample0':bi,'barycentric':bary,'sources':tri,
                                'd_m':d,'slope':a,'plane':plane})
        receipt['diagnostic']={'phase':'sample_coverage','completed_source_planes':len(source_planes),
                               'completed_sample_records':len(records),'expected_sample_records':581,
                               'lower_m':lower,'upper_m':upper}
        need(len(records)==581, 'sample coverage differs')
        for sid in ids:
            size=norm(directions[sid])
            if size:upper=min(upper,MAX_DELTA/size)
        receipt['interval']={'lower_m':lower,'upper_m':upper,'sample_records':len(records),
                             'source_planes':len(source_planes),'source_displacement_cap_m':MAX_DELTA}
        receipt['diagnostic']={'phase':'final_interval','lower_m':lower,'upper_m':upper,
                               'completed_sample_records':len(records),'expected_sample_records':581}
        need(math.isfinite(lower) and not math.isnan(upper) and 0<lower<=upper and upper>=0,
             'empty/nonpositive amplitude interval')
        amplitude=lower
        receipt['diagnostic'].update(phase='ideal_plane_residuals',amplitude_m=amplitude,
            failed_samples=[dict(r,ideal_side_m=r['d_m']+amplitude*r['slope']) for r in records
                            if not r['d_m']+amplitude*r['slope']>=MARGIN])
        need(all(r['d_m']+amplitude*r['slope']>=MARGIN for r in records), 'ideal plane residual failed')
        original=(engine.SOURCE/'garment/female_sportsuit01.mhclo').read_bytes()
        lines=mapping['lines'][:];edits=[]
        for sid in ids:
            row=mapping['rows'][sid]
            values=[engine.f32(o+amplitude*directions[sid][k]/scales[k]) for k,o in enumerate(row['offset'])]
            tokens=[format(v,'.9g') for v in values]
            need(all(engine.f32(float(t))==v for t,v in zip(tokens,values)), 'offset decimal roundtrip failed')
            matches=list(re.finditer(r'\S+',lines[row['line0']]))
            need(len(matches)==9, 'offset source line malformed')
            for k in (8,7,6):
                match=matches[k];line=lines[row['line0']]
                lines[row['line0']]=line[:match.start()]+tokens[k-6]+line[match.end():]
            edits.append({'source_id':sid,'old_offset':row['offset'],'new_offset_f32':values})
        candidate=''.join(lines).encode();_,new_mapping,changed=engine.validate_source_change(original,candidate,ids)
        realized,_=engine.fit_rows(new_mapping,neutral)
        for r in records:
            point=interpolate([realized[i] for i in r['sources']],r['barycentric'])
            r['realized_side_m']=dot(sub(point,r['plane']['point']),r['plane']['normal'])
            receipt['diagnostic']={'phase':'saved_text_plane_residual','sample':r,
                                   'completed_sample_records':len(records),'expected_sample_records':581,
                                   'required_side_floor_m':RESIDUAL_FLOOR,'lower_m':lower,'upper_m':upper}
            need(math.isfinite(r['realized_side_m']) and r['realized_side_m']>=RESIDUAL_FLOOR,
                 'saved-text realized sample below frozen0.9999mm floor')
        # Case checks enforce20mm before publication; never call score_case.
        case_checks=[]
        for name,snapshot in loaded:
            _,_,maximum,case_scales=engine.candidate_part(snapshot,mapping,new_mapping,policy)
            case_checks.append({'case':name,'max_rest_displacement_m':maximum,'scales':case_scales})
        path=args.out/'female_sportsuit01.mhclo';path.write_bytes(candidate)
        manifest={'schema_version':1,'kind':'nvwa85-current19-offset-asset-manifest-v1',
                  'status':'ONE_CANDIDATE_FROZEN_NOT_SCORED',
                  'candidate_id':freeze['candidate_id'],'candidate_count':1,'cohort_kind':freeze['cohort_kind'],
                  **{key:freeze[key] for key in ('cohort_manifest_sha256','source_inventory_sha256',
                    'execution_files_sha256','reference_policy_sha256','support_sha256')},
                  'original_obj_sha256':digest(engine.SOURCE/'garment/female_sportsuit01.obj'),
                  'candidate_sha256':digest(path),'mhclo_sha256':digest(path),
                  'original_mhclo_sha256':hashlib.sha256(original).hexdigest(),
                  'representation':'MHCLO offsets only; original OBJ bytes unchanged','changed_source_ids':changed}
        (args.out/'asset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        receipt.update(status='ONE_CANDIDATE_FROZEN_NOT_SCORED',candidate_created=True,
                       candidate_sha256=manifest['mhclo_sha256'],asset_manifest_sha256=digest(args.out/'asset-manifest.json'),amplitude_m=amplitude,lower_m=lower,upper_m=upper,
                       edits=edits,source_planes=source_planes,planes=records,case_displacement_checks=case_checks,
                       normals_tangents='NOT-RUN actual generated normal/tangent and candidate upload parity')
    except Exception as error:
        receipt.update(status='REJECT_AUTHORING_SINGLE_ATTEMPT',error=str(error))
        save()
        raise
    save()
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('freeze','corpus','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=attempt(args.freeze,args.corpus,args.out)
    print(json.dumps({key:result[key] for key in ('status','candidate_created','candidate_sha256')}))
