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
RETAINED = HERE / 'fixtures/pre-travel-query'
MAIN = 'crates/nvwa-cli/src/main.rs'
QUERY = 'crates/nvwa-cli/src/motion_query.rs'
TEST = 'crates/nvwa-cli/tests/travel_query.rs'
V15_ASSET = 'assets/characters/mpfb-b1-v15/manifest.json'

SPEC = importlib.util.spec_from_file_location('nvwa_test_travel_run72', HERE / 'run.py')
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class TravelQueryContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cls.selected = API.check_inputs(ROOT)['checked_input_context']

    def test_live_selection_and_historical_only_rejection(self):
        self.assertEqual(self.selected['id'], 'nvwa-travel-query-source-context-v1')
        self.assertEqual(len(self.selected['files']), 1423)
        self.assertEqual(self.selected['current_rust_execution'], 'NOT-RUN')
        with self.assertRaisesRegex(ValueError, 'travel-query exact source is not historical'):
            API.check_source_context(ROOT, self.pins, historical_only=True)

    def test_pending_and_forged_successors_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-travel-query-') as directory:
            root = Path(directory).resolve()
            for name in self.selected['files']:
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

            # Old query bytes select the original V15 gate. It must still
            # reject a tree that combines those bytes with successor controls.
            for name in (MAIN, QUERY):
                shutil.copyfile(RETAINED / name, root / name)
            (root / TEST).unlink()
            with self.assertRaisesRegex(ValueError, r'V15 exact source: source bytes mismatch: (experiments|scripts)/'):
                API.check_source_context(root, self.pins)
