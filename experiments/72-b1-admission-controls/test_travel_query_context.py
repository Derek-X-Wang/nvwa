"""Exercise the live 72 source selector against the exact travel-query delta."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EYE = ROOT / 'experiments/73-high-poly-eyes'
RETAINED = HERE / 'fixtures/pre-travel-query'
MAIN = 'crates/nvwa-cli/src/main.rs'
QUERY = 'crates/nvwa-cli/src/motion_query.rs'
TEST = 'crates/nvwa-cli/tests/travel_query.rs'
V15_ASSET = 'assets/characters/mpfb-b1-v15/manifest.json'
CONTROL_FILES = (
    HERE / 'input-context-travel-query-v1.json',
    HERE / 'travel_query_source_context.py',
    HERE / 'test_travel_query_context.py',
    RETAINED / MAIN,
    RETAINED / QUERY,
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


API = load('nvwa_test_travel_run72', HERE / 'run.py')
FROZEN = load('nvwa_test_travel_frozen73', EYE / 'frozen_context.py')


class TravelQueryContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cls.selected = API.check_inputs(ROOT)['checked_input_context']
        raw = (EYE / 'FROZEN-INPUTS.json').read_bytes()
        original = json.loads(raw)
        contexts = FROZEN.current_source_contexts(EYE, raw, original)
        running = FROZEN._running_source_context(EYE, original, contexts)
        query = FROZEN._motion_query_source_context(EYE, running)
        cls.cpu = FROZEN._cpu_context(EYE, query[1])
        cls.frozen = FROZEN.integration_source_context(EYE, cls.cpu, ROOT)

    def test_live_selection_and_historical_only_rejection(self):
        self.assertEqual(self.selected['id'], 'nvwa-travel-query-source-context-v1')
        self.assertEqual(len(self.selected['files']), 1423)
        self.assertEqual(self.selected['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(self.frozen[0], self.selected['id'])
        self.assertEqual(len(self.frozen[1]), 1709)
        with self.assertRaisesRegex(ValueError, 'travel-query exact source is not historical'):
            API.check_source_context(ROOT, self.pins, historical_only=True)

    def test_pending_and_forged_successors_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-travel-query-') as directory:
            root = Path(directory).resolve()
            for name in self.selected['files'].keys() | self.frozen[1].keys():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)

            (root / TEST).unlink()
            with self.assertRaisesRegex(ValueError, 'missing/nonregular: ' + re.escape(TEST)):
                API.check_source_context(root, self.pins)
            shutil.copyfile(ROOT / TEST, root / TEST)

            for name in (MAIN, QUERY):
                with self.subTest(predecessor_file=name):
                    shutil.copyfile(RETAINED / name, root / name)
                    with self.assertRaisesRegex(ValueError, 'source bytes mismatch: ' + re.escape(name)):
                        API.check_source_context(root, self.pins)
                    shutil.copyfile(ROOT / name, root / name)

            (root / V15_ASSET).write_bytes((root / V15_ASSET).read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'source bytes mismatch: ' + re.escape(V15_ASSET)):
                API.check_source_context(root, self.pins)
            shutil.copyfile(ROOT / V15_ASSET, root / V15_ASSET)

            (root / QUERY).unlink()
            (root / QUERY).symlink_to(ROOT / QUERY)
            with self.assertRaisesRegex(ValueError, 'symlink: ' + re.escape(QUERY)):
                API.check_source_context(root, self.pins)
            (root / QUERY).unlink()

            # Remove successor additions and restore both V15 CLI files. The
            # inherited gates still reject the ordinary control byte drift.
            for name in (MAIN, QUERY):
                shutil.copyfile(RETAINED / name, root / name)
            (root / TEST).unlink()
            for source in CONTROL_FILES:
                (root / source.relative_to(ROOT)).unlink(missing_ok=True)
            gates = (lambda: API.check_source_context(root, self.pins),
                     lambda: FROZEN.integration_source_context(EYE, self.cpu, root))
            for gate in gates:
                with self.assertRaisesRegex(ValueError, r'V15 exact source: source bytes mismatch: (experiments|scripts)/'):
                    gate()

            # Any one successor-only file routes the same tree to travel
            # admission, which must reject the V15 product bytes.
            for source in (*CONTROL_FILES, ROOT / TEST):
                relative = source.relative_to(ROOT)
                target = root / relative
                shutil.copyfile(source, target)
                try:
                    for cohort, gate in zip((72, 73), gates):
                        with self.subTest(cohort=cohort, retained_only=relative):
                            with self.assertRaisesRegex(ValueError, r'travel-query exact source: source bytes mismatch: crates/nvwa-cli/src/'):
                                gate()
                finally:
                    target.unlink()
