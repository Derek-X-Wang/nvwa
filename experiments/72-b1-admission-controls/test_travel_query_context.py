"""Exercise the live 72 source selector against the exact travel-query delta."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest



def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setUpModule():
    # Run the original travel tests against the exact predecessor even when
    # contact-target is the current live source. All original assertions follow.
    global ROOT, HERE, EYE, RETAINED, MAIN, QUERY, TEST, V15_ASSET, INTEGRATION
    global MANIFEST, WAIST_SETUP, CONTROL_FILES, API, FROZEN
    from test_contact_target_context import source_tree
    tmp = tempfile.TemporaryDirectory(prefix='nvwa-travel-predecessor-')
    unittest.addModuleCleanup(tmp.cleanup)
    ROOT = Path(tmp.name).resolve()
    source_tree(ROOT, predecessor=True)
    HERE = ROOT / 'experiments/72-b1-admission-controls'
    EYE = ROOT / 'experiments/73-high-poly-eyes'
    RETAINED = HERE / 'pre-travel-query'
    MAIN = 'crates/nvwa-cli/src/main.rs'
    QUERY = 'crates/nvwa-cli/src/motion_query.rs'
    TEST = 'crates/nvwa-cli/tests/travel_query.rs'
    V15_ASSET = 'assets/characters/mpfb-b1-v15/manifest.json'
    INTEGRATION = HERE / 'integration_context.py'
    MANIFEST = HERE / 'input-context-travel-query-v1.json'
    WAIST_SETUP = HERE / 'test_waist_context.py'
    CONTROL_FILES = (
        MANIFEST,
        INTEGRATION,
        HERE / 'travel_query_source_context.py',
        HERE / 'test_travel_query_context.py',
        WAIST_SETUP,
        RETAINED / MAIN,
        RETAINED / QUERY,
    )
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
        self.assertEqual(self.selected['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(self.frozen[0], self.selected['id'])
        after = json.loads(MANIFEST.read_bytes())['after']
        self.assertEqual({name: self.selected['files'][name] for name in after},
                         {name: pin['sha256'] for name, pin in after.items()})
        self.assertEqual({name: self.frozen[1][name] for name in after}, after)
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

            # Any one successor input routes the same tree to travel
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

            for source in (INTEGRATION, WAIST_SETUP):
                target = root / source.relative_to(ROOT)
                target.symlink_to(root / 'missing-replay-control')
                try:
                    for cohort, gate in zip((72, 73), gates):
                        with self.subTest(cohort=cohort, dangling=source.name):
                            with self.assertRaisesRegex(ValueError, r'travel-query exact source: source bytes mismatch: crates/nvwa-cli/src/'):
                                gate()
                finally:
                    target.unlink()
