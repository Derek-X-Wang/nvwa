"""Exercise the CI-called source gate in disposable repository copies."""
import hashlib
import importlib.util
import itertools
import json
import math
import os
import re
import signal
import stat
import time
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
SPEC = importlib.util.spec_from_file_location('eye73_frozen_gate_controls', EXP / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
PRODUCT = 'hair79-short01-product-v1'
ORIGINAL = 'original-frozen309'
CLOSEOUT = 'character-stage-closeout-v1'
LATEST = CONTEXT.RIG119_CONTEXT


PROTOCOL = 'nvwa73-source-gate-v1'


def assert_gate_result(test, result, rejects, expected_context):
    """The one consumer for actual CLI results and parser-only controls."""
    output = result.stdout + result.stderr
    test.assertEqual(result.stderr, '', output)
    text = result.stdout
    test.assertTrue(text.endswith('\n') and text.count('\n') == 1, output)
    body = text[:-1]
    test.assertTrue(body.startswith('{') and body.endswith('}'), output)
    try:
        record = json.loads(body)
    except json.JSONDecodeError as error:
        test.fail(f'invalid source-gate JSON: {error}: {output}')
    test.assertIs(type(record), dict, output)
    field = 'message' if rejects else 'context'
    test.assertEqual(set(record), {'protocol', 'outcome', field}, output)
    for value in record.values():
        test.assertIs(type(value), str, output)
    test.assertEqual(record['protocol'], PROTOCOL, output)
    test.assertEqual(record['outcome'], 'rejected' if rejects else 'accepted', output)
    test.assertEqual(result.returncode, 2 if rejects else 0, output)
    if rejects:
        test.assertTrue(record['message'], output)
        test.assertIn('FROZEN-INPUTS.json', record['message'], output)
    else:
        test.assertEqual(record['context'], expected_context, output)
    return record


# Frozen P001-P128, in order. Synthetic outputs exercise only the consumer above.
# id, requested rejection, fixture context, returncode, stdout, stderr, must fail
PARSER_CONTROLS = [
    ('P001', False, 'original-frozen309', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"original-frozen309"}\n', '', False),
    ('P002', False, 'character-stage-closeout-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"character-stage-closeout-v1"}\n', '', False),
    ('P003', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', False),
    ('P004', False, 'rig119-unit-handoff-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"rig119-unit-handoff-v1"}\n', '', False),
    ('P005', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', False),
    ('P006', False, 'hair79-short01-product-v1', 0, '', '', True),
    ('P007', False, 'hair79-short01-product-v1', 0, '\n', '', True),
    ('P008', False, 'hair79-short01-product-v1', 0, '  \n', '', True),
    ('P009', False, 'hair79-short01-product-v1', 0, 'not-json\n', '', True),
    ('P010', False, 'hair79-short01-product-v1', 0, '{"protocol":\n', '', True),
    ('P011', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}', '', True),
    ('P012', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P013', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n\n', '', True),
    ('P014', False, 'hair79-short01-product-v1', 0, '\n{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P015', False, 'hair79-short01-product-v1', 0, 'trace\n{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P016', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\nextra', '', True),
    ('P017', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P018', False, 'hair79-short01-product-v1', 0, ' {"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P019', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"} \n', '', True),
    ('P020', False, 'hair79-short01-product-v1', 0, '{\n"protocol":"nvwa73-source-gate-v1"}\n', '', True),
    ('P021', False, 'hair79-short01-product-v1', 0, 'null\n', '', True),
    ('P022', False, 'hair79-short01-product-v1', 0, 'true\n', '', True),
    ('P023', False, 'hair79-short01-product-v1', 0, '0\n', '', True),
    ('P024', False, 'hair79-short01-product-v1', 0, '1.5\n', '', True),
    ('P025', False, 'hair79-short01-product-v1', 0, '[]\n', '', True),
    ('P026', False, 'hair79-short01-product-v1', 0, '["x"]\n', '', True),
    ('P027', False, 'hair79-short01-product-v1', 0, '"accepted"\n', '', True),
    ('P028', False, 'hair79-short01-product-v1', 0, '{"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P029', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","context":"hair79-short01-product-v1"}\n', '', True),
    ('P030', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted"}\n', '', True),
    ('P031', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1","extra":1}\n', '', True),
    ('P032', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1","schema_version":1}\n', '', True),
    ('P033', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1","version":1}\n', '', True),
    ('P034', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1","message":1}\n', '', True),
    ('P035', False, 'hair79-short01-product-v1', 0, '{"protocol":null,"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P036', False, 'hair79-short01-product-v1', 0, '{"protocol":true,"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P037', False, 'hair79-short01-product-v1', 0, '{"protocol":0,"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P038', False, 'hair79-short01-product-v1', 0, '{"protocol":1.5,"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P039', False, 'hair79-short01-product-v1', 0, '{"protocol":[],"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P040', False, 'hair79-short01-product-v1', 0, '{"protocol":{},"outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P041', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":null,"context":"hair79-short01-product-v1"}\n', '', True),
    ('P042', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":true,"context":"hair79-short01-product-v1"}\n', '', True),
    ('P043', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":0,"context":"hair79-short01-product-v1"}\n', '', True),
    ('P044', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":1.5,"context":"hair79-short01-product-v1"}\n', '', True),
    ('P045', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":[],"context":"hair79-short01-product-v1"}\n', '', True),
    ('P046', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":{},"context":"hair79-short01-product-v1"}\n', '', True),
    ('P047', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":null}\n', '', True),
    ('P048', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":true}\n', '', True),
    ('P049', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":0}\n', '', True),
    ('P050', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":1.5}\n', '', True),
    ('P051', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":[]}\n', '', True),
    ('P052', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":{}}\n', '', True),
    ('P053', False, 'hair79-short01-product-v1', 0, '{"protocol":"","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P054', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v2","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P055', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P056', False, 'hair79-short01-product-v1', 0, '{"protocol":"other","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P057', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"","context":"hair79-short01-product-v1"}\n', '', True),
    ('P058', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"unknown","context":"hair79-short01-product-v1"}\n', '', True),
    ('P059', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","context":"hair79-short01-product-v1"}\n', '', True),
    ('P060', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', 'diagnostic\n', True),
    ('P061', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '\n', True),
    ('P062', False, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P063', False, 'hair79-short01-product-v1', 1, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P064', False, 'hair79-short01-product-v1', 64, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P065', False, 'hair79-short01-product-v1', -15, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P066', True, 'hair79-short01-product-v1', 2, '{"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P067', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P068', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected"}\n', '', True),
    ('P069', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection","extra":1}\n', '', True),
    ('P070', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection","schema_version":1}\n', '', True),
    ('P071', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection","version":1}\n', '', True),
    ('P072', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection","context":1}\n', '', True),
    ('P073', True, 'hair79-short01-product-v1', 2, '{"protocol":null,"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P074', True, 'hair79-short01-product-v1', 2, '{"protocol":true,"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P075', True, 'hair79-short01-product-v1', 2, '{"protocol":0,"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P076', True, 'hair79-short01-product-v1', 2, '{"protocol":1.5,"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P077', True, 'hair79-short01-product-v1', 2, '{"protocol":[],"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P078', True, 'hair79-short01-product-v1', 2, '{"protocol":{},"outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P079', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":null,"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P080', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":true,"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P081', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":0,"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P082', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":1.5,"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P083', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":[],"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P084', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":{},"message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P085', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":null}\n', '', True),
    ('P086', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":true}\n', '', True),
    ('P087', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":0}\n', '', True),
    ('P088', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":1.5}\n', '', True),
    ('P089', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":[]}\n', '', True),
    ('P090', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":{}}\n', '', True),
    ('P091', True, 'hair79-short01-product-v1', 2, '{"protocol":"","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P092', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v2","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P093', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P094', True, 'hair79-short01-product-v1', 2, '{"protocol":"other","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P095', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P096', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"unknown","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P097', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P098', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', 'diagnostic\n', True),
    ('P099', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '\n', True),
    ('P100', True, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P101', True, 'hair79-short01-product-v1', 1, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P102', True, 'hair79-short01-product-v1', 64, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P103', True, 'hair79-short01-product-v1', -15, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P104', False, 'character-stage-closeout-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"original-frozen309"}\n', '', True),
    ('P105', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"original-frozen309"}\n', '', True),
    ('P106', False, 'rig119-unit-handoff-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"original-frozen309"}\n', '', True),
    ('P107', False, 'original-frozen309', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"character-stage-closeout-v1"}\n', '', True),
    ('P108', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"character-stage-closeout-v1"}\n', '', True),
    ('P109', False, 'rig119-unit-handoff-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"character-stage-closeout-v1"}\n', '', True),
    ('P110', False, 'original-frozen309', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P111', False, 'character-stage-closeout-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P112', False, 'rig119-unit-handoff-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P113', False, 'original-frozen309', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"rig119-unit-handoff-v1"}\n', '', True),
    ('P114', False, 'character-stage-closeout-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"rig119-unit-handoff-v1"}\n', '', True),
    ('P115', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"rig119-unit-handoff-v1"}\n', '', True),
    ('P116', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":""}\n', '', True),
    ('P117', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"unknown-context"}\n', '', True),
    ('P118', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":""}\n', '', True),
    ('P119', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":" "}\n', '', True),
    ('P120', True, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"no required marker"}\n', '', True),
    ('P121', True, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P122', False, 'hair79-short01-product-v1', 2, '{"protocol":"nvwa73-source-gate-v1","outcome":"rejected","message":"FROZEN-INPUTS.json source context: controlled rejection"}\n', '', True),
    ('P123', True, 'hair79-short01-product-v1', 1, '', 'Traceback (most recent call last):\nValueError: CONTROL_PLAIN_VALUEERROR\n', True),
    ('P124', False, 'hair79-short01-product-v1', 0, '{"protocol":"ignored","protocol":"nvwa73-source-gate-v1","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', False),
    ('P125', False, 'hair79-short01-product-v1', 0, '{"protocol":"nvwa73-source-gate-v1","protocol":"wrong","outcome":"accepted","context":"hair79-short01-product-v1"}\n', '', True),
    ('P126', False, 'hair79-short01-product-v1', 0, '{}\n', '', True),
    ('P127', False, 'hair79-short01-product-v1', 0, '{"protocol":}\n', '', True),
    ('P128', False, 'hair79-short01-product-v1', 0, '{"protocol":"unterminated}\n', '', True),
]


class FrozenInputGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate_calls = {'positive': 0, 'rejection': 0}
        cls.launch_attempts = cls.started = cls.returned = cls.nonsignalled = 0
        cls.signalled = cls.timeouts = 0
        cls.adapter_starts = {'new': 0, 'legacy': 0}
        cls.control_outcomes = {}
        cls.gate_return_codes = {}
        cls.scratch = tempfile.TemporaryDirectory(prefix='nvwa73-freeze-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        cls.exp = cls.root / 'experiments/73-high-poly-eyes'
        cls.exp.mkdir(parents=True)
        cls.raw = (EXP / 'FROZEN-INPUTS.json').read_bytes()
        cls.inputs = json.loads(cls.raw)
        # Copy the real inputs, never link them: mutations must not reach the repo.
        for name in list(cls.inputs) + list(CONTEXT.RIG119_SUPPLEMENTS):
            destination = cls.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        for name in ['test_prepare.py', 'cpu_probe.py', 'frozen_context.py', 'source_gate.py',
                     'source-context-closeout-v1.json', 'source-context-hair79-short01-v1.json', CONTEXT.RIG119_CONTEXT_NAME]:
            shutil.copyfile(EXP / name, cls.exp / name)
        shutil.copytree(EXP / 'fixtures', cls.exp / 'fixtures')
        shutil.copytree(EXP / 'compat-fixtures-rig119', cls.exp / 'compat-fixtures-rig119')
        cls.contexts = CONTEXT.source_contexts(EXP, cls.raw, cls.inputs)
        cls.all_contexts = CONTEXT.source_contexts(EXP, cls.raw, cls.inputs, include_current=True)
        cls.maps = dict(cls.all_contexts)
        historical = CONTEXT.historical_sources(EXP, cls.contexts)
        cls.original = historical[ORIGINAL]
        cls.current = {name: (cls.root / name).read_bytes() for name in cls.original}
        cls.latest = dict(cls.current)
        cls.latest.update({name: (cls.root / name).read_bytes() for name in CONTEXT.RIG119_SUPPLEMENTS})
        # PRODUCT keeps its original historical short01 meaning. The shared
        # adapter bytes now come from their separate authenticated local archive.
        cls.current.update(historical[PRODUCT])
        cls.closeout = dict(cls.original)
        closeout = json.loads((EXP / 'source-context-closeout-v1.json').read_bytes())
        for name, item in closeout['overrides'].items():
            raw = historical[CLOSEOUT].get(name, (cls.root / name).read_bytes())
            if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != item:
                raise ValueError('archived closeout fixture does not match old pin: ' + name)
            cls.closeout[name] = raw
        cls.snapshots = {ORIGINAL: cls.original, CLOSEOUT: cls.closeout, PRODUCT: cls.current, LATEST: cls.latest}
        for context, snapshot in cls.snapshots.items():
            for name, raw in snapshot.items():
                if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != cls.maps[context][name]:
                    raise ValueError('complete source fixture mismatch: ' + context + ' ' + name)
        for name, raw in cls.current.items():
            (cls.root / name).write_bytes(raw)
        for name in CONTEXT.RIG119_SUPPLEMENTS:
            (cls.root / name).unlink()

    def setUp(self):
        # Verification never carries across test methods. Every method starts
        # with a fresh actual gate green on the same isolated source copy.
        self.method_calls = 0
        self.fixture_context = PRODUCT
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    @classmethod
    def tearDownClass(cls):
        # Observations only: count actual completed children, without replacing
        # any case/assertion or making timing/call-count estimates into gates.
        print(json.dumps({'source_gate_subprocess_observations': {
            'mode': 'optimized' if sys.flags.optimize else 'normal',
            'requested_outcomes': cls.gate_calls,
            'actual_return_codes': cls.gate_return_codes,
            'completed_calls': cls.returned,
            'attempted_calls': cls.launch_attempts,
            'confirmed_starts': cls.started,
            'nonsignalled_returns': cls.nonsignalled,
            'signal_returns': cls.signalled,
            'timeouts': cls.timeouts,
            'adapter_starts': cls.adapter_starts,
            'direct_control_outcomes': cls.control_outcomes,
        }}, sort_keys=True), file=sys.stderr)

    def write_context(self, name):
        self.fixture_context = name
        for relative in CONTEXT.RIG119_SUPPLEMENTS:
            path = self.root / relative
            if path.exists() or path.is_symlink():
                path.unlink()
        for relative, raw in self.snapshots[name].items():
            (self.root / relative).write_bytes(raw)

    def event(self, phase, **fields):
        print(json.dumps({'source_gate_event': {
            'mode': 'optimized' if sys.flags.optimize else 'normal',
            'method': self._testMethodName, 'phase': phase, **fields,
        }}, sort_keys=True), file=sys.stderr, flush=True)

    def launch(self, local_id, outcome, adapter='new', extra_args=(), expected_context=None):
        # A local observer can pass its existing whole-group deadline. This is
        # diagnostic trial instrumentation, not a change to the CI clock.
        if local_id == 'T01' and 'NVWA73_LOCAL_GROUP_DEADLINE' in os.environ:
            try:
                deadline = float(os.environ['NVWA73_LOCAL_GROUP_DEADLINE'])
            except ValueError:
                self.fail('invalid local group deadline; STOP before T01')
            self.assertTrue(math.isfinite(deadline) and deadline - time.monotonic() >= 40,
                            'insufficient local group budget for T01 + cleanup; STOP')
        command = [sys.executable, '-B']
        if sys.flags.optimize:
            command.append('-O')
        if adapter == 'legacy':
            command += [str(self.exp / 'test_prepare.py'),
                        'SourceContract.test_frozen_source_inputs', '-v']
        else:
            command += [str(self.exp / 'source_gate.py')]
        command += list(extra_args)
        cls = type(self)
        cls.launch_attempts += 1
        ordinal = cls.launch_attempts
        mode = 'optimized' if sys.flags.optimize else 'normal'
        fields = {'id': f'{mode}/{self._testMethodName}/{local_id}',
                  'ordinal_in_mode': ordinal, 'adapter': adapter,
                  'requested_outcome': outcome,
                  'expected_context': expected_context if outcome == 'positive' else None,
                  'consumer_expected_context_argument':
                      ('legacy authentic-output adapter; no JSON context field' if adapter == 'legacy'
                       else expected_context if expected_context is not None else self.fixture_context),
                  'written_fixture_base_context': self.fixture_context}
        self.event('attempt', **fields, argv=command, cwd=str(self.root), timeout=30)
        try:
            result = subprocess.run(command, cwd=self.root, capture_output=True,
                                    text=True, timeout=30)
        except subprocess.TimeoutExpired as error:
            cls.started += 1
            cls.adapter_starts[adapter] += 1
            cls.timeouts += 1
            cls.control_outcomes[outcome] = cls.control_outcomes.get(outcome, 0) + 1
            self.event('timeout', **fields,
                       stdout=error.stdout.decode('ascii') if isinstance(error.stdout, bytes) else error.stdout,
                       stderr=error.stderr.decode('ascii') if isinstance(error.stderr, bytes) else error.stderr)
            raise
        except OSError as error:
            self.event('launch_failure', **fields, error=str(error))
            raise
        cls.started += 1
        cls.adapter_starts[adapter] += 1
        cls.returned += 1
        if result.returncode < 0:
            cls.signalled += 1
        else:
            cls.nonsignalled += 1
        code = str(result.returncode)
        cls.gate_return_codes[code] = cls.gate_return_codes.get(code, 0) + 1
        if local_id.startswith('C') or local_id == 'SETUP':
            cls.gate_calls['rejection' if outcome == 'expected_rejection' else 'positive'] += 1
        else:
            cls.control_outcomes[outcome] = cls.control_outcomes.get(outcome, 0) + 1
        self.event('return', **fields, returncode=result.returncode,
                   stdout=result.stdout, stderr=result.stderr)
        return result

    def gate(self, raw, rejects, expected_context=None):
        manifest = self.exp / 'FROZEN-INPUTS.json'
        if raw is None:
            manifest.unlink(missing_ok=True)
        else:
            manifest.write_bytes(raw)
        self.method_calls += 1
        local_id = ('SETUP' if self._testMethodName == 'test_z_protocol_and_legacy_contract_controls'
                    else f'C{self.method_calls:03d}')
        consumer_context = self.fixture_context if expected_context is None else expected_context
        result = self.launch(local_id, 'expected_rejection' if rejects else 'positive',
                             expected_context=consumer_context)
        assert_gate_result(self, result, rejects, consumer_context)

    def legacy_result(self, result, rejects=False, error=None, import_failure=False):
        output = result.stdout + result.stderr
        if import_failure:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn('ModuleNotFoundError', output, output)
            self.assertIn('frozen_context', output, output)
            self.assertIn('Traceback (most recent call last)', output, output)
            return
        self.assertIn('Ran 1 test', output, output)
        self.assertNotIn('skipped', output, output)
        if error is not None:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn('ERROR', output, output)
            self.assertIn('FAILED (errors=1)', output, output)
            self.assertIn(error, output, output)
        else:
            self.assertNotIn('ERROR', output, output)
            if rejects:
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn('FAILED (failures=1)', output, output)
                self.assertIn('FROZEN-INPUTS.json', output, output)
            else:
                self.assertEqual(result.returncode, 0, output)
                self.assertIn('\nOK\n', output, output)

    def test_valid_current_manifest(self):
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_exact_original_context_accepts_at_actual_called_gate_without_git_history(self):
        try:
            self.write_context(ORIGINAL)
            self.gate(self.raw, rejects=False, expected_context=ORIGINAL)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_exact_closeout_context_accepts_at_actual_called_gate_without_git_history(self):
        try:
            self.write_context(CLOSEOUT)
            self.gate(self.raw, rejects=False, expected_context=CLOSEOUT)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_exact_rig119_context_accepts_and_restores_at_actual_called_gate(self):
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)
        try:
            self.write_context(LATEST)
            self.gate(self.raw, rejects=False, expected_context=LATEST)
            self.assertEqual(len(self.maps[LATEST]), 311)
            self.assertEqual(CONTEXT.select_context(self.maps[LATEST], self.all_contexts)[0], LATEST)
            for name in self.maps[LATEST]:
                incomplete = dict(self.maps[LATEST])
                incomplete.pop(name)
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(incomplete, self.all_contexts)
            with self.assertRaisesRegex(ValueError, 'source context'):
                CONTEXT.select_context(dict(self.maps[LATEST], unreviewed={'bytes': 0, 'sha256': '0' * 64}), self.all_contexts)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_rig119_module_and_v3_mutation_missing_symlink_reject_and_restore(self):
        try:
            self.write_context(LATEST)
            for relative in CONTEXT.RIG119_SUPPLEMENTS:
                path = self.root / relative
                original = path.read_bytes()
                target = self.root / 'outside-rig119-supplement'
                target.write_bytes(original)
                self.gate(self.raw, rejects=False, expected_context=LATEST)
                for fault in ('tampered', 'missing', 'symlink'):
                    with self.subTest(source=relative, fault=fault):
                        try:
                            path.unlink()
                            if fault == 'tampered':
                                path.write_bytes(original + b' ')
                            elif fault == 'symlink':
                                path.symlink_to(target)
                            self.gate(self.raw, rejects=True)
                        finally:
                            if path.exists() or path.is_symlink():
                                path.unlink()
                            path.write_bytes(original)
                    # Outside subTest: a failed restore green must stop the loop.
                    # No guarded input changes before the next fault.
                    self.gate(self.raw, rejects=False, expected_context=LATEST)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_every_rig119_historical_single_path_hybrid_rejects_and_restores(self):
        try:
            for historical in (ORIGINAL, CLOSEOUT, PRODUCT):
                for left, right in ((LATEST, historical), (historical, LATEST)):
                    self.write_context(left)
                    self.gate(self.raw, rejects=False, expected_context=left)
                    for name in self.original:
                        raw = self.snapshots[left][name]
                        other = self.snapshots[right][name]
                        if raw == other:
                            continue
                        with self.subTest(context=left, substituted=right, source=name):
                            try:
                                (self.root / name).write_bytes(other)
                                self.gate(self.raw, rejects=True)
                            finally:
                                (self.root / name).write_bytes(raw)
                        # Outside subTest: only a successful real restore green
                        # can authorize the next mutation of this same copy.
                        self.gate(self.raw, rejects=False, expected_context=left)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_all_fourteen_mixed_contexts_reject_at_actual_called_gate(self):
        names = list(json.loads((EXP / 'source-context-closeout-v1.json').read_bytes())['overrides'])
        try:
            self.write_context(ORIGINAL)
            self.gate(self.raw, rejects=False, expected_context=ORIGINAL)
            for choices in itertools.product((False, True), repeat=4):
                if all(choices) or not any(choices):
                    continue
                with self.subTest(closeout_files=choices):
                    for name, closeout in zip(names, choices):
                        (self.root / name).write_bytes((self.closeout if closeout else self.original)[name])
                    self.gate(self.raw, rejects=True)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_every_product_single_path_crossover_rejects_at_actual_called_gate(self):
        try:
            for historical in (ORIGINAL, CLOSEOUT):
                for left, right in ((PRODUCT, historical), (historical, PRODUCT)):
                    self.write_context(left)
                    self.gate(self.raw, rejects=False, expected_context=left)
                    for name, raw in self.snapshots[left].items():
                        other = self.snapshots[right][name]
                        if raw == other:
                            continue
                        with self.subTest(context=left, substituted=right, source=name):
                            (self.root / name).write_bytes(other)
                            self.gate(self.raw, rejects=True)
                            (self.root / name).write_bytes(raw)
        finally:
            self.write_context(PRODUCT)
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_all_complete_context_maps_and_every_mixture_reject_except_three_admitted(self):
        changing = list(self.original)
        variants = [sorted({json.dumps(files[name], sort_keys=True) for _, files in self.contexts})
                    for name in changing]
        accepted = rejected = 0
        for values in itertools.product(*variants):
            actual = dict(self.inputs)
            actual.update({name: json.loads(value) for name, value in zip(changing, values)})
            matching = [name for name, expected in self.contexts if actual == expected]
            if matching:
                self.assertEqual(CONTEXT.select_context(actual, self.contexts)[0], matching[0])
                accepted += 1
            else:
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)
                rejected += 1
        self.assertEqual((accepted, rejected), (3, 12285))
        for context, expected in self.contexts:
            for name in expected:
                actual = dict(expected)
                actual.pop(name)
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)
            for actual in ({}, dict(expected, unreviewed={'bytes': 0, 'sha256': '0' * 64})):
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)

    def corrupt_required_file(self, relative, label):
        path = self.exp / relative
        original = path.read_bytes()
        target = self.root / 'original-context-or-fixture'
        target.write_bytes(original)
        faults = ['missing', 'empty', 'corrupt', 'tampered', 'symlink']
        if relative.endswith('.json'):
            faults += ['empty-object', 'invalid-json']
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)
        for fault in faults:
            with self.subTest(file=label, fault=fault):
                path.unlink()
                try:
                    if fault == 'symlink':
                        path.symlink_to(target)
                    elif fault != 'missing':
                        path.write_bytes({'empty': b'', 'corrupt': bytes([original[0] ^ 1]) + original[1:],
                                          'empty-object': b'{}', 'invalid-json': b'{',
                                          'tampered': original + b' '}[fault])
                    self.gate(self.raw, rejects=True)
                finally:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.write_bytes(original)
            # Outside subTest: a failed restore green must stop the loop rather
            # than permit the next fault to reuse an unverified baseline.
            self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_context_manifest_missing_empty_corrupt_tampered_and_symlink_reject(self):
        for relative in (CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME, CONTEXT.RIG119_CONTEXT_NAME):
            self.corrupt_required_file(relative, relative)

    def test_historical_fixture_manifest_and_every_blob_fail_closed_at_actual_called_gate(self):
        self.corrupt_required_file(CONTEXT.FIXTURES_NAME, 'historical fixture manifest')
        manifest = json.loads((EXP / CONTEXT.FIXTURES_NAME).read_bytes())
        for context, items in manifest['contexts'].items():
            for name, item in items.items():
                self.corrupt_required_file(item['fixture'], context + ' ' + name)

    def test_undeclared_historical_fixture_rejects_at_actual_called_gate(self):
        path = self.exp / 'fixtures/source-contexts/unreviewed-source'
        try:
            path.write_bytes(b'unreviewed')
            self.gate(self.raw, rejects=True)
        finally:
            path.unlink()
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_compatibility_manifest_and_both_old_adapter_blobs_fail_closed_and_restore(self):
        self.corrupt_required_file(CONTEXT.COMPAT_FIXTURES_NAME, 'rig119 compatibility fixture manifest')
        manifest = json.loads((EXP / CONTEXT.COMPAT_FIXTURES_NAME).read_bytes())
        for name, item in manifest['files'].items():
            self.corrupt_required_file(item['fixture'], 'old shared adapter ' + name)

    def test_undeclared_compatibility_fixture_rejects_and_restores(self):
        path = self.exp / 'compat-fixtures-rig119/unreviewed-source'
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)
        try:
            path.write_bytes(b'unreviewed')
            self.gate(self.raw, rejects=True)
        finally:
            path.unlink()
        self.gate(self.raw, rejects=False, expected_context=PRODUCT)

    def test_original_manifest_cannot_be_replaced_with_complete_current_hashes(self):
        current = dict(self.inputs)
        for name, raw in self.current.items():
            current[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.gate(json.dumps(current).encode(), rejects=True)

    def test_original_manifest_symlink_rejects_at_actual_called_gate(self):
        path = self.exp / 'FROZEN-INPUTS.json'
        target = self.root / 'original-inputs.json'
        target.write_bytes(self.raw)
        path.unlink(missing_ok=True)
        try:
            path.symlink_to(target)
            self.gate(self.raw, rejects=True)
        finally:
            path.unlink()
            path.write_bytes(self.raw)

    def test_missing_and_symlink_source_inputs_reject_at_actual_called_gate(self):
        name = next(iter(self.current))
        path = self.root / name
        original = path.read_bytes()
        target = self.root / 'original-source.txt'
        target.write_bytes(original)
        try:
            path.unlink()
            self.gate(self.raw, rejects=True)
            path.symlink_to(target)
            self.gate(self.raw, rejects=True)
        finally:
            if path.exists() or path.is_symlink():
                path.unlink()
            path.write_bytes(original)

    def test_missing_manifest_rejects_without_skip(self):
        self.gate(None, rejects=True)

    def test_empty_manifest_rejects(self):
        self.gate(b'{}', rejects=True)

    def test_corrupt_manifest_rejects(self):
        name = next(iter(self.inputs))
        item = self.inputs[name]
        for raw in [b'', b'{', b'[]', b'null', b'{"input": null}',
                    json.dumps({name: {}}).encode(),
                    json.dumps({name: {'bytes': -1, 'sha256': 'bad'}}).encode(),
                    json.dumps({name: {'bytes': True, 'sha256': '0' * 64}}).encode(),
                    json.dumps({name: {**item, 'sha256': 'bad'}}).encode(),
                    json.dumps({name: {**item, 'sha256': '0' * 64}}).encode(),
                    json.dumps({name: {**item, 'bytes': item['bytes'] + 1}}).encode()]:
            with self.subTest(raw=raw):
                self.gate(raw, rejects=True)

    def test_changed_file_hash_and_size_reject(self):
        # Same-size corruption exercises SHA; truncation also exercises bytes.
        name = min(self.inputs, key=lambda key: self.inputs[key]['bytes'])
        path = self.root / name
        original = path.read_bytes()
        self.assertGreater(len(original), 0)
        try:
            for raw in [bytes([original[0] ^ 1]) + original[1:], original[:-1]]:
                with self.subTest(size=len(raw)):
                    path.write_bytes(raw)
                    self.gate(self.raw, rejects=True)
        finally:
            path.write_bytes(original)

    def test_z_protocol_and_legacy_contract_controls(self):
        # No child is launched by these vectors. Every vector calls the same
        # consumer that gate() uses for a freshly returned real CLI result.
        for case_id, rejects, context, code, stdout, stderr, fails in PARSER_CONTROLS:
            result = subprocess.CompletedProcess(['parser-only'], code, stdout, stderr)
            if fails:
                with self.assertRaises(AssertionError, msg=case_id):
                    assert_gate_result(self, result, rejects, context)
            else:
                assert_gate_result(self, result, rejects, context)
            self.event('parser', id=case_id, result='pass')

        manifest = self.exp / 'FROZEN-INPUTS.json'
        helper = self.exp / 'frozen_context.py'
        moved = self.exp / 'frozen_context.control-away'
        helper_raw = helper.read_bytes()
        source = self.root / next(iter(self.current))
        source_raw = source.read_bytes()
        source_mode = stat.S_IMODE(source.stat().st_mode)
        entry = 'def source_contexts(exp, raw, original, include_current=False):\n'
        self.assertEqual(helper_raw.count(entry.encode()), 1)

        def inject(body):
            helper.write_bytes(helper_raw.replace(entry.encode(), (entry + body).encode(), 1))

        def positive(case_id, legacy=False):
            result = self.launch(case_id, 'positive', 'legacy' if legacy else 'new',
                                 expected_context=PRODUCT)
            if legacy:
                self.legacy_result(result)
            else:
                assert_gate_result(self, result, False, PRODUCT)

        def unexpected(case_id, error, legacy=False, import_failure=False):
            result = self.launch(case_id, 'unexpected_error', 'legacy' if legacy else 'new')
            if legacy:
                self.legacy_result(result, error=error, import_failure=import_failure)
            else:
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual(result.stdout, '', result.stdout + result.stderr)
                self.assertIn('Traceback (most recent call last)', result.stderr)
                self.assertIn(error, result.stderr)

        try:
            positive('L01', legacy=True)
            try:
                manifest.write_bytes(b'{}')
                self.legacy_result(self.launch('L02', 'expected_rejection', 'legacy'), rejects=True)
            finally:
                manifest.write_bytes(self.raw)
            positive('L03', legacy=True)

            try:
                inject('    raise ValueError("CONTROL_PLAIN_VALUEERROR")\n')
                unexpected('L04', 'ValueError: CONTROL_PLAIN_VALUEERROR', legacy=True)
            finally:
                helper.write_bytes(helper_raw)
            positive('L05', legacy=True)

            try:
                helper.rename(moved)
                unexpected('L06', 'ModuleNotFoundError', legacy=True, import_failure=True)
            finally:
                if moved.exists():
                    moved.rename(helper)
            positive('L07', legacy=True)

            try:
                source.chmod(0)
                # This scheduled child must reach a real read permission error.
                # A host that bypasses it cannot claim complete acceptance.
                unexpected('L08', 'PermissionError', legacy=True)
            finally:
                source.chmod(source_mode)
                source.write_bytes(source_raw)
            positive('L09', legacy=True)

            try:
                inject('    raise ValueError("CONTROL_PLAIN_VALUEERROR")\n')
                unexpected('E01', 'ValueError: CONTROL_PLAIN_VALUEERROR')
            finally:
                helper.write_bytes(helper_raw)
            positive('E02')

            try:
                helper.rename(moved)
                unexpected('E03', 'ModuleNotFoundError')
            finally:
                if moved.exists():
                    moved.rename(helper)
            positive('E04')

            try:
                source.chmod(0)
                unexpected('E05', 'PermissionError')
            finally:
                source.chmod(source_mode)
                source.write_bytes(source_raw)
            positive('E06')

            result = self.launch('U01', 'cli_usage64', extra_args=('--invalid-control',))
            self.assertEqual(result.returncode, 64)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, 'usage: source_gate.py (no arguments)\n')

            try:
                inject('    import os, signal, sys\n'
                       '    print("CONTROL_SIGNAL_ENTERED", file=sys.stderr, flush=True)\n'
                       '    os.kill(os.getpid(), signal.SIGTERM)\n')
                result = self.launch('S01', 'expected_signal', expected_context=PRODUCT)
                self.assertEqual(result.returncode, -signal.SIGTERM)
                self.assertEqual(result.stdout, '')
                self.assertEqual(result.stderr, 'CONTROL_SIGNAL_ENTERED\n')
                with self.assertRaises(AssertionError):
                    assert_gate_result(self, result, False, PRODUCT)
            finally:
                helper.write_bytes(helper_raw)
            positive('S02')

            try:
                inject('    import os, sys, time\n'
                       '    print(f"CONTROL_TIMEOUT_ENTERED pid={os.getpid()}", file=sys.stderr, flush=True)\n'
                       '    time.sleep(60)\n')
                try:
                    self.launch('T01', 'expected_timeout', expected_context=PRODUCT)
                except subprocess.TimeoutExpired as error:
                    stdout = error.stdout
                    stderr = error.stderr
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode('ascii')
                    if isinstance(stderr, bytes):
                        stderr = stderr.decode('ascii')
                    self.assertIn(stdout, (None, ''), 'timeout cleanup UNKNOWN: unexpected stdout; STOP')
                    marker = re.fullmatch(r'CONTROL_TIMEOUT_ENTERED pid=([1-9][0-9]*)\n', stderr or '')
                    self.assertIsNotNone(marker, 'timeout cleanup UNKNOWN: invalid entered marker; STOP')
                    pid = int(marker.group(1))
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        self.event('cleanup', id='T01', pid=pid, result='absent')
                    except OSError as probe_error:
                        self.fail(f'timeout cleanup UNKNOWN: {probe_error}; STOP')
                    else:
                        self.fail('timeout cleanup UNKNOWN: PID present; STOP')
                else:
                    self.fail('T01 did not raise real TimeoutExpired; STOP')
            finally:
                helper.write_bytes(helper_raw)
            positive('T02')
        finally:
            # Always restore copied paths/bytes/modes, including interrupted or
            # UNKNOWN cleanup. No additional child is authorized by this block.
            if moved.exists():
                moved.rename(helper)
            helper.write_bytes(helper_raw)
            source.chmod(source_mode)
            source.write_bytes(source_raw)
            manifest.write_bytes(self.raw)


if __name__ == '__main__':
    unittest.main()
