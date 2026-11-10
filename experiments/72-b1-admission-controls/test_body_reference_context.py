"""The body-reference successor admits exact new bytes and rejects mutations."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('body_reference_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class BodyReferenceSourceContext(unittest.TestCase):
    def test_exact_successor_and_changed_file_rejection(self):
        pins = json.loads((HERE / 'pins.json').read_bytes())
        current = CONTEXT.check_source_context(ROOT, pins)
        self.assertEqual(current['id'], CONTEXT.BODY_REFERENCE_CONTEXT_ID)
        self.assertEqual(len(current['files']), 525)
        with tempfile.TemporaryDirectory(prefix='nvwa-body-reference-context-') as directory:
            root = Path(directory)
            for name in current['files']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
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
