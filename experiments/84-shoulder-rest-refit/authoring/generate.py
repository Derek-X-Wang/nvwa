#!/usr/bin/env python3
"""Exactly one gated neutral MHCLO-offset attempt. Importing does not generate it.

Root must freeze this source hash, policy, hybrid corpus and baseline preflight
before invoking. This program never calls a crossing/ROI candidate scorer.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'evaluation'))
import evaluate_rest as engine
sys.path.insert(0, str(ROOT / 'experiments/60-b1-continuous-motion'))
from geometry import closest_triangle, sub, dot, cross, norm, scale, add

SUPPORT_SHA = '66dd2cc157b92bf5651e3c1e88c33d3ce72e6f6ec9fed8694a27984970b05053'
SAMPLES = ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.),(.5,.5,0.),(0.,.5,.5),(.5,0.,.5),(1/3,1/3,1/3))
MARGIN = .001
RESIDUAL_FLOOR = MARGIN - 1e-7
MAX_DELTA = .020


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return engine.corpus.strict_load(path.read_bytes())


def interpolate(values, bary):
    return [sum(v[k]*w for v,w in zip(values,bary)) for k in range(3)]


def positive_scales(mapping, cage):
    for axis,key in enumerate('xyz'):
        lo,hi,reference = mapping['scales'][key]
        span = engine.f32(cage[hi][axis]-cage[lo][axis])
        need(math.isfinite(reference) and reference>0 and math.isfinite(span) and span>0,
             'nonpositive/nonfinite reference or span')
    _,scales = engine.fit_rows(mapping,cage)
    need(all(math.isfinite(v) and v>0 for v in scales), 'nonpositive/nonfinite offset scale')
    return scales


def triangle_sources(part):
    ids=part['source_ids']
    return [[ids[i] for i in part['indices'][k:k+3]] for k in range(0,len(part['indices']),3)]


def diagnostic_value(value):
    """Keep failure witnesses JSON-safe without changing any geometry arithmetic."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: diagnostic_value(item) for key,item in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic_value(item) for item in value]
    return value


def nearest_plane(point, body, triangles, smooth, diagnostic=None):
    # Exhaustive equal-distance tie enumeration; no result-dependent nearest fallback.
    nearest=math.inf; hits=[]
    for ti,tri in enumerate(triangles):
        a,b,c=[body[i] for i in tri]
        q,bary=closest_triangle(point,a,b,c)
        d2=dot(sub(point,q),sub(point,q))
        nearest=min(nearest,d2)
        hits.append((d2,ti,q,bary))
    selected=[]
    for d2,ti,q,bary in hits:
        if d2>nearest+1e-12:
            continue
        tri=triangles[ti];a,b,c=[body[i] for i in tri]
        normal=cross(sub(b,a),sub(c,a));area=norm(normal)
        if diagnostic is not None:
            diagnostic.update(nearest_distance_squared_m2=nearest,
                              plane_under_check={'body_triangle0':ti,'body_source_ids':tri,
                                'point':q,'body_barycentric':bary,'normal_unnormalized':normal,
                                'double_area_m2':area,'distance_squared_m2':d2},
                              completed_distance_ties=len(selected))
        need(area>1e-12 and bary is not None, 'nearest plane degenerate')
        normal=scale(normal,1/area)
        if diagnostic is not None:
            diagnostic['plane_under_check']['normal']=normal
            diagnostic['plane_under_check']['smooth_normal']=interpolate([smooth[i] for i in tri],bary)
        need(dot(normal,interpolate([smooth[i] for i in tri],bary))>0,
             'nearest winding disagrees with independently smoothed body normal')
        selected.append((d2,ti,q,normal,bary))
    selected.sort(key=lambda item:(item[0],item[1]))
    if diagnostic is not None:
        diagnostic.update(eligible_distance_ties=len(selected),nearest_ties=selected)
    need(bool(selected), 'nearest plane missing')
    chosen=selected[0]
    need(all(norm(sub(item[3],chosen[3]))<=1e-9 for item in selected), 'ambiguous nearest normal tie')
    return {'body_triangle0':chosen[1], 'point':chosen[2], 'normal':chosen[3],
            'body_barycentric':chosen[4], 'distance_ties':len(selected)}


