#!/usr/bin/env python3
"""Offline reproduction. No build, model, download, renderer or browser."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import candidate as c
import evaluate as e

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source-cache',type=Path);a=p.parse_args()
    out=a.output.resolve();c.need(out.is_relative_to(c.ROOT/'.work/m2-neutral-ab'),'owned private output directory');c.need(not out.exists(),'fresh output directory')
    subprocess.run([sys.executable,str(c.HERE/'evaluate.py'),'--output',str(out),'--surface'],check=True,cwd=c.ROOT)
    subprocess.run([sys.executable,str(c.HERE/'test_candidate.py')],check=True,cwd=c.ROOT)
    subprocess.run([sys.executable,'-O',str(c.HERE/'test_candidate.py')],check=True,cwd=c.ROOT)
    baseline=e.E.Asset();s=c.module('surface49_reproduce','experiments/49-runtime-pose-parity/offline/surface.py');s.Asset=lambda:baseline
    for name,keys in [('baseline-surface',e.KEYS),('baseline-static-neutral-surface',[0])]:
        if 'static' in name:baseline.channels={}
        (out/(name+'.json')).write_text(json.dumps(s.analyze(keys=keys,budget_seconds=60),indent=2)+'\n')
    (out/'candidate-static-neutral-surface.json').write_text(json.dumps(e.surface(c.HERE/'artifacts/assets/generated/genuine44-upper-arm-neutral50.glb',neutral=True),indent=2)+'\n')
    if a.source_cache:
        result=e.D.evaluate('native',a.source_cache)
        (out/'source-cache-audit.json').write_text(json.dumps({k:result[k] for k in ['source_text_audit','source_receipt_sha256','verified_url_byte_receipts','recorded_source_hashes','numerical_controls']},indent=2)+'\n')
    print(json.dumps({'status':'PASS','output':str(out),'runtime':'NOT-RUN: offline command never starts graphics'}))
if __name__=='__main__':main()
