#!/usr/bin/env python3
"""Print a frozen two-parameter capture protocol; never send requests or launch UI."""
import json
from diagnose import CLIPS

requests = []
for torso in (-1, 0, 1):
    for jaw in (-1, 0, 1):
        for clip in CLIPS:
            for seconds in (0, 2, 4):
                requests.append({"request_id": f"e70-{len(requests) + 1:03}", "action": "sample", "torso_length": torso, "jaw_drop": jaw, "clip_id": clip, "seconds": seconds})
print(json.dumps({"scope": "planned54 held cases/platform; printed commands are NOT executed evidence", "requests": requests, "web_batches": [list(range(1, 28)), list(range(28, 55))], "batch_reason": "experiment60 sink admits32 captures per fresh directory;54 requires two fresh capture batches"}, indent=2))
