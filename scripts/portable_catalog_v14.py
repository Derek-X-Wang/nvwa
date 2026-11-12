"""Authenticate the additive v14 asset check without weakening prior catalog pins."""

import hashlib
import json


UPPER_ARM_CHECKS = (
    "python3 -B scripts/test-upper-arm-muscle-v14.py\n"
    "python3 -B -O scripts/test-upper-arm-muscle-v14.py\n"
)
PREDECESSOR_SHA256 = "1a2719b28dad9a288f28e0ff5ba793120e6108217c564099d662fc1b104d7f14"


def predecessor_catalog(catalog):
    """Require the exact one-time trailing addition and restore the old bytes."""
    selected = [group for group in catalog if group.get("name") == "b1-inputs"]
    if len(selected) != 1:
        raise ValueError("required unique b1-inputs group")
    run = selected[0].get("run")
    if not isinstance(run, str) or not run.endswith(UPPER_ARM_CHECKS):
        raise ValueError("required exact v14 checks at end of b1-inputs")
    if run.count(UPPER_ARM_CHECKS) != 1:
        raise ValueError("duplicate v14 asset checks")
    previous = [dict(group, run=run[:-len(UPPER_ARM_CHECKS)])
                if group["name"] == "b1-inputs" else dict(group) for group in catalog]
    previous_bytes = (json.dumps(previous, indent=2) + "\n").encode()
    if hashlib.sha256(previous_bytes).hexdigest() != PREDECESSOR_SHA256:
        raise ValueError("v14 addition changed the authenticated predecessor catalog")
    return previous


def predecessor_bytes(catalog_bytes):
    catalog = json.loads(catalog_bytes)
    if (json.dumps(catalog, indent=2) + "\n").encode() != catalog_bytes:
        raise ValueError("portable catalog encoding changed")
    return (json.dumps(predecessor_catalog(catalog), indent=2) + "\n").encode()
