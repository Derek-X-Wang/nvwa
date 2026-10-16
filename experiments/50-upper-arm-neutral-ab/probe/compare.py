#!/usr/bin/env python3
"""Explicit new-artifact identity adapter to unchanged experiment49 assertions."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import candidate as c
sys.path.insert(0,str(c.ROOT/'experiments/49-runtime-pose-parity/offline'))
import compare as compare49

def compare(raw,variant):
    artifact=c.HERE/'artifacts'
    if variant=='candidate':
        work=artifact/'genuine44-upper-arm-neutral50.nvwa.json'
        asset=c.candidate_asset(artifact/'assets/generated/genuine44-upper-arm-neutral50.glb')
    else:
        work=c.ROOT/'experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json'
        asset=compare49.Asset()
    compare49.WORK_PATH=work;compare49.WORK_SHA=c.sha(work.read_bytes())
    result=compare49.compare(raw,asset)
    result['variant']=variant
    result['adapter']='Only explicit Work identity and candidate GLB hash differ; unchanged49 pose/skin thresholds and assertions'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--variant',choices=['baseline','candidate'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw=compare49.strict_loads(a.capture.read_text());result=compare(raw,a.variant);result['capture_sha256']=c.sha(a.capture.read_bytes())
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','platform','variant','max_errors']}))
if __name__=='__main__':main()
