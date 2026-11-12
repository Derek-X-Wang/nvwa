"""The 73 frozen-source consumer admits only the exact v14 successor."""
import hashlib
import json
from pathlib import Path
import unittest

from frozen_context import (FOREARM_CONTEXT_ID, UPPER_ARM_CHANGED,
                            UPPER_ARM_CONTEXT_ID, upper_arm_source_context,
                            _cpu_context)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class UpperArmMuscleContext(unittest.TestCase):
    def test_exact_successor_and_predecessor_bytes(self):
        frozen = json.loads((HERE / 'FROZEN-INPUTS.json').read_bytes())
        from frozen_context import _motion_query_source_context, _running_source_context, current_source_contexts
        contexts = current_source_contexts(HERE, (HERE / 'FROZEN-INPUTS.json').read_bytes(), frozen)
        cpu = _cpu_context(HERE, _motion_query_source_context(HERE, _running_source_context(HERE, frozen, contexts))[1])
        context, files = upper_arm_source_context(HERE, cpu)
        self.assertEqual(context, UPPER_ARM_CONTEXT_ID)
        self.assertEqual(len(files), 1416)
        self.assertEqual({p for p in UPPER_ARM_CHANGED if p in files}, set(UPPER_ARM_CHANGED))
        for path, expected in files.items():
            source = ROOT / path
            self.assertTrue(source.is_file(), path)
            self.assertEqual(source.stat().st_size, expected['bytes'], path)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'], path)


if __name__ == '__main__':
    unittest.main()
