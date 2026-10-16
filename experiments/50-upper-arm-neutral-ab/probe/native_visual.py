#!/usr/bin/env python3
"""Prepare fresh product GPU screenshot exports using an existing probe stage.

No build or launch. The Studio's existing --capture path saves GPU readback;
this is not an operating-system screenshot or an undocumented CUA filesystem API.
"""
import argparse
import json
from pathlib import Path
import shlex
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import candidate as c

def prepare(stage):
    stage=stage.resolve();c.need(stage.is_relative_to(c.ROOT/'.work/m2-neutral-ab'),'owned stage')
    receipt=json.loads((stage/'staging.json').read_text());app=stage/'NvwaNeutralAB.app';mac=app/'Contents/MacOS'
    c.need(c.sha((mac/'probe-bin').read_bytes())==receipt['native_binary_sha256'],'same actual binary')
    q=lambda p:shlex.quote(str(p))
    outputs={name:stage/name for name in ['native-visual.json','native-canvas.png','native-visual.log','visual-exit-code.txt']}
    c.need(not any(p.exists() for p in outputs.values()),'fresh visual outputs')
    work=next((stage/'works').glob('*.nvwa.json'))
    command=[str(mac/'probe-bin'),'--work',str(work),'--capture',str(outputs['native-canvas.png']),'--smoke-seconds','5','--timeout','30']
    launcher=mac/'NvwaNeutralAB';backup=stage/'original-launcher.sh';c.need(not backup.exists(),'fresh launcher backup');backup.write_bytes(launcher.read_bytes())
    launcher.write_text('#!/bin/sh\nexport NVWA_ASSET_ROOT='+q(stage/'assets')+'\nexport NVWA_POSE_OUTPUT='+q(outputs['native-visual.json'])+'\n'+shlex.join(command)+' > '+q(outputs['native-visual.log'])+' 2>&1\nprobe_exit=$?\nprintf \'%s\\n\' "$probe_exit" > '+q(outputs['visual-exit-code.txt'])+'\nexit "$probe_exit"\n')
    result={'variant':receipt['variant'],'command':command,'original_launcher_sha256':c.sha(backup.read_bytes()),'visual_launcher_sha256':c.sha(launcher.read_bytes()),'binary_sha256':receipt['native_binary_sha256'],'capture_source':'existing Studio Screenshot::primary_window GPU readback/save_to_disk','formal_performance':'NOT-RUN'}
    (stage/'visual-preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(app)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',type=Path);a=p.parse_args();prepare(a.stage)
