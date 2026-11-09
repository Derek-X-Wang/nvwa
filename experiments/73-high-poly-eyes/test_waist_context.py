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
        cls.files = json.loads((HERE / CONTEXT.WAIST_CONTEXT_NAME).read_bytes())['files']
        cls.retained = json.loads((HERE / 'fixtures/pre-waist/manifest.json').read_bytes())['files']

    def invoke_gate(self, root=ROOT, exp=HERE):
        with patch.object(ENTRY, 'ROOT', root), patch.object(ENTRY, 'EXP', exp):
            ENTRY.SourceContract('test_frozen_source_inputs').test_frozen_source_inputs()

    def gate(self, root=ROOT, exp=HERE, waist=True):
        self.invoke_gate(root, exp)
        self.assertEqual(CONTEXT.has_waist_inputs(root), waist)

    def copied(self, root):
        for name in self.files:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
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


if __name__ == '__main__':
    unittest.main()
