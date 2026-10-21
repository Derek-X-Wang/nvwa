"""Synthetic generator admission controls. No source planes or candidate assets."""
import argparse
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate as g


class AdmissionControls(unittest.TestCase):
    def test_execution_failure_precedes_other_admission(self):
        args = argparse.Namespace(freeze=Path('synthetic-freeze'),
                                  policy=Path('must-not-read'), preflight=Path('must-not-read'))
        # create=True keeps this order control portable while the independent
        # evaluator supplies verify_execution. It does not test its implementation.
        with patch.object(g, 'load', return_value={}) as read, \
             patch.object(g.engine, 'verify_execution', create=True,
                          side_effect=ValueError('synthetic missing execution receipt')) as verify, \
             patch.object(g.engine, 'authenticate_hybrid') as authenticate, \
             patch.object(g.engine, 'baseline_preflight') as baseline, \
             patch.object(g.engine, 'candidate_part') as candidate:
            with self.assertRaisesRegex(ValueError, 'missing execution receipt'):
                g.admission(args)
            read.assert_called_once_with(args.freeze)
            verify.assert_called_once_with({})
            authenticate.assert_not_called()
            baseline.assert_not_called()
            candidate.assert_not_called()

    def test_missing_go_stops_after_execution_verification(self):
        args = argparse.Namespace(freeze=Path('synthetic-freeze'))
        with patch.object(g, 'load', return_value={}) as read, \
             patch.object(g.engine, 'verify_execution', create=True, return_value=None) as verify, \
             patch.object(g.engine, 'authenticate_hybrid') as authenticate:
            with self.assertRaisesRegex(ValueError, 'root authoring GO missing'):
                g.admission(args)
            read.assert_called_once_with(args.freeze)
            verify.assert_called_once_with({})
            authenticate.assert_not_called()

    def test_existing_attempt_directory_is_preserved_before_sampling(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'already-attempted'
            out.mkdir()
            sentinel = out / 'authoring-receipt.json'
            original = b'{"status":"REJECTED_PRIOR_ATTEMPT"}\n'
            sentinel.write_bytes(original)
            args = argparse.Namespace(out=out)
            # Admission is synthetic; no actual corpus or asset is read.
            with patch.object(g, 'admission', return_value=({}, {}, {}, [], {}, [])), \
                 patch.object(g.engine, 'raw_cage') as cage, \
                 patch.object(g, 'nearest_plane') as plane, \
                 patch.object(g.engine, 'candidate_part') as candidate:
                with self.assertRaisesRegex(ValueError, 'attempt directory exists'):
                    g.attempt(args)
                cage.assert_not_called()
                plane.assert_not_called()
                candidate.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['authoring-receipt.json'])


if __name__ == '__main__':
    unittest.main()
