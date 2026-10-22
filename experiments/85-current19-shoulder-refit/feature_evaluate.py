#!/usr/bin/env python3
"""Gated current19 position-only evaluation. Importing never reads a candidate.

Authenticate the prospective execution freeze and all19 actual baseline rows
before reading the one saved candidate. The old hybrid authenticator is unused.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import current19 as c
import feature_execution as x
import feature_policy as feature
import author as original_author
import scoring
from geometry_checks import e

FRESH_SHA='fc4196e7f00fadf0dd2860418fd515ea0befd9de84e4dc0f527057dd5860aa67'
TARGET_SHA='f88a431ab6dfb2da3bd9a64852f0c490bafe29b21a86e86b98d063862ad00b51'
WITNESS_SHA='1188685316400b597130fa503704b44f6386cb50da5606c3a152be8f78aad2dc'
OBJ_SHA='f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9'
IDENTITY_KEYS=('candidate_id','cohort_kind','cohort_manifest_sha256',
               'source_inventory_sha256','execution_files_sha256',
               'reference_policy_sha256','support_sha256','authoring_policy_version',
               'feature_policy_sha256','previous_rejection')
LIMIT='NOT-RUN actual generated normals/tangents, candidate upload, GPU, Web/CLI runtime parity, visual adoption'


def frozen_read(path,sha,label):
    c.need(type(sha) is str and re.fullmatch('[0-9a-f]{64}',sha),
           'missing/malformed frozen '+label+' hash')
    raw=path.read_bytes()
    c.need(c.digest(raw)==sha,'frozen '+label+' bytes differ')
    return raw


def require_baseline(context):
    c.need([name for name,_ in context.loaded]==list(c.CASES) and
           [row['case'] for row in context.baseline]==list(c.CASES) and
           all(row['status']=='PASS' for row in context.baseline),
           'all19 fresh baseline checks required before candidate read/score')


def authenticate_candidate(context,candidate_path,receipt_path,manifest_path):
    """Called only after load_context completes every original-baseline check."""
    require_baseline(context)
    freeze=context.freeze
    c.need(freeze['status']==x.SCORING,'current19 scoring freeze required')
    attempt=Path(freeze['attempt_directory'])
    for path,name in ((candidate_path,'female_sportsuit01.mhclo'),
                      (receipt_path,'authoring-receipt.json'),
                      (manifest_path,'asset-manifest.json')):
        c.need(path.is_absolute() and path==attempt/name and path.resolve()==attempt/name,
               'candidate/receipt outside exact frozen attempt directory')
    receipt=c.strict_load(frozen_read(receipt_path,freeze['authoring_receipt_sha256'],'authoring receipt'))
    manifest=c.strict_load(frozen_read(manifest_path,freeze['asset_manifest_sha256'],'asset manifest'))
    c.need(type(receipt['schema_version']) is int and receipt['schema_version']==1 and
           receipt['kind']=='nvwa85-current19-feature-authoring-receipt-v4' and
           type(manifest['schema_version']) is int and manifest['schema_version']==1 and
           manifest['kind']=='nvwa85-current19-feature-offset-asset-manifest-v4',
           'wrong current19 candidate receipt schema')
    c.need(receipt['status']==manifest['status']=='ONE_CANDIDATE_FROZEN_NOT_SCORED' and
           receipt['candidate_created'] is True and type(receipt['candidate_count']) is int and
           receipt['candidate_count']==1 and type(manifest['candidate_count']) is int and
           manifest['candidate_count']==1 and receipt['scoring']=='NOT-RUN',
           'single unscored successful authoring receipt required')
    for key in IDENTITY_KEYS:
        c.need(receipt[key]==freeze[key] and manifest[key]==freeze[key],
               'candidate receipt identity differs: '+key)
    for key in ('logical_sample_count','face_constraint_count'):
        c.need(key in manifest and key in receipt and
               type(manifest[key]) is int and type(receipt[key]) is int and
               manifest[key]==receipt[key] and manifest[key]>0,
               'manifest constraint count missing/invalid/differs: '+key)
    c.need(manifest['logical_sample_count']==feature.LOGICAL_SAMPLE_COUNT,
           'manifest logical sample count differs')
    c.need(receipt['candidate_sha256']==manifest['candidate_sha256']==
           manifest['mhclo_sha256']==freeze['candidate_sha256'],
           'candidate receipt/hash crosslink differs')
    c.need(receipt['asset_manifest_sha256']==freeze['asset_manifest_sha256'] and
           receipt['baseline_geometry_sha256']==freeze['baseline_geometry_sha256'] and
           receipt['independent_audit_sha256']==freeze['independent_audit']['sha256'] and
           receipt['authoring_generator_sha256']==c.digest((c.HERE/'feature_author.py').read_bytes()) and
           receipt['attempt_directory']==freeze['attempt_directory'],
           'authoring provenance crosslink differs')
    c.need(manifest['original_mhclo_sha256']==e.SOURCE_MHCLO_SHA and
           manifest['original_obj_sha256']==OBJ_SHA and
           manifest['representation']=='MHCLO offsets only; original OBJ bytes unchanged',
           'candidate original garment identity differs')
    original=(e.SOURCE/'garment/female_sportsuit01.mhclo').read_bytes()
    c.need(c.digest((e.SOURCE/'garment/female_sportsuit01.obj').read_bytes())==OBJ_SHA,
           'original garment topology bytes differ')
    raw=frozen_read(candidate_path,freeze['candidate_sha256'],'candidate source')
    old,new,changed=e.validate_source_change(original,raw,context.policy['position_source_ids'])
    c.need(old==context.mapping,'candidate source baseline mapping differs')
    c.need(manifest['changed_source_ids']==changed,'manifest/source changed offset IDs differ')
    checks=receipt['case_displacement_checks']
    c.need([row['case'] for row in checks]==list(c.CASES),
           'authoring displacement checks omit/reorder current19 slots')
    c.need(all(c.finite(row['max_rest_displacement_m']) and
               0<=row['max_rest_displacement_m']<=.020 for row in checks),
           'authoring displacement checks exceed20mm')
    validate_receipt_constraints(context,receipt,new)
    return new,changed


def validate_constraint_records(receipt,expected_samples,expected_planes,realized,trace):
    """Production admission seam: independent coverage and saved-byte geometry."""
    logical=receipt['logical_samples'];planes=receipt['planes']
    c.need(type(receipt['logical_sample_count']) is int and
           receipt['logical_sample_count']==feature.LOGICAL_SAMPLE_COUNT and
           type(receipt['face_constraint_count']) is int and
           receipt['face_constraint_count']==len(planes),'logical/face constraint count differs')
    c.need(len(expected_samples)==feature.LOGICAL_SAMPLE_COUNT,
           'independent logical sample coverage differs')
    feature.validate_constraint_coverage(logical,planes,expected_samples=expected_samples)
    c.need(len(expected_planes)==len(planes),'independent nearest face count differs')
    c.need(receipt['source_planes']=={str(sid):plane for sid,plane in trace['source_planes'].items()},
           'independent source feature planes differ')
    lower,upper=feature.amplitude_interval(expected_samples,expected_planes,trace['directions'],
                                          expected_samples=expected_samples)
    expected_interval={'lower_m':lower,'upper_m':upper,'logical_sample_count':len(expected_samples),
        'face_constraint_count':len(expected_planes),'source_planes':len(trace['source_planes']),
        'source_displacement_cap_m':feature.MAX_DELTA}
    c.need(receipt['interval']==expected_interval,'independent complete interval metadata differs')
    amplitude=receipt['amplitude_m']
    c.need(c.finite(amplitude) and 0<amplitude and
           c.finite(receipt['lower_m']) and c.finite(receipt['upper_m']) and
           amplitude==receipt['lower_m']==lower and receipt['upper_m']==upper,
           'single lower-endpoint amplitude identity differs')
    for record,expected in zip(planes,expected_planes):
        for key in ('logical_sample0','triangle0','sample0','barycentric','sources',
                    'body_triangle0','plane','d_m','slope'):
            c.need(record[key]==expected[key],'independent face constraint differs: '+key)
        c.need(c.finite(record['slope']) and
               record['d_m']+amplitude*record['slope']>=feature.MARGIN,
               'ideal face residual failed')
        point=original_author.interpolate([realized[i] for i in record['sources']],record['barycentric'])
        side=original_author.dot(original_author.sub(point,record['plane']['point']),
                                 record['plane']['normal'])
        c.need(c.finite(record['realized_side_m']) and record['realized_side_m']==side and
               side>=feature.RESIDUAL_FLOOR,'saved-text actual face residual differs/below floor')
    feature.validate_realized_constraints(logical,planes,realized,expected_samples=expected_samples)
    for sid in trace['source_ids']:
        old=trace['original_mapping']['rows'][sid]['offset']
        expected=[e.f32(offset+lower*trace['directions'][sid][axis]/trace['scales'][axis])
                  for axis,offset in enumerate(old)]
        c.need(trace['candidate_mapping']['rows'][sid]['offset']==expected,
               'saved candidate offset differs from original lower-endpoint feature displacement')


def validate_receipt_constraints(context,receipt,new_mapping):
    """Reconstruct expected logical samples and every nearest face from old inputs."""
    neutral=e.raw_cage({'torso_length':0,'jaw_drop':0})
    fitted,_=e.fit_rows(context.mapping,neutral)
    realized,_=e.fit_rows(new_mapping,neutral)
    scales=original_author.positive_scales(context.mapping,neutral)
    parts={part['name']:part for part in context.loaded[-1][1]['parts']}
    cloth=original_author.triangle_sources(parts['garment'])
    body=original_author.triangle_sources(parts['body'])
    smooth=feature.source_normals(neutral,body)
    directions={sid:[0.,0.,0.] for sid in range(len(fitted))};source_planes={}
    for ring,weight in zip(context.support['position_graph_rings'],(1.,.75,.25)):
        for sid in ring:
            plane=feature.feature_direction(fitted[sid],neutral,body,smooth)
            source_planes[sid]=plane
            directions[sid]=original_author.scale(plane['normal'],weight)
    expected_samples=[];expected_planes=[]
    for triangle0 in context.support['incident_triangles0']:
        sources=cloth[triangle0]
        for sample0,barycentric in enumerate(original_author.SAMPLES):
            point=original_author.interpolate([fitted[i] for i in sources],barycentric)
            direction=original_author.interpolate([directions[sid] for sid in sources],barycentric)
            faces=feature.nearest_faces(point,neutral,body,smooth)
            row={'logical_sample0':len(expected_samples),'triangle0':triangle0,'sample0':sample0,
                 'barycentric':list(barycentric),'sources':sources,
                 'nearest_face_ids':[face['body_triangle0'] for face in faces]}
            expected_samples.append(row)
            for face in faces:
                expected_planes.append({**{key:row[key] for key in
                    ('logical_sample0','triangle0','sample0','barycentric','sources')},
                    'body_triangle0':face['body_triangle0'],'plane':face,
                    'd_m':original_author.dot(original_author.sub(point,face['point']),face['normal']),
                    'slope':original_author.dot(direction,face['normal'])})
    trace={'source_planes':source_planes,'directions':directions,'scales':scales,
           'source_ids':context.support['position_source_ids'],'original_mapping':context.mapping,
           'candidate_mapping':new_mapping}
    validate_constraint_records(receipt,expected_samples,expected_planes,realized,trace)


def old_rejection_control(fresh,retained):
    """Keep the actual old pair and the production scorer's exact predicate seam."""
    frozen_read(fresh,FRESH_SHA,'original camera/control anchor')
    target=retained/'retained-shoulder-source80/one-target-v1/target.json'
    witness=retained/'retained-shoulder-source80/one-target-evaluation-v1/fresh-new-pair-witness.json'
    frozen_read(target,TARGET_SHA,'old rejected target')
    frozen_read(witness,WITNESS_SHA,'old rejected pair witness')
    # The unchanged function calls the SAME kernels.crossing_pairs as score_case.
    # Replacing proper_cross by false must make this control throw, never pass.
    return e.old_rejection_control(fresh,retained)


