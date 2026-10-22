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
import execution as x
import scoring
from geometry_checks import e

FRESH_SHA='fc4196e7f00fadf0dd2860418fd515ea0befd9de84e4dc0f527057dd5860aa67'
TARGET_SHA='f88a431ab6dfb2da3bd9a64852f0c490bafe29b21a86e86b98d063862ad00b51'
WITNESS_SHA='1188685316400b597130fa503704b44f6386cb50da5606c3a152be8f78aad2dc'
OBJ_SHA='f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9'
IDENTITY_KEYS=('candidate_id','cohort_kind','cohort_manifest_sha256',
               'source_inventory_sha256','execution_files_sha256',
               'reference_policy_sha256','support_sha256')
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
           receipt['kind']=='nvwa85-current19-authoring-receipt-v1' and
           type(manifest['schema_version']) is int and manifest['schema_version']==1 and
           manifest['kind']=='nvwa85-current19-offset-asset-manifest-v1',
           'wrong current19 candidate receipt schema')
    c.need(receipt['status']==manifest['status']=='ONE_CANDIDATE_FROZEN_NOT_SCORED' and
           receipt['candidate_created'] is True and type(receipt['candidate_count']) is int and
           receipt['candidate_count']==1 and type(manifest['candidate_count']) is int and
           manifest['candidate_count']==1 and receipt['scoring']=='NOT-RUN',
           'single unscored successful authoring receipt required')
    for key in IDENTITY_KEYS:
        c.need(receipt[key]==freeze[key] and manifest[key]==freeze[key],
               'candidate receipt identity differs: '+key)
    c.need(receipt['candidate_sha256']==manifest['candidate_sha256']==
           manifest['mhclo_sha256']==freeze['candidate_sha256'],
           'candidate receipt/hash crosslink differs')
    c.need(receipt['asset_manifest_sha256']==freeze['asset_manifest_sha256'] and
           receipt['baseline_geometry_sha256']==freeze['baseline_geometry_sha256'] and
           receipt['independent_audit_sha256']==freeze['independent_audit']['sha256'] and
           receipt['authoring_generator_sha256']==c.digest((c.HERE/'author.py').read_bytes()) and
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
    return new,changed


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
    return {'schema_version':1,'kind':'nvwa85-current19-position-evaluation-v1',
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
