"""CLI Level 1 successor preserves the merged display source identity."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('cli_level1_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class CliLevel1Context(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        hip = CONTEXT._hip_context(HERE, upper)
        arm = CONTEXT._arm_context(HERE, hip)
        body = CONTEXT._body_reference_context(HERE, arm)
        hand = CONTEXT._hand_context(HERE, body)
        shoulder = CONTEXT._shoulder_context(HERE, hand)
        forearm = CONTEXT._forearm_context(HERE, shoulder)
        muscle = CONTEXT._upper_arm_context(HERE, forearm)
        cls.previous = CONTEXT._level1_context(HERE, muscle)
        cls.current = CONTEXT._cli_level1_context(HERE, cls.previous)

    def test_exact_six_file_successor_and_live_source(self):
        self.assertEqual(self.previous[0], CONTEXT.LEVEL1_CONTEXT_ID)
        self.assertEqual(self.current[0], CONTEXT.CLI_LEVEL1_CONTEXT_ID)
        self.assertEqual(len(self.current[1]), len(self.previous[1]))
        self.assertEqual({p for p in self.previous[1]
                          if self.current[1][p] != self.previous[1][p]},
                         set(CONTEXT.CLI_LEVEL1_CHANGED))
        self.assertEqual(CONTEXT.check_source_context(ROOT, self.pins)['id'],
                         CONTEXT.CLI_LEVEL1_CONTEXT_ID)

    def test_manifest_and_historical_fixtures_are_pinned(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-cli-level1-context-') as directory:
            exp = Path(directory)
            manifest = exp / CONTEXT.CLI_LEVEL1_CONTEXT_NAME
            shutil.copyfile(HERE / CONTEXT.CLI_LEVEL1_CONTEXT_NAME, manifest)
            for name in CONTEXT.CLI_LEVEL1_CHANGED:
                fixture = exp / CONTEXT.CLI_LEVEL1_FIXTURES / name
                fixture.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(CONTEXT.pre_cli_level1_file(name), fixture)
            self.assertEqual(CONTEXT._cli_level1_context(exp, self.previous)[0],
                             CONTEXT.CLI_LEVEL1_CONTEXT_ID)
            original = manifest.read_bytes()
            manifest.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'manifest identity mismatch'):
                CONTEXT._cli_level1_context(exp, self.previous)
            manifest.write_bytes(original)
            fixture = exp / CONTEXT.CLI_LEVEL1_FIXTURES / CONTEXT.CLI_LEVEL1_CHANGED[0]
            fixture.write_bytes(fixture.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'predecessor bytes mismatch'):
                CONTEXT._cli_level1_context(exp, self.previous)


if __name__ == '__main__':
    unittest.main()
