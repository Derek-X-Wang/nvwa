"""Actual WAIST source admission, historical crossovers and strict refusal/recovery."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('waist_73_context', HERE / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
sys.path.insert(0, str(HERE))
try:
    SPEC = importlib.util.spec_from_file_location('waist73_actual', HERE / 'test_prepare.py')
    ENTRY = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(ENTRY)
finally:
    sys.path.pop(0)

PRODUCT = ('assets/characters/mpfb-b1-v5/base.obj', 'assets/characters/mpfb-b1-v5/body.mhclo', 'assets/characters/mpfb-b1-v5/composite.json', 'assets/characters/mpfb-b1-v5/empty.macro', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.obj', 'assets/characters/mpfb-b1-v5/licenses/CC0-1.0.txt', 'assets/characters/mpfb-b1-v5/licenses/CHEEK-VOLUME-DERIVATION-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/LOWER-FACE-SQUARING-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/MPFB-LICENSE.md', 'assets/characters/mpfb-b1-v5/licenses/PARAMETER-SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/provenance.json', 'assets/characters/mpfb-b1-v5/manifest.json', 'assets/characters/mpfb-b1-v5/provenance/README.md', 'assets/characters/mpfb-b1-v5/provenance/cheek-volume-derivation.json', 'assets/characters/mpfb-b1-v5/provenance/chin-bones-source.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/parameter-source-receipt.json', 'assets/characters/mpfb-b1-v5/provenance/runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json', 'assets/characters/mpfb-b1-v5/provenance/waist-source-validation.json', 'assets/characters/mpfb-b1-v5/rig.game_engine.json', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-decr.target', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-incr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-decr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-incr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-decr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-incr.target', 'assets/characters/mpfb-b1-v5/vertex_groups.json', 'assets/characters/mpfb-b1-v5/weights.game_engine.json', 'crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/appearance.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-cli/tests/waist.rs', 'crates/nvwa-core/src/appearance.rs', 'crates/nvwa-core/src/b1.rs', 'crates/nvwa-core/tests/appearance.rs', 'crates/nvwa-core/tests/waist.rs', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'docs/agents/cpu-render.md', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')


class WaistSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (HERE / 'FROZEN-INPUTS.json').read_bytes()
        original = json.loads(raw)
        cpu = CONTEXT.cpu_source_context(HERE, raw, original)
        waist = CONTEXT._waist_context(HERE, cpu[1])
        reference = CONTEXT._reference_motion_context(HERE, cpu)
        retained = CONTEXT._combined_predecessors(HERE, waist, reference)
        cls.files = waist[1]
        cls.combined = CONTEXT._combined_context(HERE, cpu)
        cls.predecessors = retained
        cls.pre_leg = ROOT / 'experiments/72-b1-admission-controls/fixtures/pre-leg'
        temporary = tempfile.TemporaryDirectory(prefix='nvwa-waist-parent-')
        cls.addClassCleanup(temporary.cleanup)
        cls.waist_root = Path(temporary.name)
        for name in cls.files:
            dest = cls.waist_root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            old = retained['waist']
            historical = cls.pre_leg / name
            dest.write_bytes(old[name] if name in old else
                             historical.read_bytes() if historical.is_file() else
                             (ROOT / name).read_bytes())
        cls.retained = json.loads((HERE / 'fixtures/pre-waist/manifest.json').read_bytes())['files']

    def invoke_gate(self, root=None, exp=HERE):
        root = self.waist_root if root is None else root
        with patch.object(ENTRY, 'ROOT', root), patch.object(ENTRY, 'EXP', exp):
            ENTRY.SourceContract('test_frozen_source_inputs').test_frozen_source_inputs()

    def gate(self, root=None, exp=HERE, waist=True):
        root = self.waist_root if root is None else root
        self.invoke_gate(root, exp)
        self.assertEqual(CONTEXT.has_waist_inputs(root), waist)

    def copied(self, root, combined=False):
        files = self.combined[1] if combined else self.files
        source = ROOT if combined else self.waist_root
        for name in files:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            historical = self.pre_leg / name
            shutil.copyfile(historical if combined and historical.is_file()
                            else source / name, dest)
        exp = root / 'experiments' / HERE.name
        exp.mkdir(parents=True, exist_ok=True)
        for path in HERE.iterdir():
            if path.is_file():
                shutil.copyfile(path, exp / path.name)
        shutil.copytree(HERE / 'fixtures', exp / 'fixtures')
        return exp

    def test_actual_current_union_and_unchanged_historical_cohorts(self):
        self.gate()
        self.assertEqual(len(self.files), 391)
        raw = (HERE / 'FROZEN-INPUTS.json').read_bytes()
        original = json.loads(raw)
        self.assertEqual(len(original), 309)
        self.assertEqual(len(CONTEXT.source_contexts(HERE, raw, original)), 6)
        self.assertEqual(len(CONTEXT.admitted_source_contexts(HERE, raw, original)), 7)
        self.assertEqual(len(CONTEXT.current_source_contexts(HERE, raw, original)), 8)
        _, previous = CONTEXT.cpu_source_context(HERE, raw, original)
        self.assertEqual(len(previous), 324)
        self.assertEqual(set(CONTEXT.WAIST_NEW_FILES), set(PRODUCT) - set(self.retained))
        self.assertEqual(set(self.files), set(previous) | set(CONTEXT.WAIST_ADDITIONS))
        for name in set(previous) - set(PRODUCT):
            self.assertEqual(self.files[name], previous[name], name)
        # Real CI wiring: the opt-in integration target must run on the native path.
        script = (ROOT / 'experiments/27-ci-baseline/check.sh').read_text()
        command = 'cargo test -p nvwa-cli --features cpu-render,motion-query --test cpu_render --locked --offline -- --test-threads=1'
        self.assertEqual(script.count(command), 1)
        self.assertIn(command, script.split('  native)\n', 1)[1].split('    ;;', 1)[0])
        self.assertNotIn(command, script.split('  portable)\n', 1)[1].split('    ;;', 1)[0])

    def test_product_and_asset_boundary_faults_reject_and_recover(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-waist-context-') as directory:
            root = Path(directory) / 'source'
            exp = self.copied(root)
            self.gate(root, exp)
            # Every union leaf is hashed by the real gate. Fault injection covers all
            # changed code, endpoints, manifest, receipt and retained predecessor bytes.
            paths = [root / n for n in PRODUCT if not n.startswith('assets/') or n.endswith(('manifest.json', 'measure-waist-circ-decr.target', 'measure-waist-circ-incr.target', 'waist-circumference-source.json'))]
            paths += [exp / CONTEXT.WAIST_CONTEXT_NAME, exp / 'fixtures/pre-waist/manifest.json']
            paths += [exp / item['fixture'] for item in self.retained.values()]
            target = Path(directory) / 'original'
            for path in paths:
                raw = path.read_bytes()
                target.write_bytes(raw)
                for fault in ('missing', 'hash', 'size', 'symlink'):
                    with self.subTest(path=path.relative_to(root), fault=fault):
                        path.unlink()
                        try:
                            if fault == 'hash': path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                            elif fault == 'size': path.write_bytes(raw + b'\n')
                            elif fault == 'symlink': path.symlink_to(target)
                            with self.assertRaises((ValueError, AssertionError)):
                                self.invoke_gate(root, exp)
                        finally:
                            if path.exists() or path.is_symlink(): path.unlink()
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.gate(root, exp)
            extra = exp / 'fixtures/pre-waist/unreviewed'
            try:
                extra.write_bytes(b'unreviewed')
                with self.assertRaises((ValueError, AssertionError)):
                    self.invoke_gate(root, exp)
            finally:
                extra.unlink()
            self.gate(root, exp)

    def test_bidirectional_actual_gate_crossovers_and_missing_whole_extension(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-waist-crossover-') as directory:
            root = Path(directory)
            exp = self.copied(root)
            current = {n: (root / n).read_bytes() for n in PRODUCT}
            retained = {n: (exp / item['fixture']).read_bytes() for n, item in self.retained.items()}
            for name in PRODUCT:
                if name.startswith('assets/') and not name.endswith(('manifest.json', 'measure-waist-circ-decr.target', 'measure-waist-circ-incr.target')):
                    continue
                path = root / name
                try:
                    if name in retained: path.write_bytes(retained[name])
                    else: path.unlink()
                    with self.assertRaises((ValueError, AssertionError)):
                        self.invoke_gate(root, exp)
                finally:
                    path.write_bytes(current[name])
                self.gate(root, exp)
            for name in CONTEXT.WAIST_NEW_FILES:
                (root / name).unlink()
            with self.assertRaises((ValueError, AssertionError)):
                self.invoke_gate(root, exp)
            for name, data in retained.items():
                (root / name).write_bytes(data)
            self.gate(root, exp, waist=False)
            for name in PRODUCT:
                if name.startswith('assets/') and not name.endswith(('manifest.json', 'measure-waist-circ-decr.target', 'measure-waist-circ-incr.target')):
                    continue
                path = root / name
                try:
                    path.write_bytes(current[name])
                    with self.assertRaises((ValueError, AssertionError)):
                        self.invoke_gate(root, exp)
                finally:
                    if name in retained: path.write_bytes(retained[name])
                    else: path.unlink()
                self.gate(root, exp, waist=False)


    def test_combined_exact_union_and_refuses_mixture_and_drift(self):
        context, files = self.combined
        self.assertEqual(context, CONTEXT.COMBINED_CONTEXT_ID)
        self.assertEqual(set(files), set(self.files) | set(CONTEXT.REFERENCE_MOTION_ADDITIONS))
        self.assertEqual(len(files), 394)
        self.invoke_gate(ROOT)
        with tempfile.TemporaryDirectory(prefix='nvwa-combined-context-') as directory:
            root = Path(directory)
            exp = self.copied(root, combined=True)
            self.invoke_gate(root, exp)
            for predecessor in self.predecessors.values():
                for name, historical in predecessor.items():
                    path = root / name
                    current = path.read_bytes()
                    self.assertNotEqual(historical, current)
                    try:
                        path.write_bytes(historical)
                        with self.assertRaises((ValueError, AssertionError)):
                            self.invoke_gate(root, exp)
                    finally:
                        path.write_bytes(current)
                    self.invoke_gate(root, exp)

            # The manifest and exact fixture inventory also reject extra inputs.
            manifest = exp / CONTEXT.COMBINED_CONTEXT_NAME
            extra = exp / CONTEXT.COMBINED_FIXTURES / 'unreviewed'
            try:
                extra.write_bytes(b'unreviewed')
                with self.assertRaises((ValueError, AssertionError)):
                    self.invoke_gate(root, exp)
            finally:
                extra.unlink()
            self.invoke_gate(root, exp)

            added = [root / name for name in CONTEXT.REFERENCE_MOTION_ADDITIONS]
            retained = [exp / CONTEXT.COMBINED_FIXTURES / variant / name
                        for variant, paths in self.predecessors.items() for name in paths]
            for path in [*added, *retained, manifest]:
                current = path.read_bytes()
                for fault in ('missing', 'one-byte'):
                    with self.subTest(path=path.relative_to(root), fault=fault):
                        try:
                            if fault == 'missing':
                                path.unlink()
                            else:
                                path.write_bytes(bytes([current[0] ^ 1]) + current[1:])
                            with self.assertRaises((ValueError, AssertionError)):
                                self.invoke_gate(root, exp)
                        finally:
                            path.write_bytes(current)
                        self.invoke_gate(root, exp)


if __name__ == '__main__':
    unittest.main()
