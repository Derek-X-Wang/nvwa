"""Exact v9 source admission with immutable v8 predecessor bytes."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('arm_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class ArmProportionsSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        cls.predecessor = CONTEXT._hip_context(HERE, upper)
        cls.current = CONTEXT._arm_context(HERE, cls.predecessor)

    def test_exact_union_preserves_v8(self):
        self.assertEqual(self.predecessor[0], CONTEXT.HIP_CONTEXT_ID)
        self.assertEqual(len(self.predecessor[1]), 401)
        expected = CONTEXT.CHEST_CONTEXT_ID if CONTEXT.has_chest_inputs(ROOT) else CONTEXT.ARM_CONTEXT_ID
        self.assertEqual(CONTEXT.check_inputs(ROOT)['checked_input_context']['id'], expected)
        self.assertEqual({name for name in self.predecessor[1]
                          if self.current[1][name] != self.predecessor[1][name]},
                         set(CONTEXT.ARM_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_changed_source_asset_and_predecessor_pin_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-arm-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                historical = HERE / CONTEXT.CHEST_FIXTURES / name
                shutil.copyfile(historical if name in CONTEXT.CHEST_CHANGED and historical.is_file()
                                else ROOT / name, destination)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'], CONTEXT.ARM_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v9/manifest.json',
                         'assets/characters/mpfb-b1-v9/targets/measure-wrist-circ-incr.target'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.ARM_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'arm source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)

    def test_fixed_cc0_gzip_targets_expand_exactly(self):
        root = ROOT / CONTEXT.ARM_ASSET_PREFIX
        receipt = json.loads((root / 'provenance/arm-proportion-target-source.json').read_bytes())
        self.assertEqual(receipt['source_commit'], 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(len(receipt['files']), 6)
        for item in receipt['files']:
            folder = 'hands' if item['parameter'] == 'wrist_circumference' else 'arms'
            compressed = (root / 'provenance/source/data/targets' / folder / f"{item['name']}.target.gz").read_bytes()
            expanded = gzip.decompress(compressed)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), item['source_sha256'])
            self.assertEqual(len(compressed), item['source_bytes'])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), item['expanded_sha256'])
            self.assertEqual(len(expanded), item['expanded_bytes'])
            self.assertEqual((root / 'targets' / f"{item['name']}.target").read_bytes(), expanded)

    def test_length_targets_move_bilateral_elbow_and_hand_joint_helpers(self):
        root = ROOT / CONTEXT.ARM_ASSET_PREFIX
        groups = json.loads((root / 'vertex_groups.json').read_bytes())

        def helper(name):
            return [index for start, end in groups[name] for index in range(start, end + 1)]

        def movement(target, name):
            deltas = {}
            for line in (root / 'targets' / f'{target}.target').read_text().splitlines():
                if line and not line.startswith('#'):
                    index, *axes = line.split()
                    deltas[int(index)] = [float(axis) for axis in axes[:3]]
            indices = helper(name)
            return [sum(deltas.get(index, (0., 0., 0.))[axis] for index in indices) / len(indices)
                    for axis in range(3)]

        for stem, affected, fixed in (
            ('measure-upperarm-length', ('elbow', 'hand'), ('shoulder',)),
            ('measure-lowerarm-length', ('hand',), ('shoulder', 'elbow')),
        ):
            for sign in ('decr', 'incr'):
                target = f'{stem}-{sign}'
                for joint in affected:
                    left = movement(target, f'joint-l-{joint}')
                    right = movement(target, f'joint-r-{joint}')
                    self.assertGreater(sum(value * value for value in left), 0.001, target)
                    self.assertAlmostEqual(left[0], -right[0], places=6)
                    self.assertAlmostEqual(left[1], right[1], places=6)
                    self.assertAlmostEqual(left[2], right[2], places=6)
                for joint in fixed:
                    self.assertEqual(movement(target, f'joint-l-{joint}'), [0., 0., 0.])
                    self.assertEqual(movement(target, f'joint-r-{joint}'), [0., 0., 0.])
        for sign in ('decr', 'incr'):
            target = f'measure-wrist-circ-{sign}'
            for joint in ('shoulder', 'elbow', 'hand'):
                self.assertEqual(movement(target, f'joint-l-{joint}'), [0., 0., 0.])
                self.assertEqual(movement(target, f'joint-r-{joint}'), [0., 0., 0.])


if __name__ == '__main__':
    unittest.main()
