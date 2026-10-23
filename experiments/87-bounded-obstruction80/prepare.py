#!/usr/bin/env python3
"""Write a DRAFT policy for root review/freeze. Never execute an attempt.

Root must supply exact prerequisite report plus its complete raw closure list,
review and authorization identities. This is local output only, not admission.
"""
import argparse
import json
from pathlib import Path
import obstruction as o

WORK = Path('/Users/derekxwang/.codex/work-products/nvwa')
DESIGN=WORK/'2026-10-22-contact80-budget116-design'
V4=WORK/'2026-10-22-shoulder-feature-v4'
OLD=WORK/'2026-10-21-current19-baseline'

def row(path):
    path=Path(path).resolve()
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':o.digest(raw)}

def prepare(prerequisites, supplemental, output):
    root=Path(__file__).resolve().parents[2]
    paths={
        'audit':WORK/'2026-10-22-surface80/blocker-audit-v2.json',
        'v4_receipt':V4/'one-feature-refit-v4/authoring-receipt.json',
        'v4_freeze':V4/'AUTHORING-FREEZE-v4.json',
        'v3_receipt':OLD/'one-rest-refit-v1/authoring-receipt.json',
        'support':root/'experiments/84-shoulder-rest-refit/authoring/support-proposal.json',
        'base':root/'assets/characters/mpfb-b1-v1/base.obj',
        'mhclo':root/'assets/characters/mpfb-b1-v1/garment/female_sportsuit01.mhclo',
        'garment_obj':root/'assets/characters/mpfb-b1-v1/garment/female_sportsuit01.obj',
        'design':DESIGN/'surface80/DESIGN.md',
        'rereview':DESIGN/'review/TARGETED-REREVIEW.md',
        'ledger':DESIGN/'surface80/BLOCKER-DISPOSITION.json',
        'prerequisites':Path(prerequisites),
    }
    inputs={key:row(path) for key,path in paths.items()}
    for key,sha in o.PINS.items():o.need(inputs[key]['sha256']==sha,'original pin differs '+key)
    extras=o.strict_load(Path(supplemental).read_bytes())
    o.need(type(extras) is list and bool(extras),'supplemental closure must be a nonempty list')
    o.validate_prerequisites(paths['prerequisites'].read_bytes(),extras,inputs)
    for item in extras:o.read_pinned(item)
    return {'kind':o.KIND,'attempt_limit':1,'mode':'rejection-only','time_limit_seconds':1200,
        'execution_files':o.inventory(Path(__file__).parent), 'inputs':inputs,'supplemental_inputs':extras,
        'exclusive_output':str(Path(output).resolve()),'old_v4_source_root':str(V4/'reviewed-source-v2'),
        'review_sha256':'ROOT_MUST_FREEZE_REVIEW_SHA256','authorization_sha256':'ROOT_MUST_FREEZE_AUTHORIZATION_SHA256',
        'technical_admission':{'domain':'frozen83-garment-audit/contact-real-body-unmasked',
            'frame':'same-neutral-source-cage','metric':'original-policy-source-meter',
            'correction':'only-frozen30-mapping-offsets','physical_correspondence':'UNKNOWN'}}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prerequisites',required=True);p.add_argument('--supplemental',required=True)
    p.add_argument('--attempt-output',required=True);p.add_argument('--draft-output',required=True)
    a=p.parse_args()
    result=prepare(a.prerequisites,a.supplemental,a.attempt_output)
    with Path(a.draft_output).open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
