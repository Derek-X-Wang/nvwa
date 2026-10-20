"""Red-capable actual-source controls plus independent patch result invariants."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import author_patch as author
import replay_prior
import verify_result
from derive_target import InvalidEvidence, verify_capture, raw_f32_hash

RETAINED=Path(os.environ['NVWA_SHOULDER_RETAINED'])

class ActualControls(unittest.TestCase):
    def test_known_actual_prior_new_pair_and_disabled_predicate_mutation(self):
        self.assertTrue(replay_prior.replay(RETAINED)['prior_corrected_pair_crosses'])
        with patch.object(replay_prior.old,'proper_cross',return_value=False):
            with self.assertRaisesRegex(InvalidEvidence,'known rejected new pair'):
                replay_prior.replay(RETAINED)

    def test_three_actual_source_proofs_pass_and_actual_normal_mutation_is_red(self):
        author.authenticate(RETAINED)
        e=json.loads((RETAINED/'h80proof-v1/combined/capture.json').read_text())
        contract=json.loads((RETAINED/'H80-SOURCE-CONTRACT-v1.json').read_text())
        verify_capture(e,'combined','h80proof-v1-combined',contract)
        e['frame']['full_base']['parts'][0]['normals'][0][0]+=0.25
        with self.assertRaises(InvalidEvidence):
            verify_capture(e,'combined','h80proof-v1-combined',contract)

    def test_actual_stale_last_witness_is_red(self):
        e=json.loads((RETAINED/'h80proof-v1/source_garment/capture.json').read_text())
        contract=json.loads((RETAINED/'H80-SOURCE-CONTRACT-v1.json').read_text())
        e['frame']['source_diagnostic']['Last_independent_witness']['update_epoch']-=1
        e['report']['source_diagnostic']=copy.deepcopy(e['frame']['source_diagnostic'])
        with self.assertRaisesRegex(InvalidEvidence,'same epoch'):
            verify_capture(e,'source_garment','h80proof-v1-source_garment',contract)

    def test_sealed_support_closure_and_single_target_vectors(self):
        policy,topology=author.frozen()
        self.assertEqual(len(topology['position_incident_triangles0']),26)
        self.assertEqual(len(topology['normal_source_ids']),21)
        self.assertEqual(len(topology['normal_accumulation_triangles0']),61)
        target_path=author.ROOT/'.work/shoulder-patch80/one-target-v1/target.json'
        self.assertEqual(author.digest(target_path),'fe1a413e2c46fbc82083f2f96e163407a5657ac8dec179a3e1eb9b7a97eb678b')
        target=json.loads(target_path.read_text())
        self.assertEqual([r['source_id'] for r in target['vectors']],policy['position_source_ids'])
        for r in target['vectors']:
            self.assertLessEqual(author.length(r['delta_clavicle_m']),policy['max_vector_m'])
        self.assertEqual([r['source_id'] for r in target['vectors'] if any(r['delta_clavicle_m'])],[212,830,847])

    def test_independent_rejection_audit_and_disabled_witness_mutation(self):
        report=author.ROOT/'.work/shoulder-patch80/evaluation-v1/report.json'
        self.assertEqual(verify_result.audit(report)['rejected_cases'],6)
        with patch.object(verify_result,'witnesses',return_value=[]):
            with self.assertRaisesRegex(ValueError,'audit invariant'):
                verify_result.audit(report)

if __name__=='__main__':unittest.main()
