"""The 73 frozen-source consumer admits only the exact v14 successor."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from frozen_context import (FOREARM_CONTEXT_ID, UPPER_ARM_CHANGED,
                            UPPER_ARM_CONTEXT_ID, upper_arm_source_context,
                            _cpu_context)
from frozen_context import (LEVEL1_CONTEXT_ID, LEVEL1_CHANGED, LEVEL1_ADDED,
                            level1_source_context, pre_level1_file,
                            CLI_LEVEL1_CONTEXT_ID, CLI_LEVEL1_CHANGED,
                            cli_level1_source_context, pre_cli_level1_file,
                            CLI_LEVEL1_CONTEXT_NAME, CLI_LEVEL1_FIXTURES,
                            _cli_level1_context)

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
            source = pre_level1_file(path)
            self.assertTrue(source.is_file(), path)
            self.assertEqual(source.stat().st_size, expected['bytes'], path)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'], path)
        successor, current = level1_source_context(HERE, cpu)
        self.assertEqual(successor, LEVEL1_CONTEXT_ID)
        self.assertEqual(len(current), 1418)
        self.assertEqual({p for p in files if current[p] != files[p]}, set(LEVEL1_CHANGED))
        self.assertEqual(set(current) - set(files), set(LEVEL1_ADDED))
        for path, expected in current.items():
            source = pre_cli_level1_file(path)
            self.assertTrue(source.is_file(), path)
            self.assertEqual(source.stat().st_size, expected['bytes'], path)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'], path)
        cli_successor, cli_current = cli_level1_source_context(HERE, cpu)
        self.assertEqual(cli_successor, CLI_LEVEL1_CONTEXT_ID)
        self.assertEqual(len(cli_current), 1418)
        self.assertEqual({p for p in current if cli_current[p] != current[p]},
                         set(CLI_LEVEL1_CHANGED))
        for path, expected in cli_current.items():
            source = ROOT / path
            self.assertTrue(source.is_file(), path)
            self.assertEqual(source.stat().st_size, expected['bytes'], path)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'], path)
        with tempfile.TemporaryDirectory(prefix='nvwa-73-cli-level1-context-') as directory:
            exp = Path(directory) / '73-high-poly-eyes'
            exp.mkdir()
            manifest = exp / CLI_LEVEL1_CONTEXT_NAME
            manifest.parent.mkdir(parents=True)
            shutil.copyfile(HERE / CLI_LEVEL1_CONTEXT_NAME, manifest)
            for name in CLI_LEVEL1_CHANGED:
                fixture = exp / CLI_LEVEL1_FIXTURES / name
                fixture.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pre_cli_level1_file(name), fixture)
            self.assertEqual(_cli_level1_context(exp, (successor, current))[0],
                             CLI_LEVEL1_CONTEXT_ID)
            original = manifest.read_bytes()
            manifest.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'manifest identity mismatch'):
                _cli_level1_context(exp, (successor, current))
            manifest.write_bytes(original)
            fixture = exp / CLI_LEVEL1_FIXTURES / CLI_LEVEL1_CHANGED[0]
            fixture.write_bytes(fixture.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'predecessor bytes mismatch'):
                _cli_level1_context(exp, (successor, current))


if __name__ == '__main__':
    unittest.main()
