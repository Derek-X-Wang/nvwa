#!/usr/bin/env python3
"""Print exact root-owned Studio sample commands. Does not send commands or use GUI."""
import json
from checker import CLIPS
for torso in [0.,-1.,1.]:
 for clip in CLIPS:
  for t in ([0.,1.,2.,3.,4.] if torso==0 else [2.]):
   print(json.dumps({'request_id':f't{torso:+g}_{clip}_{int(t)}'.replace('+','p').replace('-','m'),'action':'sample','torso_length':torso,'jaw_drop':0.,'clip_id':clip,'seconds':t}))
