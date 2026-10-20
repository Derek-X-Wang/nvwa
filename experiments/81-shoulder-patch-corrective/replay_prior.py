#!/usr/bin/env python3
"""Replay the original single-vertex rejection against immutable actual input."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/79-shoulder-pose-corrective'))
import evaluate_target as old
from derive_target import digest, need, f32, rotate, quaternion

def replay(retained):
    fresh = retained / 'h80proof-v1/combined/capture.json'
    target_path = retained / 'retained-shoulder-source80/one-target-v1/target.json'
    witness_path = retained / 'retained-shoulder-source80/one-target-evaluation-v1/fresh-new-pair-witness.json'
    need(digest(fresh) == old.FRESH_SHA, 'prior actual input changed')
    need(digest(target_path) == old.TARGET_SHA, 'prior target changed')
    f = json.loads(fresh.read_text())['frame']['full_base']
    cloth = next(p for p in f['parts'] if p['name'] == 'garment')
    body = next(p for p in f['parts'] if p['name'] == 'body')
    target = json.loads(target_path.read_text())
    w, _ = old.activation(f['bones'])
    q = quaternion(next(b for b in f['bones'] if b['name'] == 'clavicle_l')['canonical_posed'])
    delta = [f32(x*w) for x in rotate(q,target['delta_clavicle_m'])]
    corrected = copy.deepcopy(cloth)
    corrected['positions'] = [[f32(x+d) for x,d in zip(p,delta)] if sid == 847 else p[:] for sid,p in zip(cloth['source_ids'],cloth['positions'])]
    def triangle(part, tid):
        return [part['positions'][i] for i in part['indices'][3*tid:3*tid+3]]
    a, b = triangle(cloth,240), triangle(body,13661)
    c = triangle(corrected,240)
    need(not old.proper_cross(a,b), 'red baseline pair unexpectedly crosses')
    need(old.proper_cross(c,b), 'known rejected new pair escaped evaluator')
    # A false/disabled crossing predicate must make this actual witness red.
    witness = json.loads(witness_path.read_text())
    need(witness['garment_render_triangle0'] == 240 and witness['body_render_triangle0'] == 13661, 'prior pair identity changed')
    return {'status':'PASS_RED_CAPABLE_PRIOR_REJECTION_REPLAY','fresh_sha256':digest(fresh),'target_sha256':digest(target_path),'baseline_pair_crosses':False,'prior_corrected_pair_crosses':True,'pair':[240,13661], 'scope':'Actual retained baseline positions with analytical prior correction. Prior actual corrected upload corroboration is retained separately.'}

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    need(not a.out.exists(),'output already exists');a.out.parent.mkdir(parents=True,exist_ok=True)
    r=replay(a.retained);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
