"""Provenance mutation controls through the actual historical comparison CLI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

p = argparse.ArgumentParser()
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--prepared', type=Path, required=True)
p.add_argument('--scratch', type=Path, required=True)
a, rest = p.parse_known_args()
sys.argv = [sys.argv[0], *rest]


class Controls(unittest.TestCase):
    def invoke(self, reference, prepared, output):
        flags = ['-B'] + (['-O'] if sys.flags.optimize else [])
        return subprocess.run([sys.executable, *flags, str(Path(__file__).with_name('historical_reference.py')),
            '--reference', str(reference), '--prepared', str(prepared), '--out', str(output)],
            capture_output=True, text=True)

    def test_authenticated_actual_static_reference(self):
        with tempfile.TemporaryDirectory(dir=a.scratch) as temporary:
            r = self.invoke(a.reference, a.prepared, Path(temporary) / 'report.json')
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_changed_reference_coordinates_rejected_by_actual_cli(self):
        with tempfile.TemporaryDirectory(dir=a.scratch) as temporary:
            temporary = Path(temporary)
            reference = temporary / 'reference'
            reference.mkdir()
            shutil.copy2(a.reference / 'summary.json', reference / 'summary.json')
            original = json.loads((a.reference / 'body-positive.json').read_text())
            original['garment_positions'][246][0] += .01
            (reference / 'body-positive.json').write_text(json.dumps(original))
            r = self.invoke(reference, a.prepared, temporary / 'report.json')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('retained original-tool result hash differs', r.stderr)
            self.assertFalse((temporary / 'report.json').exists())

    def test_changed_prepared_capture_rejected_by_actual_cli(self):
        with tempfile.TemporaryDirectory(dir=a.scratch) as temporary:
            temporary = Path(temporary)
            prepared = temporary / 'inputs.json'
            shutil.copy2(a.prepared.with_name('preparation.json'), temporary / 'preparation.json')
            packet = json.loads(a.prepared.read_text())
            packet['cases'][0]['garment_rest']['246'][0] += .01
            prepared.write_text(json.dumps(packet))
            r = self.invoke(a.reference, prepared, temporary / 'report.json')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('prepared inputs changed', r.stderr)
            self.assertFalse((temporary / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
