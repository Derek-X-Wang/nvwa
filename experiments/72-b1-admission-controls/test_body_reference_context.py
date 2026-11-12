"""The body-reference successor admits exact new bytes and rejects mutations."""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('body_reference_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class BodyReferenceSourceContext(unittest.TestCase):
    def test_exact_successor_and_changed_file_rejection(self):
        pins = json.loads((HERE / 'pins.json').read_bytes())
        live = CONTEXT.check_source_context(ROOT, pins)
        self.assertEqual(live['id'], CONTEXT.UPPER_ARM_CONTEXT_ID)
        cpu = CONTEXT.cpu_source_context(pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        hip = CONTEXT._hip_context(HERE, upper)
        arm = CONTEXT._arm_context(HERE, hip)
        current = CONTEXT._body_reference_context(HERE, arm)
        self.assertEqual(current[0], CONTEXT.BODY_REFERENCE_CONTEXT_ID)
        self.assertEqual(len(current[1]), 525)
        with tempfile.TemporaryDirectory(prefix='nvwa-body-reference-context-') as directory:
            root = Path(directory)
            for name in current[1]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                before_hand = HERE / CONTEXT.HAND_FIXTURES / name
                shutil.copyfile(before_hand if before_hand.is_file() else ROOT / name, target)
            self.assertEqual(CONTEXT.check_source_context(root, pins)['id'],
                             CONTEXT.BODY_REFERENCE_CONTEXT_ID)
            for name in (CONTEXT.BODY_REFERENCE_CHANGED[0],
                         CONTEXT.BODY_REFERENCE_ADDED):
                target = root / name
                original = target.read_bytes()
                with self.subTest(name=name):
                    target.write_bytes(original + b'\n')
                    with self.assertRaisesRegex(ValueError, 'body reference source context'):
                        CONTEXT.check_source_context(root, pins)
                    target.write_bytes(original)
                    self.assertEqual(CONTEXT.check_source_context(root, pins)['id'],
                                     CONTEXT.BODY_REFERENCE_CONTEXT_ID)

    def test_contact_sheet_pins_source_and_cli_before_rendering(self):
        spec = importlib.util.spec_from_file_location(
            'body_reference_matrix', ROOT / 'scripts/render-body-reference.py')
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with tempfile.TemporaryDirectory(prefix='nvwa-body-reference-matrix-') as directory:
            root = Path(directory)
            work = root / 'source.json'
            original = json.dumps({'character': {'diagnostic_pose': 'neutral'},
                                   'stage': {'camera': {}}}).encode()
            work.write_bytes(original)
            cli = root / 'nvwa-cli'
            cli.write_bytes(b'original CLI')
            assets = root / 'assets'
            assets.mkdir()
            output = root / 'views'
            calls = []

            def fake_cli(command, **_kwargs):
                saved_work = Path(command[2])
                folder = Path(command[command.index('--output') + 1])
                folder.mkdir()
                png = b'image-' + str(len(calls)).encode()
                (folder / 'actual.png').write_bytes(png)
                (folder / 'receipt.json').write_text(json.dumps({
                    'mode': 'body_reference', 'parts': [['body', 1, 26756]],
                    'work_sha256': generator.digest(saved_work),
                    'png_sha256': generator.digest(folder / 'actual.png'),
                    'geometry_sha256': 'fixed geometry receipt',
                    'executable_sha256': generator.digest(cli),
                    'asset_sha256': {'mesh': 'fixed asset hash'},
                }))
                calls.append(folder.name)
                if len(calls) == 1:
                    work.write_bytes(b'replaced while rendering')
                return subprocess.CompletedProcess(command, 0, '', '')

            argv = ['render-body-reference.py', '--cli', str(cli), '--work', str(work),
                    '--assets', str(assets), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(generator.subprocess, 'run', fake_cli):
                generator.main()
            manifest = json.loads((output / 'matrix.json').read_text())
            self.assertEqual(calls, ['neutral-front', 'neutral-quarter',
                                     'neutral-side', 'neutral-back'])
            self.assertEqual((output / manifest['source_work']).read_bytes(), original)
            self.assertEqual(manifest['source_work_sha256'],
                             hashlib.sha256(original).hexdigest())
            self.assertEqual(manifest['cli_sha256'], generator.digest(cli))
            self.assertEqual(manifest['asset_sha256'], {'mesh': 'fixed asset hash'})

    def test_contact_sheet_rejects_mismatched_cli_receipt(self):
        spec = importlib.util.spec_from_file_location(
            'body_reference_matrix_mismatch', ROOT / 'scripts/render-body-reference.py')
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with tempfile.TemporaryDirectory(prefix='nvwa-body-reference-cli-') as directory:
            root = Path(directory)
            work = root / 'source.json'
            work.write_text(json.dumps({'character': {}, 'stage': {'camera': {}}}))
            cli = root / 'nvwa-cli'
            cli.write_bytes(b'original CLI')
            assets = root / 'assets'
            assets.mkdir()

            def fake_cli(command, **_kwargs):
                folder = Path(command[command.index('--output') + 1])
                folder.mkdir()
                (folder / 'actual.png').write_bytes(b'image')
                (folder / 'receipt.json').write_text(json.dumps({
                    'mode': 'body_reference', 'parts': [['body', 1, 26756]],
                    'work_sha256': generator.digest(Path(command[2])),
                    'png_sha256': generator.digest(folder / 'actual.png'),
                    'executable_sha256': 'wrong',
                }))
                return subprocess.CompletedProcess(command, 0, '', '')

            argv = ['render-body-reference.py', '--cli', str(cli), '--work', str(work),
                    '--assets', str(assets), '--output', str(root / 'views')]
            with patch.object(sys, 'argv', argv), patch.object(generator.subprocess, 'run', fake_cli):
                with self.assertRaisesRegex(RuntimeError, 'inconsistent body reference receipt'):
                    generator.main()
