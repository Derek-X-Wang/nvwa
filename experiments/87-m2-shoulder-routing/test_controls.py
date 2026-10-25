#!/usr/bin/env python3
"""Rejections at the constructor's source gate and actual four-slot seam."""
import copy
import json
from unittest.mock import patch
import candidate as c


def rejected(call, expected):
    try:
        call()
    except ValueError as error:
        c.require(expected in str(error), 'expected real rejection: '+str(error))
        return str(error)
    raise ValueError('negative control accepted')


def main():
    data = c.load()
    good = c.source_preflight(data)
    bad = copy.deepcopy(data)
    vertex = bad[1]['vertex_indices'][0]
    bad[5][vertex][0] += .001
    # A bad source must stop before reaching any new weight operation.
    with patch.object(c, 'four_slots', side_effect=RuntimeError('new weights reached')):
        reason = rejected(lambda: c.construct(bad), 'source-route reconstruction')
    names, slots = data[-2:]
    # The fixture-only cap must reject real discarded support, not renormalize it away.
    mass_reason = rejected(lambda: c.four_slots({'pelvis': .2, 'spine': .2, 'chest': .2, 'neck': .2, 'upper_arm.R': .2}, names, slots), 'discarded mass exceeds1%')
    invalid_reason = rejected(lambda: c.four_slots({'chest': float('nan')}, names, slots), 'finite positive')
    # Resolve actual node IDs back through the original skin slot table.
    joints, weights, reduction = c.four_slots({'chest': .75, 'upper_arm.R': .25}, names, slots)
    skin = data[6]
    actual = {data[0].nodes[skin['joints'][slot]]['name']: weight for slot, weight in zip(joints, weights) if weight}
    c.require(actual == {'chest': .75, 'upper_arm.R': .25}, 'node-to-skin-slot roundtrip')
    print(json.dumps({'status': 'PASS', 'source_preflight': {k:v for k,v in good.items() if k != 'samples'},
                      'rejected': [reason, mass_reason, invalid_reason], 'node_slot_roundtrip': actual}))


if __name__ == '__main__':
    main()