def evaluate(context,new_mapping,changed,fresh,retained):
    require_baseline(context)
    frozen_read(fresh,FRESH_SHA,'original camera/control anchor')
    cam,fr=e.camera_for(fresh)
    control=old_rejection_control(fresh,retained)
    results=[]
    for name,snapshot in context.loaded:
        candidate,affected,maximum,scales=e.candidate_part(
            snapshot,context.mapping,new_mapping,context.policy)
        results.append(scoring.score_case(name,snapshot,candidate,affected,maximum,scales,cam,fr))
    c.need([row['case'] for row in results]==list(c.CASES),'scorer omitted/reordered current19 slots')
    failures=[{'case':row['case'],'failures':row['failures']} for row in results if row['failures']]
    freeze=context.freeze
    return {'schema_version':1,'kind':'nvwa85-current19-feature-position-evaluation-v4',
            'status':'REJECT' if failures else 'POSITION_ONLY_OFFLINE_PASS_RUNTIME_PARITY_NOT_RUN',
            **{key:freeze[key] for key in IDENTITY_KEYS},
            **{key:freeze[key] for key in ('candidate_sha256','authoring_receipt_sha256',
                                        'asset_manifest_sha256','baseline_geometry_sha256')},
            'historical18':'MISSING / NOT-RUN exact historical raw replay',
            'candidate_read':True,'quality_acceptance':False,
            'baseline_reconstruction':context.baseline,'changed_source_offsets':changed,
            'old_rejection_control':control,'results':results,'failures':failures,
            'normals_tangents_actual_upload_GPU_Web_CLI':LIMIT,
            'scope':'Current19 actual native baseline plus analytical source-refit/full-positive LBS positions only.'}


def run(args):
    c.need(not args.out.exists(),'unique evaluation output already exists')
    # No candidate/receipt/manifest bytes before full19 reauthentication/preflight.
    context=x.load_context(args.freeze,args.corpus,(x.SCORING,))
    new,changed=authenticate_candidate(context,args.candidate,args.authoring_receipt,args.asset_manifest)
    report=evaluate(context,new,changed,args.fresh,args.retained)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation also protects the report against concurrent overwrites.
    with args.out.open('x') as stream:
        stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 3 if report['failures'] else 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('freeze','corpus','candidate','authoring-receipt','asset-manifest','fresh','retained','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    try:
        return run(parser.parse_args(argv))
    except (KeyError,TypeError,ValueError,OSError,IndexError,ArithmeticError) as error:
        print('NOT-RUN:',error,file=sys.stderr)
        return 2


if __name__=='__main__':sys.exit(main())