def admission(args):
    freeze=load(args.freeze)
    engine.verify_execution(freeze)  # Authenticate all imported implementation before admission.
    need(freeze.get('status')=='FROZEN_FOR_AUTHORING' and freeze.get('candidate_count')==1,
         'root authoring GO missing')
    need(freeze.get('authoring_policy_version')==3, 'v3 policy freeze missing')
    need(freeze['authoring_generator_sha256']==digest(Path(__file__)), 'generator source changed')
    need(freeze['policy_sha256']==digest(args.policy), 'frozen policy changed')
    policy=load(args.policy)
    need(policy['baseline_rest_bound_m']==1e-7 and policy['baseline_posed_bound_m']==1e-5,
         'predeclared rest/posed reconstruction bound mismatch')
    need(policy['thresholds']==engine.THRESHOLDS, 'original scoring thresholds changed')
    for key in ('cohort_manifest_sha256','source_inventory_sha256'):
        need(policy[key]==freeze[key], 'policy/corpus freeze mismatch: '+key)
    need(freeze['baseline_preflight_sha256']==digest(args.preflight), 'baseline preflight receipt changed')
    receipt=load(args.preflight)
    need(receipt.get('status')=='PASS_BASELINE_PREFLIGHT_ONLY' and receipt.get('candidate_read') is False,
         'all19 original baseline preflight did not pass')
    for key in ('cohort_manifest_sha256','source_inventory_sha256'):
        need(receipt[key]==freeze[key], 'preflight input identity differs')
    need(receipt['execution_files_sha256']==freeze['execution_files_sha256'],
         'baseline preflight implementation freeze differs')
    need(len(receipt['baseline_reconstruction'])==19, 'baseline preflight missing slots')
    support=load(HERE/'support-proposal.json')
    need(digest(HERE/'support-proposal.json')==SUPPORT_SHA==freeze['support_sha256'], 'support freeze changed')
    for key in ('position_source_ids','incident_triangles0','normal_source_ids','normal_accumulation_triangles0'):
        need(policy[key]==support[key], 'policy/support sets differ: '+key)
    loaded=engine.authenticate_hybrid(args.corpus,args.fresh,freeze)
    mapping,baseline=engine.baseline_preflight(loaded)  # Recompute original only; no candidate score.
    for _,snapshot in loaded:
        cage=engine.source_rows(next(p for p in snapshot['parts'] if p['name']=='body'),'rest_positions')
        positive_scales(mapping,cage)
        for part in snapshot['parts']:
            for row in part['full_joint_influences']:
                need([j for j,w in row]==sorted(j for j,w in row), 'full-positive source bone row order differs')
    return freeze,policy,support,loaded,mapping,baseline


def attempt(args):
    freeze,policy,support,loaded,mapping,baseline=admission(args)
    # Persistent exclusive directory consumes this invocation's attempt before sampling.
    need(not args.out.exists(), 'attempt directory exists; no second candidate')
    args.out.mkdir(parents=True)
    receipt={'status':'AUTHORING_STARTED_ONE_ATTEMPT','candidate_count':1,'policy_sha256':digest(args.policy),
             'cohort_manifest_sha256':freeze['cohort_manifest_sha256'],
             'baseline_preflight_sha256':digest(args.preflight),'authoring_generator_sha256':digest(Path(__file__)),
             'support_sha256':SUPPORT_SHA,'execution_files_sha256':freeze['execution_files_sha256'],
             'scoring':'NOT-RUN','candidate_created':False}
    def save():
        (args.out/'authoring-receipt.json').write_text(json.dumps(diagnostic_value(receipt),indent=2,allow_nan=False)+'\n')
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
        manifest={'candidate_id':'nvwa-shoulder-rest-refit-v1','policy_sha256':digest(args.policy),
                  'original_obj_sha256':digest(engine.SOURCE/'garment/female_sportsuit01.obj'),
                  'mhclo_sha256':digest(path),'original_mhclo_sha256':hashlib.sha256(original).hexdigest(),
                  'representation':'MHCLO offsets only; original OBJ bytes unchanged','changed_source_ids':changed}
        (args.out/'asset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        receipt.update(status='ONE_CANDIDATE_FROZEN_NOT_SCORED',candidate_created=True,
                       candidate_sha256=manifest['mhclo_sha256'],amplitude_m=amplitude,lower_m=lower,upper_m=upper,
                       edits=edits,source_planes=source_planes,planes=records,case_displacement_checks=case_checks,
                       normals_tangents='NOT-RUN actual generated normal/tangent and candidate upload parity')
    except Exception as error:
        receipt.update(status='REJECT_AUTHORING_SINGLE_ATTEMPT',error=str(error))
        save()
        raise
    save()
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('freeze','policy','preflight','corpus','fresh','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=attempt(args)
    print(json.dumps({k:result[k] for k in ('status','candidate_created','candidate_sha256')}))
